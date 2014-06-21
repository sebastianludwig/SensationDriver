#!/usr/bin/env python

import sys
import democlient
import sensationprotocol_pb2 as sensationprotocol

client = democlient.DemoClient()
client.connect('sensationdriver.local', 10000)


command = sensationprotocol.Command()
command.region = int(sys.argv[1])
command.actor_index = int(sys.argv[2])
command.intensity = float(sys.argv[3])


client.send(command.SerializeToString())

client.disconnect()