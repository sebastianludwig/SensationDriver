import logging
import sensationprotocol_pb2 as sensationprotocol

class MessageLogger:
  def __init__(self):
    self.logger = logging.getLogger('root')
    
  def on_client_connected(self):
    pass

  def on_client_disconnected(self):
    pass

  def on_server_shutdown(self):
    pass

  def process_message(self, message):
    sensation = sensationprotocol.Sensation()
    sensation.ParseFromString(message)
    
    self.logger.info('received sensation:\n--\n%s--', sensation)
