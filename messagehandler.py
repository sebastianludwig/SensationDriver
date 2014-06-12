import sensationprotocol_pb2 as sensationprotocol
import adafruit

class MessageHandler:
  def __init__(self):
    self.pwm = adafruit.Adafruit_PWM_Servo_Driver(0x40, debug=True)
    self.pwm.setPWMFreq(1700)                        # Set max frequency to (~1,6kHz)
  
  def process_message(self, message):
    command = sensationprotocol.Command()
    command.ParseFromString(message)
    
    print 'received command:\n--\n%s--' % command
    
    self.pwm.setPWM(command.actor_index, 0, int(command.intensity * 4096))
    