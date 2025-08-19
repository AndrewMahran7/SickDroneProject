#!/usr/bin/env python3
"""
Debug script for ESP32 MAVLink connection issues
This script helps diagnose why DroneKit can't connect to the ESP32
"""

import socket
import time
import struct
import subprocess
import platform

def check_wifi_connection():
    """Check if connected to ESP32-AccessPoint"""
    print("🔍 Checking WiFi Connection...")
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['netsh', 'wlan', 'show', 'interface'], 
                                  capture_output=True, text=True, timeout=5)
            if "ESP32-AccessPoint" in result.stdout:
                print("✅ Connected to ESP32-AccessPoint WiFi")
                return True
            else:
                print("❌ Not connected to ESP32-AccessPoint WiFi")
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'SSID' in line and 'BSSID' not in line:
                        print(f"   Current: {line.strip()}")
                return False
    except Exception as e:
        print(f"❌ WiFi check failed: {e}")
        return False

def test_ping():
    """Test if ESP32 responds to ping"""
    print("\n📡 Testing ESP32 Connectivity...")
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['ping', '-n', '3', '192.168.4.1'], 
                                   capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                print("✅ ESP32 responds to ping")
                return True
            else:
                print("❌ ESP32 not responding to ping")
                print("   Check: ESP32 power, WiFi AP mode, network settings")
                return False
    except Exception as e:
        print(f"❌ Ping test failed: {e}")
        return False

def test_udp_echo():
    """Test basic UDP communication"""
    print("\n🔌 Testing UDP Communication...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        
        # Send test message
        test_msg = b"HELLO_ESP32"
        sock.sendto(test_msg, ('192.168.4.1', 14550))
        
        # Try to receive response
        try:
            data, addr = sock.recvfrom(1024)
            print(f"✅ UDP response from {addr}: {len(data)} bytes")
            return True
        except socket.timeout:
            print("⚠️  No UDP response (normal if ESP32 only forwards MAVLink)")
            return True  # This is actually OK
        finally:
            sock.close()
            
    except Exception as e:
        print(f"❌ UDP test failed: {e}")
        return False

def listen_for_mavlink(duration=10):
    """Listen for MAVLink messages"""
    print(f"\n📻 Listening for MAVLink messages ({duration} seconds)...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('192.168.4.2', 14550))  # Bind to laptop IP
        sock.settimeout(1)
        
        mavlink_count = 0
        heartbeat_count = 0
        other_msgs = []
        
        print("   Waiting for messages...")
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                data, addr = sock.recvfrom(1024)
                
                # Check for MAVLink magic bytes
                if len(data) >= 6 and data[0] in [0xFE, 0xFD]:
                    mavlink_count += 1
                    
                    # Parse message type
                    if data[0] == 0xFE:  # MAVLink v1
                        if len(data) >= 8:
                            msg_id = struct.unpack('<B', data[5:6])[0]
                            if msg_id == 0:
                                heartbeat_count += 1
                            elif msg_id not in [msg[0] for msg in other_msgs]:
                                other_msgs.append((msg_id, f"v1_msg_{msg_id}"))
                    
                    elif data[0] == 0xFD:  # MAVLink v2
                        if len(data) >= 10:
                            msg_id = struct.unpack('<I', data[7:10] + b'\x00')[0] & 0xFFFFFF
                            if msg_id == 0:
                                heartbeat_count += 1
                            elif msg_id not in [msg[0] for msg in other_msgs]:
                                other_msgs.append((msg_id, f"v2_msg_{msg_id}"))
                
                else:
                    print(f"   Non-MAVLink data from {addr}: {data[:20]}...")
                    
            except socket.timeout:
                continue
                
        sock.close()
        
        print(f"\n📊 Results:")
        print(f"   Total MAVLink messages: {mavlink_count}")
        print(f"   Heartbeat messages: {heartbeat_count}")
        print(f"   Other message types: {len(other_msgs)}")
        
        if other_msgs:
            print("   Message types seen:", [msg[1] for msg in other_msgs[:5]])
        
        if mavlink_count == 0:
            print("\n❌ NO MAVLINK MESSAGES DETECTED")
            print("   Possible causes:")
            print("   • Flight controller not connected to ESP32")
            print("   • ESP32 not running MAVLink bridge code") 
            print("   • Wrong serial baud rate (should be 57600 or 115200)")
            print("   • ESP32 code not configured for UDP forwarding")
            return False
            
        elif heartbeat_count == 0:
            print("\n⚠️  MAVLink data but no heartbeats")
            print("   Flight controller may be in wrong mode")
            return False
            
        else:
            print("\n✅ MAVLink heartbeats detected - ESP32 bridge working!")
            return True
            
    except Exception as e:
        print(f"❌ MAVLink listening failed: {e}")
        return False

def test_dronekit_simple():
    """Test DroneKit connection with minimal setup"""
    print("\n🔗 Testing DroneKit Connection...")
    try:
        from dronekit import connect
        
        # Try the most promising connection string based on our tests
        connection_string = 'udpin:192.168.4.2:14550'
        print(f"   Attempting: {connection_string}")
        
        vehicle = connect(connection_string, wait_ready=False, timeout=10)
        print("   Connection object created, checking for heartbeat...")
        
        # Wait for heartbeat manually
        start_time = time.time()
        while time.time() - start_time < 15:
            try:
                if hasattr(vehicle, 'last_heartbeat') and vehicle.last_heartbeat:
                    print(f"✅ DroneKit connected successfully!")
                    print(f"   System ID: {getattr(vehicle, 'system_id', 'unknown')}")
                    print(f"   Vehicle mode: {getattr(vehicle, 'mode', 'unknown')}")
                    vehicle.close()
                    return True
            except:
                pass
            time.sleep(0.5)
        
        print("❌ DroneKit timeout waiting for heartbeat")
        vehicle.close()
        return False
        
    except ImportError:
        print("❌ DroneKit not installed")
        return False
    except Exception as e:
        print(f"❌ DroneKit test failed: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("🚁 ESP32 MAVLink Connection Diagnostics")
    print("=" * 50)
    
    tests = [
        ("WiFi Connection", check_wifi_connection),
        ("ESP32 Ping", test_ping), 
        ("UDP Communication", test_udp_echo),
        ("MAVLink Messages", lambda: listen_for_mavlink(10)),
        ("DroneKit Connection", test_dronekit_simple)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        result = test_func()
        results.append((test_name, result))
        
        if not result and test_name in ["WiFi Connection", "ESP32 Ping"]:
            print(f"\n❌ {test_name} failed - skipping remaining tests")
            break
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    # Provide recommendations
    failed_tests = [name for name, result in results if not result]
    
    if not failed_tests:
        print("\n🎉 All tests passed! DroneKit should work.")
    else:
        print(f"\n🔧 TROUBLESHOOTING:")
        if "WiFi Connection" in failed_tests:
            print("   1. Connect to ESP32-AccessPoint WiFi network")
        if "ESP32 Ping" in failed_tests:
            print("   2. Check ESP32 power and WiFi access point mode")
        if "MAVLink Messages" in failed_tests:
            print("   3. Verify flight controller is connected to ESP32")
            print("   4. Check ESP32 MAVLink bridge code is running")
            print("   5. Verify serial baud rate (57600 or 115200)")
        if "DroneKit Connection" in failed_tests and "MAVLink Messages" not in failed_tests:
            print("   6. Try different DroneKit connection strings")
            print("   7. Check firewall/antivirus blocking UDP port 14550")

if __name__ == "__main__":
    main()
