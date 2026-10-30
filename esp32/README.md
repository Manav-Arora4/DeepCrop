# ESP32 IoT Agricultural Sensor Node

## Hardware Bill of Materials (BOM)
1. **Microcontroller**: ESP32-S3 DevKit (ESP32-S3-WROOM-1 **N16R8**, 16MB flash + 8MB octal PSRAM)
2. **Atmospheric Sensor**: DHT22 / AM2302 module (Temperature & Relative Humidity)
3. **Soil Moisture Sensor**: Soil Moisture Hygrometer Module (resistive fork probe + LM393 comparator board)
4. **Soil pH Sensor**: ELECROW Crowtail pH Sensor (analog output)
5. **Prototyping**: MB102 830-point breadboard, M-M / M-F / F-F jumper wires, 1/4W metal-film resistor kit
6. **Power / programming**: data-capable USB-C cable (laptop USB or a 5V USB adapter)

No pH buffer solutions are used, so pH readings are uncalibrated and relative only (see [Calibration](#calibration)).

## Wiring Pinout
| Sensor | Sensor Pin | ESP32-S3 Pin | Description |
|---|---|---|---|
| **DHT22** | DATA / OUT | GPIO 4 | Digital. Bare 4-pin sensors need a 10kΩ pull-up to 3.3V; 3-pin modules usually have one on board |
| **DHT22** | VCC / + | 3V3 | Power |
| **DHT22** | GND / − | GND | Ground |
| **Soil Moisture** | AO | GPIO 1 (ADC1_CH0) | Analog voltage. Leave DO unconnected |
| **Soil Moisture** | VCC | 3V3 | Power |
| **Soil Moisture** | GND | GND | Ground |
| **Soil pH** | SIG / AO | GPIO 2 (ADC1_CH1) | Analog pH voltage (see voltage warning below) |
| **Soil pH** | VCC | 3V3 or 5V | Power (see below) |
| **Soil pH** | GND | GND | Ground |

### Why these pins
- Analog sensors must use **ADC1 (GPIO 1–10)**. ADC2 cannot be read while Wi-Fi is active.
- On N16R8 modules, **GPIO 35–37** are used by the octal PSRAM and must not be wired.
- Avoid strapping pins **0, 3, 45, 46**, USB pins **19, 20**, and UART0 pins **43, 44**.

### pH sensor voltage warning
ESP32-S3 ADC inputs accept **at most 3.3V**, and readings are only accurate up to about 3.1V.

1. Power the pH board from **3V3** if it works at that voltage. Then no divider is needed (`PH_DIVIDER_RATIO 1.0`).
2. If it must run from **5V**, measure its output with a multimeter while the probe is in vinegar. Acidic liquids give the highest voltage on most boards. If the output can exceed ~3.0V, add a divider from the resistor kit:

```text
pH AO ──[ 10kΩ ]──┬── GPIO 2
                  │
               [ 20kΩ ]
                  │
                 GND
```

   Then set `PH_DIVIDER_RATIO 1.5` in `config.h`, since (10k + 20k) / 20k = 1.5.

### Soil moisture sensor limitations
The resistive fork probe passes DC current through the soil, so it **corrodes and drifts** with continuous use.
- Readings depend on soil salinity and fertilizer, not only on water content.
- Recalibrate it regularly, and record its condition with each data-collection session.
- If long-term readings drift, swap in a capacitive v1.2 sensor (same AO wiring). Otherwise, report the drift as a limitation of the dataset.

## Calibration
Calibration constants live in `config.h`. Set `CALIBRATION_MODE true`, flash, and open the Serial Monitor at 115200 baud. The node then prints raw millivolt readings every second, without Wi-Fi.

**Soil moisture**
1. Hold the probe in dry air and note the moisture mV → `MOISTURE_DRY_MV`.
2. Put the probe in a glass of water up to the line and note the mV → `MOISTURE_WET_MV`.

**pH: uncalibrated, relative readings only**

This project does not use pH buffer solutions. The goal is to see that pH *differs* between plants or over time, not to correct soil pH. So:
- `PH7_MV` / `PH4_MV` keep their placeholder values. The pH number the node sends is a **relative index on an approximate pH scale, not a measured pH**.
- Readings can be compared with each other only when taken with the same probe, the same settings and similar temperature. A higher or lower value shows a direction of change, not an exact amount.
- **Record the raw pH millivolts** next to each observation. The node prints them on the Serial Monitor every reading, e.g. `pH: 6.12 (1580 mV)`. The mV value is the honest measurement and can be converted later if buffers ever become available.
- **In the report and on the dashboard,** call these values "uncalibrated pH (relative)". Do not compare them to agronomic pH thresholds as if they were absolute. Mention the lack of calibration as a limitation.
- Optional sanity check: rinse the probe and dip it in tap water, then in vinegar. The vinegar reading should move clearly toward acidic. That confirms the probe responds, but it is not a calibration.

Set `CALIBRATION_MODE false` and reflash for normal operation.

> Moisture values in `config.h.example` are placeholders until you do the dry/wet steps above. Treat both probes as prototype hardware, not laboratory instruments.

## Flashing Instructions
1. Install **esp32 by Espressif Systems** (v3.x) in the Arduino IDE Boards Manager.
2. Open `esp32/firmware/tomato_node/` in the Arduino IDE.
3. Copy `config.h.example` to `config.h`, then set your Wi-Fi SSID and the backend IP address. `config.h` is git-ignored, so credentials stay local.
4. Install these libraries with the Arduino Library Manager:
   - `DHT sensor library` by Adafruit
   - `Adafruit Unified Sensor`
   - `ArduinoJson` (**v7.x**)
5. In the **Tools** menu, select:
   - Board: **ESP32S3 Dev Module**
   - Flash Size: **16MB (128Mb)**
   - PSRAM: **OPI PSRAM**
   - USB CDC On Boot: **Enabled** (needed for Serial output over the native USB port)
6. Connect the USB-C port labelled **USB** or **COM**, select its port, and upload. If upload fails, hold **BOOT**, tap **RST**, then release **BOOT** and retry.
