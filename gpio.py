import RPi.GPIO as GPIO

class GPIOOutput:
  def __init__(self, pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    self.pin = pin

  def high(self):
    GPIO.output(self.pin, GPIO.HIGH)

  def low(self):
    GPIO.output(self.pin, GPIO.LOW)

  def __del__(self):
    GPIO.cleanup()
