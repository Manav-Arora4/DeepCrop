from fastapi import APIRouter, Depends, HTTPException, Query
from pathlib import Path

from backend.api.deps import get_rag, get_crop_manager
from backend.services.rag_service import RAGService
from backend.services.crop_manager import CropManager
from backend.core.config import get_settings

router = APIRouter(prefix="/rag", tags=["RAG & Knowledge Base"])


@router.post("/ingest/{crop_id}")
async def ingest_crop_knowledge(
    crop_id: str,
    force: bool = Query(default=False),
    rag: RAGService = Depends(get_rag),
    manager: CropManager = Depends(get_crop_manager),
):
    """Trigger ingestion of a crop's Markdown knowledge base into ChromaDB."""
    crop_data = manager.get_crop(crop_id)
    if not crop_data:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_id}' not found.")

    settings = get_settings()
    k_path = Path(settings.CROPS_DIRECTORY) / crop_id / "knowledge"
    if not k_path.exists():
        raise HTTPException(status_code=404, detail=f"Knowledge directory missing for '{crop_id}'.")

    count = await rag.ingest_crop_knowledge(crop_id, k_path, force=force)
    return {
        "status": "success",
        "crop_id": crop_id,
        "chunks_indexed": count,
    }


@router.get("/status/{crop_id}")
async def get_rag_status(
    crop_id: str,
    rag: RAGService = Depends(get_rag),
):
    """Check ChromaDB indexing stats for a crop module."""
    return rag.get_collection_stats(crop_id)
