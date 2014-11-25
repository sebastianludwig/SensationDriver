#!/usr/bin/env ruby

require 'time'

# change if necessary
#------------------------------------------
MOTOR_MIN_INTENSITY = 0.3
MAPPING_CURVE_DEGREE = 1.5
#------------------------------------------


def select_file(kind, pattern)
    logs = Dir.glob(pattern).sort
    if logs.size == 0
        raise "No #{kind.downcase} logs found with pattern #{pattern} in #{Dir.pwd}"
    elsif logs.size == 1
        return logs[0]
    else
        puts "\n#{kind.capitalize} logs:"
        logs.each_with_index { |file, index| puts "#{index}\t#{File.basename(file)}" }
        print "\nSelect #{kind.downcase} log: "
        return logs[STDIN.gets.strip.to_i]
    end
end

PATTERNS = {
    # probe;1416835751492;3;0
    probe: /(?<time>\d{13});(?<actor>\d+);(?<intensity>[\d\.]+)/,
    # send;1416835751495;{ Message: Type = Vibration; Vibration = { Vibration: TargetRegion = Chest; ActorIndex = 3; Intensity = 0; Priority = 0; }; MuscleStimulation = null; LoadPattern = null; PlayPattern = null; }
    send: /(?<time>\d{13}).+ActorIndex = (?<actor>\d+); Intensity = (?<intensity>[\d\.]+)/,
    # parse;1416835753996;type: VIBRATION;vibration {;  target_region: CHEST;  actor_index: 3;  intensity: 0.9011609554290771;  priority: 0;};
    parse: /(?<time>\d{13}).+actor_index: (?<actor>\d+);\s*intensity: (?<intensity>[\d\.]+)/,
    # process;1416835753981;target_region: BACK;actor_index: 11;intensity: 0.007905662059783936;priority: 0;
    process: /(?<time>\d{13}).+actor_index: (?<actor>\d+);\s*intensity: (?<intensity>[\d\.]+)/,
    # set_pwm;1416835753981;11;0.5
    set_pwm: /(?<time>\d{13});(?<actor>\d+);(?<intensity>[\d\.]+)/,
    # set_intensity;1416835753981;3;0.9039502143859863;0;0.9016096698202323;direct
    # set_intensity;1416835753981;11;0.007905662059783936;0;0.30049204566357335;delayed;0.2
    set_intensity: /(?<time>\d{13});(?<actor>\d+);(?<intensity>[-\d\.e]+);(?<priority>[\d\.]+);(?<target_intensity>[\d\.]+);(?<mode>[a-z]+)(;(?<delay>[\d\.]+))?/
}

def reverse_map_intensity(intensity)
    ((intensity - MOTOR_MIN_INTENSITY) / (1 - MOTOR_MIN_INTENSITY)) ** (1/MAPPING_CURVE_DEGREE)
end

def parse_line(action, line)
    match = PATTERNS[action].match(line)
    raise "Pattern for #{action.inspect} not matching \"#{line}\"" unless match
    if action == :set_intensity
        command = {
            action: action,
            time: match[:time].to_i,
            actor: match[:actor].to_i,
            intensity: match[:intensity].to_f,
            target_intensity: match[:target_intensity].to_f,
            mode: match[:mode].to_sym,
            delay: match[:delay].to_f / 10000,
        }
    else
        command = {
            action: action,
            time: match[:time].to_i,
            actor: match[:actor].to_i,
            intensity: match[:intensity].to_f
        }
    end
    if action == :set_pwm
        command[:mapped_intensity] = command[:intensity]
        command[:intensity] = reverse_map_intensity(command[:intensity]) if command[:intensity] > 0.0000001
    end
    command[:intensity] = command[:intensity].round(7)
    command
end

def parse_file(path)
    action = /[a-z_]+/
    IO.foreach(path).map { |line| send(:parse_line, action.match(line)[0].to_sym, line) }
end


