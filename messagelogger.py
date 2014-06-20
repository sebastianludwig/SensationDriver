import logging
import sensationprotocol_pb2 as sensationprotocol

class MessageLogger:
  def __init__(self):
    self.logger = logging.getLogger('root')
  
  def process_message(self, message):
    command = sensationprotocol.Command()
    command.ParseFromString(message)
    
    self.logger.info('received command:\n--\n%s--', command)
