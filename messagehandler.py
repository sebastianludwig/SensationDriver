import sensationprotocol_pb2 as sensationprotocol

class MessageHandler:
  def process_message(self, message):
    command = sensationprotocol.Command()
    command.ParseFromString(message)
    
    print 'received command:\n--\n%s--' % command
    