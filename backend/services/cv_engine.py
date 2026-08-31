import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.image_prediction import ImagePrediction
from backend.schemas.prediction import CVPredictionResponse
from backend.services.crop_manager import CropManager
from backend.core.config import get_settings
from ml.cv.models.base import AbstractCVModel
from ml.cv.models.demo import DemoCVModel
from ml.cv.models.efficientnet import EfficientNetCVModel


class CVEngine:
    """
    Computer Vision Service Layer.
    Dispatches leaf image inference to EfficientNetCVModel or DemoCVModel.
    """

    def __init__(self, db: AsyncSession, crop_manager: CropManager):
        self.db = db
        self.crop_manager = crop_manager
        self.settings = get_settings()
        self._model_cache: Dict[str, AbstractCVModel] = {}

    def get_model(self, crop_id: str) -> AbstractCVModel:
        if crop_id in self._model_cache:
            return self._model_cache[crop_id]

        crop_data = self.crop_manager.get_crop(crop_id)
        disease_classes = self.crop_manager.get_disease_classes(crop_id) or []

        if crop_data:
            cv_cfg = crop_data.get("cv_model", {})
            model_rel_path = cv_cfg.get("path")
            if model_rel_path:
                model_full = Path(model_rel_path)
                if not model_full.exists():
                    model_full = Path(self.settings.CROPS_DIRECTORY) / crop_id / "models" / "cv" / "efficientnet_tomato_v1.pth"

                if model_full.exists():
                    model = EfficientNetCVModel(
                        model_path=model_full,
                        crop_id=crop_id,
                        disease_classes=disease_classes,
                        version=cv_cfg.get("version", "v1.0"),
                    )
                    self._model_cache[crop_id] = model
                    return model

        # Fallback to DemoCVModel
        demo_model = DemoCVModel(
            crop_id=crop_id,
            disease_classes=disease_classes,
            version="demo_v0.1",
        )
        self._model_cache[crop_id] = demo_model
        return demo_model

    async def predict_image(
        self,
        image_bytes: bytes,
        crop_id: str,
        plant_id: str,
        image_path: str,
        sensor_reading_id: Optional[int] = None,
    ) -> CVPredictionResponse:
        model = self.get_model(crop_id)
        result = model.predict(image_bytes)

        low_conf = result.confidence < self.settings.CV_CONFIDENCE_THRESHOLD

        record = ImagePrediction(
            plant_id=plant_id,
            crop_id=crop_id,
            image_path=image_path,
            disease=result.disease,
            disease_id=result.disease_id,
            confidence=result.confidence,
            severity=result.severity,
            model_version=result.model_version,
            model_status=result.model_status,
            low_confidence_warning=low_conf,
            sensor_reading_id=sensor_reading_id,
            class_probabilities=result.class_probabilities,
            timestamp=datetime.now(timezone.utc),
        )

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        return CVPredictionResponse(
            id=record.id,
            crop=record.crop_id,
            disease=record.disease,
            disease_id=record.disease_id,
            confidence=record.confidence,
            severity=record.severity,
            model_version=record.model_version,
            model_status=record.model_status,
            low_confidence_warning=record.low_confidence_warning,
            plant_id=record.plant_id,
            timestamp=record.timestamp,
        )
