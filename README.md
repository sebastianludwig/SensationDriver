# SensationDriver

A fair word of warning: This project has only ever been used on OS X. 
Linux shouldn't be a problem, but you've probably got to fiddle around quite a lot on Windows.
However, if you do, let me know and I'll be happy to include your findings and improvements!

## Installation

### On the Pi

1. Zeroconf aka Bonjour

    Usefull, but not necessary: `sudo apt-get install avahi-daemon` (<hostname>.local)

    You might also want to change the hostname of your Pi: `sudo nano /etc/hostname`

1. Configure I2C

    Source: https://learn.adafruit.com/adafruits-raspberry-pi-lesson-4-gpio-setup/configuring-i2c

    - add "i2c-bcm2708" and "i2c-dev" to /etc/modules
    - sudo apt-get install "python-smbus" and "i2c-tools"
    - comment out "spi-bcm2708" and "i2c-bcm2708" in /etc/modprobe.d/raspi-blacklist.conf (if it exists)
    - check success: `sudo i2cdetect -y 1` should detect something (not an empty table, probably 40 & 70)

1. Install Python 3.4

    See http://procrastinative.ninja/2014/07/20/install-python34-on-raspberry-pi/

1. Compile python-smbus for Python3

    See http://procrastinative.ninja/2014/07/21/smbus-for-python34-on-raspberry/

1. Install dependencies

    Bundler: `sudo gem install bundler`
    Gems: `(sudo) bundle install`

    Python: `rake dependencies:install`

### On your Workstation

1. Install dependencies

    Bundler: `sudo gem install bundler`
    Gems: `(sudo) bundle install`


1. Install Python3-Protobuf

    If you want to change the protocol definition, you need a protobuf compiler, generating valid Python 3 code

    DL Python3-Protobuf 2.5.1 (https://github.com/GreatFruitOmsk/protobuf-py3)
    install: brew install autoconf automake libtool, ./autogen.sh , ./configure, make, (sudo) make install

## Usage

There's a Rakefile that makes executing common tasks more convenient. 
Run `rake -T` or `rake -D` for a list of tasks and descriptions.

To start a server locally execute `rake server`.
To connect to that server with an interactive command line client run `rake client[localhost]`.

