from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class DeviceRegister(BaseModel):
    device_id: str = Field(..., example="esp32_001")
    plant_id: Optional[str] = Field(None, example="plant_01")
    crop_id: str = Field(..., example="tomato")
    simulated: bool = Field(default=False)


class DeviceStatusResponse(BaseModel):
    device_id: str
    plant_id: Optional[str] = None
    crop_id: str
    status: str
    last_seen: Optional[datetime] = None
    simulated: bool

    model_config = ConfigDict(from_attributes=True)
