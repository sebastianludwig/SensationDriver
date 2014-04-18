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
      data = self.receive_bytes(4, client_socket)
      if not data: return
      message_length = int(struct.unpack('!i', data)[0])
      message = self.receive_bytes(message_length, client_socket)
      print 'message %s' % message

    finally:
      client_socket.close()
      
  def receive_bytes(self, number_of_bytes, client_socket):
    print 'trying to receive %d bytes' % number_of_bytes
    bytes_received = 0
    result = ''
    while len(result) < number_of_bytes:
      remaining_bytes = number_of_bytes - len(result)
      recv_bytes = min(remaining_bytes, 16)
      print 'got "%s"...' % result
      print 'remaining %d bytes' % recv_bytes
      data = client_socket.recv(recv_bytes)
      print 'received %s' % data
      if not data: return None
      
      result += data
    print 'finished with "%s"' % result
    return result
    
  def handle_client_new(self, client_socket, client_address):
    print 'connection from', client_address
    try:
      data = ''
      message_size = None
      
      while True:
        new_data = client_socket.recv(16)
        if not new_data:
          break
        
        data += new_data
        
        if message_size == None and len(data) >= 4:
          message_size = int(struct.unpack('!i', data[:4])[0])
          print 'received message of size %d' % message_size
          data = data[4:]
        if not message_size == None and len(data) >= message_size:
          print 'received message %s' % data[:message_size]
          data = data[message_size:]
        
    finally:
      client_socket.close()
    
    
  def loop(self):
    try:
      
      while True:
        # Wait for a connection
        print 'waiting for a connection'
        client_socket, client_address = self.socket.accept()

        self.handle_client_new(client_socket, client_address)
        
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