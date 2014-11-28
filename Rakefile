#encoding: utf-8


# call rake -T get a list of all invocable tasks
# call rake all=true -T to get all tasks
# call rake [all=true] -D to get a little bit more description

require 'time'
require 'rb-fsevent'
require 'colorize'
require 'json'
require 'open3'
require 'thread'

PI_HOSTNAME = "sensationdriver.local"
PI_USER = 'pi'
SERVER_LOG_PATH = File.join('log', 'server.log')
PYTHON = 'python3.4'
DAEMON_SCRIPT = 'sensation_daemon.sh'

class RemoteTask
    attr_reader :name, :local_task, :remote_task

    @@tasks = []

    def self.create(scope, name, &definition)
        @@tasks << RemoteTask.new(scope, name, &definition)
    end

    def self.tasks;; @@tasks end

    def initialize(scope, name, &definition)
        @scope = scope
        @name = name
        @description = ''
        instance_eval(&definition)
    end

    def scope(destination)
        destination == :remote ? ['remote'] + @scope : @scope.dup
    end

    def description(destination)
        if destination == :remote and (!is_raspberry? or ENV['all'])
            return @description + " on the Raspberry"
        elsif destination == :local and ((@local_only_on_pi and is_raspberry?) or ENV['all'])
            return @description
        end
    end

    def desc(text)
        @description = text
    end

    def local(options = {}, &task)
        @local_only_on_pi = options.fetch :pi_only, false

        @local_task = Proc.new do
            raise "Only supported on Raspberry Pi" if @local_only_on_pi and !is_raspberry?
            task.call()
        end
    end

    def remote(&task)
        @remote_task = Proc.new do
            raise "Not supported on Raspberry Pi" if is_raspberry?
            task.call()
        end
    end

    def backticks(command, options = {})
        local(pi_only: options.fetch(:local_only_on_pi, false)) { puts backtick(command) }
        remote { puts ssh_backtick(command) }
    end
end


def remote_task(name, &definition)
    scope = Rake.application().instance_eval { current_scope.path }
    scope = scope.split(':')

    RemoteTask.create(scope, name, &definition)
end

def sibling_path(*components)
    File.join(File.dirname(__FILE__), components)
end

def terminal_title(title)
    `/bin/bash -c 'echo -n -e \"\033]0;#{title}\007\" > /dev/tty'`
end

def remote_project_path
    "/home/pi/projects/#{File.basename(File.dirname(__FILE__))}"
end

def is_raspberry?
  `uname` == "Linux\n"
end

def backtick(command)
    command += " 2>&1"
    output = `#{command}`
    if output.include? 'Could not resolve hostname'
        puts "First attampt to resolve hostname failed - retry.."
        output = `#{command}`
        raise output if output.include? 'Could not resolve hostname'
    end
    return output
end

def ssh_command(command = '')
    ssh_command = "ssh #{PI_USER}@#{PI_HOSTNAME}"
    ssh_command += " '#{command}'" if command and !command.empty?
    ssh_command
end

def ssh_backtick(command)
    backtick(ssh_command(command))
end

namespace :dependencies do
    desc "Install python package dependencies through pip."
    task :install do
        command = "#{PYTHON} -m pip install -r #{sibling_path('requirements.txt')}"
        command += " -r #{sibling_path('requirements_rpi.txt')}" if is_raspberry?
        command = "sudo " + command if is_raspberry?
        puts `#{command}`
    end
end

desc "Compiles the protobuf protocol definitions. Creates the necessary python files, as well as the C# files."
task :compile do
    filenames = Dir.glob(sibling_path('*.proto'))
    puts `protoc --proto_path='#{File.dirname(__FILE__)}' --python_out='#{sibling_path('src', 'sensationdriver', 'protocol')}' #{filenames.join(' ')}`

    filenames.each do |filename|
        puts `protobuf-generate pbnet #{filename}`
    end

    camel_case = lambda { |s, capitalize_first = false| s.downcase.split(/[\s_]/).map.with_index { |word, index| (index.zero? and !capitalize_first) ? word : word.capitalize }.join }
    properties = []
    mappings = []
    config = JSON.parse IO.read sibling_path('conf', 'actor_conf.json')
    config['vibration']['regions'].each do |region|
        region['actors'].each do |actor|
            property_name = camel_case.call(region['name']) + '_' + camel_case.call(actor['position'])
            properties << "\tpublic float #{property_name};"
            mappings << "\t\tpropertyMappings[\"#{property_name}\"] = new ActorLocation(Vibration.Region.#{camel_case.call(region['name'], true)}, #{actor['index']});"
        end
    end

    mappings.insert(0, "\tstatic SensationPatterns() {")
    mappings.push("\t}")

    lines = properties + [""] * 2 + mappings

    IO.write(sibling_path('SensationPattern_properties.cs'), lines.join("\n"))
