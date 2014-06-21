import socket
import struct
import logging

class SensationServer:
  def __init__(self, logger = None):
    self.logger = logger if logger is not None else logging.getLogger('root')
    self.handler = None
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  
  def listen(self, address, port):
    self.socket.bind((address, port))
    self.socket.listen(0)
  
  def handle_client(self, client_socket, client_address):
    self.logger.info('connection from %s', client_address)
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
        self.logger.info('waiting for a connection')
        client_socket, client_address = self.socket.accept()

        self.handler.on_client_connected()
        self.handle_client(client_socket, client_address)
        self.handler.on_client_disconnected()
        
    except KeyboardInterrupt:
      self.logger.info("^C detected")
      pass 
    finally:
      self.logger.info("closing server..")
      self.handler.on_server_shutdown()
      self.socket.close()
