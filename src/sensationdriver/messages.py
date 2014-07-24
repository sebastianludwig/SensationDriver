import logging
from .protocol import sensationprotocol_pb2 as sensationprotocol

from . import platform


class Logger:
    def __init__(self, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('root')

    def set_up(self):
        pass

    def tear_down(self):
        pass

    def process_message(self, message):
        sensation = sensationprotocol.Sensation()
        sensation.ParseFromString(message)

        self.logger.info('received sensation:\n--\n%s--', sensation)

if platform.is_raspberry():
    from adafruit import pca9685
    from adafruit import wirebus

    class Handler:
        def __init__(self, logger=None):
            self.logger = logger if logger is not None else logging.getLogger('root')
            pca9685.Driver.softwareReset()
            self.__prepare_drivers()

        def __prepare_drivers(self):
            self.drivers = {}

            mapping = {
                sensationprotocol.Sensation.LEFT_HAND:      0x40,
                sensationprotocol.Sensation.LEFT_FOREARM:   0x41,
                sensationprotocol.Sensation.LEFT_UPPER_ARM: 0x42
            }

            for (region, address) in mapping.items():
                if not wirebus.I2C.isDeviceAnswering(address):
                    self.logger.warning("No driver found for at address 0x%02X for region %d", address, region)
                    continue

                driver = pca9685.Driver(address, debug=True, logger=self.logger)
                # TODO use ALLCALL address
                driver.setPWMFreq(1700)                        # Set max frequency to (~1,6kHz)
                self.drivers[region] = driver

        def set_up(self):
            for driver in self.drivers.values():
                driver.setAllPWM(0, 0)

        def tear_down(self):
            if not __debug__:
                for driver in self.drivers.itervalues():
                    driver.setAllPWM(0, 0)

        def process_message(self, message):
            sensation = sensationprotocol.Sensation()
            sensation.ParseFromString(message)

            self.logger.debug('received sensation:\n--\n%s--', sensation)

            if sensation.region in self.drivers:
                self.drivers[sensation.region].setPWM(sensation.actor_index, 0, int(sensation.intensity * 4096))
