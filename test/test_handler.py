import yaml

from utils import *

from sensationdriver import handler

class TestActorConfigParsing(unittest.TestCase):
    def test_simple_parsing(self):
        config = """{
                        "vibration": {
                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        },
                                        {
                                            "position": "index finger",
                                            "index": 1,
                                            "outlet": 1
                                        }
                                    ]
                                },
                                {
                                    "name": "RIGHT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x41",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        },
                                        {
                                            "position": "index finger",
                                            "index": 1,
                                            "outlet": 1
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = handler.parse_actor_config(config)
        self.assertEqual(len(result['drivers']), 2)
        self.assertEqual(len(result['regions']), 2)
        self.assertEqual(len(result['regions']['LEFT_HAND']), 2)
        self.assertEqual(len(result['regions']['RIGHT_HAND']), 2)

    def test_driver_reusage(self):
        # two regions, same driver
        config = """{
                        "vibration": {
                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        }
                                    ]
                                },
                                {
                                    "name": "LEFT_FOREARM",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "index finger",
                                            "index": 1,
                                            "outlet": 1
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = handler.parse_actor_config(config)
        self.assertEqual(len(result['drivers']), 1)
        self.assertEqual(len(result['regions']), 2)
        self.assertEqual(result['regions']['LEFT_HAND'][0].driver, result['regions']['LEFT_FOREARM'][0].driver)

    def test_region_merging(self):
        # one region, split into two definitions (different drivers)
        config = """{
                        "vibration": {
                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        }
                                    ]
                                },
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x41",
                                    "actors": [
                                        {
                                            "position": "index finger",
                                            "index": 1,
                                            "outlet": 1
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = handler.parse_actor_config(config)
        self.assertEqual(len(result['drivers']), 2)
        self.assertEqual(len(result['regions']), 1)
        self.assertEqual(len(result['regions']['LEFT_HAND']), 2)
        self.assertNotEqual(result['regions']['LEFT_HAND'][0].driver, result['regions']['LEFT_HAND'][1].driver)

    def test_global_actor_settings(self):
        config = """{
                        "vibration": {
                            "actor_mapping_curve_degree": 42,
                            "actor_min_intensity": 43,
                            "actor_min_intensity_warmup": 44,
                            "actor_min_instant_intensity": 45,

                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = handler.parse_actor_config(config, logger=TestLogger())

        actor = result['regions']['LEFT_HAND'][0]
        self.assertEqual(actor.mapping_curve_degree, 42)
        self.assertEqual(actor.min_intensity, 43)
        self.assertEqual(actor.min_intensity_warmup, 44)
        self.assertEqual(actor.min_instant_intensity, 45)

    def test_region_actor_settings(self):
        config = """{
                        "vibration": {
                            "actor_mapping_curve_degree": 42,
                            "actor_min_intensity": 43,
                            "actor_min_intensity_warmup": 44,
                            "actor_min_instant_intensity": 45,

                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    
                                    "actor_mapping_curve_degree": 52,
                                    "actor_min_intensity": 53,
                                    "actor_min_intensity_warmup": 54,
                                    "actor_min_instant_intensity": 55,

                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = handler.parse_actor_config(config, logger=TestLogger())

        actor = result['regions']['LEFT_HAND'][0]
        self.assertEqual(actor.mapping_curve_degree, 52)
        self.assertEqual(actor.min_intensity, 53)
        self.assertEqual(actor.min_intensity_warmup, 54)
        self.assertEqual(actor.min_instant_intensity, 55)

    def test_local_actor_settings(self):
        config = """{
                        "vibration": {
                            "actor_mapping_curve_degree": 42,
                            "actor_min_intensity": 43,
                            "actor_min_intensity_warmup": 44,
                            "actor_min_instant_intensity": 45,

                            "regions": [
                                {
                                    "name": "LEFT_HAND",
                                    "i2c_bus_number": 1,
                                    "driver_address": "0x40",
                                    
                                    "actor_mapping_curve_degree": 52,
                                    "actor_min_intensity": 53,
                                    "actor_min_intensity_warmup": 54,
                                    "actor_min_instant_intensity": 55,

                                    "actors": [
                                        {
                                            "position": "thumb",
                                            "index": 0,
                                            "outlet": 0,

                                            "mapping_curve_degree": 62,
                                            "min_intensity": 63,
                                            "min_intensity_warmup": 64,
                                            "min_instant_intensity": 65,
                                        }
                                    ]
                                }
                            ]
                        }
                    }"""
        config = yaml.load(config)

        result = handler.parse_actor_config(config, logger=TestLogger())

        actor = result['regions']['LEFT_HAND'][0]
        self.assertEqual(actor.mapping_curve_degree, 62)
        self.assertEqual(actor.min_intensity, 63)
        self.assertEqual(actor.min_intensity_warmup, 64)
        self.assertEqual(actor.min_instant_intensity, 65)
