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
