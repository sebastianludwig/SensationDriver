import time

class Profiler(object):
    def __init__(self, path):
        self.file = open(path, 'w', 262144)       # 256 KiB buffer

    def __del__(self):
        self.file.close()

    def log(self, action, *text):
        def convert(text):
            return str(text).replace("\n", ';')

        timestamp = round(time.time() * 1000)
        text = (action, timestamp) + text
        self.file.write(';'.join(map(convert, text)) + "\n")
