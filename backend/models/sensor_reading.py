from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base


class SensorReading(Base):
    """Environmental IoT sensor reading with explicit data provenance."""
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    crop_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    plant_id: Mapped[str] = mapped_column(String(64), ForeignKey("plants.id"), index=True, nullable=False)

    moisture: Mapped[float | None] = mapped_column(Float, nullable=True)
    ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Academic Provenance: "real" | "simulated" | "manual"
    data_source: Mapped[str] = mapped_column(String(32), default="real", nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_notes: Mapped[str | None] = mapped_column(String(256), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
