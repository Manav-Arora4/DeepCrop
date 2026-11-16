# Sensor-only scorer: results (sensor_risk_v1.0)

Data: external dataset supplied for this project; not collected with this project's sensor node. 840 observations of 30 tomato plants (2026-10-01 to 2026-10-28); device ID as recorded in the dataset: `esp32_001`. pH is from an uncalibrated probe and is used only as a change from each plant's own baseline.

Evaluation: 5-fold cross-validation grouped by plant (every score comes from plants the model never saw), 95% intervals from 1,000 plant-level bootstrap resamples. Columns that would leak the answer (treatment, notes, severity, leaf counts) are never used as features.

## Task 1: is the plant diseased now?

837 observations, 168 positive, from 11 of 30 plants.

| Model | ROC-AUC (95% CI) | PR-AUC (95% CI) | F1 @0.5 | Brier |
|---|---:|---:|---:|---:|
| Logistic regression | 0.569 (0.448–0.686) | 0.21 (0.098–0.351) | 0.383 | 0.243 |
| Random forest **(selected)** | 0.612 (0.491–0.744) | 0.264 (0.134–0.435) | 0.296 | 0.198 |
| No-skill baseline | 0.475 | 0.192 | 0.0 | 0.161 |

Most influential features: `moisture_mean_3` (0.19), `soil_moisture_pct` (0.145), `humidity_max_3` (0.097), `moisture_change_1` (0.086), `humidity_mean_3` (0.083).

## Task 2: will a healthy plant become diseased within 7 days?

533 observations, 60 positive, from 9 of 28 plants.

| Model | ROC-AUC (95% CI) | PR-AUC (95% CI) | F1 @0.5 | Brier |
|---|---:|---:|---:|---:|
| Logistic regression **(selected)** | 0.549 (0.392–0.683) | 0.142 (0.061–0.308) | 0.207 | 0.229 |
| Random forest | 0.431 (0.29–0.572) | 0.108 (0.047–0.229) | 0.114 | 0.156 |
| No-skill baseline | 0.438 | 0.099 | 0.0 | 0.1 |

Most influential features: `soil_moisture_pct` (0.17), `moisture_mean_3` (0.169), `hours_humid_proxy_3` (0.165), `humidity_max_3` (0.1), `growth_stage_idx` (0.099).

## Limits

- Few independent units: 30 plants. Plant-level intervals are wide by design; read them, not just the point estimate.
- Task 2 rests on 9 plants that became diseased during collection.
- The selected model is the better of two candidates on the same cross-validation, so its score is slightly optimistic.
- When an interval includes 0.5, the sensors show no reliable signal for that task on this data. Report that as a finding, not a failure.
- These are sensor-only scores. They become one input to the weighted fusion with the photo model and the RAG assessment (see `ml/fusion.py`).
