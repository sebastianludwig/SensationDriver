import socket
import struct

class SensationServer:
  def __init__(self):
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.handler = None
    self.on_client_connect = None
    self.on_client_disconnect = None
  
  def listen(self, address, port):
    self.socket.bind((address, port))
    self.socket.listen(0)
  
  def handle_client(self, client_socket, client_address):
    print 'connection from', client_address
    try:
      buffer = ''
      message_size = None
      
      while True:
        new_data = client_socket.recv(4096)
        if not new_data: break
        
        buffer += new_data
        
        # process the buffer
        while True:
          # message size to parse
          if message_size == None and len(buffer) >= 4:
            message_size = int(struct.unpack('!i', buffer[:4])[0])
            buffer = buffer[4:]
          # message to parse
          elif message_size and len(buffer) >= message_size:
            message = buffer[:message_size]
            if self.handler: self.handler.process_message(message)
            buffer = buffer[message_size:]
            message_size = None
          # neither -> need more data
          else:
            break
        
    finally:
      client_socket.close()
  
    
  def loop(self):
    try:
      
      while True:
        # Wait for a connection
        print 'waiting for a connection'
        client_socket, client_address = self.socket.accept()

        if self.on_client_connect: self.on_client_connect()
        self.handle_client(client_socket, client_address)
        if self.on_client_disconnect: self.on_client_disconnect()
        
    except KeyboardInterrupt:
      print "^C detected" 
      pass 
    finally: 
      print "closing server.."
      self.socket.close()
