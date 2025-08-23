#!/usr/bin/env python3
"""
Test version of the GoPro drone app without dronekit dependency
This allows testing the GoPro integration functionality
"""
from flask import Flask, render_template, jsonify, request, Response
import os
import math
import threading
import time
import socket
import re
import cv2
import requests
import numpy as np

app = Flask(__name__, 
           template_folder='interface/templates',
           static_folder='interface/static')

# Mock classes for testing without actual drone connection
class MockVehicle:
    def __init__(self):
        self.location = MockLocation()
        self.attitude = MockAttitude()
        self.battery = MockBattery()
        self.velocity = [0.0, 0.0, 0.0]
        self.groundspeed = 0.0
        self.heading = 0
        
class MockLocation:
    def __init__(self):
        self.global_relative_frame = MockGlobalRelativeFrame()
        
class MockGlobalRelativeFrame:
    def __init__(self):
        self.lat = 40.7128  # NYC coordinates for testing
        self.lon = -74.0060
        self.alt = 100.0

class MockAttitude:
    def __init__(self):
        self.pitch = 0.0
        self.yaw = 0.0
        self.roll = 0.0
        
class MockBattery:
    def __init__(self):
        self.voltage = 12.6
        self.current = -10.0
        self.level = 85

# Global variables
vehicle = MockVehicle()
current_user_location = (40.7134, -74.0055)  # Slightly different for testing
tracking_thread = None
tracking_active = False

# GoPro Controller Class
class GoproController:
    def __init__(self, base_url="http://10.5.5.9:8080"):
        self.base_url = base_url
        self.is_connected = False
        self.is_recording = False
        self.is_streaming = False
        
    def connect(self):
        """Connect to GoPro WiFi"""
        try:
            response = requests.get(f"{self.base_url}/gp/gpControl/status", timeout=5)
            if response.status_code == 200:
                self.is_connected = True
                return True
        except:
            pass
        self.is_connected = False
        return False
        
    def start_recording(self):
        """Start video recording"""
        try:
            response = requests.get(f"{self.base_url}/gp/gpControl/command/shutter?p=1", timeout=5)
            if response.status_code == 200:
                self.is_recording = True
                return True
        except:
            pass
        return False
        
    def stop_recording(self):
        """Stop video recording"""
        try:
            response = requests.get(f"{self.base_url}/gp/gpControl/command/shutter?p=0", timeout=5)
            if response.status_code == 200:
                self.is_recording = False
                return True
        except:
            pass
        return False
        
    def take_photo(self):
        """Take a photo"""
        try:
            # Set to photo mode first
            requests.get(f"{self.base_url}/gp/gpControl/command/mode?p=1", timeout=5)
            time.sleep(1)
            # Take photo
            response = requests.get(f"{self.base_url}/gp/gpControl/command/shutter?p=1", timeout=5)
            return response.status_code == 200
        except:
            return False
            
    def get_status(self):
        """Get GoPro status"""
        return {
            'connected': self.is_connected,
            'recording': self.is_recording,
            'streaming': self.is_streaming,
            'battery': 85,  # Mock value
            'mode': 'video' if self.is_recording else 'idle'
        }

# Initialize GoPro controller
gopro = GoproController()

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing between two GPS coordinates"""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon_rad = math.radians(lon2 - lon1)
    
    x = math.sin(delta_lon_rad) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon_rad)
    
    bearing = math.atan2(x, y)
    bearing = math.degrees(bearing)
    return (bearing + 360) % 360

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates in meters"""
    R = 6371000  # Earth's radius in meters
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_gimbal_tilt(drone_alt, user_alt, horizontal_distance):
    """Calculate gimbal tilt angle to center user in frame"""
    height_diff = drone_alt - user_alt
    if horizontal_distance > 0:
        angle = math.degrees(math.atan(height_diff / horizontal_distance))
        return max(-90, min(0, angle))
    return 0

def orient_drone_towards_user():
    """Orient drone front towards user and adjust gimbal tilt"""
    global current_user_location, vehicle
    
    if not current_user_location or not vehicle:
        return False
    
    try:
        drone_lat = vehicle.location.global_relative_frame.lat
        drone_lon = vehicle.location.global_relative_frame.lon
        drone_alt = vehicle.location.global_relative_frame.alt
        
        user_lat, user_lon = current_user_location
        user_alt = 0  # Assume ground level
        
        # Calculate bearing to user
        bearing = calculate_bearing(drone_lat, drone_lon, user_lat, user_lon)
        
        # Calculate distance and gimbal tilt
        horizontal_distance = calculate_distance(drone_lat, drone_lon, user_lat, user_lon)
        tilt_angle = calculate_gimbal_tilt(drone_alt, user_alt, horizontal_distance)
        
        print(f"Orienting drone: bearing={bearing:.1f}°, tilt={tilt_angle:.1f}°, distance={horizontal_distance:.1f}m")
        
        # In a real implementation, you would send these commands to the drone
        # For now, we'll just update mock values
        return True
        
    except Exception as e:
        print(f"Error orienting drone: {e}")
        return False

