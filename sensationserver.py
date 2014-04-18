#! python

import socket
import struct

class SensationServer:
  def __init__(self):
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  
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
          # message_size to parse
          if message_size == None and len(buffer) >= 4:
            message_size = int(struct.unpack('!i', buffer[:4])[0])
            buffer = buffer[4:]
          # message to parse
          elif message_size and len(buffer) >= message_size:
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

        self.handle_client(client_socket, client_address)
        
    except KeyboardInterrupt:
      print "^C detected" 
      pass 
    finally: 
      print "closing server.."
      self.socket.close()



server = SensationServer()
server.listen('localhost', 10000)
server.loop()

exit()
#----------------------------------
    
# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = ('localhost', 10000)
print 'starting up on %s port %s' % server_address
sock.bind(server_address)

# Listen for incoming connections
sock.listen(1)

while True:
  # Wait for a connection
  print 'waiting for a connection'
  connection, client_address = sock.accept()
    
  try:
    print 'connection from', client_address

    # Receive the data in small chunks and retransmit it
    while True:
      data = connection.recv(16)
      print 'received "%s"' % data
      if data:
        print 'sending data back to the client'
        connection.sendall(data)
      else:
        print 'no more data from', client_address
        break
        
  finally:
    # Clean up the connection
    connection.close()