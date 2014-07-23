#!/usr/bin/env python3.4

import project
import sys
sys.path.append(project.relative_path('src'))

import sensationdriver
from sensationdriver.protocol import sensationprotocol_pb2 as sensationprotocol

if len(sys.argv) < 5:
  raise IndexError("Not enough parameters. Usage: run-client.py <host:string> <region:int> <actor:int> <intensity:float:[0-1]")

client = sensationdriver.Client()
client.connect(sys.argv[1], 10000)


sensation = sensationprotocol.Sensation()
sensation.region = int(sys.argv[2])
sensation.actor_index = int(sys.argv[3])
sensation.intensity = float(sys.argv[4])


client.send(sensation.SerializeToString())

client.disconnect()