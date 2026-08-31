from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base


class DiseaseRiskPrediction(Base):
    """Multimodal Disease Risk Prediction record."""
    __tablename__ = "disease_risk_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plant_id: Mapped[str] = mapped_column(String(64), ForeignKey("plants.id"), index=True, nullable=False)
    crop_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)  # "low"|"moderate"|"high"|"critical"
    contributing_factors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    cv_prediction_id: Mapped[int | None] = mapped_column(ForeignKey("image_predictions.id"), nullable=True)
    sensor_reading_id: Mapped[int | None] = mapped_column(ForeignKey("sensor_readings.id"), nullable=True)

    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_status: Mapped[str] = mapped_column(String(32), nullable=False)  # "ready"|"demo"
    feature_importances: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
