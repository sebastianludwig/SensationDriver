#!/usr/bin/env python3.4

import project
import sys
import re
sys.path.append(project.relative_path('src'))

import time

import sensationdriver
from sensationdriver import protocol

if len(sys.argv) < 2:
    raise IndexError("Not enough parameters. Usage: run-client.py <host:string> [<region:int> <actor:int> <priority:int> <intensity:float>]")


client = sensationdriver.Client()
client.connect(sys.argv[1], 10000)

def send(client, target_region, actor_index, priority, intensity):
    print("setting %d.%d -> %0.2f @ %d" % (target_region, actor_index, intensity, priority))
    vibration = protocol.Vibration()
    vibration.target_region = target_region
    vibration.actor_index = actor_index
    vibration.priority = priority
    vibration.intensity = intensity

    message = protocol.Message()
    message.type = protocol.Message.VIBRATION    
    message.vibration.CopyFrom(vibration)
    client.send(message.SerializeToString())

def test(client, region, index, priority, intensity):
    print("testing actor %d ..." % index)
    print("...", end="", flush=True)
    send(client, region, index, priority, intensity)

    print("...waiting...")
    time.sleep(0.5)

    print("...", end="", flush=True)
    send(client, region, index, priority, 0)
    print("...done")
    print()
    

if len(sys.argv) >= 3:
    region = int(sys.argv[2])
else:
    region = 0

if len(sys.argv) >= 4:
    actor = int(sys.argv[3])
else:
    actor = 0

if len(sys.argv) >= 5:
    priority = int(sys.argv[4])
else:
    priority = 100

if len(sys.argv) >= 6:
    intensity = float(sys.argv[5])
else:
    intensity = 0


if len(sys.argv) == 6:
    send(client, region, actor, priority, intensity)
else:                       # interactive mode
    print("Usage:")
    print("set region:      `region = <region:int>`      short: `r=<int>`")
    print("set actor:       `actor = <actor:int>`        short: `a=<int>`")
    print("set priority:    `priority = <priority:int>`  short: `p=<int>`")
    print("set intensity:   `<intensity:float>`          repeat: blank line")
    print("test connector:  `test`                       short: `t`")
    print("test region:     `test_region`                short: `tr`")
    print("exit:            `exit`, Ctrl+D or Ctrl+C")
    print()

    setter_pattern = re.compile('(\w+)=(\w+)')
    try:
        for line in sys.stdin:
            try:
                line = line.lower().strip().replace(" ", "")
                setter = setter_pattern.match(line)
                if setter:
                    if setter.group(1) == "region" or setter.group(1) == "r":
                        region = int(setter.group(2))
                    elif setter.group(1) == "actor" or setter.group(1) == "a":
                        actor = int(setter.group(2))
                    elif setter.group(1) == "priority" or setter.group(1) == "p":
                        priority = int(setter.group(2))
                elif re.match('[-+]?(\d*[.])?\d+', line):
                    intensity = float(line)
                    send(client, region, actor, priority, intensity)
                elif len(line) == 0:
                    send(client, region, actor, priority, intensity)
                elif line == "exit":
                    break
                elif line == "test" or line == "t":
                    for i in range(0, 4):
                        index = actor//4*4 + i * 2
                        test(client, region, index, priority, intensity)
                elif line == "test_region" or line == "tr":
                    for i in range(0, 16):
                        test(client, region, i, priority, intensity)
                        
            except Exception as error:
                print(repr(error))

    except KeyboardInterrupt:
        pass


client.disconnect()

print()
