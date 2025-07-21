from dronekit import connect
import time

vehicle = connect('tcp:172.16.0.55:14550', wait_ready=True)

try:
    while True:
        print("Location:", vehicle.location.global_frame)
        print("Attitude:", vehicle.attitude)
        print("Battery:", vehicle.battery)
        print("GPS:", vehicle.gps_0)
        print("Speed:", vehicle.groundspeed)
        time.sleep(2)
except KeyboardInterrupt:
    print("Exiting")
finally:
    pass