import pickle
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from ml.disease_risk.models.base import AbstractDiseaseRiskModel, DiseaseRiskResult
from ml.disease_risk.models.random_forest import score_to_risk_level
from ml.disease_risk.feature_builder import FEATURE_NAMES, build_feature_vector


class XGBoostRiskModel(AbstractDiseaseRiskModel):
    """
    XGBoost Classifier for gradient-boosted multimodal risk estimation.
    Used for academic model comparison against Random Forest baseline.
    """

    def __init__(self, model_path: Optional[Path | str] = None, version: str = "xgb_v1.0"):
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
            probs = self._model.predict_proba([feat_vec])[0]
            score = float(probs[1]) if len(probs) > 1 else float(probs[0])
            score = max(0.0, min(1.0, score))
            importances = dict(zip(FEATURE_NAMES, [float(v) for v in self._model.feature_importances_]))
            status = "ready"
        else:
            score = 0.15
            importances = {"humidity": 0.32, "cv_is_disease": 0.28, "moisture_stress": 0.22, "temp_stress": 0.18}
            status = "demo"

        factors = []
        if feat_vec[3] > 70:
            factors.append("High humidity promotes fungal development")
        if feat_vec[5] > 0.5:
            factors.append("Visual foliar lesions detected")

        return DiseaseRiskResult(
            risk_score=round(score, 4),
            risk_level=score_to_risk_level(score),
            contributing_factors=factors if factors else ["Optimal growing environment"],
            model_version=self.version,
            model_status=status,
            feature_importances=importances,
        )

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "name": "XGBoost Multimodal Disease Risk Model",
            "version": self.version,
            "status": self._status,
            "architecture": "XGBClassifier",
            "features": FEATURE_NAMES,
        }
