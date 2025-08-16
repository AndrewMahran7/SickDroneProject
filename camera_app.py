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

def cleanup_detector():
    """Cleanup and reset detector instance"""
    global detector_instance
    if detector_instance is not None:
        try:
            detector_instance.cleanup()
            log_message("INFO", "CAMERA", "Detector instance cleaned up")
        except:
            pass
        detector_instance = None

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
    return jsonify({
        "tracking_active": False,
        "follow_mode": False,
        "camera_mode": True,
        "user_has_location": False,
        "drone_has_location": False
    })

# Camera and Human Detection Routes

@app.route("/camera/start", methods=["POST"])
def start_camera():
    """Start the camera and human detection"""
    try:
        print("🎥 TESTING MODE: Starting laptop camera and human detection")
        
        # Cleanup any existing detector first
        cleanup_detector()
        
        # Get fresh detector instance
        detector = get_detector()
        
        # Ensure camera is not already running
        if detector.is_running:
            log_message("WARNING", "CAMERA", "Camera already running - stopping first")
            detector.cleanup()
            time.sleep(1)  # Give time for cleanup
        
        # Start detection in a separate thread with laptop camera (index 0)
        detection_thread = threading.Thread(
            target=detector.run_detection, 
            args=(0, False),  # Use camera 0 (laptop), no OpenCV window
            daemon=True
        )
        detection_thread.start()
        
        # Wait a moment for initialization
        time.sleep(1)
        
        if detector.is_running:
            log_message("SUCCESS", "CAMERA", "Single laptop camera instance started successfully")
            return jsonify({"status": "Camera started successfully"})
        else:
            log_message("ERROR", "CAMERA", "Failed to start camera - check if camera is being used by another application")
            return jsonify({"error": "Failed to start camera"}), 500
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to start camera: {str(e)}")
        cleanup_detector()  # Cleanup on error
        return jsonify({"error": str(e)}), 500

@app.route("/camera/stop", methods=["POST"]) 
def stop_camera():
    """Stop the camera and human detection"""
    try:
        print("🛑 TESTING MODE: Stopping laptop camera")
        cleanup_detector()
        
        log_message("INFO", "CAMERA", "Laptop camera stopped and cleaned up")
        return jsonify({"status": "Camera stopped"})
        
    except Exception as e:
        log_message("ERROR", "CAMERA", f"Failed to stop camera: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/camera/feed")
def camera_feed():
    """Video feed for the camera stream"""
    def generate():
        global detector_instance
        if detector_instance is None:
            yield f"data:image/jpeg;base64,\n\n"
            return
            
        while detector_instance and detector_instance.is_running:
            try:
                frame_data = detector_instance.get_frame_as_base64()
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
        
        return jsonify({
            "status": "TESTING: Tracking adjustment calculated (no actual movement)",
            "adjustments": adjustments
        })
        
    except Exception as e:
        log_message("ERROR", "TRACKING", f"Failed to track person: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 Starting Camera-Only Testing Mode")
    print("📹 Using single laptop camera instance")
    print("🌐 Access the interface at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
