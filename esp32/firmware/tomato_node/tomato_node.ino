/*
  =============================================================================
  AgriHealth AI — ESP32 Precision Agricultural Sensor Node
  Firmware for Tomato Environmental Monitoring
  
  Sensors:
  - DHT22 (Air Temperature & Atmospheric Humidity)
  - Capacitive Soil Moisture Sensor v1.2 (Analog)
  - Analog Soil pH Sensor Probe (DFRobot pH meter compatible)
  
  Protocol:
  - HTTP REST POST to /sensors/reading with JSON payload
  =============================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include "config.h"

#define DHTPIN 4
#define DHTTYPE DHT22
#define SOIL_MOISTURE_PIN 34
#define PH_PIN 35

DHT dht(DHTPIN, DHTTYPE);

// Calibration constants
const int AIR_VALUE = 3200;    // Dry sensor reading in air
const int WATER_VALUE = 1400;  // Submerged sensor reading in water

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n[AgriHealth Node] Starting ESP32 Sensor Node...");
  dht.begin();

  // Connect to Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[WiFi] Connecting to network");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
}

float readSoilMoisture() {
  int raw = analogRead(SOIL_MOISTURE_PIN);
  float moisture = map(raw, AIR_VALUE, WATER_VALUE, 0, 100);
  return constrain(moisture, 0.0, 100.0);
}

float readPH() {
  int raw = analogRead(PH_PIN);
  float voltage = raw * (3.3 / 4095.0);
  // Linear calibration: pH = 7.0 + ((2.5 - voltage) / 0.18)
  float ph = 7.0 + ((1.65 - voltage) * 3.5);
  return constrain(ph, 0.0, 14.0);
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();
    float moisture = readSoilMoisture();
    float ph = readPH();

    if (isnan(humidity) || isnan(temperature)) {
      Serial.println("[DHT22] Warning: Failed to read from sensor.");
    } else {
      Serial.printf("[Sensors] Moisture: %.1f%% | pH: %.2f | Temp: %.1f C | Hum: %.1f%%\n",
                    moisture, ph, temperature, humidity);

      HTTPClient http;
      String endpoint = String(API_BASE_URL) + "/sensors/reading";
      http.begin(endpoint);
      http.addHeader("Content-Type", "application/json");

      StaticJsonDocument<256> doc;
      doc["device_id"] = DEVICE_ID;
      doc["crop_id"] = CROP_ID;
      doc["plant_id"] = PLANT_ID;
      doc["moisture"] = moisture;
      doc["ph"] = ph;
      doc["temperature"] = temperature;
      doc["humidity"] = humidity;
      doc["data_source"] = "real";

      String requestBody;
      serializeJson(doc, requestBody);

      int httpResponseCode = http.POST(requestBody);
      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.printf("[HTTP POST] Success (%d): %s\n", httpResponseCode, response.c_str());
      } else {
        Serial.printf("[HTTP POST] Error code: %d\n", httpResponseCode);
      }
      http.end();
    }
  }

  delay(TRANSMIT_INTERVAL_MS);
}
