from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class PlantCreate(BaseModel):
    id: str = Field(..., example="plant_01")
    crop_id: str = Field(..., example="tomato")
    name: str = Field(..., example="Tomato Bed A1")
    location: Optional[str] = Field(None, example="Greenhouse Section 2")
    growth_stage: Optional[str] = Field(default="vegetative", example="flowering")


class PlantResponse(BaseModel):
    id: str
    crop_id: str
    name: str
    location: Optional[str] = None
    growth_stage: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
