from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.disease_risk_prediction import DiseaseRiskPrediction
from backend.models.sensor_reading import SensorReading
from backend.models.image_prediction import ImagePrediction
from backend.schemas.prediction import DiseaseRiskRequest, DiseaseRiskResponse
from backend.services.crop_manager import CropManager
from ml.disease_risk.models.random_forest import RandomForestRiskModel


class DiseaseRiskService:
    """Multimodal Disease Risk Prediction service."""

    def __init__(self, db: AsyncSession, crop_manager: CropManager):
        self.db = db
        self.crop_manager = crop_manager
        self._model = RandomForestRiskModel()

    async def predict_risk(self, req: DiseaseRiskRequest) -> DiseaseRiskResponse:
        sensor_data = None
        if req.sensor_reading_id:
            s_res = await self.db.execute(
                select(SensorReading).where(SensorReading.id == req.sensor_reading_id)
            )
            s_obj = s_res.scalar_one_or_none()
            if s_obj:
                sensor_data = {
                    "moisture": s_obj.moisture,
                    "ph": s_obj.ph,
                    "temperature": s_obj.temperature,
                    "humidity": s_obj.humidity,
                }

        cv_data = None
        if req.cv_prediction_id:
            cv_res = await self.db.execute(
                select(ImagePrediction).where(ImagePrediction.id == req.cv_prediction_id)
            )
            cv_obj = cv_res.scalar_one_or_none()
            if cv_obj:
                cv_data = {
                    "disease": cv_obj.disease,
                    "disease_id": cv_obj.disease_id,
                    "confidence": cv_obj.confidence,
                }

        thresholds = self.crop_manager.get_thresholds(req.crop_id) or {}

        features = {
            "sensor": sensor_data,
            "cv": cv_data,
            "thresholds": thresholds,
            "crop_id": req.crop_id,
        }

        # If both modalities are missing, return unknown status gracefully
        if sensor_data is None and cv_data is None:
            res_score = 0.0
            res_level = "unknown"
            factors = ["Insufficient data — no sensor readings or image predictions provided"]
            m_status = "demo"
            m_ver = "demo_baseline_v0.1"
            importances = None
        else:
            result = self._model.predict(features)
            res_score = result.risk_score
            res_level = result.risk_level
            factors = result.contributing_factors
            m_status = result.model_status
            m_ver = result.model_version
            importances = result.feature_importances

        record = DiseaseRiskPrediction(
            plant_id=req.plant_id,
            crop_id=req.crop_id,
            risk_score=res_score,
            risk_level=res_level,
            contributing_factors=factors,
            cv_prediction_id=req.cv_prediction_id,
            sensor_reading_id=req.sensor_reading_id,
            model_version=m_ver,
            model_status=m_status,
            feature_importances=importances,
            timestamp=datetime.now(timezone.utc),
        )

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        return DiseaseRiskResponse(
            id=record.id,
            crop_id=record.crop_id,
            plant_id=record.plant_id,
            risk_score=record.risk_score,
            risk_level=record.risk_level,
            contributing_factors=record.contributing_factors,
            model_version=record.model_version,
            model_status=record.model_status,
            timestamp=record.timestamp,
        )
