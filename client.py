#! python

import democlient
import sensationprotocol_pb2 as sensationprotocol

client = democlient.DemoClient()
client.connect('localhost', 10000)


command = sensationprotocol.Command()
command.region = sensationprotocol.Command.LEFT_HAND
command.actor_index = 1
command.intensity = 0.2


client.send(command.SerializeToString())

client.disconnect()