import logging
import sensationprotocol_pb2 as sensationprotocol

class MessageLogger:
  def __init__(self):
    self.logger = logging.getLogger('root')
    
  def on_client_connected(self):
    pass

  def on_client_disconnected(self):
    pass

  def process_message(self, message):
    command = sensationprotocol.Command()
    command.ParseFromString(message)
    
    self.logger.info('received command:\n--\n%s--', command)
