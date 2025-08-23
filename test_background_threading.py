#!/usr/bin/env python3
"""
Background Stream Test - Test if we need a background thread for frame capture
This will help confirm the threading issue hypothesis
"""

import cv2
import time
import threading
import base64
from datetime import datetime

# Global variables to simulate the main app
current_gopro_frame = None
stream_active = False
background_thread = None

def log_debug(message, level="DEBUG"):
    """Debug logging with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {level}: {message}")

def background_frame_capture(ip="10.5.5.9"):
    """Background thread that continuously captures frames - like we need in main app"""
    global current_gopro_frame, stream_active
    
    log_debug("=== BACKGROUND FRAME CAPTURE STARTED ===", "INFO")
    
    stream_active = True
    cap = None
    
    try:
        # Try to find a working stream URL
        stream_urls = [
            f"udp://@0.0.0.0:8554",
            f"rtsp://{ip}:554/live",
            f"http://{ip}:8080/live/amba.m3u8"
        ]
        
        for url in stream_urls:
            log_debug(f"Trying background stream: {url}")
            
            if url.startswith("udp://"):
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            elif url.startswith("rtsp://"):
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            else:
                cap = cv2.VideoCapture(url)
            
            if cap and cap.isOpened():
                # Test a frame
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    log_debug(f"✅ Background stream working: {url}")
                    break
                else:
                    cap.release()
                    cap = None
            elif cap:
                cap.release()
                cap = None
        
        if not cap:
            log_debug("❌ No working stream URL found for background capture")
            return
        
        # Configure capture like main app
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 15)
        cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
        
        log_debug("🔄 Starting continuous background capture...")
        
        frame_count = 0
        last_log_time = time.time()
        
        while stream_active:
            try:
                ret, frame = cap.read()
                
                if ret and frame is not None and frame.size > 0:
                    frame_count += 1
                    
                    # Update global frame (this is what the main app needs)
                    current_gopro_frame = frame.copy()
                    
                    # Log progress every 10 seconds
                    if time.time() - last_log_time > 10:
                        log_debug(f"📸 Background capture working - Frame {frame_count}, Shape: {frame.shape}")
                        last_log_time = time.time()
                
                else:
                    time.sleep(0.1)  # Wait if no frame
                    
            except Exception as e:
                log_debug(f"❌ Background capture error: {e}")
                time.sleep(1)
        
        log_debug(f"📊 Background capture ended - Total frames: {frame_count}")
        
    except Exception as e:
        log_debug(f"❌ Background thread error: {e}")
    
    finally:
        if cap:
            cap.release()
        stream_active = False

def simulate_frame_requests():
    """Simulate the JavaScript making frame requests"""
    global current_gopro_frame
    
    log_debug("=== SIMULATING FRAME REQUESTS ===", "INFO")
    
    request_count = 0
    success_count = 0
    
    for i in range(30):  # 30 requests over 60 seconds
        request_count += 1
        
        # Simulate frame endpoint logic
        if current_gopro_frame is not None:
            try:
                # Encode like real endpoint
                _, buffer = cv2.imencode('.jpg', current_gopro_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                success_count += 1
                log_debug(f"✅ Frame request {request_count}: SUCCESS - {len(frame_b64)} chars")
                
            except Exception as e:
                log_debug(f"❌ Frame request {request_count}: Encoding error - {e}")
        else:
            log_debug(f"❌ Frame request {request_count}: No frame available")
        
        time.sleep(2)  # Wait 2 seconds between requests
    
    log_debug(f"📊 Frame request summary: {success_count}/{request_count} successful")
    return success_count, request_count

def main():
    """Main test - demonstrates the threading solution"""
    global background_thread, stream_active
    
    print("=" * 70)
    print("Background Stream Threading Test")
    print("=" * 70)
    
    log_debug("Testing background frame capture vs on-demand requests...", "INFO")
    
    # Start background capture thread
    log_debug("STEP 1: Starting background frame capture thread...", "INFO")
    background_thread = threading.Thread(target=background_frame_capture, daemon=True)
    background_thread.start()
    
    # Wait a bit for stream to start
    time.sleep(5)
    
    # Test frame requests
    log_debug("STEP 2: Starting frame request simulation...", "INFO")
    success_count, total_count = simulate_frame_requests()
    
    # Stop background thread
    log_debug("STEP 3: Stopping background capture...", "INFO")
    stream_active = False
    
    if background_thread.is_alive():
        background_thread.join(timeout=5)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    
    success_rate = success_count / total_count * 100 if total_count > 0 else 0
    
    log_debug(f"Frame request success rate: {success_rate:.1f}% ({success_count}/{total_count})", "INFO")
    
    if success_rate > 80:
        log_debug("✅ SOLUTION CONFIRMED: Background thread works!", "SUCCESS")
        log_debug("💡 The main app needs a background thread to populate current_gopro_frame", "INFO")
    elif success_rate > 0:
        log_debug("⚠️ PARTIAL SUCCESS: Some frames captured", "WARNING")
        log_debug("💡 Stream works but may have reliability issues", "INFO")
    else:
        log_debug("❌ FAILED: No frames captured", "ERROR")
        log_debug("💡 OpenCV stream capture is not working", "INFO")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
