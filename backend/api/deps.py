from functools import lru_cache
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_db
from backend.core.config import get_settings
from backend.services.crop_manager import CropManager
from backend.services.rag_service import get_rag_service, RAGService


async def get_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    return db


@lru_cache(maxsize=1)
def get_crop_manager() -> CropManager:
    settings = get_settings()
    return CropManager(crops_dir=settings.CROPS_DIRECTORY)


def get_rag() -> RAGService:
    return get_rag_service()
