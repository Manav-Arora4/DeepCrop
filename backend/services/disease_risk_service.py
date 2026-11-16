"""
Disease-risk service: weighted fusion of three separately built scorers (ml/fusion.py).

  photo   P(diseased) = 1 - P(healthy) from the leaf-photo model's stored class probabilities
  sensor  7-day risk from the sensor scorer (ml/sensor_risk), fed the plant's last three readings
  rag     grounded 0-1 assessment from the RAG + LLM scorer (ml/rag_risk); needs Ollama

A scorer with no input, a demo/untrained model, or a failed grounding check is left out and
the remaining weights are renormalised. Weights are provisional until fitted on paired data,
so every result is stored with model_status "provisional" and its per-scorer breakdown.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.models.disease_risk_prediction import DiseaseRiskPrediction
from backend.models.image_prediction import ImagePrediction
from backend.models.plant import Plant
from backend.models.sensor_reading import SensorReading
from backend.schemas.prediction import DiseaseRiskRequest, DiseaseRiskResponse
from backend.services.crop_manager import CropManager
from ml.fusion import DEFAULT_WEIGHTS, fuse, photo_score

SENSOR_MODEL = Path("crops/{crop}/models/sensor_risk/sensor_risk_7d_v1.joblib")
FUSION_VERSION = "fusion_v1"
_sensor_models: Dict[str, Any] = {}


def _load_sensor_model(crop_id: str):
    if crop_id not in _sensor_models:
        path = Path(str(SENSOR_MODEL).format(crop=crop_id))
        if path.exists():
            import joblib
            _sensor_models[crop_id] = joblib.load(path)
        else:
            _sensor_models[crop_id] = None
    return _sensor_models[crop_id]


def to_response(r: DiseaseRiskPrediction) -> DiseaseRiskResponse:
    return DiseaseRiskResponse(
        id=r.id, crop_id=r.crop_id, plant_id=r.plant_id, risk_score=r.risk_score, risk_level=r.risk_level,
        contributing_factors=r.contributing_factors, model_version=r.model_version, model_status=r.model_status,
        components=r.components, timestamp=r.timestamp,
    )


class DiseaseRiskService:
    def __init__(self, db: AsyncSession, crop_manager: CropManager):
        self.db = db
        self.crop_manager = crop_manager
        self.settings = get_settings()

    async def _recent_readings(self, plant_id: str, upto_id: Optional[int]) -> list:
        q = select(SensorReading).where(SensorReading.plant_id == plant_id)
        if upto_id:
            q = q.where(SensorReading.id <= upto_id)
        res = await self.db.execute(q.order_by(SensorReading.timestamp.desc()).limit(3))
        return list(reversed(res.scalars().all()))

    def _sensor_features(self, readings: list, growth_stage: str) -> Optional[pd.DataFrame]:
        from ml.sensor_risk.features import FEATURES, build_features
        rows = [{
            "plant_id": "p", "ts": r.timestamp, "temperature_c": r.temperature, "humidity_pct": r.humidity,
            "soil_moisture_pct": r.moisture,
            # The app stores calibrated-style pH, the model was trained on raw mV: hold the pH feature neutral
            "soil_ph_mv": 0.0, "watered_last_24h": "no", "growth_stage": growth_stage,
        } for r in readings]
        df = pd.DataFrame(rows)
        if df[["temperature_c", "humidity_pct", "soil_moisture_pct"]].iloc[-1].isna().any():
            return None
        return build_features(df).iloc[[-1]][FEATURES]

    async def predict_risk(self, req: DiseaseRiskRequest) -> DiseaseRiskResponse:
        plant = await self.db.get(Plant, req.plant_id)
        growth_stage = (plant.growth_stage if plant and plant.growth_stage else "flowering")
        details: Dict[str, Any] = {}
        photo = sensor = rag = None

        # 1. Photo scorer
        cv_obj = await self.db.get(ImagePrediction, req.cv_prediction_id) if req.cv_prediction_id else None
        if cv_obj and cv_obj.model_status == "ready" and cv_obj.class_probabilities:
            photo = photo_score(cv_obj.class_probabilities)
            details["photo"] = {"disease": cv_obj.disease, "confidence": round(cv_obj.confidence, 3), "model": cv_obj.model_version}
        elif cv_obj:
            details["photo"] = {"skipped": f"photo model status is '{cv_obj.model_status}'"}

        # 2. Sensor scorer
        readings = await self._recent_readings(req.plant_id, req.sensor_reading_id) if req.sensor_reading_id else []
        latest = readings[-1] if readings else None
        model = _load_sensor_model(req.crop_id)
        if latest and model is not None:
            feats = self._sensor_features(readings, growth_stage)
            if feats is not None:
                sensor = round(float(model.predict_proba(feats)[0, 1]), 4)
                details["sensor"] = {"readings_used": len(readings), "data_source": latest.data_source, "model": "sensor_risk_v1.0"}
        elif latest:
            details["sensor"] = {"skipped": "sensor model not trained (run python -m ml.sensor_risk.train)"}

        # 3. RAG + LLM scorer
        if latest and self.settings.LLM_PROVIDER == "ollama":
            from ml.rag_risk.scorer import score as rag_score
            hum = [r.humidity for r in readings if r.humidity is not None]
            rag_readings = {
                "temperature_c": latest.temperature, "humidity_pct": latest.humidity, "soil_moisture_pct": latest.moisture,
                "humidity_mean_3": sum(hum) / len(hum) if hum else None, "humidity_max_3": max(hum) if hum else None,
            }
            photo_in = {"disease": cv_obj.disease, "confidence": cv_obj.confidence} if photo is not None else None
            try:
                r = await asyncio.wait_for(rag_score(
                    rag_readings, growth_stage, photo=photo_in, crop_id=req.crop_id,
                    model=self.settings.OLLAMA_MODEL, base_url=self.settings.OLLAMA_BASE_URL), timeout=150)
                if r.grounded:
                    rag = r.score
                    details["rag"] = {"likely_diseases": r.likely_diseases, "references": r.references,
                                      "evidence": r.evidence, "model": r.model}
                else:
                    details["rag"] = {"skipped": "answer failed grounding checks", "failures": r.failures}
            except Exception as e:
                details["rag"] = {"skipped": f"LLM unavailable ({type(e).__name__})"}

        if photo is None and sensor is None and rag is None:
            score, level, status = 0.0, "unknown", "provisional"
            factors = ["Not enough input: add a sensor reading or scan a leaf"]
            components = {"missing": ["photo", "sensor", "rag"], "details": details}
        else:
            fused = fuse(photo=photo, sensor=sensor, rag=rag)
            score, level, status = fused.score, fused.level, "provisional"
            names = {"photo": "Leaf photo", "sensor": "Sensors", "rag": "Knowledge base + LLM"}
            factors = [f"{names[k]}: {fused.used[k]:.2f}, weight {fused.weights[k]:.2f}" for k in fused.used]
            factors += [f"{names[k]}: not used" for k in fused.missing]
            components = {
                "scores": fused.used, "weights": fused.weights, "contributions": fused.contributions,
                "missing": fused.missing, "default_weights": DEFAULT_WEIGHTS, "provisional_weights": True,
                "details": details,
            }

        record = DiseaseRiskPrediction(
            plant_id=req.plant_id, crop_id=req.crop_id, risk_score=score, risk_level=level,
            contributing_factors=factors, cv_prediction_id=req.cv_prediction_id,
            sensor_reading_id=req.sensor_reading_id, model_version=FUSION_VERSION, model_status=status,
            feature_importances=None, components=components, timestamp=datetime.now(timezone.utc),
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return to_response(record)
