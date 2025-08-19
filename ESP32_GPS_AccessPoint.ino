/*
 * ESP32 WiFi Access Point for GPS Streaming
 * 
 * This sketch creates a WiFi Access Point that allows phones to connect
 * and stream GPS data to a Python script running on a laptop.
 * 
 * Network Configuration:
 * - SSID: ESP32-AccessPoint
 * - Password: esp32password
 * - ESP32 IP: 192.168.4.1
 * - Laptop IP: 192.168.4.2 (auto-assigned)
 * - GPS UDP Port: 11123
 * 
 * Hardware: ESP32 Dev Board (any variant)
 * 
 * Setup Instructions:
 * 1. Upload this sketch to ESP32
 * 2. Open Serial Monitor (115200 baud)
 * 3. Connect phone to "ESP32-AccessPoint" WiFi
 * 4. Run Python GPS receiver script on laptop
 * 5. Use GPS2IP or Share GPS app to stream to 192.168.4.2:11123
 */

#include <WiFi.h>

// Access Point credentials
const char* ap_ssid = "ESP32-AccessPoint";
const char* ap_password = "esp32password";

// Network configuration
IPAddress local_ip(192, 168, 4, 1);    // ESP32 IP
IPAddress gateway(192, 168, 4, 1);     // Gateway IP  
IPAddress subnet(255, 255, 255, 0);    // Subnet mask

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n🚁 ESP32 GPS Access Point Starting...");
  Serial.println("=====================================");
  
  // Configure and start Access Point
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(local_ip, gateway, subnet);
  
  bool ap_started = WiFi.softAP(ap_ssid, ap_password);
  
  if (ap_started) {
    Serial.println("✅ WiFi Access Point Started Successfully!");
    Serial.println("\n📡 Network Information:");
    Serial.printf("   SSID: %s\n", ap_ssid);
    Serial.printf("   Password: %s\n", ap_password);
    Serial.printf("   ESP32 IP: %s\n", WiFi.softAPIP().toString().c_str());
    Serial.printf("   Gateway: %s\n", gateway.toString().c_str());
    Serial.printf("   Subnet: %s\n", subnet.toString().c_str());
    Serial.println("\n📱 Phone Setup Instructions:");
    Serial.printf("   1. Connect phone to WiFi: %s\n", ap_ssid);
    Serial.printf("   2. Install GPS2IP (iPhone) or Share GPS (Android)\n");
    Serial.printf("   3. Stream GPS to IP: 192.168.4.2 Port: 11123\n");
    Serial.printf("   4. Run Python GPS receiver on laptop\n");
    Serial.println("\n💻 Laptop will auto-receive IP: 192.168.4.2");
    Serial.println("=====================================");
  } else {
    Serial.println("❌ Failed to start Access Point!");
    Serial.println("   Check ESP32 power and reset");
  }
}

void loop() {
  // Check connected devices every 30 seconds
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 30000) {
    lastCheck = millis();
    
    int clients = WiFi.softAPgetStationNum();
    Serial.printf("📊 Connected devices: %d\n", clients);
    
    if (clients > 0) {
      Serial.println("   ✅ Device(s) connected to access point");
      Serial.println("   📡 Ready to receive GPS data");
    } else {
      Serial.println("   ⏳ Waiting for devices to connect...");
    }
  }
  
  // Keep the ESP32 responsive
  delay(1000);
}
