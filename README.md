# SickDroneProject 🚁

An autonomous drone tracking and control system that combines GPS location tracking, human detection, and intelligent flight control for advanced surveillance and following applications.

## 🌟 Features

### 📍 GPS Location Tracking
- **Multi-source GPS integration**: Phone GPS (GPS2IP app) with laptop GPS fallback
- **Real-time UDP streaming**: Receives GPS data on port 11123 from phone apps
- **GPS source prioritization**: Phone GPS > Laptop GPS > Manual HTTP input
- **Live status monitoring**: Color-coded GPS health indicators

### 👁️ Human Detection & Tracking
- **YOLOv8 powered detection**: Real-time human detection using Ultralytics YOLOv8n model
- **Person locking system**: Lock onto specific individuals for tracking
- **Bounding box visualization**: Toggle-able detection overlays
- **Live camera feed**: Real-time video stream with detection results

### 🎯 Autonomous Drone Control
- **Follow mode**: Autonomous tracking with configurable elevation and distance
- **Gimbal integration**: Camera orientation control for optimal tracking
- **Basic flight controls**: Takeoff, landing, and emergency home functions
- **DroneKit integration**: Compatible with Pixhawk flight controllers

### 🌐 Web Interface
- **Live dashboard**: Real-time status monitoring and control
- **Mobile responsive**: Works on phones, tablets, and desktops
- **System logs**: Comprehensive logging with auto-scroll and filtering
- **ESP32 integration**: WiFi access point for remote connectivity

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Pixhawk-compatible drone with DroneKit support
- ESP32 (optional, for WiFi access point)
- Phone with GPS2IP app (iPhone) or Share GPS app (Android)
- USB camera or laptop camera for human detection

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AndrewMahran7/SickDroneProject.git
   cd SickDroneProject
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Core Dependencies:**
   - `ultralytics` - YOLOv8 for human detection
   - `dronekit` - Drone control and telemetry
   - `flask` - Web interface
   - `opencv-python` - Camera and image processing
   - `numpy` - Numerical operations

4. **Download YOLOv8 model** (if not present)
   ```bash
   # The yolov8n.pt model will be downloaded automatically on first run
   ```

### Basic Usage

1. **Start the application**
   ```bash
   python sdronep/app.py
   ```

2. **Open web interface**
   - Navigate to `http://localhost:5000` in your browser

3. **Configure GPS streaming** (optional)
   - Connect phone to ESP32-AccessPoint WiFi
   - Set GPS2IP to stream to `192.168.4.2:11123`

4. **Start tracking**
   - Click "Start User Tracking" for GPS
   - Click "Start Drone Tracking" for telemetry
   - Enable camera for human detection
   - Configure and start "Follow Mode" for autonomous tracking

## 📖 Detailed Setup

### GPS Configuration
The system supports multiple GPS sources with automatic prioritization:

1. **Phone GPS (Preferred)**
   - Install GPS2IP (iPhone) or Share GPS (Android)
   - Connect to ESP32-AccessPoint WiFi
   - Configure streaming to `192.168.4.2:11123`

2. **Laptop GPS (Fallback)**
   - Uses browser geolocation API
   - Automatic fallback when phone GPS unavailable

3. **Manual GPS (Backup)**
   - HTTP POST to `/location` endpoint
   - For testing and emergency use

### Drone Connection
- Connect Pixhawk via USB or telemetry radio
- Default connection string: `/dev/ttyUSB0` (Linux) or `COM3` (Windows)
- Configure in `config.py` for your specific setup

### Camera Setup
- Default: Laptop webcam (index 0)
- External cameras: Modify camera index in `human_detection.py`
- Resolution: 1280x720 (configurable)

## 🎮 Usage Guide

### Web Interface Sections

1. **User Location Tracking**
   - Start/stop GPS location tracking
   - View current coordinates and GPS source

2. **Drone Telemetry**
   - Monitor drone connection and location
   - View battery status and flight mode

3. **Live Status**
   - Real-time location data
   - Distance calculations
   - GPS source health indicators

4. **Drone Follow Mode**
   - Configure elevation (5-100m) and distance (5-50m)
   - Autonomous tracking with takeoff/landing

