#!/usr/bin/env python3
"""
GoPro Stream Issue Diagnostic Script
Run this when connected to GoPro WiFi to identify the exact problem
"""

import cv2
import time
import threading
import requests
import base64
from datetime import datetime

# Global variables to match the main app
current_gopro_frame = None
gopro_streaming = False

def log_debug(message, level="DEBUG"):
    """Debug logging with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {level}: {message}")

def test_frame_capture_basic(ip="10.5.5.9"):
    """Test basic frame capture like the main app does"""
    global current_gopro_frame, gopro_streaming
    
    log_debug("=== BASIC FRAME CAPTURE TEST ===", "INFO")
    
    # Test the exact same URLs as the main app
    stream_urls = [
        f"udp://@0.0.0.0:8554",
        f"rtsp://{ip}:554/live",
        f"http://{ip}:8080/live/amba.m3u8"
    ]
    
    for url in stream_urls:
        log_debug(f"Testing URL: {url}")
        
        cap = None
        try:
            # Use the exact same approach as main app
            if url.startswith("udp://"):
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            elif url.startswith("rtsp://"):
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                # Set RTSP timeout to prevent hanging
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)  # 10 second timeout
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)   # 5 second read timeout
            else:
                cap = cv2.VideoCapture(url)
            
            if cap and cap.isOpened():
                log_debug("  ✅ Stream opened successfully")
                
                # H.264 decoder optimizations (same as main app)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # Minimal buffer to prevent buildup
                cap.set(cv2.CAP_PROP_FPS, 15)           # Lower FPS for stability
                cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)    # Ensure RGB conversion
                
                # Test frame reading for 35 seconds (longer than the 30s timeout)
                log_debug("  🔄 Testing frame capture for 35 seconds...")
                start_time = time.time()
                frame_count = 0
                last_success = 0
                consecutive_failures = 0
                
                while time.time() - start_time < 35:
                    elapsed = time.time() - start_time
                    
                    try:
                        ret, frame = cap.read()
                        
                        if ret and frame is not None and frame.size > 0:
                            frame_count += 1
                            last_success = elapsed
                            consecutive_failures = 0
                            
                            # Store frame globally like main app
                            current_gopro_frame = frame.copy()
                            
                            if frame_count == 1:
                                log_debug(f"    ✅ FIRST FRAME captured at {elapsed:.1f}s - Shape: {frame.shape}")
                            elif frame_count % 20 == 0:  # Log every 20th frame
                                log_debug(f"    ✅ Frame {frame_count} at {elapsed:.1f}s - Still working")
                                
                        else:
                            consecutive_failures += 1
                            if consecutive_failures % 10 == 1:  # Log every 10th failure
                                log_debug(f"    ❌ Frame read failed at {elapsed:.1f}s (failures: {consecutive_failures})")
                    
                    except Exception as frame_error:
                        log_debug(f"    ❌ Frame exception at {elapsed:.1f}s: {frame_error}")
                        consecutive_failures += 1
                    
                    time.sleep(0.1)  # Small delay like main app
                
                total_time = time.time() - start_time
                log_debug(f"  📊 RESULTS after {total_time:.1f}s:")
                log_debug(f"    Total frames: {frame_count}")
                log_debug(f"    Last successful frame: {last_success:.1f}s ago")
                log_debug(f"    Consecutive failures: {consecutive_failures}")
                
                if frame_count > 0:
                    log_debug(f"  ✅ SUCCESS: {url} can capture frames!")
                    return url, True
                else:
                    log_debug(f"  ❌ FAILED: {url} - no frames captured")
                    
            else:
                log_debug(f"  ❌ Failed to open stream: {url}")
                
        except Exception as e:
            log_debug(f"  ❌ Exception with {url}: {e}")
        
        finally:
            if cap:
                cap.release()
        
        print("-" * 50)
    
    return None, False

def simulate_main_app_behavior(working_url):
    """Simulate the exact behavior of the main app's generate_gopro_stream function"""
    global current_gopro_frame, gopro_streaming
    
    log_debug("=== SIMULATING MAIN APP BEHAVIOR ===", "INFO")
    
    gopro_streaming = True  # Set streaming flag
    
    cap = None
    try:
        log_debug(f"Opening stream like main app: {working_url}")
        
        # Use same logic as main app
        if working_url.startswith("udp://"):
            cap = cv2.VideoCapture(working_url, cv2.CAP_FFMPEG)
        elif working_url.startswith("rtsp://"):
            cap = cv2.VideoCapture(working_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
        else:
            cap = cv2.VideoCapture(working_url)
        
        if not cap or not cap.isOpened():
            log_debug("❌ Failed to open stream in simulation")
            return
        
        # Apply same settings as main app
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 15)
        cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
        
        log_debug("✅ Stream opened, starting frame processing like main app...")
        
        frame_count = 0
        last_frame_time = time.time()
        consecutive_failures = 0
        
        # Run for 40 seconds (past the 30s timeout)
        start_time = time.time()
        
        while gopro_streaming and (time.time() - start_time) < 40:
            elapsed = time.time() - start_time
            
            try:
                ret, frame = cap.read()
                
                if not ret or frame is None or frame.size == 0:
                    consecutive_failures += 1
                    if consecutive_failures >= 15:
                        log_debug(f"❌ Too many consecutive failures ({consecutive_failures}) at {elapsed:.1f}s")
                        break
                    time.sleep(0.2)
                    continue
                
                # Validate frame dimensions (same as main app)
                if len(frame.shape) != 3 or frame.shape[0] < 10 or frame.shape[1] < 10:
                    consecutive_failures += 1
                    log_debug(f"⚠️ Invalid frame dimensions at {elapsed:.1f}s: {frame.shape}")
                    continue
                
                # Reset failure counter
                consecutive_failures = 0
                
                # Check for stream timeout (same as main app)
                current_time = time.time()
                if current_time - last_frame_time > 10:
                    log_debug(f"⚠️ Stream timeout detected at {elapsed:.1f}s - restarting would happen here")
                    break
                
                last_frame_time = current_time
                frame_count += 1
                
                # Process every 5th frame like main app
                if frame_count % 5 != 0:
                    continue
                
                # Resize frame like main app
                height, width = frame.shape[:2]
                if width > 640:
                    scale = 640 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                # Store current frame for single-frame access (main app behavior)
                current_gopro_frame = frame.copy()
                
                # Log progress
                if frame_count % 50 == 0:
                    log_debug(f"📈 Frame {frame_count} processed at {elapsed:.1f}s - Shape: {frame.shape}")
                
                # Test single frame endpoint behavior
                if frame_count % 100 == 0:
                    test_single_frame_endpoint()
                
            except Exception as inner_e:
                log_debug(f"❌ Inner loop error at {elapsed:.1f}s: {inner_e}")
                consecutive_failures += 1
                if consecutive_failures >= 15:
                    break
                time.sleep(0.1)
        
        total_elapsed = time.time() - start_time
        log_debug(f"📊 SIMULATION COMPLETE after {total_elapsed:.1f}s:")
        log_debug(f"  Total frames processed: {frame_count}")
        log_debug(f"  Consecutive failures: {consecutive_failures}")
        log_debug(f"  Current frame available: {current_gopro_frame is not None}")
        
    except Exception as e:
        log_debug(f"❌ Simulation error: {e}")
    
    finally:
        if cap:
            cap.release()
        gopro_streaming = False

