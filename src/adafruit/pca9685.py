#!/usr/bin/python

import logging
import time
import math
from .wirebus import I2C

# ===========================================================================
# Based on https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code
# Copyright (c) 2012-2013 Limor Fried, Kevin Townsend and Mikey Sklar for Adafruit Industries. All rights reserved.
# ===========================================================================

class Driver(object):
  # Registers/etc.
  __MODE1              = 0x00
  __MODE2              = 0x01
  __SUBADR1            = 0x02
  __SUBADR2            = 0x03
  __SUBADR3            = 0x04
  __PRESCALE           = 0xFE
  __LED0_ON_L          = 0x06
  __LED0_ON_H          = 0x07
  __LED0_OFF_L         = 0x08
  __LED0_OFF_H         = 0x09
  __ALL_LED_ON_L       = 0xFA
  __ALL_LED_ON_H       = 0xFB
  __ALL_LED_OFF_L      = 0xFC
  __ALL_LED_OFF_H      = 0xFD

  # Bits
  __RESTART            = 0x80
  __SLEEP              = 0x10
  __ALLCALL            = 0x01
  __INVRT              = 0x10
  __OUTDRV             = 0x04

  general_call_i2c = I2C(0x00)

  @classmethod
  def softwareReset(cls):
    "Sends a software reset (SWRST) command to all the servo drivers on the bus"
    cls.general_call_i2c.writeRaw8(0x06)        # SWRST

  def __init__(self, address=0x40, debug=False, logger=None):
    self.logger = logger if logger is not None else logging.getLogger('root')
    self.i2c = I2C(address, logger=self.logger)
    self.i2c.debug = debug
    self.address = address
    self.debug = debug
    if self.debug:
      self.logger.debug("Reseting PCA9685 MODE1 (without SLEEP) and MODE2")
    self.setAllPWM(0, 0)
    self.i2c.write8(self.__MODE2, self.__OUTDRV)
    self.i2c.write8(self.__MODE1, self.__ALLCALL)
    time.sleep(0.005)                                       # wait for oscillator

  def wakeUp(self):
    "Activates the sleep mode"
    mode1 = self.i2c.readU8(self.__MODE1)
    mode1 = mode1 & ~self.__SLEEP
    self.i2c.write8(self.__MODE1, mode1)
    time.sleep(0.005)

  def sleep(self):
    "Deactivates the sleep mode"
    mode1 = self.i2c.readU8(self.__MODE1)
    self.i2c.write8(self.__MODE1, mode1 | self.__SLEEP)

  def setPWMFreq(self, freq):
    "Sets the PWM frequency"
    # calculate pre scale (datasheet section 7.3.5)
    prescaleval = 25000000.0    # 25MHz
    prescaleval /= 4096.0       # 12-bit
    prescaleval /= float(freq)
    prescaleval -= 1.0
    if self.debug:
      self.logger.debug("Setting PWM frequency to %d Hz", freq)
      self.logger.debug("Estimated pre-scale: %.2f", prescaleval)
    prescale = int(prescaleval + 0.5)
    if self.debug:
      self.logger.debug("Final pre-scale: %d", prescale)

    oldmode = self.i2c.readU8(self.__MODE1)
    newmode = (oldmode & 0x7F) | self.__SLEEP                 # sleep (and preparation for restart)
    self.i2c.write8(self.__MODE1, newmode)                    # go to sleep
    self.i2c.write8(self.__PRESCALE, prescale)
    self.i2c.write8(self.__MODE1, oldmode)
    # restart (datasheet section 7.3.1.1)
    time.sleep(0.005)                                         # wait for oscillator
    self.i2c.write8(self.__MODE1, oldmode | self.__RESTART)

  def setPWM(self, channel, on, off):
    "Sets a single PWM channel"
    self.i2c.write8(self.__LED0_ON_L+4*channel, on & 0xFF)
    self.i2c.write8(self.__LED0_ON_H+4*channel, on >> 8)
    self.i2c.write8(self.__LED0_OFF_L+4*channel, off & 0xFF)
    self.i2c.write8(self.__LED0_OFF_H+4*channel, off >> 8)

  def setAllPWM(self, on, off):
    "Sets a all PWM channels"
    self.i2c.write8(self.__ALL_LED_ON_L, on & 0xFF)
    self.i2c.write8(self.__ALL_LED_ON_H, on >> 8)
    self.i2c.write8(self.__ALL_LED_OFF_L, off & 0xFF)
    self.i2c.write8(self.__ALL_LED_OFF_H, off >> 8)
