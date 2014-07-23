#!/bin/bash
 
### BEGIN INIT INFO
# Provides:          sensation
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Runs the sensation server
# Description:       Really
### END INIT INFO

# Usage
# 1. Copy to /etc/init.d (`sudo cp bin/sensation_daemon.sh /etc/init.d`)
# 2. Make sure it's executable (`sudo chmod 755 /etc/init.d/sensation_daemon.sh`)
# 3. Hook into startup (`sudo update-rc.d sensation_daemon.sh defaults`)
 
# Change the next 2 lines to suit where you install your script and what you want to call it
DAEMON=/home/pi/projects/SensationDriver/bin/run-server.py
DAEMON_NAME=sensation
 
# This next line determines what user the script runs as.
# root generally not recommended but necessary if you are using the Raspberry Pi GPIO from Python.
DAEMON_USER=root
 
# The process ID of the script when it runs is stored here:
PIDFILE=/var/run/$DAEMON_NAME.pid

PATH=$PATH:/opt/python3.4/bin
 
. /lib/lsb/init-functions

do_start () {
    log_daemon_msg "Starting system $DAEMON_NAME daemon"
    start-stop-daemon --start --background --pidfile $PIDFILE --make-pidfile --user $DAEMON_USER --chuid $DAEMON_USER --exec $DAEMON
    log_end_msg $?
}
do_stop () {
    log_daemon_msg "Stopping system $DAEMON_NAME daemon"
    start-stop-daemon --stop --pidfile $PIDFILE --retry 10
    log_end_msg $?
}
 
case "$1" in
 
    start|stop)
        do_${1}
        ;;
 
    restart|reload|force-reload)
        do_stop
        do_start
        ;;
 
    status)
        status_of_proc "$DAEMON_NAME" "$DAEMON" && exit 0 || exit $?
        ;;
    *)
        echo "Usage: /etc/init.d/$DAEMON_NAME {start|stop|restart|status}"
        exit 1
        ;;
 
esac
exit 0