def test_single_frame_endpoint():
    """Test the single frame endpoint logic"""
    global current_gopro_frame, gopro_streaming
    
    # Simulate the endpoint logic
    if not gopro_streaming:
        result = {"error": "GoPro streaming not active", "frame": None}
        log_debug("  📡 Frame endpoint: GoPro streaming not active")
        return result
    
    if current_gopro_frame is None:
        result = {"error": "No frame available", "frame": None, "status": "NO_FRAME"}
        log_debug("  📡 Frame endpoint: No frame available")
        return result
    
    try:
        # Try to encode like the real endpoint
        _, buffer = cv2.imencode('.jpg', current_gopro_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        result = {
            "frame": f"data:image/jpeg;base64,{frame_b64[:50]}...",  # Truncated for logging
            "status": "OK",
            "frame_size": len(frame_b64)
        }
        log_debug(f"  📡 Frame endpoint: SUCCESS - {len(frame_b64)} bytes")
        return result
    
    except Exception as e:
        result = {"error": str(e), "frame": None}
        log_debug(f"  📡 Frame endpoint: ERROR - {e}")
        return result

def main():
    """Main diagnostic function"""
    print("=" * 70)
    print("GoPro Stream Issue Diagnostic")
    print("=" * 70)
    
    log_debug("Starting comprehensive GoPro stream diagnosis...", "INFO")
    
    # Test 1: Find a working stream URL
    log_debug("STEP 1: Finding working stream URL...", "INFO")
    working_url, success = test_frame_capture_basic()
    
    if not success:
        log_debug("❌ CRITICAL: No stream URLs work - check GoPro setup", "ERROR")
        return
    
    log_debug(f"✅ Found working URL: {working_url}", "SUCCESS")
    
    # Test 2: Simulate main app behavior
    log_debug("STEP 2: Simulating main app behavior...", "INFO")
    simulate_main_app_behavior(working_url)
    
    # Final summary
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    log_debug("Key findings:", "INFO")
    log_debug(f"1. Working stream URL: {working_url}", "INFO")
    log_debug(f"2. Final frame available: {current_gopro_frame is not None}", "INFO")
    log_debug(f"3. Stream was active: {gopro_streaming}", "INFO")
    
    if current_gopro_frame is not None:
        log_debug("✅ DIAGNOSIS: Stream capture is working!", "SUCCESS")
        log_debug("💡 The issue might be in Flask routing, JavaScript, or browser caching", "INFO")
    else:
        log_debug("❌ DIAGNOSIS: Stream capture is failing", "ERROR")
        log_debug("💡 OpenCV timeout is the root cause", "INFO")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
