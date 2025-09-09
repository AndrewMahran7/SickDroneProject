// Drone Location Tracker - JavaScript Module

// Global state variables
let isUserTracking = false;
let isDroneTracking = false;
let isDroneFollowing = false;
let watchId = null;
let intervalId = null;
let statusUpdateId = null;
let logUpdateId = null;
let lastKnownPosition = null;

// Camera variables
let cameraActive = false;
let detectionInterval = null;
let cameraFeedInterval = null;

// DOM elements - will be initialized when DOM loads
let userStatus, droneStatus, followStatus, basicControlStatus;
let startBtn, stopBtn, droneStartBtn, droneStopBtn, followStartBtn, followStopBtn, homeBtn, takeoffBtn, landBtn, clearLogsBtn;
let logDisplay, autoScrollLogs;
let startCameraBtn, stopCameraBtn, toggleBoxesBtn, cameraFeed, cameraPlaceholder;
let detectionCount, lockedPerson, boxStatus, personList, unlockPersonBtn, trackPersonBtn, trackingInfo, cameraStatus;

// Initialize DOM elements when page loads
function initializeDOMElements() {
    userStatus = document.getElementById("userStatus");
    droneStatus = document.getElementById("droneStatus");
    followStatus = document.getElementById("followStatus");
    basicControlStatus = document.getElementById("basicControlStatus");
    startBtn = document.getElementById("startBtn");
    stopBtn = document.getElementById("stopBtn");
    droneStartBtn = document.getElementById("droneStartBtn");
    droneStopBtn = document.getElementById("droneStopBtn");
    followStartBtn = document.getElementById("followStartBtn");
    followStopBtn = document.getElementById("followStopBtn");
    homeBtn = document.getElementById("homeBtn");
    takeoffBtn = document.getElementById("takeoffBtn");
    landBtn = document.getElementById("landBtn");
    clearLogsBtn = document.getElementById("clearLogsBtn");
    logDisplay = document.getElementById("logDisplay");
    autoScrollLogs = document.getElementById("autoScrollLogs");
    
    // Camera elements
    startCameraBtn = document.getElementById("startCameraBtn");
    stopCameraBtn = document.getElementById("stopCameraBtn");
    toggleBoxesBtn = document.getElementById("toggleBoxesBtn");
    cameraFeed = document.getElementById("cameraFeed");
    cameraPlaceholder = document.getElementById("cameraPlaceholder");
    detectionCount = document.getElementById("detectionCount");
    lockedPerson = document.getElementById("lockedPerson");
    boxStatus = document.getElementById("boxStatus");
    personList = document.getElementById("personList");
    unlockPersonBtn = document.getElementById("unlockPersonBtn");
    trackPersonBtn = document.getElementById("trackPersonBtn");
    trackingInfo = document.getElementById("trackingInfo");
    cameraStatus = document.getElementById("cameraStatus");
}

// Status update functions
function updateUserStatus(message, className) {
    userStatus.textContent = message;
    userStatus.className = className;
}

function updateDroneStatus(message, className) {
    droneStatus.textContent = message;
    droneStatus.className = className;
}

function updateFollowStatus(message, className) {
    followStatus.textContent = message;
    followStatus.className = className;
}

function updateBasicControlStatus(message, className) {
    basicControlStatus.textContent = message;
    basicControlStatus.className = className;
}

// Live status update function
function updateLiveStatus() {
    fetch("http://localhost:3000/status")
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log("Status update received:", data); // Debug log
            
            // Update user location display
            const userLocationElement = document.getElementById("userLocation");
            if (userLocationElement) {
                if (data.user_has_location) {
                    userLocationElement.textContent = 
                        `${data.user_location.lat.toFixed(6)}, ${data.user_location.lon.toFixed(6)}`;
                } else {
                    userLocationElement.textContent = "Not available";
                }
            }

            // Update GPS source display
            const gpsSourceElement = document.getElementById("gpsSource");
            if (gpsSourceElement) {
                if (data.gps_source && data.gps_status) {
                    gpsSourceElement.textContent = data.gps_status;
                    
                    // Color code based on GPS health
                    gpsSourceElement.className = '';
                    if (data.gps_health === 'excellent') {
                        gpsSourceElement.style.color = '#27ae60'; // Green
                    } else if (data.gps_health === 'good') {
                        gpsSourceElement.style.color = '#f39c12'; // Orange
                    } else if (data.gps_health === 'poor') {
                        gpsSourceElement.style.color = '#e74c3c'; // Red
                    } else if (data.gps_health === 'fair') {
                        gpsSourceElement.style.color = '#3498db'; // Blue
                    } else if (data.gps_health === 'manual') {
                        gpsSourceElement.style.color = '#9b59b6'; // Purple
                    } else {
                        gpsSourceElement.style.color = '#7f8c8d'; // Gray
                    }
                } else {
                    gpsSourceElement.textContent = "No GPS source";
                    gpsSourceElement.style.color = '#7f8c8d';
                }
            }

            // Update drone location display
            const droneLocationElement = document.getElementById("droneLocation");
            if (droneLocationElement) {
                if (data.drone_has_location) {
                    droneLocationElement.textContent = 
                        `${data.drone_location.lat.toFixed(6)}, ${data.drone_location.lon.toFixed(6)}`;
                } else {
                    droneLocationElement.textContent = "Not available";
                }
            }

            // Update distance display
            const distanceElement = document.getElementById("distance");
            if (distanceElement) {
                if (data.user_has_location && data.drone_has_location && data.distance_meters > 0) {
                    distanceElement.textContent = 
                        `${data.distance_meters}m (${data.distance_feet}ft)`;
                } else {
                    distanceElement.textContent = "Not calculated";
                }
            }

            // Update follow mode display
            const followModeElement = document.getElementById("followMode");
            if (followModeElement) {
                const followModeText = data.follow_mode ? 
                    `Active (${data.target_elevation}m elevation, ${data.target_distance}m distance)` : 
                    "Inactive";
                followModeElement.textContent = followModeText;
            }
            
            // Update camera status and toggle button
            const cameraStatus = document.getElementById('cameraStatus');
            const toggleCameraBtn = document.getElementById('toggleCameraBtn');
            
            if (cameraStatus && data.camera_enabled !== undefined) {
                if (data.camera_enabled) {
                    if (data.camera_running) {
                        cameraStatus.textContent = '📹 Live camera stream active';
                        cameraStatus.className = 'status-success';
                    } else {
                        cameraStatus.textContent = '📹 Camera enabled but not running';
                        cameraStatus.className = 'status-warning';
                    }
                    if (toggleCameraBtn) toggleCameraBtn.textContent = '📹 Disable Camera';
                } else {
                    cameraStatus.textContent = '📹 Camera disabled';
                    cameraStatus.className = 'status-info';
                    if (toggleCameraBtn) toggleCameraBtn.textContent = '📹 Enable Camera';
                }
            }

            // Update drone metrics
            updateDroneMetrics(data.drone_metrics);
            
            // Update GoPro status
            updateGoproStatus();
        })
        .catch(error => {
            console.error("Status update error:", error);
            // Show connection error in the UI
            const droneLocationElement = document.getElementById("droneLocation");
            if (droneLocationElement) {
                droneLocationElement.textContent = "Connection Error";
                droneLocationElement.style.color = '#e74c3c';
            }
        });
}

