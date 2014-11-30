#!/usr/bin/env python3.4

import project
import sys
import re
import time
import random

sys.path.append(project.relative_path('src'))

import sensationdriver
from sensationdriver import protocol

if len(sys.argv) < 2:
    raise IndexError("Not enough parameters. Usage: run-client.py <host:string> [<region:int> <actor:int> <priority:int> <intensity:float>]")


client = sensationdriver.Client()
client.connect(sys.argv[1], 10000)

def send(client, target_region, actor_index, priority, intensity, silent=False):
    if not silent:
        print("setting %d.%d => %0.2f @ %d" % (target_region, actor_index, intensity, priority))
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
    time.sleep(1)

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
    print("-----------------------------------------------------------------")
    print("Usage:")
    print("-----------------------------------------------------------------")
    print("set region:      `region = <region:int>`      short: `r=<int>`")
    print("set actor:       `actor = <actor:int>`        short: `a=<int>`")
    print("set priority:    `priority = <priority:int>`  short: `p=<int>`")
    print("set intensity:   `<intensity:float>`          repeat: blank line")
    print("You may omit the equal sign")
    print()
    print("show region:     `region`                     short: `r`")
    print("show actor:      `actor`                      short: `a`")
    print("show priority:   `priority`                   short: `p`")
    print()
    print("test connector:  `test`                       short: `t`")
    print("test region:     `test_region`                short: `tr`")
    print("test all:        `test_all`                   short: `ta`")
    print("manual test:     `test_manual`                short: `tm`")
    print()
    print("profiling:       `profile`                    short: `pro`")
    print("profiling cont.: `profile_cont`               short: `proc`")
    print()
    print("reconnect:       `reconnect`")
    print()
    print("exit:            `exit`, Ctrl+D or Ctrl+C")
    print("-----------------------------------------------------------------")
    print()

    setter_pattern = re.compile('([a-z]+)=?(\d+)')
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
                    else:
                        print("Unknown command:", line)
                elif re.match('[-+]?(\d*[.])?\d+', line):
                    intensity = float(line)
                    send(client, region, actor, priority, intensity)
                elif len(line) == 0:
                    send(client, region, actor, priority, intensity)
                elif line == "exit":
                    break
                elif line == "region" or line == "r":
                    print(region)
                elif line == "actor" or line == "a":
                    print(actor)
                elif line == "priority" or line == "p":
                    print(priority)
                elif line == "test" or line == "t":
                    for i in range(0, 4):
                        index = actor//4*4 + i * 2
                        test(client, region, index, priority, 1)
                elif line == "test_region" or line == "tr":
                    for i in range(0, 18):
                        test(client, region, i, priority, 1)
                elif line == "test_all" or line == "ta":
                    actors_per_region = {   0: 12, 
                                            1: 12, 
                                            2: 7, 
                                            3: 7,
                                            4: 7,
                                            5: 7,
                                            6: 18,
                                            7: 18}
                    for region in range(0, 8):
                        for index in range(0, actors_per_region[region]):
                            test(client, region, index, priority, 1)
                elif line == "test_manual" or line == "tm":
                    print("Press <Enter> to go to next actor, type `stop` to stop.")
                    start = True
                    test_actor = actor
                    for command in sys.stdin:
                        command = command.lower().strip().replace(" ", "")
                        if command == "stop":
                            break
                        if start:
                            send(client, region, test_actor, priority, 0.8)
                        else:
                            send(client, region, test_actor, priority, 0)
                            test_actor = test_actor + 1
                        start = not start
                    send(client, region, test_actor, priority, 0)
                    print("Manual test stopped.")
                elif line == "profile" or line == "pro":
                    random.seed(42)
                    number_of_messages = 5000
                    counter = 0
                    start = time.time() * 1000
                    for i in range(0, number_of_messages - 5):
                        counter += 1
                        send(client, random.randint(0, 1), random.randint(0, 11), priority, random.random(), True)
                    for i in range(0, 5):
                        counter += 1
                        send(client, region, i, priority, 0, True)
                    end = time.time() * 1000
                    print("Finished sending %d messages: %.0f ms" % (counter, end - start))
                elif line == "profile_cont" or line == "proc":
                    random.seed(42)
                    counter = 0
                    start = time.time()
                    try:
                        while True:
                            counter += 1
                            send(client, random.randint(0, 1), random.randint(0, 11), priority, random.random(), True)
                            if counter % 5000 == 0:
                                duration = time.time() - start
                                print("Sent %d messages in %.0f ms" % (counter, duration * 1000))
                                time.sleep(5)
                                counter = 0
                                start = time.time()
                    except KeyboardInterrupt:
                        print("\nStopped")
                    finally:
                        for i in range(0, 5):
                            send(client, region, i, priority, 0, True)
                elif line == "reconnect":
                    client.reconnect()
                else:
                    print("Unknown command:", line)
                        
            except Exception as error:
                print(repr(error))

    except KeyboardInterrupt:
        pass


client.disconnect()

print()
