from flask import Flask, render_template, jsonify, request
from telemetry import get_current_location, connect_vehicle
from gimbal_control import center_camera, set_gimbal_angle, get_angle
import os
import math
import threading
import time
from dronekit import VehicleMode, LocationGlobalRelative

# Get the path to the interface directory
interface_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'interface')
template_dir = os.path.join(interface_dir, 'templates')
static_dir = os.path.join(interface_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Global variables to store locations and tracking state
app.config['current_location'] = (0, 0)  # User location
app.config['drone_location'] = (0, 0)    # Drone location
app.config['tracking_active'] = False    # Drone tracking state
app.config['follow_mode'] = False        # Drone follow mode
app.config['target_elevation'] = 20      # Target elevation in meters
app.config['target_distance'] = 10       # Target ground distance in meters
app.config['drone_vehicle'] = None       # Drone vehicle connection

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in meters
    """
    if lat1 == 0 and lon1 == 0:
        return 0
    if lat2 == 0 and lon2 == 0:
        return 0
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    return c * r

def drone_telemetry_loop():
    """
    Continuously update drone location in a background thread
    """
    while True:
        try:
            if app.config.get('tracking_active', False):
                drone_lat, drone_lon = get_current_location()
                app.config['drone_location'] = (drone_lat, drone_lon)
                print(f"Drone location updated: {drone_lat}, {drone_lon}")
            time.sleep(2)  # Update every 2 seconds
        except Exception as e:
            print(f"Error getting drone location: {e}")
            time.sleep(5)  # Wait longer on error

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/location", methods=["GET", "POST"])
def handle_location():
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return "No data received", 400
        
        # Handle both possible key formats
        lat = data.get("latitude") or data.get("lat")
        lon = data.get("longitude") or data.get("lon")
        
        if lat is None or lon is None:
            return "Missing latitude or longitude", 400
            
        print("Received:", lat, lon)
        # Store the location globally for GET requests
        app.config['current_location'] = (lat, lon)
        return "OK"
    else:  # GET request
        location = app.config.get('current_location', (0, 0))
        return jsonify({"lat": location[0], "lon": location[1]})


@app.route("/center")
def center():
    center_camera()
    return "Camera centered"

@app.route("/drone/location", methods=["GET"])
def get_drone_location():
    """Get current drone location"""
    drone_location = app.config.get('drone_location', (0, 0))
    return jsonify({"lat": drone_location[0], "lon": drone_location[1]})

@app.route("/drone/start", methods=["POST"])
def start_drone_tracking():
    """Start drone telemetry tracking"""
    app.config['tracking_active'] = True
    return jsonify({"status": "Drone tracking started"})

@app.route("/drone/stop", methods=["POST"])
def stop_drone_tracking():
    """Stop drone telemetry tracking"""
    app.config['tracking_active'] = False
    return jsonify({"status": "Drone tracking stopped"})

@app.route("/distance", methods=["GET"])
def get_distance():
    """Get distance between user and drone"""
    user_location = app.config.get('current_location', (0, 0))
    drone_location = app.config.get('drone_location', (0, 0))
    
    distance = calculate_distance(
        user_location[0], user_location[1],
        drone_location[0], drone_location[1]
    )
    
    return jsonify({
        "user_location": {"lat": user_location[0], "lon": user_location[1]},
        "drone_location": {"lat": drone_location[0], "lon": drone_location[1]},
        "distance_meters": round(distance, 2),
        "distance_feet": round(distance * 3.28084, 2)
    })

@app.route("/status", methods=["GET"])
def get_status():
    """Get overall system status"""
    user_location = app.config.get('current_location', (0, 0))
    drone_location = app.config.get('drone_location', (0, 0))
    tracking_active = app.config.get('tracking_active', False)
    follow_mode = app.config.get('follow_mode', False)
    target_elevation = app.config.get('target_elevation', 20)
    target_distance = app.config.get('target_distance', 10)
    
    distance = calculate_distance(
        user_location[0], user_location[1],
        drone_location[0], drone_location[1]
    )
    
    return jsonify({
        "tracking_active": tracking_active,
        "follow_mode": follow_mode,
        "target_elevation": target_elevation,
        "target_distance": target_distance,
        "user_location": {"lat": user_location[0], "lon": user_location[1]},
        "drone_location": {"lat": drone_location[0], "lon": drone_location[1]},
        "distance_meters": round(distance, 2),
        "distance_feet": round(distance * 3.28084, 2),
        "user_has_location": user_location != (0, 0),
        "drone_has_location": drone_location != (0, 0)
    })

@app.route("/drone/follow/start", methods=["POST"])
def start_drone_follow():
    """Start drone following mode with specified elevation and distance"""
    try:
        data = request.get_json()
        elevation = data.get('elevation', 20)  # Default 20 meters
        distance = data.get('distance', 10)    # Default 10 meters
        
        # Validate inputs
        if elevation < 5 or elevation > 100:
            return jsonify({"error": "Elevation must be between 5 and 100 meters"}), 400
        if distance < 5 or distance > 50:
            return jsonify({"error": "Distance must be between 5 and 50 meters"}), 400
        
        # Store parameters
        app.config['target_elevation'] = elevation
        app.config['target_distance'] = distance
        
        # Get drone vehicle
        vehicle = get_drone_vehicle()
        if not vehicle:
            return jsonify({"error": "Failed to connect to drone"}), 500
        
        # Start tracking mode first
        app.config['tracking_active'] = True
        
        # Takeoff to target elevation
        arm_and_takeoff(vehicle, elevation)
        
        # Enable follow mode
        app.config['follow_mode'] = True
        
        return jsonify({
            "status": "Drone follow mode started",
            "elevation": elevation,
            "distance": distance
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/drone/follow/stop", methods=["POST"])
def stop_drone_follow():
    """Stop drone following mode and hover in place"""
    try:
        app.config['follow_mode'] = False
        return jsonify({"status": "Drone follow mode stopped - hovering in place"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/drone/home", methods=["POST"])
def drone_home():
    """Land the drone (homing function)"""
    try:
        # Stop follow mode
        app.config['follow_mode'] = False
        
        # Get drone vehicle
        vehicle = get_drone_vehicle()
        if not vehicle:
            return jsonify({"error": "Failed to connect to drone"}), 500
        
        # Set to LAND mode
        print("Landing drone...")
        vehicle.mode = VehicleMode("LAND")
        
        return jsonify({"status": "Drone landing initiated"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper functions
def get_drone_vehicle():
    """Get or create drone vehicle connection"""
    if app.config['drone_vehicle'] is None:
        try:
            app.config['drone_vehicle'] = connect_vehicle()
            print("Connected to drone vehicle")
        except Exception as e:
            print(f"Failed to connect to drone: {e}")
            return None
    return app.config['drone_vehicle']

def calculate_target_position(user_lat, user_lon, elevation_above_user, ground_distance):
    """
    Calculate drone target position based on user location, elevation above user, and ground distance
    This positions the drone at the specified distance behind the user (relative to north)
    """
    # For now, position drone to the south of user at specified distance
    # 1 degree latitude ≈ 111,000 meters
    lat_offset = ground_distance / 111000
    
    target_lat = user_lat - lat_offset  # Position south of user
    target_lon = user_lon  # Same longitude
    
    return target_lat, target_lon

def arm_and_takeoff(vehicle, target_elevation_above_user):
    """
    Arms vehicle and fly to target_elevation_above_user (relative to user's altitude).
    """
    print("Basic pre-arm checks")
    print(f"Target elevation: {target_elevation_above_user}m above ground level")
    
    # Don't try to arm until autopilot is ready
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialise...")
        time.sleep(1)

    print("Arming motors")
    # Copter should arm in GUIDED mode
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    # Confirm vehicle armed before attempting to take off
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)

    print(f"Taking off to {target_elevation_above_user}m above ground!")
    # Use simple_takeoff with relative altitude (automatically relative to takeoff point)
    vehicle.simple_takeoff(target_elevation_above_user)

    # Wait until the vehicle reaches a safe height
    while True:
        current_altitude = vehicle.location.global_relative_frame.alt  # Relative to takeoff point
        print(f" Relative altitude: {current_altitude}m above takeoff point")
        if current_altitude >= target_elevation_above_user * 0.95:
            print(f"Reached target elevation ({target_elevation_above_user}m above ground)")
            break
        time.sleep(1)

def update_gimbal_for_tracking():
    """Update gimbal angle based on current positions"""
    try:
        user_location = app.config.get('current_location', (0, 0))
        drone_location = app.config.get('drone_location', (0, 0))
        elevation_above_user = app.config.get('target_elevation', 20)
        
        if user_location != (0, 0) and drone_location != (0, 0):
            # Calculate gimbal angle using the existing function
            angle = get_angle(elevation_above_user, drone_location, user_location)
            set_gimbal_angle(angle)
            print(f"Gimbal angle updated to: {angle} degrees")
    except Exception as e:
        print(f"Error updating gimbal: {e}")

def drone_follow_loop():
    """
    Main drone following loop - runs in background thread
    """
    while True:
        try:
            if app.config.get('follow_mode', False):
                user_location = app.config.get('current_location', (0, 0))
                elevation_above_user = app.config.get('target_elevation', 20)
                ground_distance = app.config.get('target_distance', 10)
                
                if user_location != (0, 0):
                    # Calculate target position
                    target_lat, target_lon = calculate_target_position(
                        user_location[0], user_location[1], elevation_above_user, ground_distance
                    )
                    
                    # Move drone to target position
                    vehicle = get_drone_vehicle()
                    if vehicle:
                        # Use LocationGlobalRelative for altitude relative to takeoff point
                        target_location = LocationGlobalRelative(target_lat, target_lon, elevation_above_user)
                        vehicle.simple_goto(target_location)
                        print(f"Drone moving to: {target_lat}, {target_lon} at {elevation_above_user}m above ground")
                        
                        # Update gimbal angle
                        update_gimbal_for_tracking()
                    
            time.sleep(3)  # Update every 3 seconds
        except Exception as e:
            print(f"Error in drone follow loop: {e}")
            time.sleep(5)

# Start drone telemetry and follow loops in background threads
telemetry_thread = threading.Thread(target=drone_telemetry_loop, daemon=True)
telemetry_thread.start()

follow_thread = threading.Thread(target=drone_follow_loop, daemon=True)
follow_thread.start()

if __name__ == "__main__":
    app.run(debug=True)