// Drone metrics update function
function updateDroneMetrics(metrics) {
    if (!metrics) {
        metrics = {
            connection_status: 'Not Connected',
            armed: false,
            is_armable: false,
            flight_mode: 'Unknown',
            system_status: 'Unknown',
            altitude_relative: 0,
            altitude_absolute: 0,
            battery_level: 0,
            battery_voltage: 0,
            battery_current: 0,
            battery_status: 'Unknown',
            gps_fix_name: 'No Fix',
            gps_satellites: 0,
            gps_eph: 0,
            gps_epv: 0,
            pitch_degrees: 0,
            roll_degrees: 0,
            yaw_degrees: 0,
            groundspeed: 0,
            airspeed: 0,
            latitude: 0,
            longitude: 0,
            last_heartbeat: 0
        };
    }

    // Connection & Status
    const connectionElement = document.getElementById("connectionStatus");
    if (connectionElement) {
        connectionElement.textContent = metrics.connection_status;
        connectionElement.className = metrics.connection_status === 'Connected' ? 'metric-connected' : 
                                     metrics.connection_status === 'Error' ? 'metric-critical' : 'metric-disconnected';
    }

    const armedElement = document.getElementById("armedStatus");
    if (armedElement) {
        armedElement.textContent = metrics.armed ? "ARMED ⚠️" : "Disarmed";
        armedElement.className = metrics.armed ? 'metric-armed' : 'metric-disarmed';
    }

    const armableElement = document.getElementById("armableStatus");
    if (armableElement) {
        armableElement.textContent = metrics.is_armable ? "Ready ✓" : "Not Ready";
        armableElement.className = metrics.is_armable ? 'metric-ready' : 'metric-not-ready';
    }

    const flightModeElement = document.getElementById("flightMode");
    if (flightModeElement) {
        flightModeElement.textContent = metrics.flight_mode;
    }

    const systemStatusElement = document.getElementById("systemStatus");
    if (systemStatusElement) {
        systemStatusElement.textContent = metrics.system_status;
    }

    // Altitude & Position
    const altitudeRelativeElement = document.getElementById("altitudeRelative");
    if (altitudeRelativeElement) {
        altitudeRelativeElement.textContent = `${(metrics.altitude_relative || 0).toFixed(1)} m`;
    }

    const altitudeAbsoluteElement = document.getElementById("altitudeAbsolute");
    if (altitudeAbsoluteElement) {
        altitudeAbsoluteElement.textContent = `${(metrics.altitude_absolute || 0).toFixed(1)} m`;
    }

    const droneLatitudeElement = document.getElementById("droneLatitude");
    if (droneLatitudeElement) {
        droneLatitudeElement.textContent = (metrics.latitude || 0).toFixed(6);
    }

    const droneLongitudeElement = document.getElementById("droneLongitude");
    if (droneLongitudeElement) {
        droneLongitudeElement.textContent = (metrics.longitude || 0).toFixed(6);
    }

    // Battery Information
    const batteryElement = document.getElementById("batteryLevel");
    if (batteryElement) {
        batteryElement.textContent = `${metrics.battery_level || 0}%`;
        batteryElement.className = (metrics.battery_level || 0) > 75 ? 'battery-good' :
                                   (metrics.battery_level || 0) > 50 ? 'battery-fair' :
                                   (metrics.battery_level || 0) > 25 ? 'battery-low' : 
                                   (metrics.battery_level || 0) > 0 ? 'battery-critical' : 'metric-unknown';
    }

    const batteryVoltageElement = document.getElementById("batteryVoltage");
    if (batteryVoltageElement) {
        batteryVoltageElement.textContent = `${(metrics.battery_voltage || 0).toFixed(1)} V`;
    }

    const batteryCurrentElement = document.getElementById("batteryCurrent");
    if (batteryCurrentElement) {
        batteryCurrentElement.textContent = `${(metrics.battery_current || 0).toFixed(1)} A`;
    }
    
    const batteryStatusElement = document.getElementById("batteryStatus");
    if (batteryStatusElement) {
        batteryStatusElement.textContent = metrics.battery_status || 'Unknown';
        batteryStatusElement.className = metrics.battery_status === 'Good' ? 'metric-good' :
                                        metrics.battery_status === 'Fair' ? 'metric-warning' :
                                        metrics.battery_status === 'Low' ? 'metric-warning' :
                                        metrics.battery_status === 'Critical' ? 'metric-critical' : 'metric-unknown';
    }

    // GPS Information
    const gpsFixElement = document.getElementById("gpsFixType");
    if (gpsFixElement) {
        gpsFixElement.textContent = metrics.gps_fix_name || 'No Fix';
        gpsFixElement.className = (metrics.gps_fix_name && metrics.gps_fix_name.includes('3D')) ? 'metric-good' :
                                 (metrics.gps_fix_name && metrics.gps_fix_name.includes('2D')) ? 'metric-warning' : 'metric-critical';
    }

    const satellitesElement = document.getElementById("gpsSatellites");
    if (satellitesElement) {
        satellitesElement.textContent = metrics.gps_satellites || 0;
        satellitesElement.className = (metrics.gps_satellites || 0) >= 8 ? 'metric-good' :
                                     (metrics.gps_satellites || 0) >= 4 ? 'metric-warning' : 'metric-critical';
    }

    const gpsEphElement = document.getElementById("gpsEph");
    if (gpsEphElement) {
        gpsEphElement.textContent = (metrics.gps_eph || 0).toFixed(2);
    }

    const gpsEpvElement = document.getElementById("gpsEpv");
    if (gpsEpvElement) {
        gpsEpvElement.textContent = (metrics.gps_epv || 0).toFixed(2);
    }

    // Attitude (Orientation)
    const pitchElement = document.getElementById("pitchAngle");
    if (pitchElement) {
        pitchElement.textContent = `${(metrics.pitch_degrees || 0).toFixed(1)}°`;
    }

    const rollElement = document.getElementById("rollAngle");
    if (rollElement) {
        rollElement.textContent = `${(metrics.roll_degrees || 0).toFixed(1)}°`;
    }

    const yawElement = document.getElementById("yawAngle");
    if (yawElement) {
        yawElement.textContent = `${(metrics.yaw_degrees || 0).toFixed(1)}°`;
    }

    // Speed Information
    const groundSpeedElement = document.getElementById("groundSpeed");
    if (groundSpeedElement) {
        groundSpeedElement.textContent = `${(metrics.groundspeed || 0).toFixed(1)} m/s`;
    }

    const airSpeedElement = document.getElementById("airSpeed");
    if (airSpeedElement) {
        airSpeedElement.textContent = `${(metrics.airspeed || 0).toFixed(1)} m/s`;
    }
    
    // Last Heartbeat
    const heartbeatElement = document.getElementById("lastHeartbeat");
    if (heartbeatElement) {
        if (metrics.last_heartbeat && metrics.last_heartbeat > 0) {
            const secondsAgo = Math.floor(Date.now() / 1000 - metrics.last_heartbeat);
            heartbeatElement.textContent = secondsAgo < 60 ? `${secondsAgo}s ago` : 'Over 1 min ago';
            heartbeatElement.className = secondsAgo < 5 ? 'metric-good' : 
                                        secondsAgo < 15 ? 'metric-warning' : 'metric-critical';
        } else {
            heartbeatElement.textContent = 'Never';
            heartbeatElement.className = 'metric-unknown';
        }
    }
}

