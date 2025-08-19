#!/usr/bin/env python3
"""
Simple test to verify the camera toggle fix
"""

import requests
import time
import json

BASE_URL = "http://localhost:5000"

def check_camera_status():
    """Check current camera status"""
    try:
        response = requests.get(f"{BASE_URL}/camera/status")
        data = response.json()
        print(f"Camera Status: {data}")
        return data
    except Exception as e:
        print(f"Error checking status: {e}")
        return None

def toggle_camera():
    """Toggle camera on/off"""
    try:
        response = requests.post(f"{BASE_URL}/camera/toggle")
        data = response.json()
        print(f"Toggle Result: {data}")
        return data
    except Exception as e:
        print(f"Error toggling camera: {e}")
        return None

def test_camera_feed():
    """Test if camera feed returns appropriate response"""
    try:
        response = requests.get(f"{BASE_URL}/camera/feed")
        data = response.json()
        print(f"Camera Feed: status='{data.get('status')}', frame_length={len(data.get('frame', ''))}")
        return data
    except Exception as e:
        print(f"Error getting camera feed: {e}")
        return None

def main():
    print("🧪 Testing Camera Toggle Fix")
    print("=" * 50)
    
    # Check initial status
    print("\n1. Initial Status:")
    status = check_camera_status()
    
    # Test camera feed while disabled
    print("\n2. Testing feed while camera disabled:")
    feed = test_camera_feed()
    
    # Enable camera
    print("\n3. Enabling camera:")
    toggle_result = toggle_camera()
    time.sleep(2)  # Wait for camera to start
    
    # Check status after enabling
    print("\n4. Status after enabling:")
    status = check_camera_status()
    
    # Test camera feed while enabled
    print("\n5. Testing feed while camera enabled:")
    feed = test_camera_feed()
    
    # Disable camera
    print("\n6. Disabling camera:")
    toggle_result = toggle_camera()
    time.sleep(1)
    
    # Test camera feed while disabled again
    print("\n7. Testing feed while camera disabled again:")
    feed = test_camera_feed()
    
    # Check final status
    print("\n8. Final status:")
    status = check_camera_status()
    
    print("\n✅ Camera toggle test completed!")

if __name__ == "__main__":
    main()
