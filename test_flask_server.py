#!/usr/bin/env python3
"""
Flask Server Test - Test the frame endpoint directly
Run this alongside the main server to see if frame requests are reaching the endpoint
"""

import requests
import time
import json
from datetime import datetime

def log_debug(message, level="DEBUG"):
    """Debug logging with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {level}: {message}")

def test_server_endpoints():
    """Test all relevant server endpoints"""
    
    base_url = "http://localhost:3000"
    
    endpoints_to_test = [
        ("/status", "GET", "System status"),
        ("/gopro/stream/health", "GET", "Stream health"),
        ("/gopro/stream/frame", "GET", "Single frame"),
        ("/logs", "GET", "System logs")
    ]
    
    log_debug("=== TESTING SERVER ENDPOINTS ===", "INFO")
    
    for endpoint, method, description in endpoints_to_test:
        url = base_url + endpoint
        log_debug(f"Testing {description}: {method} {endpoint}")
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, timeout=10)
            
            log_debug(f"  Status: {response.status_code}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    data = response.json()
                    if endpoint == "/gopro/stream/frame":
                        # Special handling for frame endpoint
                        if "error" in data:
                            log_debug(f"  Error: {data['error']}")
                        elif "frame" in data and data["frame"]:
                            log_debug(f"  ✅ Frame available: {len(data['frame'])} chars")
                        else:
                            log_debug(f"  ❌ No frame data")
                    elif endpoint == "/status":
                        # Check GoPro status
                        gopro_enabled = data.get("gopro_enabled", False)
                        gopro_streaming = data.get("gopro_streaming", False)
                        log_debug(f"  GoPro enabled: {gopro_enabled}")
                        log_debug(f"  GoPro streaming: {gopro_streaming}")
                    else:
                        # Generic JSON response
                        log_debug(f"  Response keys: {list(data.keys())}")
                        
                except json.JSONDecodeError:
                    log_debug(f"  Non-JSON response: {response.text[:100]}...")
            else:
                log_debug(f"  Non-JSON response: {response.text[:100]}...")
                
        except requests.exceptions.ConnectionError:
            log_debug(f"  ❌ Connection failed - is server running?")
        except requests.exceptions.Timeout:
            log_debug(f"  ❌ Request timeout")
        except Exception as e:
            log_debug(f"  ❌ Error: {e}")
        
        print("-" * 40)

def monitor_frame_endpoint():
    """Monitor the frame endpoint continuously"""
    
    log_debug("=== MONITORING FRAME ENDPOINT ===", "INFO")
    log_debug("Requesting frames every 2 seconds for 60 seconds...")
    
    url = "http://localhost:3000/gopro/stream/frame"
    start_time = time.time()
    request_count = 0
    success_count = 0
    
    while time.time() - start_time < 60:  # Monitor for 60 seconds
        request_count += 1
        elapsed = time.time() - start_time
        
        try:
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if "frame" in data and data["frame"] and data["frame"] != "null":
                    success_count += 1
                    frame_size = len(data["frame"])
                    log_debug(f"[{elapsed:6.1f}s] ✅ Frame {request_count}: {frame_size} chars")
                else:
                    error = data.get("error", "Unknown error")
                    status = data.get("status", "Unknown status")
                    log_debug(f"[{elapsed:6.1f}s] ❌ Frame {request_count}: {error} ({status})")
            else:
                log_debug(f"[{elapsed:6.1f}s] ❌ Frame {request_count}: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            log_debug(f"[{elapsed:6.1f}s] ❌ Frame {request_count}: Connection failed")
        except Exception as e:
            log_debug(f"[{elapsed:6.1f}s] ❌ Frame {request_count}: {e}")
        
        time.sleep(2)
    
    log_debug(f"📊 MONITORING COMPLETE:")
    log_debug(f"  Total requests: {request_count}")
    log_debug(f"  Successful frames: {success_count}")
    log_debug(f"  Success rate: {success_count/request_count*100:.1f}%")

def get_server_logs():
    """Get the latest server logs"""
    
    log_debug("=== GETTING SERVER LOGS ===", "INFO")
    
    try:
        response = requests.get("http://localhost:3000/logs", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logs = data.get("logs", [])
            
            log_debug(f"Retrieved {len(logs)} log entries:")
            
            # Show recent GoPro-related logs
            gopro_logs = [log for log in logs if "GOPRO" in log.get("component", "")]
            
            log_debug("Recent GoPro logs:")
            for log_entry in gopro_logs[-10:]:  # Last 10 GoPro logs
                timestamp = log_entry.get("timestamp", "")
                level = log_entry.get("level", "")
                message = log_entry.get("message", "")
                log_debug(f"  [{timestamp}] {level}: {message}")
                
        else:
            log_debug(f"❌ Failed to get logs: HTTP {response.status_code}")
            
    except Exception as e:
        log_debug(f"❌ Error getting logs: {e}")

def main():
    """Main test function"""
    print("=" * 70)
    print("Flask Server Test")
    print("=" * 70)
    
    log_debug("Testing Flask server endpoints and monitoring frame requests...", "INFO")
    
    # Test 1: Check all endpoints
    test_server_endpoints()
    
    # Test 2: Get current logs
    get_server_logs()
    
    # Test 3: Monitor frame endpoint
    monitor_frame_endpoint()
    
    # Final summary
    print("\n" + "=" * 70)
    print("SERVER TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
