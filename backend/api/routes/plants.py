from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.plant import Plant
from backend.schemas.plant import PlantCreate, PlantResponse
from backend.api.deps import get_session

router = APIRouter(prefix="/plants", tags=["Plants"])


@router.get("", response_model=List[PlantResponse])
async def list_plants(db: AsyncSession = Depends(get_session)):
    """List all registered plants or production zones."""
    res = await db.execute(select(Plant))
    return res.scalars().all()


@router.post("", response_model=PlantResponse)
async def create_plant(plant_in: PlantCreate, db: AsyncSession = Depends(get_session)):
    """Register a new plant or monitoring zone."""
    res = await db.execute(select(Plant).where(Plant.id == plant_in.id))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Plant ID '{plant_in.id}' already exists.")

    plant = Plant(
        id=plant_in.id,
        crop_id=plant_in.crop_id,
        name=plant_in.name,
        location=plant_in.location,
        growth_stage=plant_in.growth_stage,
    )
    db.add(plant)
    await db.commit()
    await db.refresh(plant)
    return plant


@router.get("/{plant_id}", response_model=PlantResponse)
async def get_plant(plant_id: str, db: AsyncSession = Depends(get_session)):
    """Retrieve details of a specific plant."""
    res = await db.execute(select(Plant).where(Plant.id == plant_id))
    plant = res.scalar_one_or_none()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant '{plant_id}' not found.")
    return plant