// GoPro status update function
function updateGoproStatus() {
    fetch('http://localhost:3000/gopro/status')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("GoPro status update received:", data); // Debug log
            
            const goproStatus = document.getElementById('goproStatus');
            const recordingStatus = document.getElementById('recordingStatus');
            const autoTrackStatus = document.getElementById('autoTrackStatus');
            const gimbalTilt = document.getElementById('gimbalTilt');
            const tiltValue = document.getElementById('tiltValue');
            
            // Update GoPro connection status
            if (goproStatus) {
                if (data.gopro_enabled) {
                    goproStatus.textContent = `📷 GoPro Connected - ${data.gopro_ip}`;
                    goproStatus.className = 'status-success';
                    enableGoproControls(true);
                } else {
                    goproStatus.textContent = '📷 GoPro Disconnected';
                    goproStatus.className = 'status-info';
                    enableGoproControls(false);
                }
            }
            
            // Update recording status
            if (recordingStatus) {
                if (data.gopro_recording) {
                    recordingStatus.textContent = '🔴 Recording';
                    recordingStatus.className = 'status-recording';
                } else {
                    recordingStatus.textContent = '⚫ Not Recording';
                    recordingStatus.className = '';
                }
            }
            
            // Update auto-tracking status
            if (autoTrackStatus) {
                if (data.auto_tracking_enabled) {
                    autoTrackStatus.textContent = '🎯 Auto-Tracking Enabled';
                    autoTrackStatus.className = 'status-success';
                    const enableBtn = document.getElementById('enableAutoTrackBtn');
                    const disableBtn = document.getElementById('disableAutoTrackBtn');
                    if (enableBtn) enableBtn.disabled = true;
                    if (disableBtn) disableBtn.disabled = false;
                } else {
                    autoTrackStatus.textContent = '🎯 Auto-Tracking Disabled';
                    autoTrackStatus.className = '';
                    const enableBtn = document.getElementById('enableAutoTrackBtn');
                    const disableBtn = document.getElementById('disableAutoTrackBtn');
                    if (enableBtn) enableBtn.disabled = false;
                    if (disableBtn) disableBtn.disabled = true;
                }
            }
            
            // Update gimbal tilt display
            if (gimbalTilt && tiltValue) {
                gimbalTilt.value = data.gimbal_tilt_angle || 0;
                tiltValue.textContent = (data.gimbal_tilt_angle || 0) + '°';
            }
        })
        .catch(error => {
            console.error("GoPro status error:", error);
            const goproStatus = document.getElementById('goproStatus');
            if (goproStatus) {
                goproStatus.textContent = '📷 GoPro Status Error';
                goproStatus.className = 'status-error';
            }
        });
}

// System logs update function
function updateSystemLogs() {
    fetch("http://localhost:3000/logs")
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log("Logs update received:", data.logs ? data.logs.length : 0, "logs"); // Debug log
            
            const logs = data.logs || [];
            if (logs.length > 0 && logDisplay) {
                logDisplay.innerHTML = '';
                logs.forEach(log => {
                    const logElement = document.createElement('div');
                    logElement.className = `log-message ${log.level.toLowerCase()} ${log.component.toLowerCase()}`;
                    logElement.textContent = `[${log.timestamp}] ${log.level} - ${log.component}: ${log.message}`;
                    logDisplay.appendChild(logElement);
                });
                
                // Auto-scroll to bottom if enabled
                if (autoScrollLogs && autoScrollLogs.checked) {
                    logDisplay.scrollTop = logDisplay.scrollHeight;
                }
            } else if (logDisplay) {
                // Show that we're connected but no logs yet
                logDisplay.innerHTML = '<div class="log-message info">Connected to server - waiting for logs...</div>';
            }
        })
        .catch(error => {
            console.error("Log update error:", error);
            if (logDisplay) {
                logDisplay.innerHTML = `<div class="log-message error">Error loading logs: ${error.message}</div>`;
            }
        });
}

