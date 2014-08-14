#!/usr/bin/env python3.4

import project
import sys
sys.path.append(project.relative_path('src'))

import time

import sensationdriver
from sensationdriver import protocol

if len(sys.argv) < 4:
    raise IndexError("Not enough parameters. Usage: run-client.py <host:string> <region:int> <actor:int> [<priority:int>]")


vibration = protocol.Vibration()
vibration.target_region = int(sys.argv[2])
vibration.actor_index = int(sys.argv[3])
if len(sys.argv) >= 5:
    vibration.priority = int(sys.argv[4])


message = protocol.Message()
message.type = protocol.Message.VIBRATION


client = sensationdriver.Client()
client.connect(sys.argv[1], 10000)

print("Intensity: ", end="", flush=True)
for line in sys.stdin:
    vibration.intensity = float(line)
    message.vibration.CopyFrom(vibration)
    client.send(message.SerializeToString())
    print("Intensity: ", end="", flush=True)

client.disconnect()

print("")
