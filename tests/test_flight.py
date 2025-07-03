# test_flight.py
"""
Unit tests for the flight.py module.
Test cases include takeoff, landing, and connection verification.
"""

import unittest
from dronekit import connect
# from sdronep.flight import arm_and_takeoff  # Uncomment when implemented

class TestFlightFunctions(unittest.TestCase):
    def setUp(self):
        # Start SITL for test environment
        import dronekit_sitl
        self.sitl = dronekit_sitl.start_default()
        self.vehicle = connect(self.sitl.connection_string(), wait_ready=True)

    def tearDown(self):
        self.vehicle.close()
        self.sitl.stop()

    def test_connection(self):
        self.assertIsNotNone(self.vehicle)

    # def test_takeoff(self):
    #     arm_and_takeoff(self.vehicle, 10)
    #     self.assertGreaterEqual(self.vehicle.location.global_relative_frame.alt, 9.5)

if __name__ == '__main__':
    unittest.main()
