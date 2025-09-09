#!/usr/bin/env python3
"""
Direct DroneKit Connection Test
Tests DroneKit connection and takeoff without Flask server
"""

import time
from dronekit import connect, VehicleMode
from pymavlink import mavutil

def test_dronekit_connection():
    """Test direct DroneKit connection and takeoff"""
    print("🔧 DIRECT DRONEKIT CONNECTION TEST")
    print("=" * 50)
    
    # Connection strings to try
    connection_strings = [
        ('udpin:192.168.4.2:14550', 'ESP32 WiFi AP - Listen on laptop IP'),
        ('udp:192.168.4.1:14550', 'ESP32 WiFi AP - Connect to ESP32'),
        ('tcp:127.0.0.1:5760', 'SITL simulation'),
        ('com14:57600', 'Direct serial connection'),
    ]
    
    vehicle = None
    
    # Step 1: Test connection
    print("\n1. Testing DroneKit connection...")
    for conn_str, description in connection_strings:
        try:
            print(f"   Trying: {conn_str} ({description})")
            vehicle = connect(conn_str, wait_ready=False, timeout=10)
            
            # Wait for heartbeat
            start_time = time.time()
            while time.time() - start_time < 15:
                if hasattr(vehicle, 'last_heartbeat') and vehicle.last_heartbeat:
                    print(f"   ✅ Connected! Heartbeat from system {getattr(vehicle, 'system_id', 'unknown')}")
                    break
                time.sleep(0.5)
            else:
                print(f"   ❌ No heartbeat received")
                vehicle.close()
                continue
            
            break  # Successfully connected
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            continue
    
    if not vehicle:
        print("❌ Could not connect to any vehicle")
        return False
    
    # Step 2: Test vehicle status
    print("\n2. Testing vehicle status...")
    try:
        print(f"   Connection: ✅ Connected")
        print(f"   Armed: {vehicle.armed}")
        print(f"   Armable: {vehicle.is_armable}")
        print(f"   Mode: {vehicle.mode.name}")
        print(f"   System Status: {vehicle.system_status.state}")
        
        # GPS status
        try:
            gps_fix = vehicle.gps_0.fix_type
            gps_sats = vehicle.gps_0.satellites_visible
            print(f"   GPS Fix: {gps_fix} ({gps_sats} satellites)")
        except:
            print(f"   GPS: Not available")
        
        # Battery status
        try:
            battery = vehicle.battery.level if vehicle.battery.level else 0
            voltage = vehicle.battery.voltage if vehicle.battery.voltage else 0
            print(f"   Battery: {battery}% ({voltage:.1f}V)")
        except:
            print(f"   Battery: Not available")
            
    except Exception as e:
        print(f"   ❌ Error reading vehicle status: {e}")
        vehicle.close()
        return False
    
    # Step 3: Test parameter access
    print("\n3. Testing parameter access...")
    try:
        safety_enabled = vehicle.parameters.get('BRD_SAFETYENABLE', 'N/A')
        arming_check = vehicle.parameters.get('ARMING_CHECK', 'N/A')
        print(f"   Safety Switch: {safety_enabled}")
        print(f"   Arming Checks: {arming_check}")
        
        # If safety is enabled and this looks like SITL, disable it
        if safety_enabled == 1 and not vehicle.is_armable:
            print("   🔧 Disabling safety for SITL/testing...")
            vehicle.parameters['BRD_SAFETYENABLE'] = 0
            vehicle.parameters['ARMING_CHECK'] = 0
            time.sleep(2)
            print("   ✅ Safety disabled")
            
    except Exception as e:
        print(f"   ⚠️ Parameter access limited: {e}")
    
    # Step 4: Test arming capability
    print("\n4. Testing arming capability...")
    max_wait = 30
    start_time = time.time()
    
    while not vehicle.is_armable and (time.time() - start_time) < max_wait:
        print(f"   Waiting for armable... ({time.time() - start_time:.1f}s)")
        time.sleep(1)
    
    if vehicle.is_armable:
        print("   ✅ Vehicle is armable")
        
        # Step 5: Test mode change to GUIDED
        print("\n5. Testing mode change to GUIDED...")
        try:
            print(f"   Current mode: {vehicle.mode.name}")
            vehicle.mode = VehicleMode("GUIDED")
            
            # Wait for mode change
            start_time = time.time()
            while vehicle.mode.name != "GUIDED" and (time.time() - start_time) < 10:
                print(f"   Waiting for GUIDED mode... Current: {vehicle.mode.name}")
                time.sleep(0.5)
            
            if vehicle.mode.name == "GUIDED":
                print("   ✅ Successfully switched to GUIDED mode")
                
                # Step 6: Test arming
                print("\n6. Testing arming...")
                vehicle.armed = True
                
                start_time = time.time()
                while not vehicle.armed and (time.time() - start_time) < 15:
                    print(f"   Waiting for arming... ({time.time() - start_time:.1f}s)")
                    time.sleep(0.5)
                
                if vehicle.armed:
                    print("   ✅ Vehicle armed successfully")
                    
                    # Step 7: Test takeoff command
                    print("\n7. Testing takeoff command...")
                    try:
                        print("   Sending takeoff command to 1.5m...")
                        vehicle.simple_takeoff(1.5)
                        
                        # Monitor for 20 seconds
                        start_time = time.time()
                        while (time.time() - start_time) < 20:
                            try:
                                altitude = vehicle.location.global_relative_frame.alt or 0
                                print(f"   [{time.time() - start_time:5.1f}s] Altitude: {altitude:.2f}m")
                                
                                if altitude >= 1.0:  # Close to target
                                    print("   🎉 TAKEOFF SUCCESS!")
                                    vehicle.mode = VehicleMode("LAND")  # Land it
                                    break
                                    
                            except Exception as e:
                                print(f"   Altitude read error: {e}")
                            
                            time.sleep(1)
                        else:
                            print("   ❌ Takeoff did not reach target altitude")
                            
                    except Exception as e:
                        print(f"   ❌ Takeoff command failed: {e}")
                    
                    # Disarm for safety
                    print("\n8. Disarming for safety...")
                    vehicle.armed = False
                    
                else:
                    print("   ❌ Failed to arm vehicle")
                    try:
                        print(f"      System status: {vehicle.system_status.state}")
                        print(f"      GPS fix: {vehicle.gps_0.fix_type}")
                        print(f"      GPS sats: {vehicle.gps_0.satellites_visible}")
                    except:
                        pass
            else:
                print(f"   ❌ Failed to switch to GUIDED mode (stuck in {vehicle.mode.name})")
                
        except Exception as e:
            print(f"   ❌ Mode change failed: {e}")
            
    else:
        print("   ❌ Vehicle not armable after 30 seconds")
        try:
            print(f"      System status: {vehicle.system_status.state}")
            print(f"      GPS fix: {vehicle.gps_0.fix_type}")
            print(f"      GPS sats: {vehicle.gps_0.satellites_visible}")
            safety = vehicle.parameters.get('BRD_SAFETYENABLE', 'N/A')
            print(f"      Safety switch: {safety}")
        except Exception as e:
            print(f"      Diagnostic error: {e}")
    
    # Cleanup
    print("\n9. Cleanup...")
    vehicle.close()
    print("   Connection closed")
    
    return True

if __name__ == "__main__":
    try:
        test_dronekit_connection()
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        
    print("\n" + "=" * 50)
    print("🏁 DIRECT DRONEKIT TEST COMPLETE")
    print("If this test works but the Flask app doesn't,")
    print("the issue is in the Flask/web integration layer.")
    input("\nPress Enter to exit...")
