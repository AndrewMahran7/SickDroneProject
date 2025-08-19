# ESP32 GPS Streaming System Setup Guide

This system allows you to stream GPS data from your phone through an ESP32 WiFi access point to a Python script on your laptop for processing and logging.

## 📋 System Overview

```
Phone (GPS2IP App) → ESP32 (WiFi AP) → Laptop (Python Script)
```

- **ESP32**: Creates WiFi access point for network connectivity
- **Phone**: Streams GPS NMEA data via UDP 
- **Laptop**: Receives, parses, and logs GPS coordinates

## 🔧 Hardware Requirements

- ESP32 development board (any variant)
- USB cable for ESP32
- Laptop with WiFi capability
- Smartphone with GPS and WiFi

## 📱 Phone Apps (Choose One)

### iPhone - GPS2IP
- Download from App Store: "GPS2IP"
- Cost: ~$2.99
- Reliable NMEA streaming over UDP

### Android - Share GPS
- Download from Google Play: "Share GPS" 
- Free version available
- Multiple output formats including NMEA

### Alternative Android - GPS2Net
- Download from Google Play: "GPS2Net"
- Free with ads
- Simple UDP streaming

## 🚀 Setup Instructions

### Step 1: ESP32 Setup
1. Install Arduino IDE with ESP32 support
2. Open `ESP32_GPS_AccessPoint.ino` 
3. Select your ESP32 board type
4. Upload the sketch to ESP32
5. Open Serial Monitor (115200 baud)
6. Verify access point starts successfully

```
✅ WiFi Access Point Started Successfully!
📡 Network Information:
   SSID: ESP32-AccessPoint
   Password: esp32password
   ESP32 IP: 192.168.4.1
```

### Step 2: Phone Configuration

#### For GPS2IP (iPhone):
1. Connect phone to "ESP32-AccessPoint" WiFi
   - Password: `esp32password`
2. Open GPS2IP app
3. Configure settings:
   - **IP Address**: `192.168.4.2` (laptop IP)
   - **Port**: `11123`
   - **Protocol**: `UDP`
   - **Format**: `NMEA`
   - **Update Rate**: `1 Hz` (or desired frequency)
4. Enable location permissions if prompted
5. Tap "Start" to begin streaming

#### For Share GPS (Android):
1. Connect phone to "ESP32-AccessPoint" WiFi  
   - Password: `esp32password`
2. Open Share GPS app
3. Go to Settings:
   - **Protocol**: `UDP`
   - **Server IP**: `192.168.4.2`
   - **Port**: `11123`
   - **Format**: `NMEA`
   - **Update Interval**: `1000ms`
4. Grant location permissions
5. Tap "Share GPS" to start streaming

### Step 3: Laptop Python Script
1. Ensure Python 3.6+ is installed
2. Navigate to project directory
3. Run the GPS receiver:
   ```bash
   python gps_receiver.py
   ```
4. Look for this output:
   ```
   🌐 GPS Receiver Started
   📡 Listening on: 192.168.4.2:11123
   🔍 Waiting for GPS data...
   ```

## 📊 Expected Output

When everything is working correctly, you'll see GPS updates like this:

```
🛰️  GPS Update [14:25:32] from 192.168.4.3
   📍 Location: 37.421998, -122.084057
   🗻 Altitude: 15.2m
   📡 Satellites: 8, HDOP: 1.2
   🚶 Moved: 2.3m, Total: 45.7m
```

## 📁 Output Files

- **`gps_tracking.csv`**: Timestamped GPS data log
- **Serial Monitor**: ESP32 connection status
- **Console**: Real-time GPS updates

## 🔧 Troubleshooting

### ESP32 Issues
- **Access Point not starting**: Check power supply, try different ESP32 board
- **No devices connecting**: Verify WiFi credentials, check phone WiFi settings
- **ESP32 not responding**: Press reset button, re-upload sketch

### Phone Connection Issues  
- **Can't connect to WiFi**: 
  - Forget and reconnect to ESP32-AccessPoint
  - Check password: `esp32password`
  - Disable mobile data temporarily
- **GPS app not streaming**:
  - Verify IP: `192.168.4.2`, Port: `11123`
  - Check location permissions
  - Try toggling GPS on/off
- **No GPS fix**:
  - Go outside or near windows
  - Wait 30-60 seconds for satellite lock
  - Check GPS is enabled in phone settings

