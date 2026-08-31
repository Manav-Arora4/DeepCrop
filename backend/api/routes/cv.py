import time
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.schemas.prediction import CVPredictionResponse
from backend.models.image_prediction import ImagePrediction
from backend.api.deps import get_session, get_crop_manager
from backend.services.cv_engine import CVEngine
from backend.services.crop_manager import CropManager
from backend.core.config import get_settings

router = APIRouter(prefix="/cv", tags=["Computer Vision"])


@router.post("/predict", response_model=CVPredictionResponse)
async def predict_disease_image(
    file: UploadFile = File(...),
    crop_id: str = Form(...),
    plant_id: str = Form(...),
    sensor_reading_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_session),
    manager: CropManager = Depends(get_crop_manager),
):
    """
    Classify plant disease from an uploaded leaf image (JPG, PNG, WEBP).
    Runs inference via EfficientNetB0 (or transparent Demo fallback if unweighted).
    """
    if not manager.validate_crop_exists(crop_id):
        raise HTTPException(status_code=404, detail=f"Crop '{crop_id}' is not registered.")

    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WEBP.",
        )

    settings = get_settings()
    upload_dir = Path(settings.UPLOADS_DIR) / crop_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = int(time.time())
    safe_name = f"{timestamp_str}_{file.filename.replace(' ', '_')}"
    dest_path = upload_dir / safe_name

    image_bytes = await file.read()
    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image size exceeds limit of {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    with open(dest_path, "wb") as f:
        f.write(image_bytes)

    cv_engine = CVEngine(db, manager)
    return await cv_engine.predict_image(
        image_bytes=image_bytes,
        crop_id=crop_id,
        plant_id=plant_id,
        image_path=str(dest_path),
        sensor_reading_id=sensor_reading_id,
    )


@router.get("/predictions/{plant_id}", response_model=List[CVPredictionResponse])
async def get_plant_cv_history(plant_id: str, db: AsyncSession = Depends(get_session)):
    """Get history of CV predictions for a specific plant."""
    res = await db.execute(
        select(ImagePrediction)
        .where(ImagePrediction.plant_id == plant_id)
        .order_by(ImagePrediction.timestamp.desc())
    )
    records = res.scalars().all()
    return [
        CVPredictionResponse(
            id=r.id,
            crop=r.crop_id,
            disease=r.disease,
            disease_id=r.disease_id,
            confidence=r.confidence,
            severity=r.severity,
            model_version=r.model_version,
            model_status=r.model_status,
            low_confidence_warning=r.low_confidence_warning,
            plant_id=r.plant_id,
            timestamp=r.timestamp,
        )
        for r in records
    ]
