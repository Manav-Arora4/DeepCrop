import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from ml.cv.models.base import AbstractCVModel, CVPredictionResult, ModelInfo


class EfficientNetCVModel(AbstractCVModel):
    """
    Production PyTorch EfficientNetB0 CV Model.
    Loads trained weights from .pth file and runs real inference.
    """

    def __init__(self, model_path: Path | str, crop_id: str, disease_classes: List[Dict[str, Any]], version: str = "v1.0.0"):
        self.model_path = Path(model_path)
        self.crop_id = crop_id
        self.disease_classes = disease_classes
        self.version = version
        self._model = None
        self._transform = None
        self._status = "ready" if self.model_path.exists() else "unavailable"

    def _load_model(self):
        if self._model is not None:
            return

        try:
            import torch
            from torchvision import transforms, models
            from PIL import Image

            num_classes = len(self.disease_classes)
            model = models.efficientnet_b0(weights=None)
            in_features = model.classifier[1].in_features
            model.classifier[1] = torch.nn.Linear(in_features, num_classes)

            state_dict = torch.load(self.model_path, map_location="cpu")
            model.load_state_dict(state_dict)
            model.eval()
            self._model = model

            self._transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            self._status = "ready"
        except Exception as e:
            self._status = "error"
            raise RuntimeError(f"Failed to load EfficientNet model from {self.model_path}: {e}")

    def predict(self, image_bytes: bytes) -> CVPredictionResult:
        if self._status != "ready" and not self.model_path.exists():
            return CVPredictionResult(
                crop=self.crop_id,
                disease="Model Weights Missing",
                disease_id="unavailable",
                confidence=0.0,
                severity=None,
                model_version=self.version,
                model_status="unavailable",
                class_probabilities=None,
            )

        try:
            import torch
            from PIL import Image

            self._load_model()
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            tensor = self._transform(img).unsqueeze(0)

            with torch.no_grad():
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=1)[0].numpy()

            pred_idx = int(probs.argmax())
            confidence = float(probs[pred_idx])
            pred_class = self.disease_classes[pred_idx]

            class_probs = {
                self.disease_classes[i]["id"]: float(probs[i])
                for i in range(len(self.disease_classes))
            }

            return CVPredictionResult(
                crop=self.crop_id,
                disease=pred_class["display"],
                disease_id=pred_class["id"],
                confidence=round(confidence, 4),
                severity=None,
                model_version=self.version,
                model_status="ready",
                class_probabilities=class_probs,
            )
        except Exception as e:
            return CVPredictionResult(
                crop=self.crop_id,
                disease=f"Inference Error: {str(e)}",
                disease_id="error",
                confidence=0.0,
                severity=None,
                model_version=self.version,
                model_status="error",
                class_probabilities=None,
            )

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=f"EfficientNetB0 {self.crop_id.title()} Disease Classifier",
            version=self.version,
            crop=self.crop_id,
            status=self._status,
            classes=[c["display"] for c in self.disease_classes],
            architecture="efficientnet_b0",
        )

    def get_status(self) -> str:
        return self._status
