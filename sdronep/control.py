# control.py
"""
Low-level functions to connect to the drone and set flight modes.
Abstracts DroneKit's connect() for cleaner usage.
"""

from dronekit import connect

def connect_vehicle(conn_str="udp:127.0.0.1:14550", wait_ready=True):
    """
    Connect to a vehicle using the specified connection string.
    """
    return connect(conn_str, wait_ready=wait_ready)
