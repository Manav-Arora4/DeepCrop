from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.schemas.crop import CropSummary, CropDetail
from backend.models.crop import CropModule
from backend.api.deps import get_crop_manager, get_session
from backend.services.crop_manager import CropManager

router = APIRouter(prefix="/crops", tags=["Crops"])


@router.get("", response_model=List[CropSummary])
async def list_crops(manager: CropManager = Depends(get_crop_manager)):
    """List all available crop modules (installed and stubs)."""
    return manager.list_crops()


@router.get("/{crop_id}", response_model=CropDetail)
async def get_crop(crop_id: str, manager: CropManager = Depends(get_crop_manager)):
    """Get full details, growth stages, thresholds, and disease classes for a crop."""
    detail = manager.get_crop_detail(crop_id)
    if not detail:
        raise HTTPException(
            status_code=404,
            detail=f"Crop module '{crop_id}' not found.",
        )
    return detail


@router.post("/{crop_id}/install")
async def install_crop(
    crop_id: str,
    db: AsyncSession = Depends(get_session),
    manager: CropManager = Depends(get_crop_manager),
):
    """Register or mark a crop module as installed."""
    crop_data = manager.get_crop(crop_id)
    if not crop_data:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_id}' module not found on disk.")

    res = await db.execute(select(CropModule).where(CropModule.id == crop_id))
    existing = res.scalar_one_or_none()

    if existing:
        existing.installed = True
    else:
        new_module = CropModule(
            id=crop_id,
            name=crop_data["name"],
            version=crop_data.get("version", "1.0.0"),
            description=crop_data.get("description", ""),
            installed=True,
            module_path=f"crops/{crop_id}",
            extra_metadata=crop_data,
        )
        db.add(new_module)

    await db.commit()
    return {"status": "success", "message": f"Crop '{crop_id}' successfully installed"}
