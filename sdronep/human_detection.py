import cv2
import numpy as np
from ultralytics import YOLO
import threading
import time
import base64
import json
from typing import Optional, Tuple, List

class HumanDetector:
    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = 0.5):
        """
        Initialize the human detector with YOLO model
        
        Args:
            model_path: Path to YOLO model (yolov8n.pt, yolov8s.pt, etc.)
            confidence_threshold: Minimum confidence for detection
        """
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.cap = None
        self.is_running = False
        self.frame_count = 0
        self.fps = 0
        self.last_time = time.time()
        
        # Colors for bounding boxes (BGR format)
        self.colors = {
            'person': (0, 255, 0),      # Green for unlocked person
            'locked': (0, 0, 255),      # Red for locked person
            'text_bg': (0, 0, 0),       # Black background for text
            'text': (255, 255, 255),    # White text
            'crosshair': (255, 255, 255) # White crosshair
        }
        
        # Detection and tracking state
        self.latest_detections = []
        self.detection_lock = threading.Lock()
        self.locked_person_id = None
        self.show_bounding_boxes = True
        
        # Web streaming
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # Camera properties (for laptop camera, will be updated for external camera)
        self.frame_center = None
        self.camera_width = 1280
        self.camera_height = 720
    
    def initialize_camera(self, camera_index: int = 0) -> bool:
        """
        Initialize the camera with DirectShow backend for Windows compatibility
        
        Args:
            camera_index: Camera index (0 for laptop camera, higher numbers for external cameras)
            
        Returns:
            bool: True if camera initialized successfully
        """
        try:
            # Use DirectShow backend for better Windows compatibility
            # This avoids MSMF errors that are common on Windows
            self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                print(f"Error: Cannot open camera {camera_index} with DirectShow backend")
                print("Available cameras: Try camera_index 0 (laptop), 1, 2, etc. for external cameras")
                return False
                
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Get actual frame dimensions
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.frame_center = (width // 2, height // 2)
            
            print(f"Camera {camera_index} initialized successfully with DirectShow: {width}x{height}")
            print(f"Frame center: {self.frame_center}")
            return True
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False
    
    def detect_humans(self, frame: np.ndarray) -> List[dict]:
        """
        Detect humans in a frame with unique IDs for tracking
        
        Args:
            frame: Input frame
            
        Returns:
            List of detection dictionaries containing bbox coordinates, confidence, and tracking info
        """
        try:
            # Run YOLO detection - class 0 is 'person'
            results = self.model.predict(
                frame, 
                classes=[0], 
                conf=self.confidence_threshold,
                verbose=False
            )
            
            detections = []
            if results and len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None:
                    for i, box in enumerate(boxes):
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        
                        # Calculate center point and area
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        area = (int(x2) - int(x1)) * (int(y2) - int(y1))
                        
                        detections.append({
                            'id': i,  # Simple ID based on detection order
                            'bbox': (int(x1), int(y1), int(x2), int(y2)),
                            'center': (center_x, center_y),
                            'confidence': float(confidence),
                            'class': 'person',
                            'area': area
                        })
            
            return detections
            
        except Exception as e:
            print(f"Error in human detection: {e}")
            return []
    
    def draw_detections(self, frame: np.ndarray, detections: List[dict]) -> np.ndarray:
        """
        Draw bounding boxes and labels on frame
        
        Args:
            frame: Input frame
            detections: List of detections
            
        Returns:
            Frame with drawn detections
        """
        if not self.show_bounding_boxes:
            return frame
            
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            confidence = detection['confidence']
            person_id = detection['id']
            
            # Use different colors for locked vs unlocked person
            is_locked = (self.locked_person_id == person_id)
            color = self.colors['locked'] if is_locked else self.colors['person']
            thickness = 3 if is_locked else 2
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # Prepare label text
            label = f"Person {person_id}: {confidence:.2f}"
            if is_locked:
                label += " [LOCKED]"
            
            # Calculate text size for background
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            
            # Draw text background
            cv2.rectangle(
                frame, 
                (x1, y1 - text_height - 10), 
                (x1 + text_width, y1), 
                self.colors['text_bg'], 
                -1
            )
            
            # Draw text
            cv2.putText(
                frame, 
                label, 
                (x1, y1 - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                self.colors['text'], 
                2
            )
            
            # Draw center point
            center_x, center_y = detection['center']
            cv2.circle(frame, (center_x, center_y), 5, color, -1)
            
            # Draw clickable area indicator for unlocked persons
            if not is_locked:
                cv2.putText(
                    frame, 
                    f"Click to lock #{person_id}", 
                    (x1, y2 + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.4, 
                    color, 
                    1
                )
        
        # Draw frame center crosshair
        if self.frame_center:
            cx, cy = self.frame_center
            cv2.line(frame, (cx - 20, cy), (cx + 20, cy), self.colors['crosshair'], 2)
            cv2.line(frame, (cx, cy - 20), (cx, cy + 20), self.colors['crosshair'], 2)
            cv2.putText(frame, "CENTER", (cx - 30, cy - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['crosshair'], 1)
        
        return frame
    
    def draw_info_overlay(self, frame: np.ndarray, detections: List[dict]) -> np.ndarray:
        """
        Draw information overlay on frame
        
        Args:
            frame: Input frame
            detections: List of detections
            
        Returns:
            Frame with info overlay
        """
        height, width = frame.shape[:2]
        
        # Update FPS calculation
        current_time = time.time()
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_time)
            self.frame_count = 0
            self.last_time = current_time
        self.frame_count += 1
        
        # Draw semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (350, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Draw information text
        info_lines = [
            f"FPS: {self.fps:.1f}",
            f"Humans Detected: {len(detections)}",
            f"Locked Person: {self.locked_person_id if self.locked_person_id is not None else 'None'}",
            f"Bounding Boxes: {'ON' if self.show_bounding_boxes else 'OFF'}",
            f"Resolution: {width}x{height}"
        ]
        
        for i, line in enumerate(info_lines):
            y_pos = 30 + (i * 22)
            cv2.putText(
                frame, 
                line, 
                (20, y_pos), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                (255, 255, 255), 
                1
            )
        
        return frame
    
    def get_largest_detection(self, detections: List[dict]) -> Optional[dict]:
        """
        Get the largest human detection (by bounding box area)
        
        Args:
            detections: List of detections
            
        Returns:
            Largest detection or None
        """
        if not detections:
            return None
            
        largest = max(detections, key=lambda d: 
                     (d['bbox'][2] - d['bbox'][0]) * (d['bbox'][3] - d['bbox'][1]))
        return largest
    
    def calculate_drone_adjustment(self, detections: List[dict]) -> dict:
        """
        Calculate drone rotation needed to center locked person
        
        Args:
            detections: List of current detections
            
        Returns:
            Dictionary with adjustment values (TESTING MODE - returns None for actual drone commands)
        """
        print("🔄 TESTING MODE: calculate_drone_adjustment called")
        
        if self.locked_person_id is None or not self.frame_center:
            print("❌ No locked person or frame center not set")
            return {'yaw_adjustment': 0, 'pitch_adjustment': 0, 'distance_adjustment': 0}
        
        # Find locked person
        locked_person = None
        for detection in detections:
            if detection['id'] == self.locked_person_id:
                locked_person = detection
                break
        
        if not locked_person:
            print(f"❌ Locked person {self.locked_person_id} not found in current detections")
            return {'yaw_adjustment': 0, 'pitch_adjustment': 0, 'distance_adjustment': 0}
        
        # Calculate offset from center
        person_center = locked_person['center']
        frame_center = self.frame_center
        
        # Calculate pixel offsets
        x_offset = person_center[0] - frame_center[0]
        y_offset = person_center[1] - frame_center[1]
        
        print(f"📍 Person center: {person_center}, Frame center: {frame_center}")
        print(f"📏 Pixel offsets: X={x_offset}, Y={y_offset}")
        
        # Convert to drone adjustments (you may need to calibrate these values)
        # Positive yaw = rotate right, Negative yaw = rotate left
        # Positive pitch = nose up, Negative pitch = nose down
        yaw_sensitivity = 0.1  # degrees per pixel
        pitch_sensitivity = 0.1  # degrees per pixel
        
        yaw_adjustment = x_offset * yaw_sensitivity
        pitch_adjustment = -y_offset * pitch_sensitivity  # Negative because y increases downward
        
        # Calculate distance adjustment based on person size
        # Larger bounding box = person is closer
        person_area = locked_person['area']
        target_area = 50000  # Target area for optimal distance
        distance_adjustment = 0
        
        if person_area < target_area * 0.8:  # Too far
            distance_adjustment = 1  # Move closer
            print("📷 Person appears small - should move closer")
        elif person_area > target_area * 1.2:  # Too close
            distance_adjustment = -1  # Move away
            print("📷 Person appears large - should move away")
        else:
            print("📷 Person size looks good")
        
        print(f"🛩️ TESTING: Would adjust drone - Yaw: {yaw_adjustment:.2f}°, Pitch: {pitch_adjustment:.2f}°")
        print(f"🛩️ TESTING: Distance adjustment: {distance_adjustment}")
        
        return {
            'yaw_adjustment': yaw_adjustment,
            'pitch_adjustment': pitch_adjustment, 
            'distance_adjustment': distance_adjustment,
            'person_center': person_center,
            'frame_center': frame_center,
            'offset': (x_offset, y_offset)
        }
    
    def lock_person(self, person_id: int) -> bool:
        """
        Lock onto a specific person
        
        Args:
            person_id: ID of person to lock onto
            
        Returns:
            bool: True if successfully locked
        """
        print(f"🔒 TESTING MODE: Attempting to lock onto person {person_id}")
        
        with self.detection_lock:
            if any(d['id'] == person_id for d in self.latest_detections):
                self.locked_person_id = person_id
                print(f"✅ Successfully locked onto person {person_id}")
                return True
            else:
                print(f"❌ Person {person_id} not found in current detections")
                return False
    
    def unlock_person(self) -> None:
        """Unlock from current person"""
        if self.locked_person_id is not None:
            print(f"🔓 TESTING MODE: Unlocking from person {self.locked_person_id}")
            self.locked_person_id = None
        else:
            print("🔓 No person currently locked")
    
    def toggle_bounding_boxes(self) -> bool:
        """Toggle bounding box visibility"""
        self.show_bounding_boxes = not self.show_bounding_boxes
        status = "enabled" if self.show_bounding_boxes else "disabled"
        print(f"👁️ TESTING MODE: Bounding boxes {status}")
        return self.show_bounding_boxes
    
    def get_frame_as_base64(self) -> Optional[str]:
        """
        Get current frame as base64 string for web streaming
        
        Returns:
            Base64 encoded frame or None if no frame available
        """
        with self.frame_lock:
            if self.latest_frame is not None:
                try:
                    _, buffer = cv2.imencode('.jpg', self.latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    return frame_base64
                except Exception as e:
                    print(f"Error encoding frame: {e}")
                    return None
        return None
    
    def save_frame(self, frame: np.ndarray) -> None:
        """
        Save current frame with timestamp
        
        Args:
            frame: Frame to save
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"human_detection_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Frame saved as {filename}")
    
    def run_detection(self, camera_index: int = 0, show_window: bool = False) -> None:
        """
        Main detection loop (now optimized for web streaming)
        
        Args:
            camera_index: Camera index to use (0 for laptop, 1+ for external cameras)
            show_window: Whether to show the OpenCV window (disabled for web mode)
        """
        print(f"🎥 TESTING MODE: Starting camera detection (camera_index={camera_index})")
        
        if not self.initialize_camera(camera_index):
            return
        
        self.is_running = True
        print("✅ Human detection started for web streaming")
        print("📱 Access the web interface to see live feed and control tracking")
        
        try:
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    print("❌ Error: Cannot read frame from camera")
                    break
                
                # Flip frame horizontally to create mirror effect (for laptop camera)
                # TODO: For external drone camera, you might want to disable this flip
                frame = cv2.flip(frame, 1)
                
                # Detect humans
                detections = self.detect_humans(frame)
                
                # Update latest detections for other modules
                with self.detection_lock:
                    self.latest_detections = detections
                
                # Draw detections and overlay
                frame_with_detections = self.draw_detections(frame, detections)
                frame_with_overlay = self.draw_info_overlay(frame_with_detections, detections)
                
                # Store frame for web streaming
                with self.frame_lock:
                    self.latest_frame = frame_with_overlay
                
                # Optional: Show window for debugging (usually disabled for web mode)
                if show_window:
                    cv2.imshow('Human Detection - Testing Mode', frame_with_overlay)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("🛑 Quitting detection via keyboard...")
                        break
                    elif key == ord('s'):
                        self.save_frame(frame_with_overlay)
                    elif key == ord('l'):
                        # Lock onto largest person for testing
                        if detections:
                            largest = self.get_largest_detection(detections)
                            if largest:
                                self.lock_person(largest['id'])
                    elif key == ord('u'):
                        # Unlock person for testing
                        self.unlock_person()
                
                # Print tracking info if person is locked
                if self.locked_person_id is not None and len(detections) > 0:
                    adjustments = self.calculate_drone_adjustment(detections)
                    # Only print every 30 frames to avoid spam
                    if self.frame_count % 30 == 0:
                        print(f"🎯 Tracking person {self.locked_person_id} - Adjustments needed: "
                              f"Yaw: {adjustments['yaw_adjustment']:.1f}°, "
                              f"Pitch: {adjustments['pitch_adjustment']:.1f}°")
                
                time.sleep(0.033)  # ~30 FPS
                
        except KeyboardInterrupt:
            print("🛑 Detection interrupted by user")
        
        finally:
            self.cleanup()
    
    def get_latest_detections(self) -> List[dict]:
        """
        Get the latest detections (thread-safe)
        
        Returns:
            List of latest detections
        """
        with self.detection_lock:
            return self.latest_detections.copy()
    
    def cleanup(self) -> None:
        """
        Clean up resources
        """
        self.is_running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("🧹 Human detection cleanup completed")

# Global detector instance for web integration
detector = None

def get_detector():
    """
    Get or create the global detector instance
    
    Returns:
        HumanDetector: Global detector instance
    """
    global detector
    if detector is None:
        print("🚀 Creating new HumanDetector instance for web integration")
        detector = HumanDetector(
            model_path="yolov8n.pt",  # TODO: Change to yolov8s.pt or yolov8m.pt for better accuracy
            confidence_threshold=0.5
        )
    return detector

def main():
    """
    Main function to run human detection in standalone mode
    """
    print("🎯 Initializing Human Detection System...")
    print("📝 TESTING MODE: All drone commands will be printed instead of executed")
    print("💡 Available keyboard controls when window is shown:")
    print("   - 'q': Quit detection")
    print("   - 's': Save current frame")
    print("   - 'l': Lock onto largest detected person")
    print("   - 'u': Unlock from current person")
    
    # Create detector instance
    detector = HumanDetector(
        model_path="yolov8n.pt",  # TODO: Use yolov8s.pt or yolov8m.pt for better accuracy
        confidence_threshold=0.5
    )
    
    # Run detection with window for testing
    try:
        # TODO: For external camera, change camera_index to 1, 2, etc.
        # TODO: For drone integration, set show_window=False and use web interface
        detector.run_detection(camera_index=0, show_window=True)
    except Exception as e:
        print(f"❌ Error running detection: {e}")
    finally:
        detector.cleanup()

if __name__ == "__main__":
    main()
