from dronekit import connect

vehicle = None

def connect_vehicle():
    """
    Connect to the flight controller via ESP32 WiFi Access Point using UDP
    Primary: UDP connection via ESP32 Access Point (ESP32-AccessPoint network)
    Fallback: COM3 serial connection if UDP fails
    
    Network Setup:
    - Connect to WiFi: ESP32-AccessPoint (password: esp32password)
    - ESP32 IP: 192.168.4.1 (Access Point)
    - Laptop IP: 192.168.4.2 (when connected to ESP32 AP)
    - Protocol: UDP on port 14550
    """
    global vehicle
    if vehicle is None:
        # Try UDP connection first (ESP32 WiFi Access Point)
        try:
            print("Attempting to connect to flight controller via ESP32 WiFi Access Point...")
            print("Make sure you're connected to WiFi network: ESP32-AccessPoint")
            vehicle = connect('udp:192.168.4.1:14550', wait_ready=True, timeout=10)
            print("Connected to flight controller via ESP32 WiFi AP on UDP 192.168.4.1:14550")
            return vehicle
        except Exception as e:
            print(f"ESP32 WiFi UDP connection failed: {e}")
            print("Make sure you're connected to 'ESP32-AccessPoint' WiFi network")
            print("Falling back to direct serial connection (COM3)...")
        
        # Fallback to COM3 if UDP fails
        try:
            print("Attempting direct serial connection to flight controller...")
            vehicle = connect('COM3', wait_ready=True, baud=57600, timeout=10)
            print("Connected to flight controller via direct serial (COM3)")
            return vehicle
        except Exception as e:
            print(f"Serial connection also failed: {e}")
            print("Unable to connect to flight controller via ESP32 WiFi UDP or serial")
            return None
    
    return vehicle

def get_current_location():
    """
    Get current location from the flight controller
    Returns GPS coordinates from the autopilot via MAVLink
    """
    v = connect_vehicle()
    if v is None:
        return (0, 0)
    
    loc = v.location.global_frame
    return loc.lat, loc.lon
