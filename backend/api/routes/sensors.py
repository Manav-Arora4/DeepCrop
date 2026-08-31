from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.sensor import (
    SensorReadingCreate,
    SensorReadingResponse,
    SimulationRequest,
    SensorHistoryResponse,
)
from backend.api.deps import get_session, get_crop_manager
from backend.services.sensor_service import SensorService
from backend.services.simulation_service import SimulationService
from backend.services.crop_manager import CropManager
from backend.core.config import get_settings

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.post("/reading", response_model=SensorReadingResponse)
async def submit_sensor_reading(
    reading: SensorReadingCreate,
    db: AsyncSession = Depends(get_session),
    manager: CropManager = Depends(get_crop_manager),
):
    """
    Ingest a real, simulated, or manual sensor reading.
    Returns the persisted reading evaluated against crop thresholds (LOW/OPTIMAL/HIGH).
    """
    if not manager.validate_crop_exists(reading.crop_id):
        raise HTTPException(status_code=404, detail=f"Crop '{reading.crop_id}' is not registered.")

    service = SensorService(db, manager)
    return await service.ingest_reading(reading)


@router.get("/latest", response_model=SensorReadingResponse)
async def get_latest_sensor_reading(
    plant_id: str = Query(..., description="ID of monitored plant"),
    crop_id: str = Query(..., description="ID of crop module"),
    db: AsyncSession = Depends(get_session),
    manager: CropManager = Depends(get_crop_manager),
):
    """Retrieve the most recent environmental reading for a given plant."""
    service = SensorService(db, manager)
    reading = await service.get_latest(plant_id, crop_id)
    if not reading:
        raise HTTPException(status_code=404, detail=f"No sensor readings found for plant '{plant_id}'.")
    return reading


@router.get("/history", response_model=SensorHistoryResponse)
async def get_sensor_history(
    plant_id: str = Query(..., description="ID of monitored plant"),
    crop_id: str = Query(..., description="ID of crop module"),
    range: str = Query(default="1d", pattern="^(1h|6h|1d|7d|30d)$"),
    db: AsyncSession = Depends(get_session),
    manager: CropManager = Depends(get_crop_manager),
):
    """Retrieve historical time-series readings with threshold statuses."""
    service = SensorService(db, manager)
    readings = await service.get_history(plant_id, crop_id, range)
    return SensorHistoryResponse(readings=readings, range=range, count=len(readings))


@router.post("/simulate", response_model=List[SensorReadingResponse])
async def simulate_sensor_stream(
    sim_req: SimulationRequest,
    db: AsyncSession = Depends(get_session),
    manager: CropManager = Depends(get_crop_manager),
):
    """
    Generate synthetic sensor data across 5 domain scenarios:
    'optimal', 'drought', 'overwatered', 'disease_risk', 'random'.
    Always tags readings with data_source='simulated'.
    """
    settings = get_settings()
    if not settings.SIMULATION_MODE:
        raise HTTPException(status_code=403, detail="Simulation mode is disabled in server configuration.")

    sim_service = SimulationService(db, manager)
    return await sim_service.generate(sim_req)
