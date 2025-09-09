from dronekit import connect
import socket
import subprocess
import platform

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
            
            # Network diagnostics
            print("\n🔍 NETWORK DIAGNOSTICS:")
            check_esp32_network_connection()
            
            print("\n🔗 Attempting DroneKit UDP connection...")
            
            # Try all possible UDP connection formats for your ESP32 setup
            udp_attempts = [
                ('udpin:192.168.4.2:14550', 'Listen on laptop IP (Mission Planner style)'),
                ('udp:192.168.4.1:14550', 'Connect to ESP32 IP (original format)'),
                ('udpout:192.168.4.1:14550', 'Send to ESP32 IP'),
                ('udpin:192.168.4.2:14551', 'Try alternate port 14551'),
                ('udpout:192.168.4.1:14551', 'Send to ESP32 alternate port'),
                ('udpin:0.0.0.0:14550', 'Listen on all interfaces'),
                ('tcp:192.168.4.1:14550', 'TCP fallback')
            ]
            
            for connection_string, description in udp_attempts:
                try:
                    print(f"   Trying: {connection_string} ({description})")
                    # Reduce timeout to fail faster and add debugging
                    vehicle = connect(connection_string, wait_ready=False, timeout=15)
                    print(f"🔗 Initial connection established, waiting for heartbeat...")
                    
                    # Wait for heartbeat with custom timeout
                    import time
                    start_time = time.time()
                    heartbeat_timeout = 30
                    
                    while time.time() - start_time < heartbeat_timeout:
                        if hasattr(vehicle, 'last_heartbeat') and vehicle.last_heartbeat:
                            print(f"✅ Connected via {connection_string}!")
                            print(f"   Heartbeat received from system {getattr(vehicle, 'system_id', 'unknown')}")
                            return vehicle
                        time.sleep(0.5)
                    
                    print(f"⚠️  Connection established but no MAVLink heartbeat received in {heartbeat_timeout}s")
                    vehicle.close()
                    raise Exception("No MAVLink heartbeat - flight controller may not be connected to ESP32")
                    
                except Exception as e:
                    print(f"   Failed {connection_string}: {e}")
                    continue
                
            raise Exception("All UDP connection attempts failed")
        except Exception as e:
            print(f"❌ ESP32 WiFi UDP connection failed: {e}")
            print("Make sure you're connected to 'ESP32-AccessPoint' WiFi network")
            print("Falling back to direct serial connection...")
        
        # Fallback to COM3 if UDP fails
        try:
            print("\n🔗 Attempting direct serial connection to flight controller...")
            vehicle = connect('COM3', wait_ready=True, baud=115200, timeout=10)
            print("✅ Connected to flight controller via direct serial (COM3)")
            return vehicle
        except Exception as e:
            print(f"❌ Serial connection also failed: {e}")
            print("Unable to connect to flight controller via ESP32 WiFi UDP or serial")
            return None
    
    return vehicle