5. **Human Detection & Tracking**
   - Live camera feed with detection overlays
   - Person locking and drone tracking integration
   - Gimbal control for optimal framing

6. **Basic Drone Controls**
   - Manual takeoff to 5 feet
   - Emergency landing
   - System status monitoring

7. **System Logs**
   - Real-time logging with categorization
   - Auto-scroll and manual clearing
   - Error tracking and debugging

### Control Flow
1. **Setup**: Connect drone, start application, open web interface
2. **GPS**: Start user location tracking (phone or laptop GPS)
3. **Drone**: Start drone tracking for telemetry monitoring
4. **Detection**: Enable camera for human detection
5. **Follow**: Configure and start autonomous follow mode
6. **Monitor**: Use system logs and live status for monitoring

## 🏗️ Project Structure

```
SickDroneProject/
├── sdronep/                    # Main application package
│   ├── app.py                  # Flask web application and main controller
│   ├── flight.py               # Drone flight control and DroneKit integration
│   ├── telemetry.py           # ESP32 telemetry and communication
│   ├── human_detection.py     # YOLOv8 human detection and tracking
│   ├── gimbal_control.py      # Camera gimbal control
│   └── navigation.py          # GPS navigation and distance calculations
├── interface/                  # Web interface
│   ├── templates/
│   │   └── index.html         # Main web dashboard
│   └── static/
│       ├── styles.css         # UI styling
│       └── scripts.js         # Frontend JavaScript
├── scripts/                   # Demo and utility scripts
│   ├── connect_demo.py        # DroneKit connection testing
│   └── waypoint_demo.py       # Waypoint navigation examples
├── tests/                     # Unit tests
│   ├── test_flight.py         # Flight control tests
│   └── test_navigation.py     # Navigation system tests
├── config.py                  # Configuration settings
├── setup.py                   # Package installation script
├── yolov8n.pt                # YOLOv8 nano model file
├── ESP32_GPS_AccessPoint.ino  # ESP32 firmware for WiFi AP
├── LICENSE                    # License and attributions
└── README.md                  # This file
```

## ⚖️ License and Attribution

### Project License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses

**Important**: This project uses YOLOv8 from Ultralytics, which has specific licensing requirements:

- **Non-commercial use**: Allowed under AGPL-3.0 license
- **Commercial use**: Requires Ultralytics Enterprise License
- **Enterprise License**: Contact [Ultralytics Licensing](https://www.ultralytics.com/license)

**Other Dependencies:**
- **DroneKit**: Apache License 2.0
- **OpenCV**: Apache License 2.0  
- **Flask**: BSD-3-Clause
- **NumPy**: BSD-3-Clause

**Commercial Usage Notice**: If you plan to use this project commercially, ensure you comply with all third-party license requirements, especially obtaining an Ultralytics Enterprise License for YOLOv8.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/AndrewMahran7/SickDroneProject/issues)
- **Documentation**: See inline code comments and this README
- **License Questions**: Contact Ultralytics for YOLOv8 commercial licensing

## 🔒 Safety Notice

**Important Safety Information:**
- Always follow local drone regulations and laws
- Maintain visual line of sight with your drone
- Test thoroughly in a safe environment before autonomous operations
- Have manual override capabilities ready at all times
- This software is provided as-is for educational and research purposes
- Users are responsible for safe and legal operation

## 🚧 Known Limitations

- Requires stable WiFi connection for phone GPS streaming
- Human detection accuracy depends on lighting conditions
- Follow mode requires adequate GPS signal quality
- DroneKit compatibility limited to supported flight controllers
- Camera performance varies with hardware capabilities

## 🔮 Future Enhancements

- [ ] Multiple person tracking and selection
- [ ] Obstacle avoidance integration
- [ ] Mission planning with waypoints
- [ ] Mobile app for remote control
- [ ] Cloud logging and analytics
- [ ] Multi-drone coordination
- [ ] Advanced gimbal control algorithms
- [ ] Weather-based flight restrictions

---

**Made with ❤️ by Andrew Mahran**

*For educational and research purposes. Please use responsibly and in compliance with local regulations.*