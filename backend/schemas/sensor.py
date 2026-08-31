from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Literal
from datetime import datetime


class ThresholdValue(BaseModel):
    value: Optional[float]
    status: Literal["LOW", "OPTIMAL", "HIGH", "UNKNOWN"]
    unit: str


class ThresholdStatus(BaseModel):
    moisture: Optional[ThresholdValue] = None
    ph: Optional[ThresholdValue] = None
    temperature: Optional[ThresholdValue] = None
    humidity: Optional[ThresholdValue] = None


class SensorReadingCreate(BaseModel):
    device_id: str = Field(..., example="esp32_001")
    crop_id: str = Field(..., example="tomato")
    plant_id: str = Field(..., example="plant_01")
    moisture: Optional[float] = Field(None, ge=0.0, le=100.0, example=42.3)
    ph: Optional[float] = Field(None, ge=0.0, le=14.0, example=6.4)
    temperature: Optional[float] = Field(None, ge=-50.0, le=100.0, example=24.5)
    humidity: Optional[float] = Field(None, ge=0.0, le=100.0, example=62.1)
    data_source: Literal["real", "simulated", "manual"] = Field(default="real")
    timestamp: Optional[datetime] = None


class SensorReadingResponse(BaseModel):
    id: int
    device_id: str
    crop_id: str
    plant_id: str
    moisture: Optional[float]
    ph: Optional[float]
    temperature: Optional[float]
    humidity: Optional[float]
    data_source: str
    threshold_status: Dict[str, ThresholdValue]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class SimulationRequest(BaseModel):
    crop_id: str = Field(..., example="tomato")
    plant_id: str = Field(..., example="plant_01")
    scenario: Literal["optimal", "drought", "overwatered", "disease_risk", "random"] = Field(default="optimal")
    count: int = Field(default=1, ge=1, le=100)


class SensorHistoryResponse(BaseModel):
    readings: List[SensorReadingResponse]
    range: str
    count: int