### Python Script Issues
- **"Address already in use"**: 
  - Close other GPS apps/scripts
  - Wait 30 seconds and retry
  - Restart script
- **No GPS data received**:
  - Check phone is streaming to correct IP/port
  - Verify laptop connected to ESP32-AccessPoint
  - Check firewall isn't blocking port 11123
- **Import errors**: Install required Python packages

### Network Issues
- **Laptop not getting 192.168.4.2**:
  - Disconnect/reconnect to ESP32-AccessPoint
  - Check network adapter settings
  - Try `ipconfig` (Windows) or `ifconfig` (Linux/Mac)

## 📈 Advanced Features

### GPS Data Logging
The system automatically logs GPS data to `gps_tracking.csv` with columns:
- Timestamp
- Latitude, Longitude (decimal degrees)
- Altitude (meters)
- Speed (m/s)
- Satellite count
- HDOP (accuracy)
- Distance moved since last update
- Total distance traveled

### Distance Tracking
- Automatically calculates distance between GPS points
- Uses Haversine formula for accuracy
- Shows movement distance and total distance traveled

### NMEA Format Support
Supports standard NMEA sentences:
- **$GPGGA**: GPS fix data (recommended)
- **$GPRMC**: Recommended minimum data
- **$GNGGA/$GNRMC**: Multi-constellation GPS (GPS+GLONASS)

## 🔧 Customization Options

### Change UDP Port
1. Modify ESP32 sketch comments (documentation only)
2. Update `gps_receiver.py` port parameter:
   ```python
   receiver = GPSReceiver(port=12345)  # Custom port
   ```
3. Configure phone app to use new port

### Change WiFi Credentials
1. Modify ESP32 sketch:
   ```cpp
   const char* ap_ssid = "MyCustomNetwork";
   const char* ap_password = "MyPassword123";
   ```
2. Update documentation accordingly

### Add Real-time Mapping
Extend the Python script with:
```python
import folium
# Create real-time map updates
```

### Add Alerts/Notifications
```python
# Add geofencing, speed alerts, etc.
if speed_ms > 25:  # 25 m/s = ~90 km/h
    print("⚠️  High speed detected!")
```

## 📝 Technical Details

### Network Configuration
- **ESP32 IP**: 192.168.4.1 (Access Point)
- **Laptop IP**: 192.168.4.2 (Auto-assigned by DHCP)
- **Phone IP**: 192.168.4.x (Auto-assigned)
- **Subnet**: 192.168.4.0/24 (255.255.255.0)
- **UDP Port**: 11123 (configurable)

### NMEA Sentence Format
```
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
       │      │         │ │          │ │ │  │   │     │ │    │
       │      │         │ │          │ │ │  │   │     │ │    └─ Checksum
       │      │         │ │          │ │ │  │   │     │ └─ Units (M=meters)
       │      │         │ │          │ │ │  │   │     └─ Height of geoid
       │      │         │ │          │ │ │  │   └─ Altitude above sea level
       │      │         │ │          │ │ │  └─ HDOP (horizontal precision)
       │      │         │ │          │ │ └─ Number of satellites
       │      │         │ │          │ └─ GPS quality indicator
       │      │         │ │          └─ Longitude (degrees + minutes)
       │      │         │ └─ N/S indicator
       │      │         └─ Latitude (degrees + minutes)
       │      └─ UTC time (HHMMSS)
       └─ Message type
```

## 🎯 Success Criteria

✅ ESP32 creates stable WiFi access point  
✅ Phone connects and maintains WiFi connection  
✅ GPS app streams NMEA data over UDP  
✅ Python script receives and parses GPS coordinates  
✅ Real-time location updates display on laptop  
✅ GPS data logged to CSV file with timestamps  
✅ Distance calculations work correctly  

## 🆘 Support

If you encounter issues:

1. **Check Serial Monitor**: ESP32 debug messages
2. **Verify Network**: All devices on 192.168.4.x network
3. **Test GPS**: Use phone's built-in GPS/maps first
4. **Check Permissions**: Location access enabled
5. **Try Different Apps**: GPS2IP vs Share GPS vs GPS2Net
6. **Restart Components**: ESP32, phone WiFi, Python script

The system is designed to be robust and provide clear error messages to help diagnose issues quickly.
