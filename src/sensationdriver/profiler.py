import time
import itertools

class Profiler(object):
    def __init__(self):
        self.entries = []

    def save_data(self, path):
        def flatten(entry):
            return itertools.chain(entry[:2], entry[2])

        def convert(entry):
            return ';'.join(str(element).replace("\n", ';') for element in entry)


        with open(path, 'w') as f:
            entries = map(convert, map(flatten, self.entries))
            f.write("\n".join(entries))

    def log(self, action, *text):
        self.entries.append((action, time.time() * 1000, text))
        
