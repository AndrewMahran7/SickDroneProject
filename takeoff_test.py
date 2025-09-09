#!/usr/bin/env python3
"""
Takeoff Diagnostic Test - Comprehensive takeoff system testing
Tests all aspects of the takeoff process to identify where failures occur
"""

import requests
import time
import json

def test_takeoff_system():
    """Test the takeoff system step by step"""
    print("🚁 TAKEOFF DIAGNOSTIC TEST")
    print("=" * 50)
    
    base_url = "http://localhost:3000"
    
    # Step 1: Check current drone status
    print("\n1. Checking current drone status...")
    try:
        response = requests.get(f"{base_url}/drone/metrics")
        if response.status_code == 200:
            metrics = response.json()
            print(f"   ✅ Connection: {metrics.get('connection_status', 'Unknown')}")
            print(f"   ✅ Armed: {metrics.get('armed', False)}")
            print(f"   ✅ Armable: {metrics.get('is_armable', False)}")
            print(f"   ✅ Flight Mode: {metrics.get('flight_mode', 'Unknown')}")
            print(f"   ✅ System Status: {metrics.get('system_status', 'Unknown')}")
            print(f"   ✅ Current Altitude: {metrics.get('altitude_relative', 0):.2f}m")
            print(f"   ✅ GPS Fix: {metrics.get('gps_fix_name', 'Unknown')}")
            print(f"   ✅ GPS Satellites: {metrics.get('gps_satellites', 0)}")
            
            # Check for pre-arm issues
            if not metrics.get('is_armable', False):
                print("   ⚠️ WARNING: Vehicle is not armable - check pre-arm conditions")
            
        else:
            print(f"   ❌ Failed to get metrics: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error getting metrics: {e}")
        return False
    
    # Step 2: Start drone tracking if not active
    print("\n2. Starting drone tracking...")
    try:
        response = requests.post(f"{base_url}/drone/start")
        if response.status_code == 200:
            print("   ✅ Drone tracking started")
        else:
            print(f"   ⚠️ Tracking start warning: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error starting tracking: {e}")
    
    # Step 3: Test basic takeoff
    print("\n3. Testing basic takeoff to 1.5m...")
    try:
        start_time = time.time()
        response = requests.post(f"{base_url}/drone/takeoff", timeout=120)  # 2 minute timeout
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Takeoff command sent successfully in {elapsed:.1f}s")
            print(f"   ✅ Response: {result.get('status', 'No status')}")
            
            # Monitor altitude for 30 seconds
            print("\n4. Monitoring takeoff progress...")
            for i in range(30):  # Monitor for 30 seconds
                time.sleep(1)
                try:
                    metrics_response = requests.get(f"{base_url}/drone/metrics")
                    if metrics_response.status_code == 200:
                        metrics = metrics_response.json()
                        altitude = metrics.get('altitude_relative', 0)
                        armed = metrics.get('armed', False)
                        mode = metrics.get('flight_mode', 'Unknown')
                        
                        print(f"   [{i+1:2d}s] Alt: {altitude:.2f}m, Armed: {armed}, Mode: {mode}")
                        
                        # Check if takeoff is successful
                        if altitude >= 1.0:  # 1 meter is close enough to 1.5m target
                            print(f"   ✅ TAKEOFF SUCCESS! Reached {altitude:.2f}m altitude")
                            return True
                        
                        # Check if drone disarmed (failure)
                        if not armed and i > 5:  # Give it 5 seconds to arm
                            print(f"   ❌ TAKEOFF FAILED: Drone disarmed during takeoff")
                            return False
                            
                except Exception as e:
                    print(f"   ❌ Error monitoring: {e}")
            
            print(f"   ❌ TAKEOFF TIMEOUT: Altitude did not reach target after 30 seconds")
            return False
            
        else:
            result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"   ❌ Takeoff command failed: HTTP {response.status_code}")
            print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
            return False
            
    except requests.Timeout:
        print(f"   ❌ TAKEOFF TIMEOUT: Command took longer than 2 minutes")
        return False
    except Exception as e:
        print(f"   ❌ Takeoff error: {e}")
        return False

def test_manual_arming():
    """Test manual arming process"""
    print("\n" + "=" * 50)
    print("🔧 MANUAL ARMING TEST")
    print("=" * 50)
    
    # This would require direct DroneKit commands
    # For now, let's check if we can get vehicle status
    try:
        response = requests.get("http://localhost:3000/drone/metrics")
        if response.status_code == 200:
            metrics = response.json()
            print(f"Current vehicle state:")
            print(f"  - Armed: {metrics.get('armed', False)}")
            print(f"  - Armable: {metrics.get('is_armable', False)}")
            print(f"  - Mode: {metrics.get('flight_mode', 'Unknown')}")
            print(f"  - System Status: {metrics.get('system_status', 'Unknown')}")
            
            # Check specific issues
            if not metrics.get('is_armable', False):
                print("\n⚠️ VEHICLE NOT ARMABLE - Possible issues:")
                print("  - Safety switch not disabled")
                print("  - GPS not ready (need GPS fix)")
                print("  - IMU/compass calibration required")
                print("  - Battery voltage too low")
                print("  - Pre-arm checks failing")
                
                gps_sats = metrics.get('gps_satellites', 0)
                gps_fix = metrics.get('gps_fix_name', 'Unknown')
                
                if gps_sats < 6:
                    print(f"  - GPS: Only {gps_sats} satellites (need 6+), Fix: {gps_fix}")
                else:
                    print(f"  - GPS: {gps_sats} satellites, Fix: {gps_fix} ✅")
                    
        return True
    except Exception as e:
        print(f"Error checking vehicle state: {e}")
        return False

if __name__ == "__main__":
    success = test_takeoff_system()
    
    if not success:
        test_manual_arming()
        
        print("\n" + "=" * 50)
        print("🔍 TROUBLESHOOTING RECOMMENDATIONS")
        print("=" * 50)
        print("1. Check if safety switch is disabled in SITL:")
        print("   - Run: python disable_safety.py")
        print("\n2. Verify GPS is working:")
        print("   - Need GPS fix with 6+ satellites for arming")
        print("\n3. Check ArduPilot logs:")
        print("   - Look for 'PreArm:' messages in console")
        print("\n4. Try manual controller takeoff:")
        print("   - If controller works but script doesn't, it's a software issue")
        print("\n5. Check vehicle mode:")
        print("   - Must be in GUIDED mode for script control")
        print("\n6. Verify DroneKit connection:")
        print("   - Check if telemetry is flowing properly")
