from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class CropSummary(BaseModel):
    id: str
    name: str
    installed: bool
    version: str
    description: str
    growth_stages: List[str]

    model_config = ConfigDict(from_attributes=True)


class CropDetail(BaseModel):
    id: str
    name: str
    installed: bool
    version: str
    description: str
    growth_stages: List[str]
    thresholds: Optional[Dict[str, Any]] = None
    disease_classes: Optional[List[Dict[str, Any]]] = None
    cv_model_status: str
    risk_model_status: str

    model_config = ConfigDict(from_attributes=True)
