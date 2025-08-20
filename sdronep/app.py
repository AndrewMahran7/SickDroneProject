from flask import Flask, render_template, jsonify, request, Response
from .telemetry import get_current_location, connect_vehicle
from .gimbal_control import center_camera, set_gimbal_angle, get_angle
from .human_detection import get_detector
import os
import math
import threading
import time
import socket
import re
from datetime import datetime
from dronekit import VehicleMode, LocationGlobalRelative

# Get the path to the interface directory
interface_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'interface')
template_dir = os.path.join(interface_dir, 'templates')
static_dir = os.path.join(interface_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Global variables to store locations and tracking state
app.config['current_location'] = (0, 0)  # User location
app.config['location_source'] = 'none'   # Track location source: 'phone', 'laptop', 'none'
app.config['last_phone_update'] = 0      # Timestamp of last phone GPS update
app.config['drone_location'] = (0, 0)    # Drone location
app.config['tracking_active'] = False    # Drone tracking state
app.config['follow_mode'] = False        # Drone follow mode
app.config['target_elevation'] = 20      # Target elevation in meters
app.config['target_distance'] = 10       # Target ground distance in meters
app.config['drone_vehicle'] = None       # Drone vehicle connection
app.config['system_logs'] = []           # System log storage
app.config['gps_udp_active'] = False     # GPS UDP receiver status

# Global variables for camera system
detector_instance = None
camera_auto_started = False
camera_enabled = False  # Boolean to control camera on/off

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

def get_detector():
    """Get or create detector instance (singleton pattern for single camera)"""
    global detector_instance
    if detector_instance is None:
        from sdronep.human_detection import HumanDetector
        detector_instance = HumanDetector()
        log_message("INFO", "CAMERA", "Single camera detector instance created")
    return detector_instance

def auto_start_camera():
    """Automatically start camera when Flask app starts"""
    global camera_auto_started, camera_enabled
    if not camera_auto_started and camera_enabled:
        try:
            print("🎥 AUTO-START: Initializing laptop camera for continuous streaming")
            detector = get_detector()
            
            # Start detection in background thread
            detection_thread = threading.Thread(
                target=detector.run_detection,
                args=(0, False),  # Use camera 0 (laptop), no OpenCV window
                daemon=True
            )
            detection_thread.start()
            
            # Wait for camera initialization with retry mechanism
            max_retries = 10  # Wait up to 5 seconds (10 * 0.5s)
            for attempt in range(max_retries):
                time.sleep(0.5)
                print(f"🔍 AUTO-START: Checking camera status (attempt {attempt + 1}/{max_retries})")
                print(f"    Detector instance: {detector is not None}")
                print(f"    Is running: {detector.is_running if detector else 'N/A'}")
                
                if detector.is_running:
                    log_message("SUCCESS", "CAMERA", "Camera auto-started for continuous live streaming")
                    camera_auto_started = True
                    print("✅ Camera live stream ready at http://localhost:5000")
                    return
            
            # If we reach here, camera didn't start properly
            log_message("WARNING", "CAMERA", f"Auto-start attempted but camera not running after {max_retries} attempts")
            print("⚠️ Camera may need manual restart - check /camera/restart endpoint")
                
        except Exception as e:
            log_message("ERROR", "CAMERA", f"Auto-start failed: {str(e)}")
            print(f"❌ Camera auto-start failed: {e}")
    elif not camera_enabled:
        print("📹 Camera disabled - skipping auto-start")
        log_message("INFO", "CAMERA", "Camera disabled by user setting")

def cleanup_detector():
    """Cleanup and reset detector instance"""
    global detector_instance, camera_auto_started
    if detector_instance is not None:
        try:
            detector_instance.cleanup()
            log_message("INFO", "CAMERA", "Detector instance cleaned up")
        except:
            pass
        detector_instance = None
        camera_auto_started = False

def validate_nmea_checksum(sentence):
    """Validate NMEA sentence checksum"""
    try:
        if '*' not in sentence:
            return False
        content, checksum = sentence.split('*')
        content = content[1:]  # Remove $ prefix
        calc_checksum = 0
        for char in content:
            calc_checksum ^= ord(char)
        return f"{calc_checksum:02X}" == checksum.upper()
    except:
        return False

def nmea_to_decimal(coord_str, direction):
    """Convert NMEA coordinate to decimal degrees"""
    try:
        if not coord_str or '.' not in coord_str:
            return None
        dot_pos = coord_str.find('.')
        if len(coord_str) < 4:
            return None
        if dot_pos >= 4:  # Longitude (DDDMM.MMMM)
            degrees = int(coord_str[:dot_pos-2])
            minutes = float(coord_str[dot_pos-2:])
        else:  # Latitude (DDMM.MMMM)
            degrees = int(coord_str[:dot_pos-2])
            minutes = float(coord_str[dot_pos-2:])
        decimal = degrees + minutes / 60.0
        if direction in ['S', 'W']:
            decimal = -decimal
        return decimal
    except (ValueError, IndexError):
        return None

def parse_nmea_gga(sentence):
    """Parse GPGGA NMEA sentence and return lat, lon if valid"""
    try:
        parts = sentence.split(',')
        if len(parts) < 15:
            return None, None
        
        lat_raw = parts[2]
        lat_dir = parts[3]
        lon_raw = parts[4]
        lon_dir = parts[5]
        quality = int(parts[6]) if parts[6] else 0
        
        if not lat_raw or not lon_raw or quality == 0:
            return None, None
        
        lat_decimal = nmea_to_decimal(lat_raw, lat_dir)
        lon_decimal = nmea_to_decimal(lon_raw, lon_dir)
        
        return lat_decimal, lon_decimal
    except (ValueError, IndexError):
        return None, None

def parse_nmea_rmc(sentence):
    """Parse GPRMC NMEA sentence and return lat, lon if valid"""
    try:
        parts = sentence.split(',')
        if len(parts) < 12:
            return None, None
        
        status = parts[2]
        lat_raw = parts[3]
        lat_dir = parts[4]
        lon_raw = parts[5]
        lon_dir = parts[6]
        
        if status != 'A' or not lat_raw or not lon_raw:
            return None, None
        
        lat_decimal = nmea_to_decimal(lat_raw, lat_dir)
        lon_decimal = nmea_to_decimal(lon_raw, lon_dir)
        
        return lat_decimal, lon_decimal
    except (ValueError, IndexError):
        return None, None

def gps_udp_receiver():
    """Background thread to listen for GPS2IP UDP data on port 11123"""
    log_message("INFO", "GPS", "Starting GPS UDP receiver on port 11123")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to listen for GPS2IP data
        try:
            sock.bind(('0.0.0.0', 11123))  # Listen on all interfaces
            app.config['gps_udp_active'] = True
            log_message("SUCCESS", "GPS", "GPS UDP receiver active - listening for phone GPS")
        except Exception as e:
            log_message("ERROR", "GPS", f"Failed to bind to port 11123: {e}")
            return
        
        sock.settimeout(1.0)  # 1 second timeout
        
        while True:
            try:
                data, address = sock.recvfrom(1024)
                message = data.decode('utf-8', errors='ignore').strip()
                
                if message.startswith('$'):
                    # Validate NMEA checksum
                    if not validate_nmea_checksum(message):
                        continue
                    
                    lat, lon = None, None
                    
                    # Parse different NMEA sentences
                    if message.startswith('$GPGGA') or message.startswith('$GNGGA'):
                        lat, lon = parse_nmea_gga(message)
                    elif message.startswith('$GPRMC') or message.startswith('$GNRMC'):
                        lat, lon = parse_nmea_rmc(message)
                    
                    # Update location if valid GPS data
                    if lat is not None and lon is not None:
                        app.config['current_location'] = (lat, lon)
                        app.config['location_source'] = 'phone'
                        app.config['last_phone_update'] = time.time()
                        log_message("INFO", "GPS", f"Phone GPS: {lat:.6f}, {lon:.6f} from {address[0]}")
                        
            except socket.timeout:
                # Check if we should fall back to laptop GPS
                if app.config['location_source'] == 'phone':
                    phone_timeout = time.time() - app.config['last_phone_update']
                    if phone_timeout > 30:  # No phone GPS for 30 seconds
                        log_message("WARNING", "GPS", "Phone GPS timeout - checking for laptop GPS")
                        # Try to get laptop GPS as fallback
                        try:
                            laptop_lat, laptop_lon = get_current_location()
                            if laptop_lat != 0 or laptop_lon != 0:
                                app.config['current_location'] = (laptop_lat, laptop_lon)
                                app.config['location_source'] = 'laptop'
                                log_message("INFO", "GPS", f"Fallback to laptop GPS: {laptop_lat:.6f}, {laptop_lon:.6f}")
                        except:
                            pass
                continue
                
            except Exception as e:
                log_message("ERROR", "GPS", f"GPS receiver error: {e}")
                time.sleep(5)
                
    except Exception as e:
        log_message("ERROR", "GPS", f"GPS UDP receiver failed: {e}")
    finally:
        app.config['gps_udp_active'] = False
        if 'sock' in locals():
            sock.close()

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
    Continuously update drone location and metrics in a background thread
    """
    log_message("INFO", "SYSTEM", "Drone telemetry loop started")
    while True:
        try:
            if app.config.get('tracking_active', False):
                vehicle = get_drone_vehicle()
                if vehicle:
                    # Update location
                    drone_lat, drone_lon = get_current_location()
                    app.config['drone_location'] = (drone_lat, drone_lon)
                    
                    # Update comprehensive drone metrics
                    app.config['drone_metrics'] = {
                        # Location and altitude
                        'latitude': drone_lat,
                        'longitude': drone_lon,
                        'altitude_relative': getattr(vehicle.location.global_relative_frame, 'alt', 0) or 0,
                        'altitude_absolute': getattr(vehicle.location.global_frame, 'alt', 0) or 0,
                        
                        # Vehicle state
                        'armed': vehicle.armed,
                        'is_armable': vehicle.is_armable,
                        'flight_mode': str(vehicle.mode.name) if vehicle.mode else 'Unknown',
                        'system_status': str(vehicle.system_status.state) if vehicle.system_status else 'Unknown',
                        
                        # Battery info
                        'battery_voltage': getattr(vehicle.battery, 'voltage', 0) or 0,
                        'battery_current': getattr(vehicle.battery, 'current', 0) or 0,
                        'battery_level': getattr(vehicle.battery, 'level', 0) or 0,
                        
                        # GPS info
                        'gps_fix_type': getattr(vehicle.gps_0, 'fix_type', 0) or 0,
                        'gps_satellites': getattr(vehicle.gps_0, 'satellites_visible', 0) or 0,
                        'gps_eph': getattr(vehicle.gps_0, 'eph', 0) or 0,
                        'gps_epv': getattr(vehicle.gps_0, 'epv', 0) or 0,
                        
                        # Attitude (orientation)
                        'pitch': getattr(vehicle.attitude, 'pitch', 0) or 0,
                        'roll': getattr(vehicle.attitude, 'roll', 0) or 0,
                        'yaw': getattr(vehicle.attitude, 'yaw', 0) or 0,
                        
                        # Velocity
                        'groundspeed': getattr(vehicle, 'groundspeed', 0) or 0,
                        'airspeed': getattr(vehicle, 'airspeed', 0) or 0,
                        
                        # Connection status
                        'connection_status': 'Connected',
                        'last_heartbeat': getattr(vehicle, 'last_heartbeat', 0) or 0,
                    }
                    
                    log_message("INFO", "DRONE", f"Metrics updated - Alt: {app.config['drone_metrics']['altitude_relative']:.1f}m, Armed: {app.config['drone_metrics']['armed']}, Mode: {app.config['drone_metrics']['flight_mode']}")
                else:
                    # Vehicle not connected - set default metrics
                    app.config['drone_metrics'] = {
                        'connection_status': 'Disconnected',
                        'armed': False,
                        'is_armable': False,
                        'flight_mode': 'Disconnected',
                        'system_status': 'Disconnected',
                        'altitude_relative': 0,
                        'altitude_absolute': 0,
                        'battery_voltage': 0,
                        'battery_level': 0,
                        'gps_fix_type': 0,
                        'gps_satellites': 0,
                        'latitude': 0,
                        'longitude': 0,
                        'pitch': 0,
                        'roll': 0,
                        'yaw': 0,
                        'groundspeed': 0,
                        'airspeed': 0,
                        'last_heartbeat': 0
                    }
                    
            time.sleep(2)  # Update every 2 seconds
        except Exception as e:
            log_message("ERROR", "DRONE", f"Error getting telemetry: {str(e)}")
            # Set error state metrics
            app.config['drone_metrics'] = {
                'connection_status': 'Error',
                'error_message': str(e),
                'armed': False,
                'is_armable': False,
                'flight_mode': 'Error',
                'altitude_relative': 0,
                'altitude_absolute': 0,
                'battery_level': 0,
                'gps_satellites': 0
            }
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
        
        # Only accept HTTP POST if no phone GPS active or phone GPS is old
        phone_timeout = time.time() - app.config.get('last_phone_update', 0)
        if app.config.get('location_source') == 'phone' and phone_timeout < 30:
            log_message("INFO", "GPS", "Ignoring HTTP location - phone GPS is active")
            return "Phone GPS active - HTTP location ignored"
            
        log_message("INFO", "USER", f"HTTP Location received: {lat:.6f}, {lon:.6f}")
        app.config['current_location'] = (lat, lon)
        app.config['location_source'] = 'http'
        return "OK"
    else:  # GET request
        location = app.config.get('current_location', (0, 0))
        location_source = app.config.get('location_source', 'none')
        last_update = app.config.get('last_phone_update', 0)
        
        # Determine GPS status message
        if location_source == 'phone':
            phone_age = time.time() - last_update
            if phone_age < 10:
                source_status = f"Phone GPS (live - {phone_age:.0f}s ago)"
            elif phone_age < 60:
                source_status = f"Phone GPS (recent - {phone_age:.0f}s ago)"
            else:
                source_status = f"Phone GPS (stale - {phone_age:.0f}s ago)"
        elif location_source == 'laptop':
            source_status = "Laptop GPS (fallback)"
        elif location_source == 'http':
            source_status = "HTTP/Manual input"
        else:
            source_status = "No GPS source"
        
        return jsonify({
            "lat": location[0], 
            "lon": location[1],
            "source": location_source,
            "source_status": source_status,
            "gps_udp_active": app.config.get('gps_udp_active', False)
        })


@app.route("/center")
def center():
    center_camera()
    return "Camera centered"

@app.route("/drone/location", methods=["GET"])
def get_drone_location():
    """Get current drone location"""
    drone_location = app.config.get('drone_location', (0, 0))
    return jsonify({"lat": drone_location[0], "lon": drone_location[1]})

@app.route("/drone/metrics", methods=["GET"])
def get_drone_metrics():
    """Get comprehensive drone metrics and telemetry"""
    drone_metrics = app.config.get('drone_metrics', {
        'connection_status': 'Not Connected',
        'armed': False,
        'is_armable': False,
        'flight_mode': 'Unknown',
        'system_status': 'Unknown',
        'altitude_relative': 0,
        'altitude_absolute': 0,
        'battery_voltage': 0,
        'battery_current': 0,
        'battery_level': 0,
        'gps_fix_type': 0,
        'gps_satellites': 0,
        'gps_eph': 0,
        'gps_epv': 0,
        'pitch': 0,
        'roll': 0,
        'yaw': 0,
        'groundspeed': 0,
        'airspeed': 0,
        'last_heartbeat': 0,
        'latitude': 0,
        'longitude': 0
    })
    
    # Add interpretive status messages
    metrics_with_status = drone_metrics.copy()
    
    # GPS fix type interpretation
    gps_fix_names = {
        0: 'No Fix',
        1: 'No Fix',
        2: '2D Fix',
        3: '3D Fix',
        4: 'DGPS',
        5: 'RTK Float',
        6: 'RTK Fixed'
    }
    metrics_with_status['gps_fix_name'] = gps_fix_names.get(drone_metrics.get('gps_fix_type', 0), 'Unknown')
    
    # Battery status interpretation
    battery_level = drone_metrics.get('battery_level', 0)
    if battery_level > 75:
        metrics_with_status['battery_status'] = 'Good'
    elif battery_level > 50:
        metrics_with_status['battery_status'] = 'Fair'
    elif battery_level > 25:
        metrics_with_status['battery_status'] = 'Low'
    elif battery_level > 0:
        metrics_with_status['battery_status'] = 'Critical'
    else:
        metrics_with_status['battery_status'] = 'Unknown'
    
    # Connection health
    connection_status = drone_metrics.get('connection_status', 'Not Connected')
    if connection_status == 'Connected':
        last_heartbeat = drone_metrics.get('last_heartbeat', 0)
        if time.time() - last_heartbeat < 5:
            metrics_with_status['connection_health'] = 'Good'
        elif time.time() - last_heartbeat < 15:
            metrics_with_status['connection_health'] = 'Fair'
        else:
            metrics_with_status['connection_health'] = 'Poor'
    else:
        metrics_with_status['connection_health'] = 'Disconnected'
    
    # Convert radians to degrees for attitude
    metrics_with_status['pitch_degrees'] = round(drone_metrics.get('pitch', 0) * 57.2958, 1)  # rad to deg
    metrics_with_status['roll_degrees'] = round(drone_metrics.get('roll', 0) * 57.2958, 1)
    metrics_with_status['yaw_degrees'] = round(drone_metrics.get('yaw', 0) * 57.2958, 1)
    
    return jsonify(metrics_with_status)

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
    """Get overall system status including comprehensive drone metrics"""
    user_location = app.config.get('current_location', (0, 0))
    drone_location = app.config.get('drone_location', (0, 0))
    tracking_active = app.config.get('tracking_active', False)
    follow_mode = app.config.get('follow_mode', False)
    target_elevation = app.config.get('target_elevation', 20)
    target_distance = app.config.get('target_distance', 10)
    location_source = app.config.get('location_source', 'none')
    last_phone_update = app.config.get('last_phone_update', 0)
    gps_udp_active = app.config.get('gps_udp_active', False)
    
    # Get comprehensive drone metrics
    drone_metrics = app.config.get('drone_metrics', {
        'connection_status': 'Not Connected',
        'armed': False,
        'is_armable': False,
        'flight_mode': 'Unknown',
        'system_status': 'Unknown',
        'altitude_relative': 0,
        'altitude_absolute': 0,
        'battery_voltage': 0,
        'battery_level': 0,
        'gps_fix_type': 0,
        'gps_satellites': 0,
        'pitch': 0,
        'roll': 0,
        'yaw': 0,
        'groundspeed': 0,
        'airspeed': 0,
        'last_heartbeat': 0
    })
    
    # Determine GPS status
    if location_source == 'phone':
        phone_age = time.time() - last_phone_update
        if phone_age < 10:
            gps_status = f"Phone GPS (live)"
            gps_health = "excellent"
        elif phone_age < 30:
            gps_status = f"Phone GPS (recent - {phone_age:.0f}s)"
            gps_health = "good"
        else:
            gps_status = f"Phone GPS (stale - {phone_age:.0f}s)"
            gps_health = "poor"
    elif location_source == 'laptop':
        gps_status = "Laptop GPS (fallback)"
        gps_health = "fair"
    elif location_source == 'http':
        gps_status = "Manual/HTTP input"
        gps_health = "manual"
    else:
        gps_status = "No GPS source"
        gps_health = "none"
    
    # Add camera status
    global detector_instance, camera_enabled
    camera_running = detector_instance is not None and detector_instance.is_running
    
    distance = calculate_distance(
        user_location[0], user_location[1],
        drone_location[0], drone_location[1]
    )
    
    return jsonify({
        "tracking_active": tracking_active,
        "follow_mode": follow_mode,
        "target_elevation": target_elevation,
        "target_distance": target_distance,
        "camera_running": camera_running,
        "camera_enabled": camera_enabled,
        "user_location": {"lat": user_location[0], "lon": user_location[1]},
        "drone_location": {"lat": drone_location[0], "lon": drone_location[1]},
        "distance_meters": round(distance, 2),
        "distance_feet": round(distance * 3.28084, 2),
        "user_has_location": user_location != (0, 0),
        "drone_has_location": drone_location != (0, 0),
        # GPS source information
        "gps_source": location_source,
        "gps_status": gps_status,
        "gps_health": gps_health,
        "gps_udp_active": gps_udp_active,
        "phone_gps_active": location_source == 'phone' and (time.time() - last_phone_update) < 30,
        # Comprehensive drone metrics
        "drone_metrics": drone_metrics
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

@app.route("/camera/status", methods=["GET"])
def get_camera_status():
    """Get current camera status"""
    global detector_instance, camera_enabled
    if detector_instance is None:
        return jsonify({
            "camera_running": False, 
            "camera_enabled": camera_enabled,
            "message": "Camera not initialized"
        })
    
    return jsonify({
        "camera_running": detector_instance.is_running,
        "camera_enabled": camera_enabled,
        "message": "Camera live stream active" if detector_instance.is_running else "Camera stopped"
    })

@app.route("/camera/enable", methods=["POST"])
def enable_camera():
    """Enable camera and start if not running"""
    try:
        global camera_enabled, camera_auto_started
        camera_enabled = True
        log_message("SUCCESS", "CAMERA", "Camera enabled")
        
        # If camera isn't running, start it
        if not camera_auto_started:
            auto_start_camera()
        
        return jsonify({
            "status": "Camera enabled", 
            "camera_enabled": camera_enabled,
            "camera_running": detector_instance.is_running if detector_instance else False
        })
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to enable camera: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/disable", methods=["POST"])
def disable_camera():
    """Disable camera and stop if running"""
    try:
        global camera_enabled
        camera_enabled = False
        log_message("INFO", "CAMERA", "Camera disabled")
        
        # Stop the camera if it's running
        cleanup_detector()
        
        return jsonify({
            "status": "Camera disabled", 
            "camera_enabled": camera_enabled,
            "camera_running": False
        })
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to disable camera: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/toggle", methods=["POST"])
def toggle_camera():
    """Toggle camera on/off"""
    try:
        global camera_enabled
        camera_enabled = not camera_enabled
        
        if camera_enabled:
            log_message("SUCCESS", "CAMERA", "Camera toggled ON")
            # Start camera if enabled
            auto_start_camera()
            status_msg = "Camera enabled and starting"
        else:
            log_message("INFO", "CAMERA", "Camera toggled OFF")
            # Stop camera if disabled
            cleanup_detector()
            status_msg = "Camera disabled and stopped"
        
        return jsonify({
            "status": status_msg,
            "camera_enabled": camera_enabled,
            "camera_running": detector_instance.is_running if detector_instance else False
        })
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to toggle camera: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/restart", methods=["POST"])
def restart_camera():
    """Restart camera if there are issues"""
    try:
        print("🔄 RESTART: Restarting camera system")
        cleanup_detector()
        time.sleep(1)
        auto_start_camera()
        
        global detector_instance
        if detector_instance and detector_instance.is_running:
            log_message("SUCCESS", "CAMERA", "Camera restarted successfully")
            return jsonify({"status": "Camera restarted successfully"})
        else:
            log_message("ERROR", "CAMERA", "Camera restart failed")
            return jsonify({"error": "Camera restart failed"}), 500
            
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Restart error: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
    """Video feed for the camera stream - returns single frame as base64"""
    global detector_instance, camera_enabled
    
    if not camera_enabled:
        return jsonify({"frame": "", "status": "Camera disabled"})
        
    if detector_instance is None or not detector_instance.is_running:
        # Return empty response if camera not running
        return jsonify({"frame": "", "status": "Camera not running"})
    
    try:
        frame_data = detector_instance.get_frame_as_base64()
        if frame_data:
            return jsonify({"frame": f"data:image/jpeg;base64,{frame_data}", "status": "OK"})
        else:
            return jsonify({"frame": "", "status": "No frame available"})
    except Exception as e:
        print(f"Camera feed error: {e}")
        return jsonify({"frame": "", "status": f"Error: {str(e)}"})

@app.route("/camera/detections", methods=["GET"])
def get_detections():
    """Get current human detections"""
    try:
        global camera_enabled
        if not camera_enabled:
            return jsonify({
                "detections": [],
                "locked_person": None,
                "show_boxes": False,
                "status": "Camera disabled"
            })
            
        detector = get_detector()
        detections = detector.get_latest_detections()
        
        return jsonify({
            "detections": detections,
            "locked_person": detector.locked_person_id,
            "show_boxes": detector.show_bounding_boxes,
            "status": "OK"
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



# Start background threads
telemetry_thread = threading.Thread(target=drone_telemetry_loop, daemon=True)
telemetry_thread.start()

follow_thread = threading.Thread(target=drone_follow_loop, daemon=True)
follow_thread.start()

# Start GPS UDP receiver thread
gps_thread = threading.Thread(target=gps_udp_receiver, daemon=True)
gps_thread.start()

if __name__ == "__main__":
    print("🚀 Starting Drone Control System")
    print("📹 Camera controls available on interface")
    print("📱 GPS UDP receiver listening on port 11123 for phone GPS")
    print("🌐 Access the interface at: http://localhost:5000")
    
    app.run(debug=False, host='127.0.0.1', port=5000)
