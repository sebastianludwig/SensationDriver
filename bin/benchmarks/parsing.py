#!/usr/bin/env python3.4

import os
import time
import timeit
import line_profiler

def relative_path(*segments):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', *segments)

import sys
sys.path.append(relative_path('..', 'src'))

import sensationdriver
from sensationdriver import protocol

raw = []

for i in range(0, 100):
    vibration = protocol.Vibration()
    vibration.target_region = 0
    vibration.actor_index = i
    vibration.priority = i * i
    vibration.intensity = 0.5
    raw.append(vibration)

def serialize():
    return [x.SerializeToString() for x in raw]

def parse(data):
    for message in data:
        protocol.Vibration().ParseFromString(message)


runs = 1000
warmups = 100

t = timeit.Timer(lambda:None)
t.timeit(warmups)
print('noop:', t.timeit(runs) / runs)

t = timeit.Timer(serialize)
t.timeit(warmups)
print('serialize:', t.timeit(runs) / runs / len(raw))

serialized = serialize()
t = timeit.Timer(lambda: parse(serialized))
t.timeit(warmups)
print('parse:', t.timeit(runs) / runs / len(raw))
