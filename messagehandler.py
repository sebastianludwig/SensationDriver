import logging
import sensationprotocol_pb2 as sensationprotocol
import adafruit

class MessageHandler:
  def __init__(self, logger = None):
    self.logger = logger if logger is not None else logging.getLogger('root')
    adafruit.Adafruit_PWM_Servo_Driver.softwareReset()
    self.__prepare_drivers()

  def __prepare_drivers(self):
    self.drivers = { }

    mapping = {
      sensationprotocol.Command.LEFT_HAND:      0x40,
      sensationprotocol.Command.LEFT_FOREARM:   0x41,
      sensationprotocol.Command.LEFT_UPPER_ARM: 0x42
    }

    for (region, address) in mapping.iteritems():
      if not adafruit.Adafruit_I2C.isDeviceAnswering(address):
        self.logger.warning("No driver found for at address 0x%02X for region %d", address, region)
        continue

      driver = adafruit.Adafruit_PWM_Servo_Driver(address, debug=True)
      # TODO use ALLCALL address
      driver.setPWMFreq(1700)                        # Set max frequency to (~1,6kHz)
      self.drivers[region] = driver

  def on_client_connected(self):
    for driver in self.drivers.itervalues():
      driver.setAllPWM(0, 0)

  def on_client_disconnected(self):
    # TODO enable - disabled for easier debugging
    # for driver in self.drivers.itervalues():
    #   driver.setAllPWM(0, 0)
    pass

  def on_server_shutdown(self):
    for driver in self.drivers.itervalues():
      driver.setAllPWM(0, 0)
  
  def process_message(self, message):
    command = sensationprotocol.Command()
    command.ParseFromString(message)
    
    self.logger.debug('received command:\n--\n%s--', command)
    
    if command.region in self.drivers:
      self.drivers[command.region].setPWM(command.actor_index, 0, int(command.intensity * 4096))

