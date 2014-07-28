class Driver(object):
    @classmethod
    def softwareReset(cls):
        pass

    def __init__(self, address=0x40, debug=False, logger=None):
        pass

    def wakeUp(self):
        pass

    def sleep(self):
        pass

    def setPWMFreq(self, freq):
        pass

    def setPWM(self, channel, on, off):
        pass

    def setAllPWM(self, on, off):
        pass
