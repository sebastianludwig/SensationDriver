#!/usr/bin/env python

import sys
import democlient
import sensationprotocol_pb2 as sensationprotocol

client = democlient.DemoClient()
client.connect('sensationdriver.local', 10000)


sensation = sensationprotocol.Sensation()
sensation.region = int(sys.argv[1])
sensation.actor_index = int(sys.argv[2])
sensation.intensity = float(sys.argv[3])


client.send(sensation.SerializeToString())

client.disconnect()