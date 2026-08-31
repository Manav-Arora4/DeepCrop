import random
from typing import List, Dict, Any
from ml.cv.models.base import AbstractCVModel, CVPredictionResult, ModelInfo


class DemoCVModel(AbstractCVModel):
    """
    Demo CV Model for development & UI testing before real PyTorch weights are trained.
    Clearly marks model_status='demo' on all outputs.
    """

    def __init__(self, crop_id: str, disease_classes: List[Dict[str, Any]], version: str = "demo_v0.1"):
        self.crop_id = crop_id
        self.disease_classes = disease_classes
        self.version = version

    def predict(self, image_bytes: bytes) -> CVPredictionResult:
        if not self.disease_classes:
            return CVPredictionResult(
                crop=self.crop_id,
                disease="Unknown",
                disease_id="unknown",
                confidence=0.50,
                severity=None,
                model_version=self.version,
                model_status="demo",
                class_probabilities=None,
            )

        # Pick a plausible class
        chosen = random.choice(self.disease_classes)
        if chosen.get("is_healthy", False):
            confidence = round(random.uniform(0.75, 0.96), 4)
        else:
            confidence = round(random.uniform(0.62, 0.91), 4)

        # Generate mock probability distribution
        num_classes = len(self.disease_classes)
        rem_prob = max(0.0, 1.0 - confidence)
        probs = {}
        for c in self.disease_classes:
            if c["id"] == chosen["id"]:
                probs[c["id"]] = confidence
            else:
                probs[c["id"]] = round(rem_prob / (num_classes - 1), 4) if num_classes > 1 else 0.0

        return CVPredictionResult(
            crop=self.crop_id,
            disease=chosen["display"],
            disease_id=chosen["id"],
            confidence=confidence,
            severity=None,
            model_version=self.version,
            model_status="demo",
            class_probabilities=probs,
        )

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=f"Demo {self.crop_id.title()} CV Model",
            version=self.version,
            crop=self.crop_id,
            status="demo",
            classes=[c["display"] for c in self.disease_classes],
            architecture="rule_based_simulator",
        )

    def get_status(self) -> str:
        return "demo"
