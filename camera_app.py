from flask import Flask, render_template, jsonify, request, Response
import os
import threading
import time
from datetime import datetime

# Get the path to the interface directory
interface_dir = os.path.join(os.path.dirname(__file__), 'interface')
template_dir = os.path.join(interface_dir, 'templates')
static_dir = os.path.join(interface_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Global variables for camera system
app.config['system_logs'] = []           # System log storage
detector_instance = None
camera_auto_started = False

def log_message(level, component, message):
    """
    Add a timestamped log message to the system logs
    level: 'INFO', 'WARNING', 'ERROR', 'SUCCESS'
    component: 'CAMERA', 'TRACKING', 'SYSTEM'
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
    global camera_auto_started
    if not camera_auto_started:
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

@app.route("/")
def index():
    return render_template("index.html")

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

@app.route("/status", methods=["GET"])
def get_status():
    """Get basic system status for camera-only mode"""
    global detector_instance
    camera_running = detector_instance is not None and detector_instance.is_running
    
    return jsonify({
        "tracking_active": False,
        "follow_mode": False,
        "camera_mode": True,
        "camera_running": camera_running,
        "user_has_location": False,
        "drone_has_location": False
    })

# Camera and Human Detection Routes

@app.route("/camera/status", methods=["GET"])
def get_camera_status():
    """Get current camera status"""
    global detector_instance
    if detector_instance is None:
        return jsonify({"camera_running": False, "message": "Camera not initialized"})
    
    return jsonify({
        "camera_running": detector_instance.is_running,
        "message": "Camera live stream active" if detector_instance.is_running else "Camera stopped"
    })

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

@app.route("/camera/feed")
def camera_feed():
    """Video feed for the camera stream - returns single frame as base64"""
    global detector_instance
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
        
        return jsonify({
            "status": "TESTING: Tracking adjustment calculated (no actual movement)",
            "adjustments": adjustments
        })
        
    except Exception as e:
        log_message("ERROR", "TRACKING", f"Failed to track person: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 Starting Camera Live Stream Mode")
    print("📹 Camera will auto-start for continuous streaming")
    print("🌐 Access the live feed at: http://localhost:5000")
    
    # Auto-start camera in a separate thread to avoid blocking Flask startup
    startup_thread = threading.Thread(target=auto_start_camera, daemon=True)
    startup_thread.start()
    
    app.run(debug=False, host='0.0.0.0', port=5000)