def check_esp32_network_connection():
    """
    Check network connectivity to ESP32 access point
    """
    try:
        # Check current WiFi connection
        if platform.system() == "Windows":
            result = subprocess.run(['netsh', 'wlan', 'show', 'interface'], 
                                  capture_output=True, text=True, timeout=5)
            if "ESP32-AccessPoint" in result.stdout:
                print("✅ Connected to ESP32-AccessPoint WiFi")
            else:
                print("⚠️  Not connected to ESP32-AccessPoint WiFi")
                print("   Current connection info:")
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'SSID' in line and 'BSSID' not in line:
                        print(f"   {line.strip()}")
        
        # Ping test to ESP32
        print("📡 Testing ping to ESP32 (192.168.4.1)...")
        if platform.system() == "Windows":
            ping_result = subprocess.run(['ping', '-n', '2', '192.168.4.1'], 
                                       capture_output=True, text=True, timeout=10)
            if ping_result.returncode == 0:
                print("✅ ESP32 is reachable via ping")
            else:
                print("❌ ESP32 not responding to ping")
                print("   This could mean:")
                print("   • ESP32 is not powered on")
                print("   • ESP32 WiFi access point is not active")
                print("   • You're not connected to ESP32-AccessPoint network")
        
        # Test UDP port 14550
        print("🔌 Testing UDP port 14550 on ESP32...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        try:
            # Try to send a test packet
            sock.sendto(b'test', ('192.168.4.1', 14550))
            print("✅ UDP port 14550 appears to be open")
        except socket.timeout:
            print("⚠️  UDP port 14550 timeout - ESP32 may not be running MAVLink bridge")
        except socket.error as e:
            print(f"❌ UDP port 14550 error: {e}")
        finally:
            sock.close()
            
        # Test DroneKit UDP connection format
        print("🔧 Testing DroneKit UDP connection string...")
        try:
            # Test if we can create a UDP socket that DroneKit would use
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Try to bind to the local address DroneKit might use
            test_sock.bind(('0.0.0.0', 0))  # Let system assign port
            test_sock.connect(('192.168.4.1', 14550))
            print("✅ DroneKit-style UDP socket connection test passed")
            local_addr = test_sock.getsockname()
            print(f"   Local address: {local_addr[0]}:{local_addr[1]}")
            test_sock.close()
        except Exception as e:
            print(f"❌ DroneKit-style UDP test failed: {e}")
            print("   This might explain the DroneKit connection issue")
            
        # Test ESP32's expected UDP pattern (Mission Planner style)
        print("🎯 Testing ESP32 Mission Planner UDP pattern...")
        try:
            # Your ESP32 expects to send TO 192.168.4.2:14550 and listen FROM any source
            mp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            mp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            mp_sock.bind(('192.168.4.2', 14550))  # Bind to the IP ESP32 sends to
            mp_sock.settimeout(2)
            
            # Send a test packet to trigger ESP32 response
            mp_sock.sendto(b'test', ('192.168.4.1', 14550))
            
            # Try to receive response
            data, addr = mp_sock.recvfrom(1024)
            print(f"✅ ESP32 Mission Planner pattern works - received from {addr}")
            mp_sock.close()
        except socket.timeout:
            print("⚠️  No response from ESP32 in Mission Planner pattern")
            mp_sock.close()
        except Exception as e:
            print(f"❌ ESP32 Mission Planner pattern failed: {e}")
            try:
                mp_sock.close()
            except:
                pass
        
        # Test for actual MAVLink messages
        print("📡 Testing for MAVLink messages from ESP32...")
        test_mavlink_messages()
            
    except Exception as e:
        print(f"❌ Network diagnostic failed: {e}")

def test_mavlink_messages():
    """
    Test if ESP32 is forwarding actual MAVLink messages
    """
    import time
    try:
        import struct
        
        # Listen for MAVLink messages on the expected port
        mavlink_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mavlink_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mavlink_sock.bind(('192.168.4.2', 14550))
        mavlink_sock.settimeout(5)
        
        print("   Listening for MAVLink messages for 5 seconds...")
        mavlink_count = 0
        heartbeat_count = 0
        
        start_time = time.time()
        while time.time() - start_time < 5:
            try:
                data, addr = mavlink_sock.recvfrom(1024)
                
                # Check if this looks like a MAVLink message
                if len(data) >= 8 and data[0] in [0xFE, 0xFD]:  # MAVLink v1 or v2 magic bytes
                    mavlink_count += 1
                    
                    # Check if it's a heartbeat message (msg_id = 0)
                    if data[0] == 0xFE and len(data) >= 8:  # MAVLink v1
                        msg_id = struct.unpack('<B', data[5:6])[0]
                        if msg_id == 0:
                            heartbeat_count += 1
                    elif data[0] == 0xFD and len(data) >= 10:  # MAVLink v2
                        msg_id = struct.unpack('<I', data[7:10] + b'\x00')[0] & 0xFFFFFF
                        if msg_id == 0:
                            heartbeat_count += 1
                            
            except socket.timeout:
                continue
        
        mavlink_sock.close()
        
        if mavlink_count > 0:
            print(f"✅ Received {mavlink_count} MAVLink messages ({heartbeat_count} heartbeats)")
            if heartbeat_count == 0:
                print("⚠️  No heartbeat messages - flight controller may not be connected")
            else:
                print("✅ Flight controller is sending heartbeats through ESP32")
        else:
            print("❌ No MAVLink messages received")
            print("   This means:")
            print("   • Flight controller is not connected to ESP32")
            print("   • ESP32 MAVLink bridge is not running")
            print("   • Wrong baud rate or serial connection on ESP32")
            
    except Exception as e:
        print(f"❌ MAVLink message test failed: {e}")

def get_current_location():
    """
    Get current location from the flight controller
    Returns GPS coordinates from the autopilot via MAVLink
    """
    v = connect_vehicle()
    if v is None:
        return (0, 0)
    
    loc = v.location.global_frame
    # Handle None values when GPS doesn't have a fix
    lat = loc.lat if loc.lat is not None else 0
    lon = loc.lon if loc.lon is not None else 0
    
    return lat, lon
