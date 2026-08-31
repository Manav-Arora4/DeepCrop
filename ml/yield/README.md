# Yield Prediction & Optimization Module (Phase 10 / Future Work)

## Overview
The Yield Optimization module is designed to forecast end-of-season harvest yields (kg/hectare or kg/plant) and recommend environmental setpoint adjustments to maximize yield efficiency.

## Target Inputs
1. **Cumulative Environmental Exposure**:
   - Degree Days (Growing Degree Units - GDU)
   - Moisture stress hours (hours with VWC < 30% or > 70%)
   - Vapor Pressure Deficit (VPD) cumulative curve
2. **Plant Phenology**:
   - Days elapsed in each growth stage (vegetative, flowering, fruit development)
3. **Disease Events**:
   - Integrated disease risk integral (AUC of disease risk timeline)
   - Severity of visual symptoms detected by CV

## Planned Models
- **LightGBM / XGBoost Regressor**: Baseline tabular yield forecast
- **LSTM / Temporal Fusion Transformer (TFT)**: Sequential time-series forecasting of weekly yield output