end

desc "Run unit tests. Pass a filename pattern to only run these tests (rake test[actors])."
task :test, :pattern do |t, args|
    Dir.chdir(sibling_path('test')) do
        pattern = args.pattern ? "*#{args.pattern}*.py" : '*.py'
        files = Dir.glob(pattern).map { |f| File.basename(f) }
        `#{PYTHON} -m unittest -v #{files.join(' ')} 2>&1`.split("\n").each do |line|
            line = line.red if line.end_with?('ERROR', 'FAIL') or line.start_with?('ERROR', 'FAIL')
            line = line.green if line.end_with? 'ok', 'OK'
            puts line
            sleep(0.02)
        end
        puts
    end
end

namespace :test do
    desc "Like test, but keeps watching for file modifications to re-run the tests. Also accepts a filename pattern."
    task :watch, [:pattern] => :test do |t, args|
        fsevent = FSEvent.new
        options = {:latency => 5, :no_defer => true }
        counter = 1
        fsevent.watch sibling_path('test'), options do |directories|
            puts "Testrun: #{counter}"
            counter += 1
            puts("#" * 70)
            `rake -f #{__FILE__} test[#{args.pattern}]`.split("\n").each do |line|
                puts line
                sleep(0.02)
            end
            puts("#" * 70)
        end
        fsevent.run
    end
end

desc 'Starts the sensation server.'
task :server do |t, args|
    extras = args.extras
    extras << 'debug' if (extras & ['debug', 'production', 'profile']).empty?
    command = "bash -c '#{PYTHON} #{sibling_path('bin', 'run-server.py')} #{extras.join(' ')}'"
    command = "sudo " + command if is_raspberry?
    exec(command)
end

desc 'Starts an interactive client.'
task :client, :server do |t, args|
    server = args.server ? args.server : PI_HOSTNAME
    command = "bash -c '#{PYTHON} #{sibling_path('bin', 'run-client.py')} #{server}'"
    command = "sudo " + command if is_raspberry?
    exec(command)
end

namespace :daemon do
    remote_task :install do
        desc "Sets up the necessary init.d scripts"

        local pi_only: true do
            puts `sudo cp #{sibling_path(['bin', DAEMON_SCRIPT])} /etc/init.d/#{DAEMON_SCRIPT}`
            puts `sudo chmod 755 /etc/init.d/#{DAEMON_SCRIPT}`
            puts `sudo update-rc.d #{DAEMON_SCRIPT} defaults`
        end    
    end

    remote_task :enable do
        desc "Enable the init.d scripts"
        backticks 'sudo update-rc.d #{DAEMON_SCRIPT} enable', local_only_on_pi: true
    end
    
    remote_task :disable do
        desc "Disable the init.d scripts"
        backticks 'sudo update-rc.d #{DAEMON_SCRIPT} disable', local_only_on_pi: true
    end

    remote_task :start do
        desc "Starts the sensation server daemon"
        backticks "sudo /etc/init.d/#{DAEMON_SCRIPT} start", local_only_on_pi: true
    end

    remote_task :status do
        desc "Checks the sensation server daemon status"
        backticks "sudo /etc/init.d/#{DAEMON_SCRIPT} status", local_only_on_pi: true
    end

    remote_task :stop do
        desc "Stops the sensation server daemon"
        backticks "sudo /etc/init.d/#{DAEMON_SCRIPT} stop", local_only_on_pi: true
    end
    
    remote_task :restart do
        desc "Restarts the sensation server daemon"
        backticks "sudo /etc/init.d/#{DAEMON_SCRIPT} restart", local_only_on_pi: true
    end
