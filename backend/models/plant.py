from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base


class Plant(Base):
    """Monitored individual plant or crop zone."""
    __tablename__ = "plants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "plant_01"
    crop_id: Mapped[str] = mapped_column(String(64), ForeignKey("crop_modules.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    growth_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. "flowering"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
