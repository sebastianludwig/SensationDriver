import sensationprotocol_pb2 as sensationprotocol

class MessageLogger:
  def __init__(self):
    pass
  
  def process_message(self, message):
    command = sensationprotocol.Command()
    command.ParseFromString(message)
    
    print 'received command:\n--\n%s--' % command
