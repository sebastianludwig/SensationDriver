#!/usr/bin/python

import logging
import os
import mmap
import time
import smbus

# ===========================================================================
# Based on https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code
# Copyright (c) 2012-2013 Limor Fried, Kevin Townsend and Mikey Sklar for Adafruit Industries. All rights reserved.
# ===========================================================================

class I2C(object):
    __BLOCK_SIZE = 4096
    __BCM2708_PERI_BASE = 0x20000000 # Base address of peripheral registers
    __GPIO_BASE = (__BCM2708_PERI_BASE + 0x00200000)  # Address of GPIO registers
    __GPFSEL0 = 0x0000 # Function select 0
    __GPFSEL2 = 0x0008 # Function select 2
    __GPPUD = 0x0094 # GPIO Pin Pull-up/down Enable
    __GPPUDCLK0 = 0x0098 # GPIO Pin Pull-up/down Enable Clock 0
    __GPIO_PUD_OFF = 0b00   # Off - disable pull-up/down
    __GPIO_PUD_UP = 0b10    # Enable Pull Up control


    @staticmethod
    def _piRevision():
        "Gets the version number of the Raspberry Pi board"
        # Courtesy quick2wire-python-api
        # https://github.com/quick2wire/quick2wire-python-api
        try:
            with open('/proc/cpuinfo','r') as f:
                for line in f:
                    if line.startswith('Revision'):
                        return 1 if line.rstrip()[-1] in ['1','2'] else 2
        except:
            return 0

    @classmethod
    def defaultBusNumber(cls):
        "Returns the default I2C bus number /dev/i2c#"
        return 0 if cls._piRevision() == 1 else 1

    @classmethod
    def pinoutConfiguredBuses(cls):
        if cls._piRevision() == 1:
            return [cls.defaultBusNumber()]     # this is not 100% correct - I guess you can change the pin configuration on a revision 1 board, too

        mf = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        memory = mmap.mmap(mf, cls.__BLOCK_SIZE, mmap.MAP_SHARED, 
                    mmap.PROT_READ | mmap.PROT_WRITE, offset=cls.__GPIO_BASE)
        os.close(mf)

        bus_numbers = []

        # Read function select registers
        # GPFSEL0 -- GPIO 0,1 I2C0   GPIO 2,3 I2C1
        memory.seek(cls.__GPFSEL0)
        reg0 = int.from_bytes(memory.read(4), byteorder='little')

        # GPFSEL0 bits --> x[20] SCL1[3] SDA1[3] x[6]
        #                        GPIO3   GPIO2
        reg0_mask = 0b00000000000000000000111111000000 
        reg0_conf = 0b00000000000000000000100100000000
        if reg0 & reg0_mask == reg0_conf:
            bus_numbers.append(1)


        # GPFSEL2 -- GPIO 28,29 I2C0
        memory.seek(cls.__GPFSEL2)
        reg2 = int.from_bytes(memory.read(4), byteorder='little')

        # GPFSEL2 bits --> x[2] SCL0[3] SDA0[3] x[24]
        #                       GPIO29  GPIO28
        reg2_mask = 0b00111111000000000000000000000000 
        reg2_conf = 0b00100100000000000000000000000000
        if reg2 & reg2_mask == reg2_conf:
            bus_numbers.append(0)

        memory.close()

        return bus_numbers

    @classmethod
    def configurePinouts(cls, logger=None):
        logger = logger if logger is not None else logging.getLogger('root')

        if cls._piRevision() < 2:
            raise RuntimeError("Rev 2 or greater Raspberry Pi required.")

        # Use /dev/mem to gain access to peripheral registers
        mf = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        memory = mmap.mmap(mf, cls.__BLOCK_SIZE, mmap.MAP_SHARED, 
                    mmap.PROT_READ | mmap.PROT_WRITE, offset=cls.__GPIO_BASE)
        # can close the file after we have mmap
        os.close(mf)

        # each 32 bit register controls the functions of 10 pins, each 3 bit, starting at the LSB
        # 000 = input
        # 100 = alt function 0

        # Read function select registers
        # GPFSEL0 -- GPIO 0,1 I2C0   GPIO 2,3 I2C1
        memory.seek(cls.__GPFSEL0)
        reg0 = int.from_bytes(memory.read(4), byteorder='little')

        # GPFSEL0 bits --> x[20] SCL1[3] SDA1[3] 
        #                        GPIO3   GPIO2   GPIO1   GPIO0
        reg0_mask = 0b00000000000000000000111111111111 
        reg0_conf = 0b00000000000000000000100100000000
        if reg0 & reg0_mask != reg0_conf:
            logger.info("register 0 configuration of I2C0 not correct. Updating.")
            reg0 = (reg0 & ~reg0_mask) | reg0_conf
            memory.seek(cls.__GPFSEL0)
            memory.write(reg0.to_bytes(4, byteorder='little'))


        # GPFSEL2 -- GPIO 28,29 I2C0
        memory.seek(cls.__GPFSEL2)
        reg2 = int.from_bytes(memory.read(4), byteorder='little')

        # GPFSEL2 bits --> x[2] SCL0[3] SDA0[3] x[24]
        #                       GPIO29  GPIO28
        reg2_mask = 0b00111111000000000000000000000000 
        reg2_conf = 0b00100100000000000000000000000000
        if reg2 & reg2_mask != reg2_conf:
            logger.info("register 2 configuration of I2C0 not correct. Updating.")
            reg2 = (reg2 & ~reg2_mask) | reg2_conf
            memory.seek(cls.__GPFSEL2)
            memory.write(reg2.to_bytes(4, byteorder="little"))

        # Configure pull up resistors for GPIO28 and GPIO29
        def configure_internal_pull_up_resistor(pin):
            memory.seek(cls.__GPPUD)
            memory.write(cls.__GPIO_PUD_UP.to_bytes(4, byteorder="little"))
            time.sleep(10e-6)

            memory.seek(cls.__GPPUDCLK0)
            memory.write((1 << pin).to_bytes(4, byteorder="little"))
            time.sleep(10e-6)

            memory.seek(cls.__GPPUD)
            memory.write(cls.__GPIO_PUD_OFF.to_bytes(4, byteorder="little"))

            memory.seek(cls.__GPPUDCLK0)
            memory.write((0 << pin).to_bytes(4, byteorder="little"))

        configure_internal_pull_up_resistor(28)
        configure_internal_pull_up_resistor(29)

        # No longer need the mmap
        memory.close()

    @classmethod
    def isDeviceAnswering(cls, address, busnum=-1):
        "Checks if a device is answering on the given address"
        try:
            bus = smbus.SMBus(busnum if busnum >= 0 else cls.defaultBusNumber())
            bus.write_quick(address)
            return True
        except IOError as err:
            return False

    def __init__(self, address, busnum=-1, debug=False, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('root')
        self.address = address
        # By default, the correct I2C bus is auto-detected using /proc/cpuinfo
        # Alternatively, you can hard-code the bus version below:
        # self.bus = smbus.SMBus(0); # Force I2C0 (early 256MB Pi's)
        # self.bus = smbus.SMBus(1); # Force I2C1 (512MB Pi's)
        self.bus = smbus.SMBus(busnum if busnum >= 0 else I2C.defaultBusNumber())
        self.debug = debug

    def reverseByteOrder(self, data):
        "Reverses the byte order of an int (16-bit) or long (32-bit) value"
        # Courtesy Vishal Sapre
        byteCount = len(hex(data)[2:].replace('L','')[::2])
        val       = 0
        for i in range(byteCount):
            val    = (val << 8) | (data & 0xff)
            data >>= 8
        return val

    def errMsg(self):
        self.logger.error("Error accessing 0x%02X: Check your I2C address", self.address)
        return -1

    def write8(self, reg, value):
        "Writes an 8-bit value to the specified register/address"
        try:
            self.bus.write_byte_data(self.address, reg, value)
            if self.debug:
                self.logger.debug("I2C: Wrote 0x%02X to register 0x%02X", value, reg)
        except IOError as err:
            return self.errMsg()

    def write16(self, reg, value):
        "Writes a 16-bit value to the specified register/address pair"
        try:
            self.bus.write_word_data(self.address, reg, value)
            if self.debug:
                self.logger.debug("I2C: Wrote 0x%02X to register pair 0x%02X,0x%02X", value, reg, reg+1)
        except IOError as err:
            return self.errMsg()

    def writeRaw8(self, value):
        "Writes an 8-bit value on the bus"
        try:
            self.bus.write_byte(self.address, value)
            if self.debug:
                self.logger.debug("I2C: Wrote 0x%02X", value)
        except IOError as err:
            return self.errMsg()

    def writeList(self, reg, list):
        "Writes an array of bytes using I2C format"
        try:
            if self.debug:
                self.logger.debug("I2C: Writing list to register 0x%02X:\n%s", reg, list)
            self.bus.write_i2c_block_data(self.address, reg, list)
        except IOError as err:
            return self.errMsg()

    def readList(self, reg, length):
        "Read a list of bytes from the I2C device"
        try:
            results = self.bus.read_i2c_block_data(self.address, reg, length)
            if self.debug:
                self.logger.debug("I2C: Device 0x%02X returned the following from reg 0x%02X:\n%s", self.address, reg, results)
            return results
        except IOError as err:
            return self.errMsg()

    def readU8(self, reg):
        "Read an unsigned byte from the I2C device"
        try:
            result = self.bus.read_byte_data(self.address, reg)
            if self.debug:
                self.logger.debug("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X", self.address, result & 0xFF, reg)
            return result
        except IOError as err:
            return self.errMsg()

    def readS8(self, reg):
        "Reads a signed byte from the I2C device"
        try:
            result = self.bus.read_byte_data(self.address, reg)
            if result > 127: result -= 256
            if self.debug:
                self.logger.debug("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X", self.address, result & 0xFF, reg)
            return result
        except IOError as err:
            return self.errMsg()

    def readU16(self, reg):
        "Reads an unsigned 16-bit value from the I2C device"
        try:
            result = self.bus.read_word_data(self.address,reg)
            if (self.debug):
                self.logger.debug("I2C: Device 0x%02X returned 0x%04X from reg 0x%02X", self.address, result & 0xFFFF, reg)
            return result
        except IOError as err:
            return self.errMsg()

    def readS16(self, reg):
        "Reads a signed 16-bit value from the I2C device"
        try:
            result = self.bus.read_word_data(self.address,reg)
            if (self.debug):
                self.logger.debug("I2C: Device 0x%02X returned 0x%04X from reg 0x%02X", self.address, result & 0xFFFF, reg)
            return result
        except IOError as err:
            return self.errMsg()

if __name__ == '__main__':
    try:
        bus = I2C(address=0)
        print("Default I2C bus is accessible")
    except:
        print("Error accessing default I2C bus")