# the action starts here
#------------------------------------------
puts "This script calulates with \nmotor_min_intensity = #{MOTOR_MIN_INTENSITY}\nmapping_curve_degree = #{MAPPING_CURVE_DEGREE}\nIf these are not the values your motors are running on, change them in the script.\n\n"

commands = parse_file select_file('client', 'sensation_profile*')
commands += parse_file select_file('server', 'sensation_server_profile*')

#------------------------------------------

puts "Read #{commands.size} commands..."

# [[all command to actor 0], [all commands to actor 1], ...]
grouped_by_actor = commands.group_by { |command| command[:actor] } .values

COMMAND_ORDER = {
    probe: 0,
    send: 1, 
    parse: 2, 
    process: 3,
    set_intensity: 4,
    set_pwm: 5
}

# [[[all commands to 0 with intensity x], [all command to 0 with intensity y], [all command to ...]], [...]]
grouped_by_actor.map! do |actor_commands| 
    commands_grouped_by_intensity = actor_commands.group_by { |command| command[:intensity] }.values
    # sort entries in each group by time and command precendence
    commands_grouped_by_intensity.map do |intensity_group| 
        intensity_group.sort_by { |command| [command[:time], COMMAND_ORDER[command[:action]]] }
    end
end

grouped_by_actor_and_intensity = grouped_by_actor.reduce(:+)

def split_by_time_coherence(actor_intensity_commands)
    return [actor_intensity_commands]
    time_buckets = []
    last_timestamp = 0
    actor_intensity_commands.each do |entry|
        time_buckets << [] if (entry[:time] - last_timestamp).abs > 250
        time_buckets.last << entry
        last_timestamp = entry[:time]
    end
    time_buckets
end

grouped_by_actor_and_intensity.map! do |actor_intensity_commands|
    split_by_time_coherence(actor_intensity_commands)
end

# split_by_time_coherence introduced sub arrays -> level them out
# [[<probe>, <send>, ...], [<probe>, <send>, ...], ...] - each and every <?> is a hash created by parse_line
command_sequences = grouped_by_actor_and_intensity.reduce(:+)

puts "Grouped into #{command_sequences.size} sequences..."

# preparation done :-)
#------------------------------------------


# get rid of dirty sequences (a normal sequence is: probe - send - parse - process - set_intensity - set_pwm)
REGULAR_COMMAND_SEQUENCE = [:probe, :send, :parse, :process, :set_intensity, :set_pwm]
command_sequences.reject! { |commands| commands.map { |c| c[:action] } != REGULAR_COMMAND_SEQUENCE } 

puts "Rejected 'malformed' sqeuences - #{command_sequences.size} sequences remaining..."


# turn sequences into a single hash with all the information combined {actor: 3, intensity: 0.710, probe: 1416867348512, send:.., parse:.., process:..., set_intensity:..., set_pwm:..., target_intensity:..., mode: :direct, delay: 0.0, mapped_intensity: 0.719})
command_sequences.map! do |commands|
    commands.map { |c| Hash[c[:action] => c[:time]].merge(c.select {|k,| k != :action and k != :time }) }.reduce(:merge)
end


def csv(command_sequences, filename)
    field_order = [:actor, :intensity, :probe, :send, :parse, :process, :set_intensity, :set_pwm, :delay]
    File.open(filename, 'w') do |file|
        file.write(field_order.map { |field| field.capitalize }.join(';') + "\n")
        command_sequences.each do |commands|
            file.write(field_order.map { |field| commands[field].to_s.sub(/\./, ',') }.join(';') + "\n")
        end
    end
end


# output = []
# command_sequences.each do |commands|
#     output << commands
# end
# `echo "#{output.join("\n")}" > profile_temp3.js`


csv_file = "profile_#{Time.now().strftime('%Y%m%d_%H%M')}.csv"
puts "Writing output to #{csv_file}..."
csv(command_sequences, csv_file)


puts "Done!"








