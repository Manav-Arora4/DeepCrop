from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional, List, Dict


@dataclass
class CVPredictionResult:
    crop: str
    disease: str                                    # Display name, e.g. "Early Blight"
    disease_id: str                                 # Internal key, e.g. "tomato_early_blight"
    confidence: float                               # 0.0 – 1.0
    severity: Optional[str]                         # "mild" | "moderate" | "severe" | None
    model_version: str
    model_status: str                               # "ready" | "demo" | "unavailable" | "error"
    class_probabilities: Optional[Dict[str, float]] # Map of {disease_id: probability} for multimodal fusion


@dataclass
class ModelInfo:
    name: str
    version: str
    crop: str
    status: str
    classes: List[str]
    architecture: str


class AbstractCVModel(ABC):
    """Abstract interface for all crop disease Computer Vision models."""

    @abstractmethod
    def predict(self, image_bytes: bytes) -> CVPredictionResult:
        """Run disease prediction on raw image bytes."""
        pass

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """Return model metadata."""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Return 'ready' | 'demo' | 'unavailable' | 'error'."""
        pass
