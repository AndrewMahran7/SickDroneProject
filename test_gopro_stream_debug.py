#!/usr/bin/env python3
"""
GoPro Stream Debugging Script
Run this when connected to GoPro WiFi to diagnose stream capture issues
"""

import cv2
import time
import sys
import requests
from datetime import datetime

def log_debug(message):
    """Debug logging with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] DEBUG: {message}")

def test_gopro_connection(ip="10.5.5.9"):
    """Test basic GoPro HTTP connection"""
    log_debug(f"Testing GoPro HTTP connection to {ip}")
    try:
        # Test basic connectivity
        response = requests.get(f"http://{ip}/gp/gpControl/status", timeout=5)
        if response.status_code == 200:
            log_debug(f"✅ GoPro HTTP connection successful - Status: {response.status_code}")
            return True
        else:
            log_debug(f"❌ GoPro HTTP connection failed - Status: {response.status_code}")
            return False
    except Exception as e:
        log_debug(f"❌ GoPro HTTP connection failed - Error: {e}")
        return False

def test_stream_urls(ip="10.5.5.9"):
    """Test different stream URLs to see which ones work"""
    
    stream_urls = [
        f"udp://@0.0.0.0:8554",
        f"rtsp://{ip}:554/live",
        f"http://{ip}:8080/live/amba.m3u8",
        f"rtsp://{ip}:8554/live"
    ]
    
    results = {}
    
    for url in stream_urls:
        log_debug(f"Testing stream URL: {url}")
        
        cap = None
        try:
            # Try to open the stream
            if url.startswith("udp://"):
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            elif url.startswith("rtsp://"):
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                # Set RTSP timeout settings
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)  # 10 second timeout
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)   # 5 second read timeout
            else:
                cap = cv2.VideoCapture(url)
            
            # Check if opened
            if cap and cap.isOpened():
                log_debug(f"  ✅ Stream opened successfully")
                
                # Try to read a frame with timeout
                log_debug(f"  🔄 Attempting to read frames...")
                frame_read_success = False
                
                for attempt in range(10):  # Try 10 times
                    log_debug(f"    Frame read attempt {attempt + 1}/10")
                    ret, frame = cap.read()
                    
                    if ret and frame is not None and frame.size > 0:
                        log_debug(f"    ✅ Frame read successful - Shape: {frame.shape}")
                        frame_read_success = True
                        break
                    else:
                        log_debug(f"    ❌ Frame read failed - ret: {ret}, frame: {frame is not None if frame is not None else 'None'}")
                        time.sleep(0.5)  # Wait between attempts
                
                if frame_read_success:
                    results[url] = "SUCCESS - Stream opened and frames readable"
                    log_debug(f"  ✅ OVERALL SUCCESS for {url}")
                else:
                    results[url] = "PARTIAL - Stream opened but no frames readable"
                    log_debug(f"  ⚠️ PARTIAL SUCCESS for {url}")
                    
            else:
                results[url] = "FAILED - Could not open stream"
                log_debug(f"  ❌ FAILED to open {url}")
                
        except Exception as e:
            results[url] = f"ERROR - {str(e)}"
            log_debug(f"  ❌ ERROR with {url}: {e}")
        
        finally:
            if cap:
                cap.release()
        
        log_debug(f"  Completed test for {url}")
        print("-" * 50)
    
    return results

def test_opencv_backends():
    """Test available OpenCV backends"""
    log_debug("Testing OpenCV backends...")
    
    backends = [
        (cv2.CAP_FFMPEG, "FFMPEG"),
        (cv2.CAP_GSTREAMER, "GStreamer"),
        (cv2.CAP_DSHOW, "DirectShow"),
    ]
    
    for backend_id, backend_name in backends:
        try:
            # Test with a dummy URL to see if backend is available
            cap = cv2.VideoCapture("test", backend_id)
            if cap:
                log_debug(f"  ✅ {backend_name} backend available")
                cap.release()
            else:
                log_debug(f"  ❌ {backend_name} backend not available")
        except Exception as e:
            log_debug(f"  ❌ {backend_name} backend error: {e}")

def test_detailed_rtsp_debug(ip="10.5.5.9"):
    """Detailed RTSP debugging with verbose logging"""
    log_debug("Starting detailed RTSP debugging...")
    
    url = f"rtsp://{ip}:554/live"
    log_debug(f"Testing RTSP URL: {url}")
    
    cap = None
    try:
        # Create capture with FFMPEG backend
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        
        # Set all possible timeout and buffer settings
        settings = {
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC: 15000,  # 15 second open timeout
            cv2.CAP_PROP_READ_TIMEOUT_MSEC: 10000,  # 10 second read timeout
            cv2.CAP_PROP_BUFFERSIZE: 1,             # Minimal buffer
            cv2.CAP_PROP_FPS: 15,                   # Target FPS
            cv2.CAP_PROP_CONVERT_RGB: 1,            # RGB conversion
        }
        
        for prop, value in settings.items():
            try:
                result = cap.set(prop, value)
                log_debug(f"  Setting {prop} = {value}: {'✅ Success' if result else '❌ Failed'}")
            except Exception as e:
                log_debug(f"  Setting {prop} failed: {e}")
        
        # Check if opened
        is_opened = cap.isOpened()
        log_debug(f"  Stream opened: {'✅ Yes' if is_opened else '❌ No'}")
        
        if is_opened:
            # Get stream properties
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            fourcc = cap.get(cv2.CAP_PROP_FOURCC)
            
            log_debug(f"  Stream properties:")
            log_debug(f"    Width: {width}")
            log_debug(f"    Height: {height}")
            log_debug(f"    FPS: {fps}")
            log_debug(f"    FOURCC: {fourcc}")
            
            # Try reading frames with detailed logging
            log_debug(f"  Starting frame reading test (30 second timeout)...")
            start_time = time.time()
            frame_count = 0
            
            while time.time() - start_time < 30:  # 30 second test
                elapsed = time.time() - start_time
                log_debug(f"    Frame attempt {frame_count + 1} at {elapsed:.1f}s")
                
                try:
                    ret, frame = cap.read()
                    
                    if ret and frame is not None and frame.size > 0:
                        frame_count += 1
                        log_debug(f"    ✅ Frame {frame_count} read successfully - Shape: {frame.shape}, Size: {frame.size}")
                        
                        if frame_count >= 5:  # Stop after 5 successful frames
                            log_debug(f"  ✅ SUCCESS: Read {frame_count} frames successfully")
                            break
                    else:
                        log_debug(f"    ❌ Frame read failed - ret: {ret}, frame valid: {frame is not None and frame.size > 0 if frame is not None else False}")
                
                except Exception as frame_error:
                    log_debug(f"    ❌ Frame read exception: {frame_error}")
                
                time.sleep(0.1)  # Small delay between attempts
            
            else:
                log_debug(f"  ⚠️ TIMEOUT: Only read {frame_count} frames in 30 seconds")
        
    except Exception as e:
        log_debug(f"  ❌ RTSP test failed: {e}")
    
    finally:
        if cap:
            cap.release()
            log_debug("  Stream released")

def main():
    """Main test function"""
    print("=" * 60)
    print("GoPro Stream Debug Test")
    print("=" * 60)
    
    log_debug("Starting GoPro stream debugging...")
    
    # Test 1: Basic HTTP connection
    print("\n1. Testing GoPro HTTP Connection")
    print("-" * 30)
    gopro_connected = test_gopro_connection()
    
    if not gopro_connected:
        log_debug("❌ GoPro not reachable - check WiFi connection")
        return
    
    # Test 2: OpenCV backends
    print("\n2. Testing OpenCV Backends")
    print("-" * 30)
    test_opencv_backends()
    
    # Test 3: Stream URLs
    print("\n3. Testing Stream URLs")
    print("-" * 30)
    stream_results = test_stream_urls()
    
    # Test 4: Detailed RTSP debugging
    print("\n4. Detailed RTSP Debug")
    print("-" * 30)
    test_detailed_rtsp_debug()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    log_debug("Stream test results:")
    for url, result in stream_results.items():
        status = "✅" if "SUCCESS" in result else "⚠️" if "PARTIAL" in result else "❌"
        log_debug(f"  {status} {url}: {result}")
    
    print("\n" + "=" * 60)
    log_debug("Debug test completed. Save this log for analysis.")

if __name__ == "__main__":
    main()