end

namespace :remote do
    desc "Connect to the Raspberry via SSH"
    task :login do
        exec(ssh_command)
    end

    desc "Opens a remote desktop via VNC"
    task :vnc do
        backtick("open vnc://#{PI_HOSTNAME}:5901")
    end

    desc "Mounts the Raspberry user home directory as drive"
    task :mount do
        backtick("open afp://#{PI_USER}@#{PI_HOSTNAME}/Home\\ Directory")
    end

    desc "Unmounts the Raspberry user home directory"
    task :unmount do
        backtick("umount '/Volumes/Home Directory'") if `mount`.include? '/Volumes/Home Directory'
    end

    desc "Copy project files to the Raspberry. Uses the configured hostname by default, accepts the IP address as optional argument (rake 'remote:copy[192.168.0.70]')."
    task :copy, :destination do |t, args|
        args.with_defaults destination: PI_HOSTNAME
        command = "rsync -ar -e \"ssh -l #{PI_USER}\" --delete --exclude '__pycache__/' --exclude 'lib' --exclude 'include' --exclude='.*' --exclude 'log' #{File.dirname(__FILE__)}/ #{args.destination}:#{remote_project_path}"
        backtick(command)
    end

    namespace :copy do
        desc "Like copy, but keeps watching for file modifications to copy the files again"
        task :watch => :copy do
            begin
                terminal_title "copy:watch"
                ip = nil

                fsevent = FSEvent.new
                options = {:latency => 5, :no_defer => true }
                fsevent.watch File.dirname(__FILE__), options do |directories|
                    puts "syncing..."
                    terminal_title "syncing..."
                    unless ip
                        parts = `ping -c 1 #{PI_HOSTNAME}`.split
                        if parts.size >= 3
                            md = parts[2].match(/(?:\d{0,3}\.){3}\d{0,3}/)
                            if md
                                ip = md[0]
                                puts "#{PI_HOSTNAME} IP resolved to #{ip}"
                            end
                        end
                    end

                    `rake -f #{__FILE__} "remote:copy[#{ip}]"`
                    puts "#{Time.now.strftime('%H:%M:%S')}: synced"
                    terminal_title "synced"
                    sleep(1)
                    terminal_title "copy:watch"
                end
                fsevent.run
            ensure
                terminal_title ""
            end
        end
    end

    desc "Reboots the Raspberry"
    task :reboot => :unmount do         # TODO support dependencies in remote_task
        ssh_backtick("sudo reboot")
    end

    desc "Shuts the Raspberry down."
    task :shutdown => :unmount do
        ssh_backtick("sudo shutdown -h now")
    end
end

namespace :log do
    remote_task :tail do
        desc "Tails the log"

        local { exec("tail -f -n 10 #{sibling_path(SERVER_LOG_PATH)}") }
        remote { exec(ssh_command("tail -f -n 10 #{File.join(remote_project_path, SERVER_LOG_PATH)}")) }
    end

    remote_task :clean do
        desc "Empties the logfile"

        local { backtick "cat /dev/null > #{sibling_path(SERVER_LOG_PATH)}" }
        remote { ssh_backtick("cat /dev/null > #{File.join(remote_project_path, SERVER_LOG_PATH)}") }
    end
end

