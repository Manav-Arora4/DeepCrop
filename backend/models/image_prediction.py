from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base


class ImagePrediction(Base):
    """Computer Vision leaf disease classification record."""
    __tablename__ = "image_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plant_id: Mapped[str] = mapped_column(String(64), ForeignKey("plants.id"), index=True, nullable=False)
    crop_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)

    disease: Mapped[str] = mapped_column(String(128), nullable=False)
    disease_id: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(64), nullable=True)

    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_status: Mapped[str] = mapped_column(String(32), nullable=False)  # "ready"|"demo"|"unavailable"|"error"
    low_confidence_warning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    sensor_reading_id: Mapped[int | None] = mapped_column(ForeignKey("sensor_readings.id"), nullable=True)
    class_probabilities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
