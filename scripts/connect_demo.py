# connect_demo.py
"""
Connects to the drone and prints basic status info.
Used for testing communication and setup.
"""

from sdronep.control import connect_vehicle

vehicle = connect_vehicle()
print(f"Connected to: {vehicle.version}")
print(f"GPS: {vehicle.gps_0}")
vehicle.close()
