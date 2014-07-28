class I2C(object):
    @staticmethod
    def getPiRevision():
        return 0

    @classmethod
    def getPiI2CBusNumber(cls):
        # Gets the I2C bus number /dev/i2c#
        return 1 if cls.getPiRevision() > 1 else 0

    @classmethod
    def isDeviceAnswering(cls, address):
        return True

    def __init__(self, address, busnum=-1, debug=False, logger=None):
        pass
