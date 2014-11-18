#encoding: utf-8

require 'time'
require 'rb-fsevent'
require 'colorize'
require 'json'

PI_HOSTNAME = "sensationdriver.local"
PI_USER = 'pi'
SERVER_LOG_PATH = File.join('log', 'server.log')
PYTHON = 'python3.4'
DAEMON_SCRIPT = 'sensation_daemon.sh'

def sibling_path(*components)
    File.join(File.dirname(__FILE__), components)
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

def ssh_exec(command)
    backtick(ssh_command(command))
end

desc 'Starts the sensation server.'
task :server do
    command = "bash -c '#{PYTHON} #{sibling_path('bin', 'run-server.py')}'"
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

namespace :server do
    desc "Sets up the necessary init.d scripts."
    task :install do
        raise "Only supported on Raspberry Pi" unless is_raspberry?
        puts `sudo cp #{sibling_path(['bin', DAEMON_SCRIPT])} /etc/init.d/#{DAEMON_SCRIPT}`
        puts `sudo chmod 755 /etc/init.d/#{DAEMON_SCRIPT}`
        puts `sudo update-rc.d #{DAEMON_SCRIPT} defaults`
    end

    desc "Enable the init.d scripts."
    task :enable do
        raise "Only supported on Raspberry Pi" unless is_raspberry?
        puts `sudo update-rc.d #{DAEMON_SCRIPT} enable`
    end

    desc "Disable the init.d scripts."
    task :disable do
        raise "Only supported on Raspberry Pi" unless is_raspberry?
        puts `sudo update-rc.d #{DAEMON_SCRIPT} disable`
    end
end

desc "Copies the files, restarts the server and tails the log."
task :deploy => ['remote:copy', 'remote:server:restart', 'remote:log:tail']

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

namespace :dependencies do
    desc "Install python package dependencies through pip."
    task :install do
        command = "#{PYTHON} -m pip install -r #{sibling_path('requirements.txt')}"
        command += " -r #{sibling_path('requirements_rpi.txt')}" if is_raspberry?
        command = "sudo " + command if is_raspberry?
        puts `#{command}`
    end
end

namespace :remote do
    desc "Connect to the Raspberry via SSH."
    task :login do
        exec(ssh_command)
    end

    desc "Opens a remote desktop via VNC."
    task :vnc do
        backtick("open vnc://#{PI_HOSTNAME}:5901")
    end

    desc "Mounts the Raspberry user home directory as drive."
    task :mount do
        backtick("open afp://#{PI_USER}@#{PI_HOSTNAME}/Home\\ Directory")
    end

    desc "Unmounts the Raspberry user home directory."
    task :unmount do
        backtick("umount '/Volumes/Home Directory'") if `mount`.include? '/Volumes/Home Directory'
    end

    desc "Copy project files to the Raspberry. Uses the configured hostname by default, accepts the IP address as optional argument (rake 'remote:copy[192.168.0.70]')."
    task :copy, :destination do |t, args|
        args.with_defaults destination: PI_HOSTNAME
        command = "rsync -ar -e \"ssh -l #{PI_USER}\" --delete --exclude '__pycache__/' --exclude 'lib' --exclude 'include' --exclude='.*' --exclude '*.log' #{File.dirname(__FILE__)}/ #{args.destination}:#{remote_project_path}"
        backtick(command)
    end

    namespace :copy do
        desc "Like copy, but keeps watching for file modifications to copy the files again."
        task :watch => :copy do
            ip = nil

            fsevent = FSEvent.new
            options = {:latency => 5, :no_defer => true }
            fsevent.watch File.dirname(__FILE__), options do |directories|
                puts "syncing..."
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
            end
            fsevent.run
        end
    end

    desc "Reboots the Raspberry."
    task :reboot => :unmount do
        ssh_exec("sudo reboot")
    end

    desc "Shuts the Raspberry down."
    task :shutdown => :unmount do
        ssh_exec("sudo shutdown -h now")
    end

    namespace :server do
        desc "Starts the sensation server daemon."
        task :start do
            puts ssh_exec("sudo /etc/init.d/#{DAEMON_SCRIPT} start")
        end

        desc "Checks the sensation server daemon status."
        task :status do
            puts ssh_exec("sudo /etc/init.d/#{DAEMON_SCRIPT} status")
        end

        desc "Stops the sensation server daemon."
        task :stop do
            puts ssh_exec("sudo /etc/init.d/#{DAEMON_SCRIPT} stop")
        end

        desc "Restarts the sensation server daemon."
        task :restart do
            puts ssh_exec("sudo /etc/init.d/#{DAEMON_SCRIPT} restart")
        end
    end

    namespace :log do
        desc "Tails the log on the Raspberry."
        task :tail do
            exec(ssh_command("tail -f -n 10 #{File.join(remote_project_path, SERVER_LOG_PATH)}"));
        end

        desc "Empties the logfile on the Raspberry."
        task :clean do
            ssh_exec("cat /dev/null > #{File.join(requirements, SERVER_LOG_PATH)}")
        end
    end
end

namespace :log do
    desc "Tails the log."
    task :tail do
        exec("tail -f -n 10 #{sibling_path(SERVER_LOG_PATH)}")
    end

    desc "Empties the logfile."
    task :clean do
        `cat /dev/null > #{sibling_path(SERVER_LOG_PATH)}`
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
