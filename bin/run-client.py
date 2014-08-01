#!/usr/bin/env python3.4

import project
import sys
sys.path.append(project.relative_path('src'))

import sensationdriver
from sensationdriver.protocol import sensationprotocol_pb2 as sensationprotocol

if len(sys.argv) < 5:
    raise IndexError("Not enough parameters. Usage: run-client.py <host:string> <region:int> <actor:int> <intensity:float:[0-1]> [<priority:int>]")


vibration = sensationprotocol.Vibration()
vibration.target_region = int(sys.argv[2])
vibration.actor_index = int(sys.argv[3])
vibration.intensity = float(sys.argv[4])
if len(sys.argv) >= 6:
    vibration.priority = int(sys.argv[5])


message = sensationprotocol.Message()
message.type = sensationprotocol.Message.VIBRATION
message.vibration.CopyFrom(vibration)



client = sensationdriver.Client()
client.connect(sys.argv[1], 10000)

client.send(message.SerializeToString())


client.disconnect()
