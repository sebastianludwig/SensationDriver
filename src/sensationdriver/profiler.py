
import time
import datetime

class Profiler(object):
    def __init__(self):
        path = "sensation_server_profile_{:%Y%m%d_%H%M}.txt".format(datetime.datetime.now())
        self.file = open(path, 'w', 262144)       # 256 KiB buffer

    def __del__(self):
        self.file.close()

    def log(self, *text):
        def convert(text):
            return str(text).replace("\n", ';')

        timestamp = round(time.time() * 1000)
        self.file.write(str(timestamp) + ';' + ';'.join(map(convert, text)) + "\n")
