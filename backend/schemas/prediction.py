from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Literal
from datetime import datetime


class CVPredictionResponse(BaseModel):
    id: int
    crop: str
    disease: str
    disease_id: str
    confidence: float
    severity: Optional[str] = None
    model_version: str
    model_status: Literal["ready", "demo", "unavailable", "error"]
    low_confidence_warning: bool
    plant_id: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class DiseaseRiskRequest(BaseModel):
    crop_id: str = Field(..., example="tomato")
    plant_id: str = Field(..., example="plant_01")
    sensor_reading_id: Optional[int] = None
    cv_prediction_id: Optional[int] = None


class DiseaseRiskResponse(BaseModel):
    id: int
    crop_id: str
    plant_id: str
    risk_score: float
    risk_level: Literal["low", "moderate", "high", "critical", "unknown"]
    contributing_factors: List[str]
    model_version: str
    model_status: Literal["ready", "demo"]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
