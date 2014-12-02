#!/usr/bin/env python3.4

import timeit
import line_profiler
import random

class Vibration(object):
    def __init__(self, priority, region, index):
        self.priority = priority
        self.target_region = region
        self.actor_index = index

class DeprecatedFilter(object):

    def _process1(self, vibration_messages):
        result = {}
        for vibration in vibration_messages:
            key = vibration.priority * 10000 + vibration.target_region * 100 + vibration.actor_index
            result[key] = vibration
        
        result = result.values()
        return result

    def filter(self, vibration_messages):
        seen = set()
        for vibration in vibration_messages:
            key = vibration.priority * 10000 + vibration.target_region * 100 + vibration.actor_index
            if key in seen:
                continue
            else:
                seen.add(key)
                yield vibration

    def _process2(self, vibration_messages):
        return list(self.filter(vibration_messages))


    def _process3(self, vibration_messages):
        def key(vibration):
            return vibration.priority * 10000 + vibration.target_region * 100 + vibration.actor_index

        return dict((key(v), v) for v in vibration_messages).values()

    def _process4(self, vibration_messages):
        return dict((v.priority * 10000 + v.target_region * 100 + v.actor_index, v) for v in vibration_messages).values()



random.seed(15)

testdata = []
for i in range(10000):
    testdata.append(Vibration(random.randint(0, 100), random.randint(0, 5), random.randint(0, 10)))


def process1():
    filter = DeprecatedFilter()
    filter._process1(testdata)

def process2():
    filter = DeprecatedFilter()
    filter._process2(testdata)

def process3():
    filter = DeprecatedFilter()
    filter._process3(testdata)

def process4():
    filter = DeprecatedFilter()
    filter._process4(testdata)

runs = 1000
warmups = 100

t = timeit.Timer(process1)
t.timeit(warmups)
print('process1:', t.timeit(runs) / runs)

t = timeit.Timer(process2)
t.timeit(warmups)
print('process2:', t.timeit(runs) / runs)

t = timeit.Timer(process3)
t.timeit(warmups)
print('process3:', t.timeit(runs) / runs)

t = timeit.Timer(process4)
t.timeit(warmups)
print('process4:', t.timeit(runs) / runs)
