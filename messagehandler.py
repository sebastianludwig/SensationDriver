import logging
import sensationprotocol_pb2 as sensationprotocol
import adafruit

# TODO
# probe i2c for drivers
# have dictionary that maps from REGION to driver
# rename to ClientHandler
# add on_client_connect and _disconnect and call them in sensationserver instead of the callbacks
# set all PWM for all drivers to 0 on connect and disconnect
class MessageHandler:
  def __init__(self, logger = None):
    self.logger = logger if logger is not None else logging.getLogger('root')
    self.pwm = adafruit.Adafruit_PWM_Servo_Driver(0x40, debug=True)
    self.pwm.setPWMFreq(1700)                        # Set max frequency to (~1,6kHz)
  
  def process_message(self, message):
    command = sensationprotocol.Command()
    command.ParseFromString(message)
    
    self.logger.debug('received command:\n--\n%s--', command)
    
    self.pwm.setPWM(command.actor_index, 0, int(command.intensity * 4096))

