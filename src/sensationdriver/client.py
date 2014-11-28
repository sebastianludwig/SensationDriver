import socket
import struct
import sys

class Client:
    def __init__(self):
        self.host = None
        self.port = None

    def __del__(self):
        self.socket.close()

    def connect(self, host, port):
        self.host = host
        self.port = port
        self.reconnect()

    def disconnect(self):
        self.socket.close()

    def reconnect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

    def send(self, message):
        try:
            message_length = struct.pack('!i', len(message))  # message length as network formatted (big-endian) byte array
            self.socket.sendall(message_length)
            self.socket.sendall(message)
        except BrokenPipeError as error:
            print(error, file=sys.stderr)
            print("reconnecting...")
            self.reconnect()
            self.socket.sendall(message_length)
            self.socket.sendall(message)

