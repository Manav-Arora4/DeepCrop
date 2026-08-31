from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base


class Recommendation(Base):
    """RAG + LLM Agronomic Recommendation audit record."""
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plant_id: Mapped[str] = mapped_column(String(64), ForeignKey("plants.id"), index=True, nullable=False)
    crop_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    sensor_reading_id: Mapped[int | None] = mapped_column(ForeignKey("sensor_readings.id"), nullable=True)
    cv_prediction_id: Mapped[int | None] = mapped_column(ForeignKey("image_predictions.id"), nullable=True)
    risk_prediction_id: Mapped[int | None] = mapped_column(ForeignKey("disease_risk_predictions.id"), nullable=True)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    contributing_factors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    recommended_actions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    prevention_steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    monitoring_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)

    sources: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # [{title, topic, relevance}]
    llm_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
