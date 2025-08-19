#!/usr/bin/env python3
"""
GPS Data Receiver for ESP32 Access Point System

This script receives GPS data streamed from a phone via UDP and processes NMEA sentences.
Works with GPS2IP (iPhone) or Share GPS (Android) apps.

Network Setup:
- Connect phone to ESP32-AccessPoint WiFi (password: esp32password)  
- Phone streams GPS to laptop IP 192.168.4.2 on port 11123
- Script listens for NMEA sentences and parses GPS coordinates

Usage:
    python gps_receiver.py

Features:
- Real-time GPS coordinate parsing
- NMEA sentence validation
- Distance calculation between GPS points
- CSV logging with timestamps
- Connection status monitoring
"""

import socket
import time
import csv
import os
import math
from datetime import datetime
import re

class GPSReceiver:
    def __init__(self, port=11123, log_file="gps_log.csv"):
        self.port = port
        self.log_file = log_file
        self.sock = None
        self.last_location = None
        self.total_distance = 0.0
        self.start_time = time.time()
        self.message_count = 0
        
        # Initialize CSV log file
        self.init_log_file()
        
    def init_log_file(self):
        """Initialize CSV log file with headers"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Latitude', 'Longitude', 
                    'Altitude', 'Speed', 'Satellites', 'HDOP',
                    'Distance_Moved', 'Total_Distance'
                ])
            print(f"📝 Created GPS log file: {self.log_file}")
    
    def start_listening(self):
        """Start UDP server to receive GPS data"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to laptop IP when connected to ESP32 access point
            server_address = ('192.168.4.2', self.port)
            self.sock.bind(server_address)
            self.sock.settimeout(1.0)  # 1 second timeout for non-blocking
            
            print("🌐 GPS Receiver Started")
            print("=" * 50)
            print(f"📡 Listening on: {server_address[0]}:{server_address[1]}")
            print("📱 Make sure your phone is:")
            print("   • Connected to ESP32-AccessPoint WiFi")
            print("   • Running GPS2IP or Share GPS app")
            print(f"   • Streaming to {server_address[0]}:{server_address[1]}")
            print("=" * 50)
            print("🔍 Waiting for GPS data...\n")
            
            no_data_time = time.time()
            
            while True:
                try:
                    data, address = self.sock.recvfrom(1024)
                    self.message_count += 1
                    no_data_time = time.time()  # Reset no-data timer
                    
                    # Decode and process the message
                    message = data.decode('utf-8', errors='ignore').strip()
                    
                    if message.startswith('$'):
                        self.process_nmea_sentence(message, address)
                    else:
                        print(f"📡 Non-NMEA data from {address}: {message[:50]}...")
                        
                except socket.timeout:
                    # Check for no-data timeout (30 seconds)
                    if time.time() - no_data_time > 30:
                        print(f"⏰ No GPS data received for 30 seconds...")
                        print("   Check phone connection and GPS app settings")
                        no_data_time = time.time()  # Reset to avoid spam
                    continue
                    
        except Exception as e:
            print(f"❌ Server error: {e}")
        finally:
            if self.sock:
                self.sock.close()
    
    def process_nmea_sentence(self, sentence, address):
        """Process NMEA GPS sentence"""
        try:
            # Validate NMEA checksum
            if not self.validate_nmea_checksum(sentence):
                print(f"⚠️  Invalid NMEA checksum: {sentence[:20]}...")
                return
            
            # Parse different NMEA sentence types
            if sentence.startswith('$GPGGA') or sentence.startswith('$GNGGA'):
                self.parse_gga_sentence(sentence, address)
            elif sentence.startswith('$GPRMC') or sentence.startswith('$GNRMC'):
                self.parse_rmc_sentence(sentence, address)
            else:
                # Other NMEA sentences (less common)
                print(f"📡 NMEA: {sentence[:30]}... from {address[0]}")
                
        except Exception as e:
            print(f"❌ Error processing NMEA: {e}")
            print(f"   Sentence: {sentence[:50]}...")
    
    def validate_nmea_checksum(self, sentence):
        """Validate NMEA sentence checksum"""
        try:
            if '*' not in sentence:
                return False
                
            content, checksum = sentence.split('*')
            content = content[1:]  # Remove $ prefix
            
            # Calculate checksum
            calc_checksum = 0
            for char in content:
                calc_checksum ^= ord(char)
            
            return f"{calc_checksum:02X}" == checksum.upper()
        except:
            return False
    
    def parse_gga_sentence(self, sentence, address):
        """Parse GPGGA sentence (GPS Fix Data)"""
        parts = sentence.split(',')
        
        if len(parts) < 15:
            return
        
        try:
            # Extract data
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
                print(f"📡 No GPS fix from {address[0]} (satellites: {satellites})")
                return
            
            # Convert to decimal degrees
            lat_decimal = self.nmea_to_decimal(lat_raw, lat_dir)
            lon_decimal = self.nmea_to_decimal(lon_raw, lon_dir)
            
            if lat_decimal is None or lon_decimal is None:
                return
            
            # Calculate movement distance
            distance_moved = 0.0
            if self.last_location:
                distance_moved = self.haversine_distance(
                    self.last_location[0], self.last_location[1],
                    lat_decimal, lon_decimal
                )
                self.total_distance += distance_moved
            
            self.last_location = (lat_decimal, lon_decimal)
            
            # Display update
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"🛰️  GPS Update [{timestamp}] from {address[0]}")
            print(f"   📍 Location: {lat_decimal:.6f}, {lon_decimal:.6f}")
            print(f"   🗻 Altitude: {altitude:.1f}m")
            print(f"   📡 Satellites: {satellites}, HDOP: {hdop:.1f}")
            
            if distance_moved > 0:
                print(f"   🚶 Moved: {distance_moved:.1f}m, Total: {self.total_distance:.1f}m")
            
            # Log to CSV
            self.log_gps_data(timestamp, lat_decimal, lon_decimal, altitude, 
                            0.0, satellites, hdop, distance_moved, self.total_distance)
            
            print()  # Empty line for readability
            
        except (ValueError, IndexError) as e:
            print(f"❌ Error parsing GGA: {e}")
    
    def parse_rmc_sentence(self, sentence, address):
        """Parse GPRMC sentence (Recommended Minimum)"""
        parts = sentence.split(',')
        
        if len(parts) < 12:
            return
            
        try:
            # Extract data
            utc_time = parts[1]
            status = parts[2]
            lat_raw = parts[3]
            lat_dir = parts[4] 
            lon_raw = parts[5]
            lon_dir = parts[6]
            speed_knots = float(parts[7]) if parts[7] else 0.0
            
            if status != 'A' or not lat_raw or not lon_raw:
                print(f"📡 No GPS fix in RMC from {address[0]}")
                return
            
            # Convert to decimal degrees and speed
            lat_decimal = self.nmea_to_decimal(lat_raw, lat_dir)
            lon_decimal = self.nmea_to_decimal(lon_raw, lon_dir)
            speed_ms = speed_knots * 0.514444  # knots to m/s
            
            if lat_decimal is None or lon_decimal is None:
                return
            
            # Calculate movement
            distance_moved = 0.0
            if self.last_location:
                distance_moved = self.haversine_distance(
                    self.last_location[0], self.last_location[1], 
                    lat_decimal, lon_decimal
                )
                self.total_distance += distance_moved
            
            self.last_location = (lat_decimal, lon_decimal)
            
            # Display update
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"🛰️  GPS Update [{timestamp}] from {address[0]}")
            print(f"   📍 Location: {lat_decimal:.6f}, {lon_decimal:.6f}")
            print(f"   🏃 Speed: {speed_ms:.1f} m/s ({speed_knots:.1f} knots)")
            
            if distance_moved > 0:
                print(f"   🚶 Moved: {distance_moved:.1f}m, Total: {self.total_distance:.1f}m")
            
            # Log to CSV
            self.log_gps_data(timestamp, lat_decimal, lon_decimal, 0.0,
                            speed_ms, 0, 0.0, distance_moved, self.total_distance)
            
            print()
            
        except (ValueError, IndexError) as e:
            print(f"❌ Error parsing RMC: {e}")
    
    def nmea_to_decimal(self, coord_str, direction):
        """Convert NMEA coordinate to decimal degrees"""
        try:
            if not coord_str:
                return None
                
            # NMEA format: DDMM.MMMM (latitude) or DDDMM.MMMM (longitude)
            if '.' not in coord_str:
                return None
            
            dot_pos = coord_str.find('.')
            
            if len(coord_str) < 4:
                return None
            
            # Extract degrees and minutes
            if dot_pos >= 4:  # Longitude (DDDMM.MMMM)
                degrees = int(coord_str[:dot_pos-2])
                minutes = float(coord_str[dot_pos-2:])
            else:  # Latitude (DDMM.MMMM)
                degrees = int(coord_str[:dot_pos-2])
                minutes = float(coord_str[dot_pos-2:])
            
            # Convert to decimal
            decimal = degrees + minutes / 60.0
            
            # Apply direction
            if direction in ['S', 'W']:
                decimal = -decimal
                
            return decimal
            
        except (ValueError, IndexError):
            return None
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS points using Haversine formula"""
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        return distance
    
    def log_gps_data(self, timestamp, lat, lon, alt, speed, sats, hdop, dist_moved, total_dist):
        """Log GPS data to CSV file"""
        try:
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, lat, lon, alt, speed, sats, hdop,
                    f"{dist_moved:.1f}", f"{total_dist:.1f}"
                ])
        except Exception as e:
            print(f"⚠️  Logging error: {e}")

def main():
    """Main function"""
    print("🛰️  ESP32 GPS Data Receiver")
    print("=" * 50)
    print("📱 Phone Setup Instructions:")
    print("   1. Connect to ESP32-AccessPoint WiFi")
    print("   2. Install GPS2IP (iPhone) or Share GPS (Android)")
    print("   3. Configure app to stream to:")
    print("      • IP: 192.168.4.2")
    print("      • Port: 11123")
    print("      • Protocol: UDP")
    print("   4. Enable location permissions")
    print("   5. Start GPS streaming in app")
    print()
    
    try:
        receiver = GPSReceiver(port=11123, log_file="gps_tracking.csv")
        receiver.start_listening()
    except KeyboardInterrupt:
        print("\n🛑 GPS receiver stopped by user")
    except Exception as e:
        print(f"❌ GPS receiver error: {e}")

if __name__ == "__main__":
    main()
