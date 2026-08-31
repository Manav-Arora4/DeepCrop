from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import get_settings
from backend.core.database import init_db
from backend.core.logging import logger
from backend.services.crop_manager import CropManager
from backend.services.rag_service import get_rag_service
from backend.api.routes import (
    crops,
    plants,
    devices,
    sensors,
    cv,
    disease_risk,
    rag,
    recommendations,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Lifecycle ---
    settings = get_settings()
    logger.info("Initializing Modular Agricultural AI Decision-Support Platform...")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER.upper()} | Model: {settings.OLLAMA_MODEL if settings.LLM_PROVIDER=='ollama' else settings.DEEPSEEK_MODEL}")

    # Ensure directories exist
    upload_dir = Path(settings.UPLOADS_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir = Path(settings.CHROMA_PERSIST_PATH)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Database Schema
    await init_db()
    logger.info("Database initialized successfully.")

    # Auto-discover crops
    crop_manager = CropManager(crops_dir=settings.CROPS_DIRECTORY)
    discovered = crop_manager.discover_modules()
    logger.info(f"Discovered {len(discovered)} crop modules: {[c['id'] for c in discovered]}")

    # Auto-seed default demo plant for immediate UI operability
    try:
        from backend.core.database import get_session_factory
        from backend.models.crop import CropModule
        from backend.models.plant import Plant
        from sqlalchemy import select

        factory = get_session_factory()
        async with factory() as session:
            # Seed Tomato crop in DB if not present
            c_res = await session.execute(select(CropModule).where(CropModule.id == "tomato"))
            if not c_res.scalar_one_or_none():
                session.add(CropModule(
                    id="tomato",
                    name="Tomato",
                    version="1.0.0",
                    description="Solanum lycopersicum module",
                    installed=True,
                    module_path="crops/tomato",
                    extra_metadata={},
                ))
            # Seed Plant_01
            p_res = await session.execute(select(Plant).where(Plant.id == "plant_01"))
            if not p_res.scalar_one_or_none():
                session.add(Plant(
                    id="plant_01",
                    crop_id="tomato",
                    name="Research Plot Tomato Alpha",
                    location="Greenhouse Zone 1",
                    growth_stage="flowering",
                ))
            await session.commit()
            logger.info("Default plant 'plant_01' (Tomato) verified.")
    except Exception as e:
        logger.warning(f"Default seed note: {e}")

    yield

    # --- Shutdown Lifecycle ---
    logger.info("Shutting down Crop Health Platform API.")


settings = get_settings()

app = FastAPI(
    title="Modular Multimodal Crop Health & Yield Platform API",
    description="Full-stack AI platform combining Computer Vision, IoT sensors, Multimodal Risk ML, and RAG Advisory.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(crops.router)
app.include_router(plants.router)
app.include_router(devices.router)
app.include_router(sensors.router)
app.include_router(cv.router)
app.include_router(disease_risk.router)
app.include_router(rag.router)
app.include_router(recommendations.router)


@app.get("/health", tags=["System"])
async def health_check():
    """System health check probe."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "llm_provider": settings.LLM_PROVIDER,
        "simulation_mode": settings.SIMULATION_MODE,
    }
