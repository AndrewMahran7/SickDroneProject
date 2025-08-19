#!/usr/bin/env python3
"""
Enhanced GPS Receiver with Real-time Mapping and Advanced Features

This enhanced version includes:
- Real-time map visualization with Folium
- Geofencing alerts
- Speed monitoring
- GPS signal quality monitoring  
- Data export options
- Web dashboard interface

Install required packages:
    pip install folium matplotlib pandas requests
"""

import socket
import time
import csv
import os
import math
import json
import webbrowser
from datetime import datetime, timedelta
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    import folium
    import pandas as pd
    import matplotlib.pyplot as plt
    ENHANCED_FEATURES = True
except ImportError:
    print("⚠️  Enhanced features disabled. Install: pip install folium pandas matplotlib")
    ENHANCED_FEATURES = False

class EnhancedGPSReceiver:
    def __init__(self, port=11123, log_file="enhanced_gps_log.csv"):
        self.port = port
        self.log_file = log_file
        self.sock = None
        self.last_location = None
        self.total_distance = 0.0
        self.start_time = time.time()
        self.message_count = 0
        self.locations = []  # Store all locations for mapping
        self.speeds = []     # Store speeds for analysis
        self.web_server = None
        
        # Enhanced features
        self.geofence_center = None
        self.geofence_radius = 100  # meters
        self.max_speed_alert = 15   # m/s (~54 km/h)
        self.min_satellites = 4     # Minimum for good accuracy
        
        # Statistics
        self.max_speed = 0.0
        self.avg_speed = 0.0
        self.gps_quality_history = []
        
        self.init_log_file()
        
    def init_log_file(self):
        """Initialize enhanced CSV log file"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'DateTime', 'Latitude', 'Longitude', 
                    'Altitude', 'Speed_ms', 'Speed_kmh', 'Satellites', 
                    'HDOP', 'GPS_Quality', 'Distance_Moved', 'Total_Distance',
                    'Bearing', 'Inside_Geofence'
                ])
            print(f"📝 Created enhanced GPS log: {self.log_file}")
    
    def set_geofence(self, lat, lon, radius_meters=100):
        """Set a circular geofence"""
        self.geofence_center = (lat, lon)
        self.geofence_radius = radius_meters
        print(f"🚧 Geofence set: {lat:.6f}, {lon:.6f} (radius: {radius_meters}m)")
    
    def check_geofence(self, lat, lon):
        """Check if location is inside geofence"""
        if not self.geofence_center:
            return True
        
        distance = self.haversine_distance(
            self.geofence_center[0], self.geofence_center[1], lat, lon
        )
        return distance <= self.geofence_radius
    
    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing between two GPS points"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        x = math.sin(delta_lon) * math.cos(lat2_rad)
        y = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
        
        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def start_listening(self):
        """Enhanced GPS listening with real-time features"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            server_address = ('192.168.4.2', self.port)
            self.sock.bind(server_address)
            self.sock.settimeout(1.0)
            
            print("🌐 Enhanced GPS Receiver Started")
            print("=" * 60)
            print(f"📡 Listening on: {server_address[0]}:{server_address[1]}")
            print(f"🗺️  Real-time mapping: {'Enabled' if ENHANCED_FEATURES else 'Disabled'}")
            print(f"🚧 Geofencing: {'Active' if self.geofence_center else 'Inactive'}")
            print(f"🚨 Speed alerts: > {self.max_speed_alert} m/s")
            print("=" * 60)
            
            # Start web dashboard in background
            if ENHANCED_FEATURES:
                self.start_web_dashboard()
            
            no_data_time = time.time()
            update_count = 0
            
            while True:
                try:
                    data, address = self.sock.recvfrom(1024)
                    self.message_count += 1
                    no_data_time = time.time()
                    
                    message = data.decode('utf-8', errors='ignore').strip()
                    
                    if message.startswith('$'):
                        self.process_nmea_enhanced(message, address)
                        update_count += 1
                        
                        # Update map every 10 GPS updates
                        if ENHANCED_FEATURES and update_count % 10 == 0:
                            self.update_realtime_map()
                            
                except socket.timeout:
                    if time.time() - no_data_time > 30:
                        print(f"⏰ No GPS data for 30s. Check connection...")
                        self.print_statistics()
                        no_data_time = time.time()
                    continue
                    
        except KeyboardInterrupt:
            print("\n🛑 Stopping GPS receiver...")
            self.save_final_report()
        except Exception as e:
            print(f"❌ Enhanced receiver error: {e}")
        finally:
            if self.sock:
                self.sock.close()
            if self.web_server:
                self.web_server.shutdown()
    
    def process_nmea_enhanced(self, sentence, address):
        """Enhanced NMEA processing with additional features"""
        try:
            if not self.validate_nmea_checksum(sentence):
                return
            
            if sentence.startswith('$GPGGA') or sentence.startswith('$GNGGA'):
                self.parse_gga_enhanced(sentence, address)
            elif sentence.startswith('$GPRMC') or sentence.startswith('$GNRMC'):
                self.parse_rmc_enhanced(sentence, address)
                
        except Exception as e:
            print(f"❌ Enhanced NMEA error: {e}")
    
    def parse_gga_enhanced(self, sentence, address):
        """Enhanced GGA parsing with alerts and analysis"""
        parts = sentence.split(',')
        if len(parts) < 15:
            return
        
        try:
            utc_time = parts[1]
            lat_raw = parts[2]
            lat_dir = parts[3]
            lon_raw = parts[4]
            lon_dir = parts[5]
            quality = int(parts[6]) if parts[6] else 0
            satellites = int(parts[7]) if parts[7] else 0
            hdop = float(parts[8]) if parts[8] else 0.0
            altitude = float(parts[9]) if parts[9] else 0.0
            
            if not lat_raw or not lon_raw or quality == 0:
                print(f"📡 Waiting for GPS fix... (sats: {satellites})")
                return
            
            lat_decimal = self.nmea_to_decimal(lat_raw, lat_dir)
            lon_decimal = self.nmea_to_decimal(lon_raw, lon_dir)
            
            if lat_decimal is None or lon_decimal is None:
                return
            
            # Enhanced calculations
            distance_moved = 0.0
            bearing = 0.0
            speed_calculated = 0.0
            
            if self.last_location:
                distance_moved = self.haversine_distance(
                    self.last_location[0], self.last_location[1],
                    lat_decimal, lon_decimal
                )
                self.total_distance += distance_moved
                
                # Calculate bearing
                bearing = self.calculate_bearing(
                    self.last_location[0], self.last_location[1],
                    lat_decimal, lon_decimal
                )
                
                # Calculate speed from position changes
                time_diff = time.time() - self.last_location[2] if len(self.last_location) > 2 else 1
                if time_diff > 0:
                    speed_calculated = distance_moved / time_diff
            
            current_time = time.time()
            self.last_location = (lat_decimal, lon_decimal, current_time)
            
            # Store location for mapping
            self.locations.append({
                'lat': lat_decimal,
                'lon': lon_decimal,
                'alt': altitude,
                'time': datetime.now(),
                'satellites': satellites,
                'hdop': hdop,
                'quality': quality
            })
            
            # GPS quality monitoring
            self.gps_quality_history.append({
                'time': datetime.now(),
                'satellites': satellites,
                'hdop': hdop,
                'quality': quality
            })
            
            # Keep only last 100 quality measurements
            if len(self.gps_quality_history) > 100:
                self.gps_quality_history.pop(0)
            
            # Geofence check
            inside_geofence = self.check_geofence(lat_decimal, lon_decimal)
            if self.geofence_center and not inside_geofence:
                print(f"🚨 GEOFENCE ALERT: Outside allowed area!")
            
            # Satellite quality check
            if satellites < self.min_satellites:
                print(f"⚠️  LOW GPS QUALITY: Only {satellites} satellites")
            
            # HDOP quality check
            if hdop > 5.0:
                print(f"⚠️  POOR GPS ACCURACY: HDOP {hdop:.1f}")
            
            # Display enhanced update
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"🛰️  GPS Update [{timestamp}] - Quality: {quality}")
            print(f"   📍 {lat_decimal:.6f}, {lon_decimal:.6f} (±{hdop*3:.1f}m)")
            print(f"   🗻 Alt: {altitude:.1f}m | 📡 Sats: {satellites} | 🎯 HDOP: {hdop:.1f}")
            
            if distance_moved > 0:
                print(f"   🧭 Bearing: {bearing:.0f}° | 🚶 Moved: {distance_moved:.1f}m")
                if speed_calculated > 0:
                    print(f"   ⚡ Speed: {speed_calculated:.1f} m/s ({speed_calculated*3.6:.1f} km/h)")
            
            if not inside_geofence:
                print(f"   🚧 Outside geofence!")
            
            # Log enhanced data
            self.log_enhanced_data(
                timestamp, datetime.now().isoformat(), lat_decimal, lon_decimal,
                altitude, speed_calculated, speed_calculated * 3.6, satellites,
                hdop, quality, distance_moved, self.total_distance,
                bearing, inside_geofence
            )
            
            print()
            
        except (ValueError, IndexError) as e:
            print(f"❌ Enhanced GGA parsing error: {e}")
    
    def parse_rmc_enhanced(self, sentence, address):
        """Enhanced RMC parsing with speed alerts"""
        parts = sentence.split(',')
        if len(parts) < 12:
            return
            
        try:
            status = parts[2]
            lat_raw = parts[3]
            lat_dir = parts[4]
            lon_raw = parts[5]
            lon_dir = parts[6]
            speed_knots = float(parts[7]) if parts[7] else 0.0
            course = float(parts[8]) if parts[8] else 0.0
            
            if status != 'A' or not lat_raw or not lon_raw:
                return
            
            lat_decimal = self.nmea_to_decimal(lat_raw, lat_dir)
            lon_decimal = self.nmea_to_decimal(lon_raw, lon_dir)
            speed_ms = speed_knots * 0.514444
            speed_kmh = speed_ms * 3.6
            
            if lat_decimal is None or lon_decimal is None:
                return
            
            # Update speed statistics
            self.speeds.append(speed_ms)
            if speed_ms > self.max_speed:
                self.max_speed = speed_ms
            
            if len(self.speeds) > 50:  # Keep last 50 speeds
                self.speeds.pop(0)
            
            self.avg_speed = sum(self.speeds) / len(self.speeds) if self.speeds else 0
            
            # Speed alert
            if speed_ms > self.max_speed_alert:
                print(f"🚨 SPEED ALERT: {speed_ms:.1f} m/s ({speed_kmh:.1f} km/h)")
            
            # Movement tracking
            distance_moved = 0.0
            if self.last_location:
                distance_moved = self.haversine_distance(
                    self.last_location[0], self.last_location[1],
                    lat_decimal, lon_decimal
                )
                self.total_distance += distance_moved
            
            self.last_location = (lat_decimal, lon_decimal, time.time())
            
            # Store for mapping
            self.locations.append({
                'lat': lat_decimal,
                'lon': lon_decimal,
                'speed': speed_ms,
                'course': course,
                'time': datetime.now()
            })
            
            # Geofence check
            inside_geofence = self.check_geofence(lat_decimal, lon_decimal)
            
            # Display enhanced RMC update
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"🛰️  GPS Update [{timestamp}] - RMC Data")
            print(f"   📍 {lat_decimal:.6f}, {lon_decimal:.6f}")
            print(f"   🏃 Speed: {speed_ms:.1f} m/s ({speed_kmh:.1f} km/h)")
            print(f"   🧭 Course: {course:.0f}° | 🚶 Moved: {distance_moved:.1f}m")
            
            # Log enhanced RMC data
            self.log_enhanced_data(
                timestamp, datetime.now().isoformat(), lat_decimal, lon_decimal,
                0.0, speed_ms, speed_kmh, 0, 0.0, 1,
                distance_moved, self.total_distance, course, inside_geofence
            )
            
            print()
            
        except (ValueError, IndexError) as e:
            print(f"❌ Enhanced RMC parsing error: {e}")
    
    def log_enhanced_data(self, timestamp, datetime_iso, lat, lon, alt, speed_ms, 
                         speed_kmh, sats, hdop, quality, dist_moved, total_dist, 
                         bearing, inside_geofence):
        """Log enhanced GPS data"""
        try:
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, datetime_iso, lat, lon, alt, 
                    f"{speed_ms:.2f}", f"{speed_kmh:.2f}", sats, f"{hdop:.2f}", 
                    quality, f"{dist_moved:.2f}", f"{total_dist:.2f}", 
                    f"{bearing:.1f}", inside_geofence
                ])
        except Exception as e:
            print(f"⚠️  Enhanced logging error: {e}")
    
    def update_realtime_map(self):
        """Update real-time HTML map"""
        if not ENHANCED_FEATURES or not self.locations:
            return
        
        try:
            # Create map centered on latest location
            latest = self.locations[-1]
            map_center = [latest['lat'], latest['lon']]
            
            # Create folium map
            gps_map = folium.Map(location=map_center, zoom_start=16)
            
            # Add all GPS points
            for i, loc in enumerate(self.locations[-50:]):  # Last 50 points
                color = 'red' if i == len(self.locations[-50:])-1 else 'blue'
                folium.CircleMarker(
                    [loc['lat'], loc['lon']],
                    radius=3,
                    popup=f"Point {i}: {loc['time'].strftime('%H:%M:%S')}",
                    color=color,
                    fill=True
                ).add_to(gps_map)
            
            # Add GPS track line
            if len(self.locations) > 1:
                track_points = [[loc['lat'], loc['lon']] for loc in self.locations[-50:]]
                folium.PolyLine(track_points, color="blue", weight=2).add_to(gps_map)
            
            # Add geofence if set
            if self.geofence_center:
                folium.Circle(
                    [self.geofence_center[0], self.geofence_center[1]],
                    radius=self.geofence_radius,
                    popup="Geofence",
                    color="red",
                    fill=False
                ).add_to(gps_map)
            
            # Save map
            gps_map.save('realtime_gps_map.html')
            
        except Exception as e:
            print(f"⚠️  Map update error: {e}")
    
    def start_web_dashboard(self):
        """Start simple web dashboard"""
        def run_server():
            try:
                os.chdir(os.path.dirname(os.path.abspath(__file__)))
                server = HTTPServer(('localhost', 8080), SimpleHTTPRequestHandler)
                print("🌐 Web dashboard: http://localhost:8080/realtime_gps_map.html")
                server.serve_forever()
            except:
                pass
        
        dashboard_thread = threading.Thread(target=run_server, daemon=True)
        dashboard_thread.start()
    
    def print_statistics(self):
        """Print GPS session statistics"""
        print("\n📊 GPS SESSION STATISTICS")
        print("=" * 40)
        runtime = time.time() - self.start_time
        print(f"⏱️  Runtime: {runtime/60:.1f} minutes")
        print(f"📡 Messages received: {self.message_count}")
        print(f"📍 GPS points logged: {len(self.locations)}")
        print(f"🚶 Total distance: {self.total_distance:.1f}m")
        
        if self.speeds:
            print(f"⚡ Max speed: {self.max_speed:.1f} m/s ({self.max_speed*3.6:.1f} km/h)")
            print(f"📈 Avg speed: {self.avg_speed:.1f} m/s ({self.avg_speed*3.6:.1f} km/h)")
        
        if self.gps_quality_history:
            avg_sats = sum(q['satellites'] for q in self.gps_quality_history) / len(self.gps_quality_history)
            avg_hdop = sum(q['hdop'] for q in self.gps_quality_history) / len(self.gps_quality_history)
            print(f"🛰️  Avg satellites: {avg_sats:.1f}")
            print(f"🎯 Avg HDOP: {avg_hdop:.1f}")
        
        print("=" * 40)
    
    def save_final_report(self):
        """Save final session report"""
        if not ENHANCED_FEATURES:
            return
            
        try:
            report = {
                'session_start': datetime.fromtimestamp(self.start_time).isoformat(),
                'session_end': datetime.now().isoformat(),
                'runtime_minutes': (time.time() - self.start_time) / 60,
                'messages_received': self.message_count,
                'gps_points': len(self.locations),
                'total_distance_m': self.total_distance,
                'max_speed_ms': self.max_speed,
                'avg_speed_ms': self.avg_speed,
                'geofence_violations': sum(1 for loc in self.locations if not self.check_geofence(loc['lat'], loc['lon'])) if self.geofence_center else 0
            }
            
            with open('gps_session_report.json', 'w') as f:
                json.dump(report, f, indent=2)
                
            print(f"📄 Session report saved: gps_session_report.json")
            
        except Exception as e:
            print(f"⚠️  Report save error: {e}")
    
    # Include all the helper methods from the basic version
    def validate_nmea_checksum(self, sentence):
        try:
            if '*' not in sentence:
                return False
            content, checksum = sentence.split('*')
            content = content[1:]
            calc_checksum = 0
            for char in content:
                calc_checksum ^= ord(char)
            return f"{calc_checksum:02X}" == checksum.upper()
        except:
            return False
    
    def nmea_to_decimal(self, coord_str, direction):
        try:
            if not coord_str or '.' not in coord_str:
                return None
            dot_pos = coord_str.find('.')
            if len(coord_str) < 4:
                return None
            if dot_pos >= 4:
                degrees = int(coord_str[:dot_pos-2])
                minutes = float(coord_str[dot_pos-2:])
            else:
                degrees = int(coord_str[:dot_pos-2])
                minutes = float(coord_str[dot_pos-2:])
            decimal = degrees + minutes / 60.0
            if direction in ['S', 'W']:
                decimal = -decimal
            return decimal
        except (ValueError, IndexError):
            return None
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371000
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

def main():
    print("🛰️  Enhanced ESP32 GPS Data Receiver")
    print("=" * 50)
    
    receiver = EnhancedGPSReceiver(port=11123)
    
    # Example: Set geofence around current area (uncomment to use)
    # receiver.set_geofence(37.4219999, -122.0840575, 50)  # 50m radius
    
    try:
        receiver.start_listening()
    except KeyboardInterrupt:
        print("\n🛑 Enhanced GPS receiver stopped")

if __name__ == "__main__":
    main()
