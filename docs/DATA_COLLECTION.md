# Field Data Collection Format

How to record real tomato observations for the multimodal experiments (Phase 5 → Phase 6).

Each **observation** is one plant at one moment, with:
- a photo of the plant, and
- the sensor readings taken at the same time.

The photo and the readings must belong to the **same plant within 15 minutes of each other**. Pairing them is the whole point of the dataset.

## Folder layout

```text
data/user_collected/tomato/
├── observations.csv
└── images/
    ├── tomato_001/
    │   ├── tomato_001_20261118-0930.jpg
    │   └── tomato_001_20261120-0915.jpg
    └── tomato_002/
        └── tomato_002_20261118-0940.jpg
```

- Give each plant a permanent ID: `tomato_001`, `tomato_002`, … Put a tag on the pot so it never changes.
- Name each photo `<plant_id>_<YYYYMMDD-HHMM>.jpg`, using the time the photo was taken.

## `observations.csv`: columns you fill in

One row per observation. Required columns are **bold**.

| Column | Example | Allowed values / notes |
|---|---|---|
| **observation_id** | `obs_0001` | Unique; just count up |
| **plant_id** | `tomato_001` | The plant's permanent ID |
| **timestamp** | `2026-11-18T09:30:00+05:30` | When the **photo** was taken, ISO format with time zone |
| **image_file** | `images/tomato_001/tomato_001_20261118-0930.jpg` | Path relative to `data/user_collected/tomato/`; several photos separated by `;` |
| **growth_stage** | `flowering` | `seedling`, `vegetative`, `flowering`, `fruit_development`, `maturity` |
| **sensor_timestamp** | `2026-11-18T09:34:00+05:30` | When the **sensor readings** were taken. Must be within 15 minutes of `timestamp`; this is checked when the data is loaded |
| **soil_moisture_pct** | `38.5` | 0–100, from the sensor |
| **temperature_c** | `29.1` | Air temperature in °C |
| **humidity_pct** | `78` | Relative humidity, 0–100 |
| soil_ph_mv | `1720` | Raw pH voltage in mV from the ESP32 Serial Monitor. Preferred, because the probe is uncalibrated |
| soil_ph | `6.4` | Only if read from a calibrated meter |
| **sensor_source** | `esp32` | Type of instrument: `esp32`, `handheld_meter`, `weather_station`, `other` |
| **sensor_device_id** | `esp32_001` | The specific unit used, e.g. `esp32_001` or `meter_A`. Readings from different units aren't directly comparable |
| **sensor_calibration_status** | `uncalibrated` | `calibrated` (state the date in notes), `factory`, `uncalibrated` |
| **disease_status** | `diseased` | `healthy`, `diseased`, `unsure` |
| **disease_type** | `tomato_early_blight` | Must match `disease_status`, see the rules below |
| **leaf_count_affected** | `3` | Examined leaves with symptoms of the suspected disease (see Severity below) |
| **total_leaf_count** | `24` | Leaves examined (see Severity below). Must be at least `leaf_count_affected` |
| **severity** | `mild` | `none`, `mild`, `moderate`, `severe`. Must match the leaf counts (see below); a mismatch is flagged when the data is loaded for Phase 6 |
| **labelled_by** | `Manav` | Who decided the disease label |
| label_checked_by | `Dr. Rao (agronomy)` | Second opinion, if any. Makes the labels much more credible |
| observation_conditions | `overcast` | Light when photographed: `direct_sun`, `shade`, `overcast`, `indoor`, `artificial` |
| watered_last_24h | `yes` | `yes` / `no` |
| treatment_applied | `copper spray 2026-11-15` | Any fungicide, pesticide or fertiliser, with the date |
| notes | `lower leaves yellowing` | Anything else |

### Disease label rules

`disease_status` and `disease_type` must always agree. **Never leave `disease_type` blank.**

| disease_status | disease_type |
|---|---|
| `healthy` | `tomato_healthy` |
| `diseased` | the specific disease ID below, or `other` if it's a disease outside the list (see the note below) |
| `unsure` | `unknown` |

Disease IDs (the same 10 classes the photo model knows):
`tomato_bacterial_spot`, `tomato_early_blight`, `tomato_late_blight`, `tomato_leaf_mold`, `tomato_septoria_leaf_spot`, `tomato_spider_mites`, `tomato_target_spot`, `tomato_yellow_leaf_curl_virus`, `tomato_mosaic_virus`, `tomato_healthy`

`unsure` rows are kept but left out of training and testing until they're re-labelled.

`other` rows are **left out of the 10-class leaf-photo experiment**, because the model has no class for them and its outputs could never match the label.
- They can still count as `diseased` in a binary healthy-vs-diseased experiment, as long as the report says so.
- They only join the 10-class experiment if the model's classes are explicitly expanded and it is retrained.

### Severity

1. **Count the leaves.**
   - Small plants: count every leaf as `total_leaf_count`.
   - Large plants: examine the **3 lowest branches** (where disease usually starts) and count the leaves on them. The result is **examined-leaf severity**, not whole-plant severity, and the report should call it that.
