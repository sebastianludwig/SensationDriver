#! python

import sys
import democlient
import sensationprotocol_pb2 as sensationprotocol

client = democlient.DemoClient()
client.connect('sensationdriver.local', 10000)


command = sensationprotocol.Command()
command.region = sensationprotocol.Command.LEFT_HAND
command.actor_index = 0
command.intensity = float(sys.argv[1])


client.send(command.SerializeToString())

client.disconnect()