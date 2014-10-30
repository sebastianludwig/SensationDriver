class I2C(object):
    @staticmethod
    def _piRevision():
        return 2

    @classmethod
    def defaultBusNumber(cls):
        "Returns the default I2C bus number /dev/i2c#"
        return 1

    @classmethod
    def pinoutConfiguredBuses(cls):
        return [0, 1]

    @classmethod
    def configurePinouts(cls, logger=None):
        pass

    @classmethod
    def isDeviceAnswering(cls, address, busnum=-1):
        return True


    def __init__(self, address, busnum=-1, debug=False, logger=None):
        pass
