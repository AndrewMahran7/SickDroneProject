from flask import Flask, render_template, jsonify, request, Response
from sdronep.telemetry import get_current_location, connect_vehicle
from sdronep.gimbal_control import center_camera, set_gimbal_angle, get_angle
from sdronep.human_detection import get_detector
import os
import math
import threading
import time
from datetime import datetime
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
app.config['system_logs'] = []           # System log storage

def log_message(level, component, message):
    """
    Add a timestamped log message to the system logs
    level: 'INFO', 'WARNING', 'ERROR', 'SUCCESS'
    component: 'DRONE', 'USER', 'SYSTEM', 'GIMBAL', 'FOLLOW'
    message: The log message
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "component": component,
        "message": message
    }
    
    # Add to logs and keep only last 100 entries
    app.config['system_logs'].append(log_entry)
    if len(app.config['system_logs']) > 100:
        app.config['system_logs'] = app.config['system_logs'][-100:]
    
    # Also print to console for debugging
    print(f"[{timestamp}] {level} - {component}: {message}")

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
    log_message("INFO", "SYSTEM", "Drone telemetry loop started")
    while True:
        try:
            if app.config.get('tracking_active', False):
                drone_lat, drone_lon = get_current_location()
                app.config['drone_location'] = (drone_lat, drone_lon)
                log_message("INFO", "DRONE", f"Location updated: {drone_lat:.6f}, {drone_lon:.6f}")
            time.sleep(2)  # Update every 2 seconds
        except Exception as e:
            log_message("ERROR", "DRONE", f"Error getting location: {str(e)}")
            time.sleep(5)  # Wait longer on error

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/location", methods=["GET", "POST"])
def handle_location():
    if request.method == "POST":
        data = request.get_json()
        if not data:
            log_message("ERROR", "USER", "No location data received")
            return "No data received", 400
        
        # Handle both possible key formats
        lat = data.get("latitude") or data.get("lat")
        lon = data.get("longitude") or data.get("lon")
        
        if lat is None or lon is None:
            log_message("ERROR", "USER", "Missing latitude or longitude in request")
            return "Missing latitude or longitude", 400
            
        log_message("INFO", "USER", f"Location received: {lat:.6f}, {lon:.6f}")
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
    log_message("SUCCESS", "DRONE", "Tracking started - monitoring Pixhawk connection")
    return jsonify({"status": "Drone tracking started"})

@app.route("/drone/stop", methods=["POST"])
def stop_drone_tracking():
    """Stop drone telemetry tracking"""
    app.config['tracking_active'] = False
    log_message("INFO", "DRONE", "Tracking stopped")
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

@app.route("/logs", methods=["GET"])
def get_logs():
    """Get system logs"""
    logs = app.config.get('system_logs', [])
    # Return most recent logs first
    return jsonify({"logs": list(reversed(logs[-50:]))})  # Last 50 logs

@app.route("/logs/clear", methods=["POST"])
def clear_logs():
    """Clear all system logs"""
    app.config['system_logs'] = []
    log_message("INFO", "SYSTEM", "Logs cleared by user")
    return jsonify({"status": "Logs cleared"})

@app.route("/drone/follow/start", methods=["POST"])
def start_drone_follow():
    """Start drone following mode with specified elevation and distance"""
    try:
        data = request.get_json()
        elevation = data.get('elevation', 20)  # Default 20 meters
        distance = data.get('distance', 10)    # Default 10 meters
        
        log_message("INFO", "FOLLOW", f"Follow mode requested: {elevation}m elevation, {distance}m distance")
        
        # Validate inputs
        if elevation < 5 or elevation > 100:
            log_message("ERROR", "FOLLOW", f"Invalid elevation: {elevation}m (must be 5-100m)")
            return jsonify({"error": "Elevation must be between 5 and 100 meters"}), 400
        if distance < 5 or distance > 50:
            log_message("ERROR", "FOLLOW", f"Invalid distance: {distance}m (must be 5-50m)")
            return jsonify({"error": "Distance must be between 5 and 50 meters"}), 400
        
        # Store parameters
        app.config['target_elevation'] = elevation
        app.config['target_distance'] = distance
        
        # Get drone vehicle
        vehicle = get_drone_vehicle()
        if not vehicle:
            log_message("ERROR", "FOLLOW", "Failed to connect to drone - check connection")
            return jsonify({"error": "Failed to connect to drone"}), 500
        
        log_message("SUCCESS", "DRONE", "Vehicle connection established")
        
        # Start tracking mode first
        app.config['tracking_active'] = True
        log_message("INFO", "DRONE", "Telemetry tracking activated")
        
        # Takeoff to target elevation
        log_message("INFO", "FOLLOW", f"Initiating takeoff to {elevation}m")
        arm_and_takeoff(vehicle, elevation)
        
        # Enable follow mode
        app.config['follow_mode'] = True
        log_message("SUCCESS", "FOLLOW", f"Follow mode activated - {elevation}m elevation, {distance}m distance")
        
        return jsonify({
            "status": "Drone follow mode started",
            "elevation": elevation,
            "distance": distance
        })
        
    except Exception as e:
        log_message("ERROR", "FOLLOW", f"Failed to start follow mode: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/drone/follow/stop", methods=["POST"])
def stop_drone_follow():
    """Stop drone following mode and hover in place"""
    try:
        app.config['follow_mode'] = False
        log_message("INFO", "FOLLOW", "Follow mode stopped - drone hovering in place")
        return jsonify({"status": "Drone follow mode stopped - hovering in place"})
    except Exception as e:
        log_message("ERROR", "FOLLOW", f"Error stopping follow mode: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/drone/home", methods=["POST"])
def drone_home():
    """Land the drone (homing function)"""
    try:
        # Stop follow mode
        app.config['follow_mode'] = False
        log_message("INFO", "FOLLOW", "Follow mode stopped for homing")
        
        # Get drone vehicle
        vehicle = get_drone_vehicle()
        if not vehicle:
            log_message("ERROR", "DRONE", "Failed to connect to drone for homing")
            return jsonify({"error": "Failed to connect to drone"}), 500
        
        # Set to LAND mode
        log_message("INFO", "DRONE", "Initiating home landing sequence")
        vehicle.mode = VehicleMode("LAND")
        
        log_message("SUCCESS", "DRONE", "Home landing initiated")
        return jsonify({"status": "Drone landing initiated"})
        
    except Exception as e:
        log_message("ERROR", "DRONE", f"Homing failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/drone/takeoff", methods=["POST"])
def drone_takeoff():
    """Simple takeoff to 5 feet (1.5 meters) above ground"""
    try:
        log_message("INFO", "DRONE", "Basic takeoff requested to 5 feet")
        
        # Get drone vehicle
        vehicle = get_drone_vehicle()
        if not vehicle:
            log_message("ERROR", "DRONE", "Failed to connect to vehicle for takeoff")
            return jsonify({"error": "Failed to connect to drone"}), 500
        
        log_message("SUCCESS", "DRONE", "Vehicle connection established for takeoff")
        
        # Start tracking mode
        app.config['tracking_active'] = True
        log_message("INFO", "DRONE", "Telemetry tracking activated")
        
        # Takeoff to 5 feet (1.5 meters)
        takeoff_altitude = 1.5  # 5 feet = ~1.5 meters
        log_message("INFO", "DRONE", f"Initiating takeoff to {takeoff_altitude}m")
        success = simple_takeoff_only(vehicle, takeoff_altitude)
        
        if success:
            log_message("SUCCESS", "DRONE", f"Takeoff completed to {takeoff_altitude}m (5 feet)")
            return jsonify({"status": f"Drone takeoff initiated to {takeoff_altitude}m (5 feet)"})
        else:
            log_message("ERROR", "DRONE", "Takeoff failed - check vehicle status")
            return jsonify({"error": "Takeoff failed"}), 500
        
    except Exception as e:
        log_message("ERROR", "DRONE", f"Takeoff error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/drone/land", methods=["POST"])
def drone_land():
    """Land the drone at current location"""
    try:
        log_message("INFO", "DRONE", "Basic landing requested at current position")
        
        # Stop follow mode if active
        app.config['follow_mode'] = False
        log_message("INFO", "FOLLOW", "Follow mode disabled for landing")
        
        # Get drone vehicle
        vehicle = get_drone_vehicle()
        if not vehicle:
            log_message("ERROR", "DRONE", "Failed to connect to vehicle for landing")
            return jsonify({"error": "Failed to connect to drone"}), 500
        
        # Set to LAND mode
        log_message("INFO", "DRONE", "Setting vehicle to LAND mode")
        vehicle.mode = VehicleMode("LAND")
        
        log_message("SUCCESS", "DRONE", "Landing sequence initiated at current location")
        return jsonify({"status": "Drone landing at current location"})
        
    except Exception as e:
        log_message("ERROR", "DRONE", f"Landing error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Helper functions
def get_drone_vehicle():
    """Get or create drone vehicle connection"""
    if app.config['drone_vehicle'] is None:
        try:
            log_message("INFO", "DRONE", "Attempting to connect to vehicle...")
            app.config['drone_vehicle'] = connect_vehicle()
            log_message("SUCCESS", "DRONE", "Vehicle connection established")
        except Exception as e:
            log_message("ERROR", "DRONE", f"Failed to connect to vehicle: {str(e)}")
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

def simple_takeoff_only(vehicle, target_altitude):
    """
    Simple takeoff function for basic takeoff to specified altitude.
    Returns True if successful, False if failed.
    """
    try:
        print("Basic pre-arm checks")
        print(f"Target altitude: {target_altitude}m above ground level")
        
        # Don't try to arm until autopilot is ready
        timeout = 60  # 60 second timeout
        start_time = time.time()
        
        while not vehicle.is_armable:
            if time.time() - start_time > timeout:
                print("Timeout waiting for vehicle to be armable")
                return False
            print(" Waiting for vehicle to initialise...")
            time.sleep(1)

        print("Arming motors")
        # Copter should arm in GUIDED mode
        vehicle.mode = VehicleMode("GUIDED")
        time.sleep(2)  # Wait for mode change
        vehicle.armed = True

        # Confirm vehicle armed before attempting to take off
        timeout = 30
        start_time = time.time()
        
        while not vehicle.armed:
            if time.time() - start_time > timeout:
                print("Timeout waiting for arming")
                return False
            print(" Waiting for arming...")
            time.sleep(1)

        print(f"Taking off to {target_altitude}m above ground!")
        vehicle.simple_takeoff(target_altitude)

        # Wait until the vehicle reaches target altitude
        while True:
            current_altitude = vehicle.location.global_relative_frame.alt
            print(f" Altitude: {current_altitude}m")
            if current_altitude >= target_altitude * 0.95:
                print(f"Reached target altitude ({target_altitude}m)")
                return True
            time.sleep(1)
            
    except Exception as e:
        print(f"Takeoff failed: {e}")
        return False

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
            log_message("INFO", "GIMBAL", f"Angle updated to {angle}°")
    except Exception as e:
        log_message("ERROR", "GIMBAL", f"Failed to update angle: {str(e)}")

def drone_follow_loop():
    """
    Main drone following loop - runs in background thread
    """
    log_message("INFO", "SYSTEM", "Drone follow loop started")
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
                        log_message("INFO", "FOLLOW", f"Moving to: {target_lat:.6f}, {target_lon:.6f} at {elevation_above_user}m")
                        
                        # Update gimbal angle
                        update_gimbal_for_tracking()
                    else:
                        log_message("WARNING", "FOLLOW", "No vehicle connection - retrying...")
                else:
                    log_message("WARNING", "FOLLOW", "No user location available for following")
                    
            time.sleep(3)  # Update every 3 seconds
        except Exception as e:
            log_message("ERROR", "FOLLOW", f"Follow loop error: {str(e)}")
            time.sleep(5)

# Camera and Human Detection Routes

@app.route("/camera/start", methods=["POST"])
def start_camera():
    """Start the camera and human detection"""
    try:
        print("🎥 TESTING MODE: Starting camera and human detection")
        detector = get_detector()
        
        # Start detection in a separate thread
        detection_thread = threading.Thread(
            target=detector.run_detection, 
            args=(0, False),  # Use camera 0 (laptop), no OpenCV window
            daemon=True
        )
        detection_thread.start()
        
        log_message("SUCCESS", "CAMERA", "Human detection camera started")
        return jsonify({"status": "Camera started successfully"})
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to start camera: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/stop", methods=["POST"]) 
def stop_camera():
    """Stop the camera and human detection"""
    try:
        print("🛑 TESTING MODE: Stopping camera")
        detector = get_detector()
        detector.cleanup()
        
        log_message("INFO", "CAMERA", "Human detection camera stopped")
        return jsonify({"status": "Camera stopped"})
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to stop camera: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/feed")
def camera_feed():
    """Video feed for the camera stream"""
    def generate():
        detector = get_detector()
        while True:
            try:
                frame_data = detector.get_frame_as_base64()
                if frame_data:
                    yield f"data:image/jpeg;base64,{frame_data}\n\n"
                else:
                    yield f"data:image/jpeg;base64,\n\n"
                time.sleep(0.1)  # ~10 FPS for web display
            except Exception as e:
                print(f"Camera feed error: {e}")
                time.sleep(0.5)
    
    return Response(generate(), mimetype='text/plain')

@app.route("/camera/detections", methods=["GET"])
def get_detections():
    """Get current human detections"""
    try:
        detector = get_detector()
        detections = detector.get_latest_detections()
        
        return jsonify({
            "detections": detections,
            "locked_person": detector.locked_person_id,
            "show_boxes": detector.show_bounding_boxes
        })
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to get detections: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/lock/<int:person_id>", methods=["POST"])
def lock_person(person_id):
    """Lock onto a specific person"""
    try:
        print(f"🔒 TESTING MODE: Locking onto person {person_id}")
        detector = get_detector()
        success = detector.lock_person(person_id)
        
        if success:
            log_message("SUCCESS", "TRACKING", f"Locked onto person {person_id}")
            return jsonify({"status": f"Locked onto person {person_id}"})
        else:
            log_message("WARNING", "TRACKING", f"Person {person_id} not found")
            return jsonify({"error": "Person not found"}), 404
            
    except Exception as e:
        log_message("ERROR", "TRACKING", f"Failed to lock person: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/unlock", methods=["POST"])
def unlock_person():
    """Unlock from current person"""
    try:
        print("🔓 TESTING MODE: Unlocking person")
        detector = get_detector()
        detector.unlock_person()
        
        log_message("INFO", "TRACKING", "Unlocked from person")
        return jsonify({"status": "Unlocked from person"})
        
    except Exception as e:
        log_message("ERROR", "TRACKING", f"Failed to unlock person: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/toggle_boxes", methods=["POST"])
def toggle_bounding_boxes():
    """Toggle bounding box visibility"""
    try:
        print("👁️ TESTING MODE: Toggling bounding boxes")
        detector = get_detector()
        show_boxes = detector.toggle_bounding_boxes()
        
        status = "enabled" if show_boxes else "disabled"
        log_message("INFO", "CAMERA", f"Bounding boxes {status}")
        return jsonify({"status": f"Bounding boxes {status}", "show_boxes": show_boxes})
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to toggle boxes: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/drone/track_person", methods=["POST"])
def track_person_with_drone():
    """Make drone adjustments to center the locked person"""
    try:
        print("🎯 TESTING MODE: Calculating drone adjustments to center person")
        detector = get_detector()
        detections = detector.get_latest_detections()
        
        if detector.locked_person_id is None:
            log_message("WARNING", "TRACKING", "No person locked for tracking")
            return jsonify({"error": "No person locked"}), 400
        
        # Calculate drone adjustments
        adjustments = detector.calculate_drone_adjustment(detections)
        
        if adjustments['yaw_adjustment'] == 0 and adjustments['pitch_adjustment'] == 0:
            log_message("INFO", "TRACKING", "Person already centered")
            return jsonify({"status": "Person already centered", "adjustments": adjustments})
        
        # TESTING MODE: Print what we would do instead of actual drone movement
        yaw_adj = adjustments['yaw_adjustment']
        pitch_adj = adjustments['pitch_adjustment']
        
        print(f"🛩️ TESTING: Would rotate drone - Yaw: {yaw_adj:.2f}°, Pitch: {pitch_adj:.2f}°")
        log_message("INFO", "TRACKING", f"TESTING: Drone adjustment needed - Yaw: {yaw_adj:.1f}°, Pitch: {pitch_adj:.1f}°")
        
        # TODO: When connecting to actual drone, implement actual rotation commands here
        # vehicle = get_drone_vehicle()
        # if vehicle:
        #     # Apply small rotational adjustments
        #     # You'll need to implement rotation commands based on your drone's capabilities
        
        return jsonify({
            "status": "TESTING: Tracking adjustment calculated (no actual movement)",
            "adjustments": adjustments
        })
        
    except Exception as e:
        log_message("ERROR", "TRACKING", f"Failed to track person: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Start drone telemetry and follow loops in background threads
telemetry_thread = threading.Thread(target=drone_telemetry_loop, daemon=True)
telemetry_thread.start()

follow_thread = threading.Thread(target=drone_follow_loop, daemon=True)
follow_thread.start()

if __name__ == "__main__":
    app.run(debug=True)
