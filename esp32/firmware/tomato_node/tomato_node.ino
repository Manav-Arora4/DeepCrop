/*
  =============================================================================
  AgriHealth AI — ESP32-S3 Precision Agricultural Sensor Node
  Firmware for Tomato Environmental Monitoring

  Board:
  - ESP32-S3 DevKit (ESP32-S3-WROOM-1 N16R8, 16MB flash + 8MB octal PSRAM)

  Sensors:
  - DHT22 / AM2302 (Air Temperature & Atmospheric Humidity)
  - Soil Moisture Hygrometer Module (resistive probe + LM393 board, AO pin)
  - ELECROW Crowtail pH Sensor (Analog)

  Protocol:
  - HTTP REST POST to /sensors/reading with JSON payload

  Pin notes (ESP32-S3):
  - Analog sensors must use ADC1 (GPIO 1-10); ADC2 is unusable while Wi-Fi is on.
  - GPIO 35-37 are taken by the octal PSRAM on N16R8 modules.
  - Avoid strapping pins 0, 3, 45, 46 and USB pins 19, 20.
  =============================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include "config.h"

#define DHTPIN 4               // Digital
#define DHTTYPE DHT22
#define SOIL_MOISTURE_PIN 1    // ADC1_CH0
#define PH_PIN 2               // ADC1_CH1

#define ADC_SAMPLES 20

DHT dht(DHTPIN, DHTTYPE);

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[WiFi] Connecting to network");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n[AgriHealth Node] Starting ESP32-S3 Sensor Node...");
  dht.begin();

  // 11dB attenuation gives roughly a 0-3.1V input range on the S3
  analogSetPinAttenuation(SOIL_MOISTURE_PIN, ADC_11db);
  analogSetPinAttenuation(PH_PIN, ADC_11db);

  if (!CALIBRATION_MODE) {
    connectWiFi();
  }
}

// Averaged, factory-calibrated ADC reading in millivolts
float readMillivolts(int pin) {
  uint32_t total = 0;
  for (int i = 0; i < ADC_SAMPLES; i++) {
    total += analogReadMilliVolts(pin);
    delay(5);
  }
  return (float)total / ADC_SAMPLES;
}

float readSoilMoisture(float mv) {
  // Two-point linear calibration between dry air and water readings
  float moisture = (mv - MOISTURE_DRY_MV) * 100.0 / (MOISTURE_WET_MV - MOISTURE_DRY_MV);
  return constrain(moisture, 0.0, 100.0);
}

float readPH(float mv) {
  // Undo the optional voltage divider, then apply two-point buffer calibration
  float probeMv = mv * PH_DIVIDER_RATIO;
  float slope = (7.0 - 4.0) / (PH7_MV - PH4_MV);
  float ph = 7.0 + (probeMv - PH7_MV) * slope;
  return constrain(ph, 0.0, 14.0);
}

void loop() {
  float moistureMv = readMillivolts(SOIL_MOISTURE_PIN);
  float phMv = readMillivolts(PH_PIN);

  // Calibration mode: print raw voltages only, no Wi-Fi or uploads
  if (CALIBRATION_MODE) {
    Serial.printf("[Calibrate] Moisture AO: %.0f mV | pH AO: %.0f mV (probe side: %.0f mV)\n",
                  moistureMv, phMv, phMv * PH_DIVIDER_RATIO);
    delay(1000);
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Connection lost, reconnecting...");
    connectWiFi();
  }

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  float moisture = readSoilMoisture(moistureMv);
  float ph = readPH(phMv);

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("[DHT22] Warning: Failed to read from sensor, sending soil data only.");
  }

  Serial.printf("[Sensors] Moisture: %.1f%% (%.0f mV) | pH: %.2f (%.0f mV) | Temp: %.1f C | Hum: %.1f%%\n",
                moisture, moistureMv, ph, phMv, temperature, humidity);

  HTTPClient http;
  String endpoint = String(API_BASE_URL) + "/sensors/reading";
  http.begin(endpoint);
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["crop_id"] = CROP_ID;
  doc["plant_id"] = PLANT_ID;
  doc["moisture"] = moisture;
  doc["ph"] = ph;
  // Backend accepts null; never send fabricated values for a failed read
  if (isnan(temperature)) doc["temperature"] = nullptr; else doc["temperature"] = temperature;
  if (isnan(humidity)) doc["humidity"] = nullptr; else doc["humidity"] = humidity;
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

  delay(TRANSMIT_INTERVAL_MS);
}
