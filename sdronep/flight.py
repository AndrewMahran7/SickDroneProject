import sdronep
from dronekit import connect, VehicleMode, LocationGlobalRelative
from datetime import time

class Flyer:
    vehicle = None
    def __init__(self, port='tcp:127.0.0.1:5760'):
        try:
            self.vehicle = connect(port, wait_ready=True)
        except:
            pass

    def arm_and_takeoff(self, aTargetAltitude):
        print("Basic pre-arm checks")

        # Don't try to arm until autopilot is ready
        while not self.vehicle.is_armable:
            print(" Waiting for vehicle to initialise...")
            time.sleep(1)

        print ("Arming motors")
        # Copter should arm in GUIDED mode
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.armed = True

        # Confirm vehicle armed before attempting to take off
        while not self.vehicle.armed:
            print("Waiting for arming...")
            time.sleep(1)

        print("Taking off!")
        self.vehicle.simple_takeoff(aTargetAltitude) # Take off to target altitude

        # Wait until the vehicle reaches a safe height before processing the goto (otherwise the command
        #  after Vehicle.simple_takeoff will execute immediately).
        while True:
            print(" Altitude: "), self.vehicle.location.global_relative_frame.alt
            #Break and return from function just below target altitude.
            if self.vehicle.location.global_relative_frame.alt>=aTargetAltitude*0.95:
                print( "Reached target altitude")
                break
            time.sleep(1)
    
    def __str__(self):
        return ("Correctly created Flyer")

        