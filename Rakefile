PI_HOSTNAME = "sensationdriver.local"
PI_USER = 'pi'
SERVER_LOG_NAME = 'server_log.log'

def sibling_path(filename)
    File.join(File.dirname(__FILE__), filename)
end

def remote_project_path
    "/home/pi/projects/#{File.basename(File.dirname(__FILE__))}"
end

def is_raspberry?
  `uname` == "Linux\n"
end

desc 'Starts the sensation server'
task :server do
    command = "bash -c '#{sibling_path('server.py')}'"
    command = "sudo " + command if is_raspberry?
    exec(command)
end

desc "Copies the files, restarts the server and tails the log"
task :deploy => ['remote:copy', 'remote:server:restart', 'remote:log:tail']

namespace :dependencies do
    desc "Install python package dependencies through pip"
    task :install do
        command = "pip install -r #{sibling_path('requirements.txt')}"
        command = "sudo " + command if is_raspberry?
        puts `#{command}`
    end
end

namespace :remote do
    desc "Connect to the Raspberry via SSH"
    task :connect do
        exec("ssh #{PI_USER}@#{PI_HOSTNAME}")
    end

    desc "Copy project files to the Raspberry"
    task :copy do
        command = "rsync -ar -e \"ssh -l #{PI_USER}\" --exclude 'lib' --exclude 'include' --exclude='.*' --exclude '*.log' #{File.dirname(__FILE__)}/ #{PI_HOSTNAME}:#{remote_project_path}"
        output = `#{command}`
        # TODO implement retry
    end

    desc "Reboots the Raspberry"
    task :reboot do
        `ssh #{PI_USER}@#{PI_HOSTNAME} 'sudo reboot'`
    end

    desc "Shuts the Raspberry down"
    task :shutdown do
        `ssh #{PI_USER}@#{PI_HOSTNAME} 'sudo shutdown -h now'`
    end

    namespace :server do
        desc "Starts the sensation server daemon"
        task :start do
            puts `ssh #{PI_USER}@#{PI_HOSTNAME} 'sudo /etc/init.d/sensation.sh start'`
        end

        desc "Checks the sensation server daemon status"
        task :status do
            puts `ssh #{PI_USER}@#{PI_HOSTNAME} 'sudo /etc/init.d/sensation.sh status'`
        end

        desc "Stops the sensation server daemon"
        task :stop do
            puts `ssh #{PI_USER}@#{PI_HOSTNAME} 'sudo /etc/init.d/sensation.sh stop'`
        end

        desc "Restarts the sensation server daemon"
        task :restart do
            puts `ssh #{PI_USER}@#{PI_HOSTNAME} 'sudo /etc/init.d/sensation.sh restart'`
        end
    end

    namespace :log do
        desc "Tails the log on the Raspberry"
        task :tail do
            exec("ssh #{PI_USER}@#{PI_HOSTNAME} 'tail -f -n 10 #{File.join(remote_project_path, SERVER_LOG_NAME)}'")
        end

        desc "Empties the logfile on the Raspberry"
        task :clean do
            `ssh #{PI_USER}@#{PI_HOSTNAME} 'cat /dev/null > #{File.join(requirements, SERVER_LOG_NAME)}'`
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
