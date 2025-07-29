from dronekit import connect

vehicle = None

def connect_vehicle():
    """Connect to the vehicle if not already connected"""
    global vehicle
    if vehicle is None:
        try:
            vehicle = connect('COM3', wait_ready=True, baud=57600)
            print("Connected to vehicle on COM3")
        except Exception as e:
            print(f"Failed to connect to vehicle: {e}")
            return None
    return vehicle

def get_current_location():
    """Get current location from the vehicle"""
    v = connect_vehicle()
    if v is None:
        return (0, 0)
    
    loc = v.location.global_frame
    return loc.lat, loc.lon