// Clear system logs function
function clearSystemLogs() {
    if (confirm("Are you sure you want to clear all system logs?")) {
        fetch("http://localhost:3000/logs/clear", {
            method: "POST"
        })
            .then(res => res.json())
            .then(data => {
                logDisplay.innerHTML = '<div class="log-message">Logs cleared - new logs will appear here...</div>';
            })
            .catch(error => {
                // Error handling for log clearing
            });
    }
}

// Camera control functions
function restartCamera() {
    const cameraStatus = document.getElementById('cameraStatus');
    cameraStatus.textContent = '🔄 Restarting camera...';
    cameraStatus.className = 'status-warning';
    
    fetch('http://localhost:3000/camera/restart', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                cameraStatus.textContent = 'Failed to restart camera: ' + data.error;
                cameraStatus.className = 'status-error';
                alert('Error restarting camera: ' + data.error);
            } else {
                cameraStatus.textContent = '📹 Camera restarted - live stream active';
                cameraStatus.className = 'status-success';
            }
        })
        .catch(error => {
            cameraStatus.textContent = 'Failed to restart camera';
            cameraStatus.className = 'status-error';
        });
}

function toggleCamera() {
    const cameraStatus = document.getElementById('cameraStatus');
    
    cameraStatus.textContent = '� Human detection now uses GoPro feed - start GoPro streaming to detect humans';
    cameraStatus.className = 'status-info';
    
    alert('Human detection has been moved to the GoPro feed. Start GoPro streaming to detect and track humans.');
}

function initializeLiveStream() {
    // GoPro integration is now the primary camera system
    const goproFeedContainer = document.getElementById('goproFeedContainer');
    const goproStatus = document.getElementById('goproStatus');
    const streamStatus = document.getElementById('streamStatus');
    const detectionStatus = document.getElementById('goproDetectionStatus');
    
    // Initialize GoPro feed container (hidden by default)
    if (goproFeedContainer) {
        goproFeedContainer.style.display = 'none';
        console.log("GoPro feed container initialized");
    } else {
        console.log("Warning: goproFeedContainer element not found");
    }
    
    // Set initial status messages
    if (goproStatus) {
        goproStatus.textContent = '📷 GoPro Disconnected';
        console.log("GoPro status initialized");
    } else {
        console.log("Warning: goproStatus element not found");
    }
    
    if (streamStatus) {
        streamStatus.textContent = '� Stream Offline';
        console.log("Stream status initialized");
    } else {
        console.log("Warning: streamStatus element not found");
    }
    
    if (detectionStatus) {
        detectionStatus.textContent = '🎯 Detection Ready (GoPro Feed)';
        console.log("Detection status initialized");
    } else {
        console.log("Warning: detectionStatus element not found");
    }
    
    console.log("Live stream initialization completed - GoPro system ready");
}

function startCameraFeed() {
    cameraFeedInterval = setInterval(() => {
        if (cameraActive) {
            fetch('http://localhost:3000/camera/feed')
                .then(response => response.json())
                .then(data => {
                    if (data.frame && data.frame.length > 50) {
                        const cameraFeed = document.getElementById('cameraFeed');
                        cameraFeed.src = data.frame;
                    }
                })
                .catch(error => {});
        }
    }, 100);
}

function startDetectionUpdates() {
    detectionInterval = setInterval(() => {
        if (document.getElementById('stopStreamBtn').disabled === false) { // GoPro streaming active
            fetch('http://localhost:3000/gopro/detections')
                .then(response => response.json())
                .then(data => {
                    updateDetectionUI(data);
                })
                .catch(error => {
                    // Silent error - GoPro might not be streaming
                });
        }
    }, 500);
}

function stopDetectionUpdates() {
    if (detectionInterval !== null) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
}

function stopCameraFeed() {
    if (cameraFeedInterval !== null) {
        clearInterval(cameraFeedInterval);
        cameraFeedInterval = null;
    }
}

function stopDetectionUpdates() {
    if (detectionInterval !== null) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
}

function updateDetectionUI(data) {
    // Update detection count
    detectionCount.textContent = data.detections.length;
    
    // Update locked person
    lockedPerson.textContent = 
        data.locked_person !== null ? `Person ${data.locked_person}` : 'None';
    
    // Update bounding box status
    boxStatus.textContent = data.show_boxes ? 'ON' : 'OFF';
    
    // Update person list
    if (data.detections.length === 0) {
        personList.innerHTML = '<p>No persons detected in GoPro feed</p>';
    } else {
        personList.innerHTML = data.detections.map(person => `
            <div class="person-item ${data.locked_person === person.id ? 'locked' : ''}">
                <div class="person-info">Person ${person.id} (${(person.confidence * 100).toFixed(1)}%)</div>
                <button onclick="lockGoproPerson(${person.id})" class="lock-btn ${data.locked_person === person.id ? 'unlock' : 'lock'}">
                    ${data.locked_person === person.id ? '🔒 Locked' : '🔓 Lock'}
                </button>
            </div>
        `).join('');
    }
    
    // Enable/disable controls based on locked person
    const hasLockedPerson = data.locked_person !== null;
    unlockPersonBtn.disabled = !hasLockedPerson;
    trackPersonBtn.disabled = !hasLockedPerson;
    
    // Update tracking info
    if (hasLockedPerson) {
        trackingInfo.innerHTML = `<p>✅ Tracking Person ${data.locked_person} in GoPro feed. Click "Center Person with Drone" to adjust drone position.</p>`;
    } else {
        trackingInfo.innerHTML = '<p>💡 Lock onto a person in the GoPro feed to enable drone tracking</p>';
    }
}

