from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.schemas.prediction import DiseaseRiskRequest, DiseaseRiskResponse
from backend.models.disease_risk_prediction import DiseaseRiskPrediction
from backend.api.deps import get_session, get_crop_manager
from backend.services.disease_risk_service import DiseaseRiskService
from backend.services.crop_manager import CropManager

router = APIRouter(prefix="/disease-risk", tags=["Multimodal Disease Risk"])


@router.post("/predict", response_model=DiseaseRiskResponse)
async def predict_disease_risk(
    req: DiseaseRiskRequest,
    db: AsyncSession = Depends(get_session),
    manager: CropManager = Depends(get_crop_manager),
):
    """
    Evaluate multimodal disease risk by combining CV foliar analysis and IoT sensor conditions.
    """
    if not manager.validate_crop_exists(req.crop_id):
        raise HTTPException(status_code=404, detail=f"Crop '{req.crop_id}' is not registered.")

    service = DiseaseRiskService(db, manager)
    return await service.predict_risk(req)


@router.get("/history/{plant_id}", response_model=List[DiseaseRiskResponse])
async def get_risk_history(plant_id: str, db: AsyncSession = Depends(get_session)):
    """Retrieve disease risk assessment timeline for a plant."""
    res = await db.execute(
        select(DiseaseRiskPrediction)
        .where(DiseaseRiskPrediction.plant_id == plant_id)
        .order_by(DiseaseRiskPrediction.timestamp.desc())
    )
    records = res.scalars().all()
    return [
        DiseaseRiskResponse(
            id=r.id,
            crop_id=r.crop_id,
            plant_id=r.plant_id,
            risk_score=r.risk_score,
            risk_level=r.risk_level,
            contributing_factors=r.contributing_factors,
            model_version=r.model_version,
            model_status=r.model_status,
            timestamp=r.timestamp,
        )
        for r in records
    ]
