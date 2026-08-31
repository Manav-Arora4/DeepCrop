# ESP32 IoT Agricultural Sensor Node

## Hardware Bill of Materials (BOM)
1. **Microcontroller**: ESP32 Development Board (NodeMCU-32S / ESP32-WROOM-32)
2. **Atmospheric Sensor**: DHT22 / AM2302 (Temperature & Relative Humidity)
3. **Soil Moisture Sensor**: Capacitive Soil Moisture Sensor v1.2 (Corrosion-resistant analog)
4. **Soil pH Sensor**: Analog Industrial pH Probe with BNC to 3-pin adapter
5. **Power**: 5V/2A Micro-USB power supply or 18650 Li-ion battery shield with solar charging

## Wiring Pinout
| Sensor | Sensor Pin | ESP32 GPIO | Description |
|---|---|---|---|
| **DHT22** | DATA | GPIO 4 | 10kΩ pull-up resistor to 3.3V |
| **DHT22** | VCC | 3.3V | Power |
| **DHT22** | GND | GND | Ground |
| **Soil Moisture** | AOUT | GPIO 34 (ADC1_CH6) | Analog voltage |
| **Soil Moisture** | VCC | 3.3V | Power |
| **Soil Moisture** | GND | GND | Ground |
| **Soil pH** | AOUT | GPIO 35 (ADC1_CH7) | Analog pH voltage |
| **Soil pH** | VCC | 5.0V / 3.3V | Power |
| **Soil pH** | GND | GND | Ground |

## Flashing Instructions
1. Open `esp32/firmware/tomato_node/` in Arduino IDE or PlatformIO.
2. Copy `config.h.example` to `config.h` and configure your Wi-Fi SSID and backend IP address.
3. Install dependencies via Arduino Library Manager:
   - `DHT sensor library` by Adafruit
   - `Adafruit Unified Sensor`
   - `ArduinoJson` (v6.x)
4. Select Board: **ESP32 Dev Module**, upload speed **921600**, and flash over USB.