function lockGoproPerson(personId) {
    fetch(`http://localhost:3000/gopro/lock/${personId}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error locking person: ' + data.error);
            }
        })
        .catch(error => {});
}

function unlockPerson() {
    fetch('http://localhost:3000/gopro/unlock', { method: 'POST' })
        .then(response => response.json())
        .then(data => {})
        .catch(error => {});
}

function toggleBoundingBoxes() {
    fetch('http://localhost:3000/gopro/toggle_boxes', { method: 'POST' })
        .then(response => response.json())
        .then(data => {})
        .catch(error => {});
}

function trackPersonWithDrone() {
    fetch('http://localhost:3000/drone/track_person', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error tracking person: ' + data.error);
            } else {
                // Show feedback in tracking info
                const adj = data.adjustments;
                trackingInfo.innerHTML = `
                    <p>🎯 Calculated drone adjustments</p>
                    <p>Yaw: ${adj.yaw_adjustment?.toFixed(1) || 0}°, Pitch: ${adj.pitch_adjustment?.toFixed(1) || 0}°</p>
                    <p>Person center: ${adj.person_center ? `(${adj.person_center[0]}, ${adj.person_center[1]})` : 'N/A'}</p>
                    <p>Frame center: ${adj.frame_center ? `(${adj.frame_center[0]}, ${adj.frame_center[1]})` : 'N/A'}</p>
                `;
            }
        })
        .catch(error => {});
}

// GoPro Integration Functions
function connectGopro() {
    const goproIP = document.getElementById('goproIP').value;
    const goproStatus = document.getElementById('goproStatus');
    
    goproStatus.textContent = '🔄 Connecting to GoPro...';
    goproStatus.className = 'status-warning';
    
    fetch('http://localhost:3000/gopro/connect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ip: goproIP })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            goproStatus.textContent = 'Failed to connect: ' + data.error;
            goproStatus.className = 'status-error';
            alert('Error connecting to GoPro: ' + data.error);
        } else {
            goproStatus.textContent = '📷 GoPro Connected - ' + data.ip;
            goproStatus.className = 'status-success';
            
            // Enable controls
            enableGoproControls(true);
        }
    })
    .catch(error => {
        goproStatus.textContent = 'Connection failed';
        goproStatus.className = 'status-error';
        alert('Connection error: ' + error);
    });
}

function disconnectGopro() {
    const goproStatus = document.getElementById('goproStatus');
    
    goproStatus.textContent = '🔄 Disconnecting...';
    goproStatus.className = 'status-warning';
    
    fetch('http://localhost:3000/gopro/disconnect', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        goproStatus.textContent = '📷 GoPro Disconnected';
        goproStatus.className = 'status-info';
        
        // Disable controls
        enableGoproControls(false);
        
        // Reset status displays
        document.getElementById('recordingStatus').textContent = '⚫ Not Recording';
        document.getElementById('autoTrackStatus').textContent = '🎯 Auto-Tracking Disabled';
    })
    .catch(error => {
        goproStatus.textContent = 'Disconnection failed';
        goproStatus.className = 'status-error';
    });
}

function enableGoproControls(enabled) {
    const controls = [
        'connectGoproBtn', 'disconnectGoproBtn', 'startStreamBtn', 'stopStreamBtn',
        'startRecordBtn', 'stopRecordBtn', 'takePhotoBtn'
    ];
    
    controls.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            if (id === 'connectGoproBtn') {
                element.disabled = enabled;
            } else if (id === 'disconnectGoproBtn') {
                element.disabled = !enabled;
            } else {
                element.disabled = !enabled;
            }
        }
    });
}

// Global variables for GoPro streaming
let streamHealthCheckInterval = null;
let streamRestartCount = 0;
let maxStreamRestarts = 3;

function startGoproStream() {
    fetch('http://localhost:3000/gopro/stream/start', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error starting stream: ' + data.error);
        } else {
            document.getElementById('startStreamBtn').disabled = true;
            document.getElementById('stopStreamBtn').disabled = false;
            
            // Show the video feed container
            document.getElementById('goproFeedContainer').style.display = 'block';
            
            // Start the video stream with error handling
            startVideoFeed();
            
            // Start health monitoring
            startStreamHealthMonitoring();
            
            // Start detection updates for GoPro feed
            startDetectionUpdates();
            
            // Reset restart counter
            streamRestartCount = 0;
            
            // Update stream status
            document.getElementById('streamStatus').textContent = '📡 Stream Starting...';
            document.getElementById('streamStatus').className = 'streaming-active';
            
            console.log('GoPro stream started');
        }
    })
    .catch(error => {
        alert('Stream start error: ' + error);
    });
}

function stopGoproStream() {
    fetch('http://localhost:3000/gopro/stream/stop', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error stopping stream: ' + data.error);
        } else {
            document.getElementById('startStreamBtn').disabled = false;
            document.getElementById('stopStreamBtn').disabled = true;
            
            // Hide the video feed container
            document.getElementById('goproFeedContainer').style.display = 'none';
            
            // Stop the video stream
            stopVideoFeed();
            
            // Stop health monitoring
            stopStreamHealthMonitoring();
            
            // Stop detection updates
            stopDetectionUpdates();
            
            // Update stream status
            document.getElementById('streamStatus').textContent = '📡 Stream Offline';
            document.getElementById('streamStatus').className = '';
            
            console.log('GoPro stream stopped');
        }
    })
    .catch(error => {
        alert('Stream stop error: ' + error);
    });
}

function startVideoFeed() {
    const goproCanvas = document.getElementById('goproFeed');
    const ctx = goproCanvas.getContext('2d');
    
    // Set canvas dimensions
    goproCanvas.width = 640;
    goproCanvas.height = 480;
    
    // Update status
    document.getElementById('streamStatus').textContent = '📡 Stream Starting...';
    document.getElementById('streamStatus').style.color = '#ffc107';
    
    // Start polling for frames
    startFramePolling();
    
    // Start detection updates when stream starts
    startGoproDetectionUpdates();
}

let framePollingInterval;
let frameCount = 0;

function startFramePolling() {
    const goproCanvas = document.getElementById('goproFeed');
    const ctx = goproCanvas.getContext('2d');
    
    framePollingInterval = setInterval(async () => {
        try {
            const response = await fetch('http://localhost:3000/gopro/stream/frame');
            const data = await response.json();
            
            if (data.frame && data.status === 'OK') {
                // Create image from base64 data
                const img = new Image();
                img.onload = function() {
                    // Set canvas size to match image if needed
                    if (goproCanvas.width !== img.width || goproCanvas.height !== img.height) {
                        goproCanvas.width = img.width;
                        goproCanvas.height = img.height;
                    }
                    
                    // Draw frame to canvas
                    ctx.drawImage(img, 0, 0);
                    frameCount++;
                    
                    // Update status
                    document.getElementById('streamStatus').textContent = `📡 Stream Live (${frameCount} frames)`;
                    document.getElementById('streamStatus').style.color = '#28a745';
                };
                img.src = data.frame;
            } else {
                // Handle no frame available
                document.getElementById('streamStatus').textContent = '📡 Stream Buffering...';
                document.getElementById('streamStatus').style.color = '#ffc107';
            }
        } catch (error) {
            console.error('Frame polling error:', error);
            document.getElementById('streamStatus').textContent = '📡 Stream Error';
            document.getElementById('streamStatus').style.color = '#dc3545';
        }
    }, 100); // Poll every 100ms for ~10fps
}

function stopVideoFeed() {
    // Stop frame polling
    if (framePollingInterval) {
        clearInterval(framePollingInterval);
        framePollingInterval = null;
    }
    
    // Clear canvas
    const goproCanvas = document.getElementById('goproFeed');
    const ctx = goproCanvas.getContext('2d');
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, goproCanvas.width, goproCanvas.height);
    
    // Update status
    document.getElementById('streamStatus').textContent = '📡 Stream Offline';
    document.getElementById('streamStatus').style.color = '#6c757d';
    
    frameCount = 0;
    
    // Stop detection updates
    stopGoproDetectionUpdates();
}

function handleStreamError() {
    if (streamRestartCount < maxStreamRestarts) {
        streamRestartCount++;
        document.getElementById('streamStatus').textContent = `� Reconnecting (${streamRestartCount}/${maxStreamRestarts})...`;
        
        console.log(`Stream error - attempting restart ${streamRestartCount}/${maxStreamRestarts}`);
        
        // Wait a moment then restart the video feed
        setTimeout(() => {
            if (document.getElementById('stopStreamBtn').disabled === false) { // Stream still active
                startVideoFeed();
            }
        }, 2000);
    } else {
        document.getElementById('streamStatus').textContent = '❌ Stream Failed';
        document.getElementById('streamStatus').className = 'stream-error';
        console.log('Max stream restart attempts reached');
        
        // Auto-stop the stream after too many failures
        setTimeout(() => {
            if (confirm('Stream has failed multiple times. Stop streaming?')) {
                stopGoproStream();
            }
        }, 1000);
    }
}

function startStreamHealthMonitoring() {
    if (streamHealthCheckInterval) {
        clearInterval(streamHealthCheckInterval);
    }
    
    streamHealthCheckInterval = setInterval(() => {
        fetch('http://localhost:3000/gopro/stream/health')
        .then(response => response.json())
        .then(data => {
            if (!data.streaming) {
                console.log('Health check: stream no longer active on backend');
                stopGoproStream();
            } else if (!data.api_responsive) {
                console.log('Health check: GoPro API not responsive');
                document.getElementById('streamStatus').textContent = '⚠️ GoPro Unresponsive';
            }
        })
        .catch(error => {
            console.log('Health check failed:', error);
        });
    }, 10000); // Check every 10 seconds
}

function stopStreamHealthMonitoring() {
    if (streamHealthCheckInterval) {
        clearInterval(streamHealthCheckInterval);
        streamHealthCheckInterval = null;
    }
}

function startGoproRecord() {
    fetch('http://localhost:3000/gopro/record/start', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error starting recording: ' + data.error);
        } else {
            document.getElementById('recordingStatus').textContent = '🔴 Recording';
            document.getElementById('recordingStatus').className = 'status-recording';
            document.getElementById('startRecordBtn').disabled = true;
            document.getElementById('stopRecordBtn').disabled = false;
        }
    })
    .catch(error => {
        alert('Recording start error: ' + error);
    });
}

function stopGoproRecord() {
    fetch('http://localhost:3000/gopro/record/stop', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error stopping recording: ' + data.error);
        } else {
            document.getElementById('recordingStatus').textContent = '⚫ Not Recording';
            document.getElementById('recordingStatus').className = '';
            document.getElementById('startRecordBtn').disabled = false;
            document.getElementById('stopRecordBtn').disabled = true;
        }
    })
    .catch(error => {
        alert('Recording stop error: ' + error);
    });
}

function takeGoproPhoto() {
    fetch('http://localhost:3000/gopro/photo', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error taking photo: ' + data.error);
        } else {
            // Flash effect to show photo was taken
            const photoBtn = document.getElementById('takePhotoBtn');
            photoBtn.style.backgroundColor = '#fff';
            setTimeout(() => {
                photoBtn.style.backgroundColor = '';
            }, 200);
        }
    })
    .catch(error => {
        alert('Photo error: ' + error);
    });
}

function enableAutoTracking() {
    fetch('http://localhost:3000/tracking/auto/enable', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error enabling auto-tracking: ' + data.error);
        } else {
            document.getElementById('autoTrackStatus').textContent = '🎯 Auto-Tracking Enabled';
            document.getElementById('autoTrackStatus').className = 'status-success';
            document.getElementById('enableAutoTrackBtn').disabled = true;
            document.getElementById('disableAutoTrackBtn').disabled = false;
        }
    })
    .catch(error => {
        alert('Auto-tracking error: ' + error);
    });
}

function disableAutoTracking() {
    fetch('http://localhost:3000/tracking/auto/disable', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error disabling auto-tracking: ' + data.error);
        } else {
            document.getElementById('autoTrackStatus').textContent = '🎯 Auto-Tracking Disabled';
            document.getElementById('autoTrackStatus').className = '';
            document.getElementById('enableAutoTrackBtn').disabled = false;
            document.getElementById('disableAutoTrackBtn').disabled = true;
        }
    })
    .catch(error => {
        alert('Auto-tracking error: ' + error);
    });
}

function updateGimbalTilt(angle) {
    document.getElementById('tiltValue').textContent = angle + '°';
    
    fetch('http://localhost:3000/gimbal/tilt', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ angle: parseFloat(angle) })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('Gimbal tilt error:', data.error);
        }
    })
    .catch(error => {
        console.error('Gimbal tilt error:', error);
    });
}

function centerGimbal() {
    document.getElementById('gimbalTilt').value = 0;
    document.getElementById('tiltValue').textContent = '0°';
    
    fetch('http://localhost:3000/gimbal/center', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error centering gimbal: ' + data.error);
        }
    })
    .catch(error => {
        alert('Gimbal center error: ' + error);
    });
}

// Location tracking functions
function sendLocationToServer(latitude, longitude) {
    const data = {
        latitude: latitude,
        longitude: longitude,
    };

    fetch("http://localhost:3000/location", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    })
        .then((res) => res.text())
        .then((text) => {
            if (isUserTracking) {
                updateUserStatus(`User tracking active: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`, "status-sending");
            }
        })
        .catch((error) => {
            if (isUserTracking) {
                updateUserStatus(`Error sending location: ${error.message}`, "status-error");
            }
        });
}

function startLocationTracking() {
    if (!navigator.geolocation) {
        updateUserStatus("Geolocation is not supported by this browser.", "status-error");
        return;
    }

    isUserTracking = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    updateUserStatus("Getting location...", "status-sending");

    navigator.geolocation.getCurrentPosition(
        (position) => {
            lastKnownPosition = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            };
            updateUserStatus("Location acquired successfully", "status-success");
            sendLocationToServer(lastKnownPosition.latitude, lastKnownPosition.longitude);

            // Start watching for position changes
            watchId = navigator.geolocation.watchPosition(
                (position) => {
                    lastKnownPosition = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    };
                    sendLocationToServer(lastKnownPosition.latitude, lastKnownPosition.longitude);
                },
                (error) => {
                    updateUserStatus("Location error: " + error.message, "status-error");
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 30000
                }
            );

            // Send location every 3 seconds
            intervalId = setInterval(() => {
                if (isUserTracking && lastKnownPosition) {
                    sendLocationToServer(lastKnownPosition.latitude, lastKnownPosition.longitude);
                }
            }, 3000);
        },
        (error) => {
            updateUserStatus("Location error: " + error.message, "status-error");
            isUserTracking = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000
        }
    );
}

function stopLocationTracking() {
    isUserTracking = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;

    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
    }

    if (intervalId !== null) {
        clearInterval(intervalId);
        intervalId = null;
    }

    updateUserStatus("User location tracking stopped.", "status-stopped");
}

// Drone control functions
function startDroneTracking() {
    fetch("http://localhost:3000/drone/start", {
        method: "POST"
    })
        .then(res => res.json())
        .then(data => {
            isDroneTracking = true;
            droneStartBtn.disabled = true;
            droneStopBtn.disabled = false;
            updateDroneStatus("Drone tracking started - monitoring Pixhawk location", "status-sending");
        })
        .catch(error => {
            updateDroneStatus(`Error starting drone tracking: ${error.message}`, "status-error");
        });
}

function stopDroneTracking() {
    fetch("http://localhost:3000/drone/stop", {
        method: "POST"
    })
        .then(res => res.json())
        .then(data => {
            isDroneTracking = false;
            droneStartBtn.disabled = false;
            droneStopBtn.disabled = true;
            updateDroneStatus("Drone tracking stopped.", "status-stopped");
        })
        .catch(error => {
            updateDroneStatus(`Error stopping drone tracking: ${error.message}`, "status-error");
        });
}

function startDroneFollow() {
    const elevation = document.getElementById("elevation").value;
    const distance = document.getElementById("groundDistance").value;

    if (!elevation || !distance) {
        updateFollowStatus("Please enter elevation and distance values", "status-error");
        return;
    }

    const data = {
        elevation: parseInt(elevation),
        distance: parseInt(distance)
    };

    updateFollowStatus("Starting drone follow mode - taking off...", "status-sending");
    followStartBtn.disabled = true;

    fetch("http://localhost:3000/drone/follow/start", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                updateFollowStatus(`Error: ${data.error}`, "status-error");
                followStartBtn.disabled = false;
            } else {
                isDroneFollowing = true;
                followStopBtn.disabled = false;
                homeBtn.disabled = false;
                updateFollowStatus(`Follow mode active - Elevation: ${data.elevation}m, Distance: ${data.distance}m`, "status-sending");
            }
        })
        .catch(error => {
            updateFollowStatus(`Error starting follow mode: ${error.message}`, "status-error");
            followStartBtn.disabled = false;
        });
}

function stopDroneFollow() {
    fetch("http://localhost:3000/drone/follow/stop", {
        method: "POST"
    })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                updateFollowStatus(`Error: ${data.error}`, "status-error");
            } else {
                isDroneFollowing = false;
                followStartBtn.disabled = false;
                followStopBtn.disabled = true;
                updateFollowStatus("Follow mode stopped - drone hovering in place", "status-stopped");
            }
        })
        .catch(error => {
            updateFollowStatus(`Error stopping follow mode: ${error.message}`, "status-error");
        });
}

function droneHome() {
    if (confirm("Are you sure you want to land the drone? This will stop all tracking and land immediately.")) {
        fetch("http://localhost:3000/drone/home", {
            method: "POST"
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    updateFollowStatus(`Error: ${data.error}`, "status-error");
                } else {
                    isDroneFollowing = false;
                    followStartBtn.disabled = false;
                    followStopBtn.disabled = true;
                    homeBtn.disabled = true;
                    updateFollowStatus("Drone landing initiated - homing complete", "status-stopped");
                }
            })
            .catch(error => {
                updateFollowStatus(`Error landing drone: ${error.message}`, "status-error");
            });
    }
}

function droneTakeoff() {
    updateBasicControlStatus("Initiating takeoff to 5 feet...", "status-sending");
    takeoffBtn.disabled = true;

    fetch("http://localhost:3000/drone/takeoff", {
        method: "POST"
    })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                updateBasicControlStatus(`Takeoff error: ${data.error}`, "status-error");
                takeoffBtn.disabled = false;
            } else {
                updateBasicControlStatus(`${data.status}`, "status-sending");
                landBtn.disabled = false;
                setTimeout(() => {
                    takeoffBtn.disabled = false;
                }, 10000);
            }
        })
        .catch(error => {
            updateBasicControlStatus(`Takeoff error: ${error.message}`, "status-error");
            takeoffBtn.disabled = false;
        });
}

function droneLand() {
    if (confirm("Are you sure you want to land the drone at its current location?")) {
        updateBasicControlStatus("Initiating landing...", "status-sending");
        landBtn.disabled = true;

        fetch("http://localhost:3000/drone/land", {
            method: "POST"
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    updateBasicControlStatus(`Landing error: ${data.error}`, "status-error");
                    landBtn.disabled = false;
                } else {
                    updateBasicControlStatus(`${data.status}`, "status-stopped");
                    takeoffBtn.disabled = false;
                    setTimeout(() => {
                        landBtn.disabled = false;
                    }, 5000);
                }
            })
            .catch(error => {
                updateBasicControlStatus(`Landing error: ${error.message}`, "status-error");
                landBtn.disabled = false;
            });
    }
}

function disableSafety() {
    console.log("Disabling safety switch...");
    updateBasicControlStatus("⏳ Disabling safety switch for SITL...", "status-sending");
    
    const disableSafetyBtn = document.getElementById('disableSafetyBtn');
    if (disableSafetyBtn) disableSafetyBtn.disabled = true;
    
    fetch('http://localhost:3000/drone/disable_safety', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            updateBasicControlStatus(`❌ Safety disable failed: ${data.error}`, "status-error");
            console.error('Safety disable error:', data.error);
        } else {
            updateBasicControlStatus(`✅ Safety disabled - Armable: ${data.is_armable}`, "status-success");
            console.log('Safety disabled:', data);
            
            // Show success message with details
            const safetyStatus = data.safety_enabled ? 'Enabled' : 'Disabled';
            const armingStatus = data.arming_check ? 'Enabled' : 'Disabled';
            
            alert(`Safety Switch: ${safetyStatus}\nArming Checks: ${armingStatus}\nVehicle Armable: ${data.is_armable}\n\nYou should now be able to takeoff!`);
        }
    })
    .catch(error => {
        updateBasicControlStatus(`❌ Safety disable error: ${error.message}`, "status-error");
        console.error('Safety disable error:', error);
    })
    .finally(() => {
        if (disableSafetyBtn) disableSafetyBtn.disabled = false;
    });
}

// Initialization function - runs when DOM is loaded
function initializeApp() {
    // Initialize DOM elements
    initializeDOMElements();
    
    // Initialize live stream
    initializeLiveStream();

    // Start periodic updates
    statusUpdateId = setInterval(updateLiveStatus, 2000);
    logUpdateId = setInterval(updateSystemLogs, 3000);

    // Handle page unload to stop tracking
    window.addEventListener('beforeunload', () => {
        if (isUserTracking) {
            stopLocationTracking();
        }
        if (isDroneTracking) {
            stopDroneTracking();
        }
        if (statusUpdateId) {
            clearInterval(statusUpdateId);
        }
        if (logUpdateId) {
            clearInterval(logUpdateId);
        }
    });

    // Initial updates
    updateLiveStatus();
    updateSystemLogs();
}

// Wait for DOM to load before initializing
document.addEventListener('DOMContentLoaded', initializeApp);

// GoPro Detection Functions
let goproDetectionInterval = null;

function startGoproDetectionUpdates() {
    if (goproDetectionInterval) {
        clearInterval(goproDetectionInterval);
    }
    
    goproDetectionInterval = setInterval(updateGoproDetections, 1000);
    console.log('Started GoPro detection updates');
}

function stopGoproDetectionUpdates() {
    if (goproDetectionInterval) {
        clearInterval(goproDetectionInterval);
        goproDetectionInterval = null;
    }
    console.log('Stopped GoPro detection updates');
}

function updateGoproDetections() {
    fetch('http://localhost:3000/gopro/detections')
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                const personCount = data.detections ? data.detections.length : 0;
                document.getElementById('detectionCount').textContent = `👥 Persons: ${personCount}`;
                
                // Update locked person status
                if (data.locked_person !== null && data.locked_person !== undefined) {
                    document.getElementById('lockedPersonStatus').textContent = `🔒 Person ${data.locked_person} locked`;
                    document.getElementById('unlockPersonBtn').disabled = false;
                    document.getElementById('lockPersonBtn').disabled = true;
                } else {
                    document.getElementById('lockedPersonStatus').textContent = '🔒 No person locked';
                    document.getElementById('unlockPersonBtn').disabled = true;
                    document.getElementById('lockPersonBtn').disabled = personCount === 0;
                }
                
                // Update detection status
                if (data.show_boxes !== undefined) {
                    document.getElementById('goproDetectionStatus').textContent = 
                        data.show_boxes ? '🎯 Detection Active (Boxes ON)' : '🎯 Detection Active (Boxes OFF)';
                }
            }
        })
        .catch(error => {
            console.log('Detection update error:', error);
            document.getElementById('detectionCount').textContent = '👥 Persons: -';
        });
}

function toggleGoproBoundingBoxes() {
    fetch('http://localhost:3000/gopro/toggle_boxes', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Toggle error: ' + data.error);
        } else {
            console.log('Detection boxes toggled:', data.status);
        }
    })
    .catch(error => {
        alert('Toggle error: ' + error);
    });
}

function lockOnNextPerson() {
    // Lock onto the first detected person (person ID 0)
    fetch('http://localhost:3000/gopro/lock/0', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Lock error: ' + data.error);
        } else {
            console.log('Locked onto person:', data.status);
        }
    })
    .catch(error => {
        alert('Lock error: ' + error);
    });
}

function unlockGoproPerson() {
    fetch('http://localhost:3000/gopro/unlock', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Unlock error: ' + data.error);
        } else {
            console.log('Unlocked person:', data.status);
        }
    })
    .catch(error => {
        alert('Unlock error: ' + error);
    });
}
