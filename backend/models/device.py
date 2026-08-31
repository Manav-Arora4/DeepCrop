from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base


class Device(Base):
    """IoT hardware device or virtual simulator client."""
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "esp32_001"
    plant_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("plants.id"), nullable=True)
    crop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
