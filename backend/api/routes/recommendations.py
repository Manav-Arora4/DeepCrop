from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.schemas.recommendation import RecommendationRequest, RecommendationResponse
from backend.models.recommendation import Recommendation
from backend.api.deps import get_session, get_crop_manager
from backend.services.recommendation_service import RecommendationService
from backend.services.crop_manager import CropManager

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendation(
    req: RecommendationRequest,
    db: AsyncSession = Depends(get_session),
    manager: CropManager = Depends(get_crop_manager),
):
    """
    Generate an LLM + RAG grounded agricultural advisory recommendation.
    """
    if not manager.validate_crop_exists(req.crop_id):
        raise HTTPException(status_code=404, detail=f"Crop '{req.crop_id}' is not registered.")

    service = RecommendationService(db, manager)
    return await service.generate(req)


@router.get("/{plant_id}", response_model=List[RecommendationResponse])
async def get_recommendation_history(plant_id: str, db: AsyncSession = Depends(get_session)):
    """Retrieve historical recommendation audit log for a plant."""
    res = await db.execute(
        select(Recommendation)
        .where(Recommendation.plant_id == plant_id)
        .order_by(Recommendation.timestamp.desc())
    )
    records = res.scalars().all()
    return [
        RecommendationResponse(
            id=r.id,
            plant_id=r.plant_id,
            crop_id=r.crop_id,
            summary=r.summary,
            contributing_factors=r.contributing_factors,
            recommended_actions=r.recommended_actions,
            prevention_steps=r.prevention_steps,
            monitoring_advice=r.monitoring_advice,
            urgency=r.urgency,
            sources=r.sources,
            llm_provider=r.llm_provider,
            llm_model=r.llm_model,
            timestamp=r.timestamp,
        )
        for r in records
    ]