namespace :backup do
    desc 'Creates a gzipped backup of the SD card. Accepts optional filname addition parameters (rake "backup:create[param1, param2]").'
    task :create do |t, args|
        puts `sudo diskutil list`
        puts "\nEnter disk number (dev/diskX): [2..n]"
        disk_number = STDIN.gets.strip.to_i
        raise "Disk number below 2 - probably wrong.." if disk_number < 2

        filename = ['sensationdriver', Time.now.strftime('%Y%m%d_%H%M')] + args.extras
        output_path = sibling_path(filename.join('_').gsub(' ', '_') + '.img.gz')

        puts `diskutil unmountDisk /dev/disk#{disk_number}`

        puts "Creating backup #{File.basename(output_path)} - this may take a while.. c[´]"

        puts `sudo dd bs=1M if=/dev/rdisk#{disk_number} | gzip > '#{output_path}'`

        puts "Finished: #{File.basename(output_path)} (#{'%.2f' % (File.size(output_path) / (1000.0 ** 3))} GB) - open in Finder? [y/n]"
        answer = STDIN.gets.strip
        `open #{File.dirname(output_path)}` if answer == 'y'
    end

    desc 'Restores a previously created backup.'
    task :restore do |t, args|
        backups = []
        Dir.chdir sibling_path do
            backups = Dir.glob('*.{img.gz,img}')
        end

        raise "No backups found in #{sibling_path}" if backups.empty?

        backups.each_with_index do |path, index|
            puts "#{index}\t#{path}"
        end
        puts
        puts "Choose backup to restore:"
        backup_path = backups[STDIN.gets.strip.to_i]
        puts

        puts `sudo diskutil list`
        puts "\nEnter disk number (dev/diskX): [2..n]"
        disk_number = STDIN.gets.strip.to_i
        raise "Disk number below 2 - probably wrong.." if disk_number < 2

        puts `diskutil unmountDisk /dev/disk#{disk_number}`

        puts "Restoring backup #{File.basename(backup_path)} - this may take a while.. c[´]"

        if File.extname(backup_path) == '.gz'
            puts `gzip -dc "#{backup_path}" | sudo dd bs=1M of=/dev/rdisk#{disk_number}`
        else
            puts `sudo dd bs=1M of=/dev/rdisk#{disk_number}`
        end

        puts "Finished"        
    end
end

namespace :time do
    namespace :sync do
        desc 'Shows the current time synchronization status.'
        task :status do
            # TODO check if ptpd2 is running and report if not
            puts `cat /var/run/ptpd2.status`
        end
    end

    desc 'Start time synchronization. On the Raspberry a PTP client is started, otherwise a PTP server is started. The client waits till a decent synchronization is reached.'
    task :sync do
        if is_raspberry?
            puts `sudo /etc/init.d/ntp stop`

            mutex = Mutex.new
            client_ready = ConditionVariable.new
            synced = ConditionVariable.new

            poll_status = Thread.new do
                mutex.synchronize { client_ready.wait(mutex) }
                puts "Trying to reach stable offset < 0.0001..."
                counter = 0
                loop do
                    status = `cat /var/run/ptpd2.status`
                    offset_info = /Offset from Master[^\n]+/.match status
                    if offset_info
                        print "\r" + offset_info.to_s.chomp
                        if /[-\d\.]+/.match(offset_info.to_s).to_s.to_f.abs < 0.0001
                            counter += 1
                        else
                            counter = 0
                        end
                        if counter > 30
                            break
                        end
                    else
                        print("\rWaiting for server...")
                    end
                    sleep 0.5
                end
                puts
                puts "Sync complete"
                puts
                synced.signal
            end

            client = Thread.new do
                command = "sudo #{sibling_path('bin', 'ptpd2_pi')} -c #{sibling_path('conf', 'ptp_client.conf')} -V"
                Open3.popen2e(command) do |stdin, stdout, wait_thread|
                    stdin.close
                    stdout.each do |line|
                        puts line
                        if line.include? 'New best master selected'
                            puts
                            mutex.synchronize do 
                                client_ready.signal
                                synced.wait(mutex)
                            end
                        end
                    end
                end
            end

            begin
                poll_status.join
                client.join
            ensure
                puts
                puts `sudo /etc/init.d/ntp start`
            end
        else
            exec("sudo #{sibling_path('bin', 'ptpd2_osx')} -c #{sibling_path('conf', 'ptp_server.conf')} -V")
        end
    end
end


def define_task(scope, name, description, actions)
    if scope.empty?
        desc description
        task name do
            actions.call()
        end
    else
        namespace scope.pop do
            define_task(scope, name, description, actions)
        end
    end
end

def define_remote_task(dsl)
    define_task(dsl.scope(:local).reverse, dsl.name, dsl.description(:local), dsl.local_task) if dsl.local_task
    define_task(dsl.scope(:remote).reverse, dsl.name, dsl.description(:remote), dsl.remote_task) if dsl.remote_task
end

RemoteTask.tasks.each { |dsl| define_remote_task dsl }
