#! python

import socket
import struct

class DemoClient:
  def __init__(self):
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
  def __del__(self):
    self.socket.close()
    
  def connect(self, host, port):
    self.socket.connect((host, port))
  
  def disconnect(self):
    self.socket.close()
  
  def send(self, message):
    message_length = struct.pack('!i', len(message))  # message length as network formatted (big-endian) byte array
    self.socket.sendall(message_length)
    self.socket.sendall(message)
    

client = DemoClient()
client.connect('localhost', 10000)

client.send('whatever this is')
client.send('something else')

client.disconnect()


exit()
# -----------------------


# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
server_address = ('localhost', 10000)
print 'connecting to %s port %s' % server_address
sock.connect(server_address)

try:
  # Send data
  message = 'This is the message.  It will be repeated.'
  print'sending "%s"' % message
  sock.sendall(message)

  # Look for the response
  amount_received = 0
  amount_expected = len(message)
    
  while amount_received < amount_expected:
    data = sock.recv(16)
    amount_received += len(data)
    print 'received "%s"' % data

finally:
  sock.close()
  sock.close()
  print 'closing socket'
  sock.close()