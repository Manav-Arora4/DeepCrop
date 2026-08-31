"""
Multimodal Feature Engineering Pipeline for Disease-Risk Prediction.
Extracts, validates, and normalizes combined environmental IoT and CV image features.
"""

from typing import Dict, Any, List, Optional
import numpy as np


FEATURE_NAMES = [
    "moisture",
    "ph",
    "temperature",
    "humidity",
    "cv_confidence",
    "cv_is_disease",
    "moisture_stress",
    "temp_stress",
    "vapor_pressure_deficit",
]


def calculate_vpd(temperature: float, humidity: float) -> float:
    """Calculate Vapor Pressure Deficit (VPD in kPa)."""
    # Saturated vapor pressure (Tetens formula)
    es = 0.61078 * np.exp((17.27 * temperature) / (temperature + 237.3))
    # Actual vapor pressure
    ea = es * (humidity / 100.0)
    return round(float(es - ea), 3)


def build_feature_vector(
    sensor_reading: Optional[Dict[str, Any]],
    cv_prediction: Optional[Dict[str, Any]],
    thresholds: Dict[str, Any],
) -> np.ndarray:
    """
    Construct standardized 1D feature array for model input.
    Handles missing modalities gracefully with default imputations.
    """
    # Defaults
    moisture = 50.0
    ph = 6.5
    temperature = 22.0
    humidity = 55.0

    if sensor_reading:
        if sensor_reading.get("moisture") is not None:
            moisture = float(sensor_reading["moisture"])
        if sensor_reading.get("ph") is not None:
            ph = float(sensor_reading["ph"])
        if sensor_reading.get("temperature") is not None:
            temperature = float(sensor_reading["temperature"])
        if sensor_reading.get("humidity") is not None:
            humidity = float(sensor_reading["humidity"])

    cv_conf = 0.0
    cv_is_disease = 0.0
    if cv_prediction:
        cv_conf = float(cv_prediction.get("confidence", 0.0))
        disease_id = cv_prediction.get("disease_id", "")
        cv_is_disease = 0.0 if ("healthy" in disease_id or disease_id == "unknown") else 1.0

    # Stress deviations from thresholds
    m_opt_min = thresholds.get("moisture", {}).get("optimal_min", 30.0)
    m_opt_max = thresholds.get("moisture", {}).get("optimal_max", 70.0)
    if moisture < m_opt_min:
        moisture_stress = m_opt_min - moisture
    elif moisture > m_opt_max:
        moisture_stress = moisture - m_opt_max
    else:
        moisture_stress = 0.0

    t_opt_min = thresholds.get("temperature", {}).get("optimal_min", 10.0)
    t_opt_max = thresholds.get("temperature", {}).get("optimal_max", 30.0)
    if temperature < t_opt_min:
        temp_stress = t_opt_min - temperature
    elif temperature > t_opt_max:
        temp_stress = temperature - t_opt_max
    else:
        temp_stress = 0.0

    vpd = calculate_vpd(temperature, humidity)

    return np.array([
        moisture,
        ph,
        temperature,
        humidity,
        cv_conf,
        cv_is_disease,
        moisture_stress,
        temp_stress,
        vpd,
    ], dtype=np.float32)
