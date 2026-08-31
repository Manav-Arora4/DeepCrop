from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_async_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if "sqlite" in settings.DATABASE_URL:
            connect_args = {"check_same_thread": False}

        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def init_db():
    """Create all database tables on application startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Import models so Base metadata is populated
        import backend.models.crop  # noqa: F401
        import backend.models.plant  # noqa: F401
        import backend.models.device  # noqa: F401
        import backend.models.sensor_reading  # noqa: F401
        import backend.models.image_prediction  # noqa: F401
        import backend.models.disease_risk_prediction  # noqa: F401
        import backend.models.recommendation  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency yielding an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
