# hello.py
"""
Simple example to demonstrate connecting to a drone (or SITL),
and printing basic vehicle information.
"""

import dronekit_sitl
from dronekit import connect

# Start SITL (Software In The Loop simulator)
print("Starting simulator...")
sitl = dronekit_sitl.start_default()
connection_string = sitl.connection_string()

# Connect to the vehicle
print(f"Connecting to vehicle on: {connection_string}")
vehicle = connect(connection_string, wait_ready=True)

# Print example attribute
print("GPS info:", vehicle.gps_0)

# Close connection
vehicle.close()
sitl.stop()
print("Finished.")
