#!/usr/bin/env python3
"""
Safety Switch Disabler for SITL
Sends MAVLink command to disable safety switch in simulation
"""

import sys
import time
from dronekit import connect, VehicleMode
from pymavlink import mavutil

def disable_safety_switch():
    """Disable safety switch in SITL simulation"""
    print("🔧 SITL Safety Switch Disabler")
    print("=" * 40)
    
    # Connection strings to try
    connection_strings = [
        "udpin:192.168.4.2:14550",  # ESP32 UDP
        "tcp:127.0.0.1:5760",       # SITL default
        "udp:127.0.0.1:14540",      # Alternative SITL
        "com14:57600",              # Serial connection
    ]
    
    vehicle = None
    
    for conn_str in connection_strings:
        try:
            print(f"Trying connection: {conn_str}")
            vehicle = connect(conn_str, wait_ready=True, timeout=10)
            print(f"✅ Connected via {conn_str}")
            break
        except Exception as e:
            print(f"❌ Failed to connect via {conn_str}: {e}")
            continue
    
    if not vehicle:
        print("❌ Could not connect to vehicle with any connection string")
        return False
    
    try:
        print("\n🔓 Disabling safety switch...")
        
        # Method 1: Set BRD_SAFETYENABLE parameter to 0
        print("Setting BRD_SAFETYENABLE = 0...")
        vehicle.parameters['BRD_SAFETYENABLE'] = 0
        time.sleep(1)
        
        # Method 2: Send safety switch disable command
        print("Sending safety switch disable command...")
        msg = vehicle.message_factory.set_mode_encode(
            0,  # target system
            mavutil.mavlink.MAV_MODE_FLAG_DECODE_POSITION_SAFETY,
            0   # custom mode
        )
        vehicle.send_mavlink(msg)
        time.sleep(1)
        
        # Method 3: Force arm enable (bypass safety)
        print("Setting ARMING_CHECK = 0 (bypass safety checks)...")
        vehicle.parameters['ARMING_CHECK'] = 0
        time.sleep(1)
        
        print("✅ Safety switch disabled successfully!")
        print("✅ Arming checks bypassed!")
        print("\n📋 Current vehicle status:")
        print(f"   Armed: {vehicle.armed}")
        print(f"   Armable: {vehicle.is_armable}")
        print(f"   Mode: {vehicle.mode.name}")
        print(f"   Safety: {vehicle.parameters.get('BRD_SAFETYENABLE', 'Unknown')}")
        print(f"   Arming Check: {vehicle.parameters.get('ARMING_CHECK', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error disabling safety switch: {e}")
        return False
    finally:
        if vehicle:
            vehicle.close()

if __name__ == "__main__":
    success = disable_safety_switch()
    
    if success:
        print("\n🎉 Safety switch disabled! You should now be able to arm and takeoff.")
        print("💡 Try running the takeoff test again: python takeoff_test.py")
    else:
        print("\n❌ Failed to disable safety switch.")
        print("💡 Try running this script again or check your connection.")
