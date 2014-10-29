class I2C(object):
    @staticmethod
    def getPiRevision():
        return 0

    @classmethod
    def initialize(cls, logger=None):
        pass

    @classmethod
    def getPiDefaultI2CBusNumber(cls):
        "Returns the default I2C bus number /dev/i2c#"
        return 0 if cls.getPiRevision() == 1 else 1

    @classmethod
    def isDeviceAnswering(cls, address):
        return True

    def __init__(self, address, busnum=-1, debug=False, logger=None):
        pass
