#!/usr/bin/env python3
"""
Test script for ESP32 telemetry connection
Run this to test UDP connection before using in main app
"""

import sys
import os

# Add the project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sdronep.telemetry import connect_vehicle, get_current_location

def main():
    print("🚁 ESP32 Telemetry Connection Test")
    print("=" * 50)
    
    # Test connection
    print("1. Testing vehicle connection...")
    vehicle = connect_vehicle()
    
    if vehicle is None:
        print("❌ Connection failed!")
        print("\n🔧 Troubleshooting steps:")
        print("1. Make sure you're connected to 'ESP32-AccessPoint' WiFi")
        print("2. Check if Mission Planner can connect to UDP 192.168.4.1:14550")
        print("3. Verify ESP32 is powered and transmitting")
        print("4. Try different UDP connection strings")
        return
    
    print(f"✅ Connected successfully!")
    print(f"Vehicle mode: {vehicle.mode.name}")
    print(f"Armed: {vehicle.armed}")
    
    # Test location
    print("\n2. Testing GPS location...")
    try:
        lat, lon = get_current_location()
        if lat != 0 or lon != 0:
            print(f"✅ GPS Location: {lat:.6f}, {lon:.6f}")
        else:
            print("⚠️ GPS not yet fixed (0, 0)")
    except Exception as e:
        print(f"❌ GPS read error: {e}")
    
    # Test basic vehicle info
    print("\n3. Vehicle Information:")
    try:
        print(f"   GPS Status: {vehicle.gps_0}")
        print(f"   Battery: {vehicle.battery}")
        print(f"   Altitude: {vehicle.location.global_relative_frame.alt}m")
        print(f"   Groundspeed: {vehicle.groundspeed} m/s")
    except Exception as e:
        print(f"❌ Vehicle info error: {e}")
    
    print("\n✅ Telemetry test completed!")
    
    # Close connection
    try:
        vehicle.close()
    except:
        pass

if __name__ == "__main__":
    main()
