#encoding: utf-8

require 'time'

PI_HOSTNAME = "sensationdriver.local"
PI_USER = 'pi'
SERVER_LOG_NAME = 'server_log.log'
PYTHON = 'python3.4'

def sibling_path(filename)
    File.join(File.dirname(__FILE__), filename)
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

desc 'Starts the sensation server'
task :server do
    command = "bash -c '#{PYTHON} #{sibling_path('server.py')}'"
    command = "sudo " + command if is_raspberry?
    exec(command)
end

namespace :server do
    desc "Sets up the necessary init.d scripts"
    task :install do
        raise "Only supported on Raspberry Pi" unless is_raspberry?
        daemon_script = 'sensation_daemon.sh'
        puts `sudo cp #{sibling_path(['bin', daemon_script])} /etc/init.d/#{daemon_script}`
        puts `sudo chmod 755 /etc/init.d/#{daemon_script}`
        puts `sudo update-rc.d #{daemon_script} defaults`
    end
end

desc "Copies the files, restarts the server and tails the log"
task :deploy => ['remote:copy', 'remote:server:restart', 'remote:log:tail']

desc "Compiles the protobuf protocol definitions into python files"
task :compile do
    filenames = Dir.glob(sibling_path(['protocol', '*.proto']))
    puts `protoc --proto_path='#{sibling_path('protocol')}' --python_out='#{File.dirname(__FILE__)}' #{filenames.join(' ')}`
end

namespace :dependencies do
    desc "Install python package dependencies through pip"
    task :install do
        command = "#{PYTHON} -m pip install -r #{sibling_path('requirements.txt')}"
        command = "sudo " + command if is_raspberry?
        puts `#{command}`
    end
end

namespace :remote do
    desc "Connect to the Raspberry via SSH"
    task :connect do
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

    desc "Copy project files to the Raspberry"
    task :copy do
        command = "rsync -ar -e \"ssh -l #{PI_USER}\" --exclude 'lib' --exclude 'include' --exclude='.*' --exclude '*.log' #{File.dirname(__FILE__)}/ #{PI_HOSTNAME}:#{remote_project_path}"
        backtick(command)
    end

    desc "Reboots the Raspberry"
    task :reboot => :unmount do
        ssh_exec("sudo reboot")
    end

    desc "Shuts the Raspberry down"
    task :shutdown => :unmount do
        ssh_exec("sudo shutdown -h now")
    end

    namespace :server do
        desc "Starts the sensation server daemon"
        task :start do
            puts ssh_exec("sudo /etc/init.d/sensation_daemon.sh start")
        end

        desc "Checks the sensation server daemon status"
        task :status do
            puts ssh_exec("sudo /etc/init.d/sensation_daemon.sh status")
        end

        desc "Stops the sensation server daemon"
        task :stop do
            puts ssh_exec("sudo /etc/init.d/sensation_daemon.sh stop")
        end

        desc "Restarts the sensation server daemon"
        task :restart do
            puts ssh_exec("sudo /etc/init.d/sensation_daemon.sh restart")
        end
    end

    namespace :log do
        desc "Tails the log on the Raspberry"
        task :tail do
            exec(ssh_command("tail -f -n 10 #{File.join(remote_project_path, SERVER_LOG_NAME)}"));
        end

        desc "Empties the logfile on the Raspberry"
        task :clean do
            ssh_exec("cat /dev/null > #{File.join(requirements, SERVER_LOG_NAME)}")
        end
    end
end

namespace :log do
    desc "Tails the log"
    task :tail do
        exec("tail -f -n 10 #{sibling_path(SERVER_LOG_NAME)}")
    end

    desc "Empties the logfile"
    task :clean do
        `cat /dev/null > #{sibling_path(SERVER_LOG_NAME)}`
    end
end

namespace :backup do
    desc 'Creates a gzipped backup of the SD card. Accepts optional filname addition parameters (rake "backup:create[param1, param2]")'
    task :create do |t, args|
        puts `diskutil list`
        puts "\nEnter disk number: [2..n]"
        disk_number = STDIN.gets.strip.to_i
        raise "Disk number below 2 - probably wrong.." if disk_number < 2

        filename = ['sensationdriver', Time.now.strftime('%Y%m%d_%H%M')] + args.extras
        output_path = sibling_path(filename.join('_').gsub(' ', '_') + '.img.gz')

        puts "Creating backup #{File.basename(output_path)} - this may take a while.. c[´]"

        puts `diskutil unmountDisk /dev/disk#{disk_number}`
        puts `sudo dd bs=1m if=/dev/rdisk#{disk_number} | gzip > '#{output_path}'`

        puts "Finished: #{File.basename(output_path)} (#{'%.2f' % (File.size(output_path) / (1000.0 ** 3))} GB) - open in Finder? [y/n]"
        answer = STDIN.gets.strip
        `open #{File.dirname(output_path)}` if answer == 'y'
    end
end