def tracking_loop():
    """Background thread for continuous tracking"""
    global tracking_active
    
    while tracking_active:
        try:
            if orient_drone_towards_user():
                print("Drone orientation updated")
            time.sleep(2)  # Update every 2 seconds
        except Exception as e:
            print(f"Error in tracking loop: {e}")
            time.sleep(5)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# GoPro Routes
@app.route('/api/gopro/connect', methods=['POST'])
def connect_gopro():
    success = gopro.connect()
    return jsonify({
        'success': success,
        'message': 'Connected to GoPro' if success else 'Failed to connect to GoPro'
    })

@app.route('/api/gopro/start_recording', methods=['POST'])
def start_recording():
    success = gopro.start_recording()
    return jsonify({
        'success': success,
        'message': 'Recording started' if success else 'Failed to start recording'
    })

@app.route('/api/gopro/stop_recording', methods=['POST'])
def stop_recording():
    success = gopro.stop_recording()
    return jsonify({
        'success': success,
        'message': 'Recording stopped' if success else 'Failed to stop recording'
    })

@app.route('/api/gopro/take_photo', methods=['POST'])
def take_photo():
    success = gopro.take_photo()
    return jsonify({
        'success': success,
        'message': 'Photo taken' if success else 'Failed to take photo'
    })

@app.route('/api/gopro/status')
def gopro_status():
    return jsonify(gopro.get_status())

# Auto-tracking Routes
@app.route('/api/tracking/enable', methods=['POST'])
def enable_tracking():
    global tracking_thread, tracking_active
    
    if not tracking_active:
        tracking_active = True
        tracking_thread = threading.Thread(target=tracking_loop, daemon=True)
        tracking_thread.start()
        return jsonify({'success': True, 'message': 'Auto-tracking enabled'})
    
    return jsonify({'success': False, 'message': 'Auto-tracking already active'})

@app.route('/api/tracking/disable', methods=['POST'])
def disable_tracking():
    global tracking_active
    tracking_active = False
    return jsonify({'success': True, 'message': 'Auto-tracking disabled'})

@app.route('/api/tracking/status')
def tracking_status():
    return jsonify({
        'active': tracking_active,
        'user_location': current_user_location
    })

@app.route('/api/orient_drone', methods=['POST'])
def orient_drone():
    success = orient_drone_towards_user()
    return jsonify({
        'success': success,
        'message': 'Drone oriented towards user' if success else 'Failed to orient drone'
    })

# Mock telemetry routes
@app.route('/api/telemetry')
def get_telemetry():
    return jsonify({
        'latitude': vehicle.location.global_relative_frame.lat,
        'longitude': vehicle.location.global_relative_frame.lon,
        'altitude': vehicle.location.global_relative_frame.alt,
        'pitch': vehicle.attitude.pitch,
        'yaw': vehicle.attitude.yaw,
        'roll': vehicle.attitude.roll,
        'battery_voltage': vehicle.battery.voltage,
        'battery_current': vehicle.battery.current,
        'battery_level': vehicle.battery.level,
        'velocity': vehicle.velocity,
        'groundspeed': vehicle.groundspeed,
        'heading': vehicle.heading
    })

@app.route('/api/connect', methods=['POST'])
def connect():
    return jsonify({'success': True, 'message': 'Mock connection established'})

@app.route('/api/arm', methods=['POST'])
def arm():
    return jsonify({'success': True, 'message': 'Vehicle armed (mock)'})

@app.route('/api/takeoff', methods=['POST'])
def takeoff():
    return jsonify({'success': True, 'message': 'Takeoff initiated (mock)'})

@app.route('/api/land', methods=['POST'])
def land():
    return jsonify({'success': True, 'message': 'Landing initiated (mock)'})

if __name__ == '__main__':
    print("Starting GoPro Drone Control Test Server...")
    print("GoPro integration features available:")
    print("- Connect to GoPro WiFi")
    print("- Start/stop recording")
    print("- Take photos") 
    print("- Auto-tracking (orient drone towards user)")
    print("- Manual gimbal control")
    print("\nAccess the interface at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
