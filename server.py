#! python

import sensationserver
import messagehandler

server = sensationserver.SensationServer()
server.handler = messagehandler.MessageHandler()
server.listen('localhost', 10000)
server.loop()
