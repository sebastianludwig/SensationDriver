#! python

import socket

import sensationserver
import messagehandler

server = sensationserver.SensationServer()
server.handler = messagehandler.MessageHandler()
server.listen('', 10000)
server.loop()
