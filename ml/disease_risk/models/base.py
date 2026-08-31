from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


@dataclass
class DiseaseRiskResult:
    risk_score: float                              # 0.0 – 1.0 continuous risk score
    risk_level: str                                # "low" | "moderate" | "high" | "critical"
    contributing_factors: List[str]                # Human-interpretable factors
    model_version: str
    model_status: str                              # "ready" | "demo"
    feature_importances: Optional[Dict[str, float]] # Feature attribution for dissertation / XAI


class AbstractDiseaseRiskModel(ABC):
    """Abstract interface for Multimodal Disease Risk Prediction models."""

    @abstractmethod
    def predict(self, features: Dict[str, Any]) -> DiseaseRiskResult:
        """
        Run inference on multimodal feature dictionary containing:
        - moisture, ph, temperature, humidity
        - cv_disease_confidence, cv_disease_is_healthy
        - growth_stage, historical trends
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        pass
