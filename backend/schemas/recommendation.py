from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class RecommendationRequest(BaseModel):
    crop_id: str = Field(..., example="tomato")
    plant_id: str = Field(..., example="plant_01")
    sensor_reading_id: Optional[int] = None
    cv_prediction_id: Optional[int] = None
    risk_prediction_id: Optional[int] = None


class RecommendationResponse(BaseModel):
    id: int
    plant_id: str
    crop_id: str
    summary: str
    contributing_factors: List[str]
    recommended_actions: List[str]
    prevention_steps: List[str]
    monitoring_advice: Optional[str] = None
    urgency: str
    sources: List[Dict[str, Any]]
    llm_provider: str
    llm_model: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
