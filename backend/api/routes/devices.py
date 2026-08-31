from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.device import Device
from backend.schemas.device import DeviceRegister, DeviceStatusResponse
from backend.api.deps import get_session

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/register", response_model=DeviceStatusResponse)
async def register_device(dev_in: DeviceRegister, db: AsyncSession = Depends(get_session)):
    """Register an ESP32 or simulated IoT device."""
    res = await db.execute(select(Device).where(Device.id == dev_in.device_id))
    existing = res.scalar_one_or_none()

    if existing:
        existing.plant_id = dev_in.plant_id
        existing.crop_id = dev_in.crop_id
        existing.simulated = dev_in.simulated
        existing.status = "online"
        existing.last_seen = datetime.now(timezone.utc)
        dev = existing
    else:
        dev = Device(
            id=dev_in.device_id,
            plant_id=dev_in.plant_id,
            crop_id=dev_in.crop_id,
            status="online",
            simulated=dev_in.simulated,
            last_seen=datetime.now(timezone.utc),
        )
        db.add(dev)

    await db.commit()
    await db.refresh(dev)

    return DeviceStatusResponse(
        device_id=dev.id,
        plant_id=dev.plant_id,
        crop_id=dev.crop_id,
        status=dev.status,
        last_seen=dev.last_seen,
        simulated=dev.simulated,
    )


@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(device_id: str, db: AsyncSession = Depends(get_session)):
    """Get connectivity and registration status of a sensor device."""
    res = await db.execute(select(Device).where(Device.id == device_id))
    dev = res.scalar_one_or_none()
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")

    return DeviceStatusResponse(
        device_id=dev.id,
        plant_id=dev.plant_id,
        crop_id=dev.crop_id,
        status=dev.status,
        last_seen=dev.last_seen,
        simulated=dev.simulated,
    )


@router.put("/{device_id}/heartbeat")
async def device_heartbeat(device_id: str, db: AsyncSession = Depends(get_session)):
    """Update last-seen timestamp for an active device."""
    res = await db.execute(select(Device).where(Device.id == device_id))
    dev = res.scalar_one_or_none()
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")

    dev.last_seen = datetime.now(timezone.utc)
    dev.status = "online"
    await db.commit()
    return {"status": "ok", "last_seen": dev.last_seen}
