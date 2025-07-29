# flight.py
"""
Contains functions to perform basic drone flight operations using DroneKit.
Includes methods for arming, takeoff, landing, and setting flight modes.
"""

from dronekit import connect, VehicleMode, LocationGlobalRelative, mavutil
import time
import requests
import json

vehicle = connect('COM3', wait_ready=True, baud=57600)

def get_location_from_endpoint():
    """
    Fetches the current location from the /location endpoint.
    Returns (lat, lon) tuple or (0, 0) if request fails.
    """
    try:
        response = requests.get('http://localhost:5000/location', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return (data['lat'], data['lon'])
        else:
            print(f"Failed to get location: HTTP {response.status_code}")
            return (0, 0)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching location: {e}")
        return (0, 0)

def arm_and_takeoff(aTargetAltitude):
    """
    Arms vehicle and fly to aTargetAltitude.
    """

    print("Basic pre-arm checks")
    # Don't try to arm until autopilot is ready
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialise...")
        time.sleep(1)

    print("Arming motors")
    # Copter should arm in GUIDED mode
    vehicle.mode    = VehicleMode("GUIDED")
    vehicle.armed   = True

    # Confirm vehicle armed before attempting to take off
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)

    print("Taking off!")
    vehicle.simple_takeoff(aTargetAltitude) # Take off to target altitude

    # Wait until the vehicle reaches a safe height before processing the goto (otherwise the command
    #  after Vehicle.simple_takeoff will execute immediately).
    while True:
        print(" Altitude: ", vehicle.location.global_relative_frame.alt)
        #Break and return from function just below target altitude.
        if vehicle.location.global_relative_frame.alt>=aTargetAltitude*0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

arm_and_takeoff(20)

try: 
    while True:
        location = get_location_from_endpoint()
        print(f"Current target location: {location}")
        
        if location != (0, 0):  # Only navigate if we have a valid location
            vehicle.simple_goto(LocationGlobalRelative(location[0], location[1], 20))
        else:
            print("No valid location received, staying in current position")
        
        time.sleep(2)  # Wait 2 seconds before fetching location again
except KeyboardInterrupt:
    print("Landing...")
    vehicle.mode = VehicleMode("LAND")
    time.sleep(5)

vehicle.close()
print("Vehicle connection closed.")