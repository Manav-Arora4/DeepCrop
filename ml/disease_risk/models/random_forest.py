import pickle
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from ml.disease_risk.models.base import AbstractDiseaseRiskModel, DiseaseRiskResult
from ml.disease_risk.feature_builder import FEATURE_NAMES, build_feature_vector


def score_to_risk_level(score: float) -> str:
    if score < 0.25:
        return "low"
    elif score < 0.50:
        return "moderate"
    elif score < 0.75:
        return "high"
    return "critical"


class RandomForestRiskModel(AbstractDiseaseRiskModel):
    """
    Random Forest Classifier / Regressor for Multimodal Disease Risk Prediction.
    Provides feature importances and Gini-based factor contributions.
    """

    def __init__(self, model_path: Optional[Path | str] = None, version: str = "rf_v1.0"):
        self.model_path = Path(model_path) if model_path else None
        self.version = version
        self._model = None
        self._status = "ready" if (self.model_path and self.model_path.exists()) else "demo"

    def _load(self):
        if self._model is not None:
            return
        if self.model_path and self.model_path.exists():
            with open(self.model_path, "rb") as f:
                self._model = pickle.load(f)
                self._status = "ready"

    def predict(self, features: Dict[str, Any]) -> DiseaseRiskResult:
        self._load()

        sensor = features.get("sensor")
        cv = features.get("cv")
        thresholds = features.get("thresholds", {})

        feat_vec = build_feature_vector(sensor, cv, thresholds)

        if self._status == "ready" and self._model is not None:
            score = float(self._model.predict_proba([feat_vec])[0][1]) if hasattr(self._model, "predict_proba") else float(self._model.predict([feat_vec])[0])
            score = max(0.0, min(1.0, score))
            importances = dict(zip(FEATURE_NAMES, [float(v) for v in self._model.feature_importances_]))
        else:
            # Rule-based agronomic score calculation for demo
            score = 0.10
            factors = []
            if sensor:
                hum = sensor.get("humidity")
                temp = sensor.get("temperature")
                mst = sensor.get("moisture")
                ph_val = sensor.get("ph")

                if hum is not None and hum > thresholds.get("humidity", {}).get("high_min", 70):
                    score += 0.30
                    factors.append(f"Elevated atmospheric humidity ({hum}%) creating spore germination microclimate")
                if temp is not None and temp > thresholds.get("temperature", {}).get("high_min", 30):
                    score += 0.20
                    factors.append(f"High temperature stress ({temp}°C)")
                elif temp is not None and temp < thresholds.get("temperature", {}).get("low_max", 10):
                    score += 0.20
                    factors.append(f"Chilling temperature stress ({temp}°C)")
                if mst is not None and mst < thresholds.get("moisture", {}).get("low_max", 30):
                    score += 0.25
                    factors.append(f"Severe soil moisture deficit ({mst}%)")
                elif mst is not None and mst > thresholds.get("moisture", {}).get("high_min", 70):
                    score += 0.20
                    factors.append(f"Waterlogged soil root hypoxia risk ({mst}%)")
                if ph_val is not None and (ph_val < 5.5 or ph_val > 7.5):
                    score += 0.15
                    factors.append(f"Suboptimal soil pH ({ph_val})")

            if cv:
                disease_id = cv.get("disease_id", "")
                conf = cv.get("confidence", 0.0)
                if disease_id and not disease_id.endswith("_healthy") and disease_id != "unknown":
                    score += (0.35 * conf)
                    factors.append(f"CV confirmed symptomatic foliage: {cv.get('disease')} ({conf:.0%})")

            score = min(round(score, 4), 1.0)
            return DiseaseRiskResult(
                risk_score=score,
                risk_level=score_to_risk_level(score),
                contributing_factors=factors if factors else ["All environmental and visual parameters within optimal bounds"],
                model_version="rf_baseline_demo_v0.1",
                model_status="demo",
                feature_importances={
                    "humidity": 0.28,
                    "cv_is_disease": 0.25,
                    "moisture_stress": 0.20,
                    "temp_stress": 0.15,
                    "vapor_pressure_deficit": 0.12,
                },
            )

        factors = []
        if feat_vec[3] > 70:
            factors.append("High humidity")
        if feat_vec[5] > 0.5:
            factors.append("Visual disease symptoms detected")
        if feat_vec[6] > 10:
            factors.append("Soil moisture deviation")

        return DiseaseRiskResult(
            risk_score=round(score, 4),
            risk_level=score_to_risk_level(score),
            contributing_factors=factors if factors else ["Optimal conditions"],
            model_version=self.version,
            model_status="ready",
            feature_importances=importances,
        )

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "name": "Random Forest Multimodal Disease Risk Model",
            "version": self.version,
            "status": self._status,
            "architecture": "RandomForestClassifier",
            "features": FEATURE_NAMES,
        }
