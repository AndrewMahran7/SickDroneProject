import cv2
import time

print("🎥 Testing laptop camera access with different backends...")

# Try DirectShow backend (usually more compatible on Windows)
print("\n1. Testing with DirectShow backend...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Cannot open camera 0 with DirectShow")
    
    # Try MSMF backend
    print("\n2. Testing with MSMF backend...")
    cap = cv2.VideoCapture(0, cv2.CAP_MSMF)
    
    if not cap.isOpened():
        print("❌ Cannot open camera 0 with MSMF either")
        print("Possible issues:")
        print("- Another app is using the camera (Zoom, Teams, etc.)")
        print("- Windows camera privacy settings block access") 
        print("- Camera driver issues")
        exit()

print("✅ Camera opened successfully")
print("Camera properties:")
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))
print(f"Width: {width}")
print(f"Height: {height}")
print(f"FPS: {fps}")

# Try to read a frame
print("\nTesting frame capture...")
for i in range(5):
    ret, frame = cap.read()
    if ret:
        print(f"✅ Successfully read frame {i+1} from camera")
        print(f"Frame shape: {frame.shape}")
        break
    else:
        print(f"❌ Failed to read frame {i+1}, trying again...")
        time.sleep(0.5)
else:
    print("❌ Could not read any frames from camera")
    print("Check if:")
    print("- Camera is being used by another application") 
    print("- Windows camera privacy settings allow desktop apps")

# Clean up
cap.release()
print("\n🧹 Camera released")
print("If frame reading works, the issue is with concurrent access in the main app")