2. **Count the symptomatic leaves.** Count every examined leaf with symptoms **attributable to the suspected disease** as `leaf_count_affected`.
   - Disease symptoms include spots, lesions, mould, and the mottling or curling of the virus classes.
   - Yellowing or curling that is more likely a nutrient deficiency, water stress or sun scorch is **not** counted. Describe it in `notes` instead.
   - When unsure whether a symptom is disease, count it, and record the doubt in `notes`.
3. **Work out the severity** from `leaf_count_affected / total_leaf_count`. The severity label must follow from the counts:

| Affected share | severity |
|---|---|
| 0% | `none` |
| under 10% | `mild` |
| 10–50% | `moderate` |
| over 50% | `severe` |

Use the same counting method for a plant on every visit.

## Columns calculated later (don't fill these in)

These are computed by a script from **later** observations of the same plant. Nobody should guess them at collection time.

| Column | Meaning |
|---|---|
| `previous_disease_status` | `disease_status` at this plant's previous visit |
| `last_healthy_observation_date` | Date of this plant's last `healthy` observation before its first `diseased` one |
| `first_diseased_observation_date` | Date this plant was first **observed** `diseased` (blank if never). The true biological onset is unknown; it lies somewhere between this date and the previous one |
| `future_disease_3d` | `1`, `0` or blank for the next 3 days, using the rules below |
| `future_disease_7d` | `1`, `0` or blank for the next 7 days, using the rules below |

Rules for `future_disease_Nd`, for an observation at time *t*:

- **`1`:** the plant is observed `diseased` at some visit after *t* and within *N* days of *t*.
- **`0`:** only when follow-up is sufficient. That means all three of these hold:
  - the plant has a visit at or after *t* + *N* days, so the whole window is covered;
  - no two consecutive visits inside the window are more than 3 days apart;
  - every visit in the window is `healthy`.
- **Blank:** anything else, such as missing visits, a gap longer than 3 days, the end of collection, or an `unsure` visit inside the window. Blank rows are excluded from the risk experiment and never counted as negatives.

Never treat a missing future observation as "stayed healthy".

## How the data will be used

The data supports **two separate experiments**, each reported on its own:

1. **Disease detection.** Does the plant have a disease **now**? Photo, sensor readings, or both are used to predict `disease_status` / `disease_type` at the same observation.
2. **Disease risk prediction.** Will a **currently healthy** plant become diseased within 7 days (`future_disease_7d`)?
   - Only observations with `disease_status = healthy` are used.
   - Each prediction uses only information available at that observation's time, never later readings.

Each experiment compares photo-only, sensor-only and photo + sensor models.

**Splitting is done by plant, not by row.**
- Every observation of a plant goes into the same partition (train, validation or test).
- Otherwise the model can learn to recognise individual plants instead of disease, which inflates accuracy.
- With few plants, a 70/15/15 split puts only 1–2 plants in the test set, which is too few to trust. Below about 30 plants, the evaluation uses **grouped cross-validation by plant** instead: each fold holds out different plants, and results are averaged across folds.

## Photo guidelines

- **Subject:** fill most of the frame with the leaves you're judging. Include the diseased leaves if there are any.
- **Light:** use daylight and avoid flash. Overcast light or shade is best, and harsh midday sun is worst. Record the light in `observation_conditions`.
- **Consistency:** take photos at about the same distance and time of day each visit.
- **Focus:** keep the photo sharp. Retake it if it's blurry.
- **Number:** one to three photos per observation is plenty.

## How much data, and how often

The risk experiment needs the **same plants visited repeatedly**, and enough plants for a plant-level split:

| | Minimum | Better |
|---|---|---|
| Plants | 10 | 30+ |
| Visits | every 2 days | daily |
| Duration | 2 weeks | 4+ weeks |
| Observations | ~70 | 300+ |
| Plants that become diseased | 3+ (and 3+ that stay healthy) | as many as possible |

What can be claimed depends on the counts:
- **The number of plants matters more than the number of observations.**
  - 300 observations of 5 plants is effectively 5 independent samples.
  - 10 plants only supports a pilot study, and the report should call it that.
- **Disease onsets matter most for the risk experiment.** It needs plants that **change** from healthy to diseased during collection. Plants that are diseased from the first visit only help the detection experiment.
- **One visit per plant still works for detection.** If each plant can only be visited once, run experiment 1 only and say so in the report.

## Sensor readings

- **ESP32 node:** the best option, because it's the project's own hardware. Wait 1–2 minutes after inserting the probes before reading.
- **Handheld meter:** fine if the ESP32 isn't ready. Set `sensor_source`, `sensor_device_id` and `sensor_calibration_status`, and use the same unit throughout.
- **pH:** record the raw mV (`soil_ph_mv`). The ESP32 probe isn't calibrated, so mV is the honest value.
- **Missing readings:** leave the cell blank. Never estimate or fill in a reading you didn't take.
