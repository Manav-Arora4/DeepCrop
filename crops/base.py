from abc import ABC, abstractmethod
from pathlib import Path
import json
from typing import Optional, List, Dict, Any


class AbstractCropModule(ABC):
    """
    Abstract base class for all crop modules.
    Each crop module is self-contained in crops/<crop_id>/ and discovered by CropRegistry.
    """

    def __init__(self, module_dir: Path):
        self.module_dir = Path(module_dir)
        self._module_json: Optional[Dict[str, Any]] = None
        self._thresholds: Optional[Dict[str, Any]] = None
        self._disease_classes: Optional[Dict[str, Any]] = None
        self._crop_config: Optional[Dict[str, Any]] = None

    @abstractmethod
    def get_crop_id(self) -> str:
        """Unique lowercase crop identifier (e.g. 'tomato', 'onion')."""
        pass

    def get_config(self) -> Dict[str, Any]:
        """Load and return module.json metadata."""
        if self._module_json is None:
            module_file = self.module_dir / "metadata" / "module.json"
            if module_file.exists():
                with open(module_file, "r", encoding="utf-8") as f:
                    self._module_json = json.load(f)
            else:
                self._module_json = {}
        return self._module_json

    def get_thresholds(self) -> Dict[str, Any]:
        """Load and return thresholds.json."""
        if self._thresholds is None:
            thresh_path = self.get_config().get("config", {}).get("thresholds_path")
            if thresh_path:
                full_path = self.module_dir.parent.parent / thresh_path
                if not full_path.exists():
                    full_path = self.module_dir / "config" / "thresholds.json"
                if full_path.exists():
                    with open(full_path, "r", encoding="utf-8") as f:
                        self._thresholds = json.load(f)
                else:
                    self._thresholds = {}
            else:
                self._thresholds = {}
        return self._thresholds

    def get_disease_classes(self) -> List[Dict[str, Any]]:
        """Load and return disease_classes.json classes list."""
        if self._disease_classes is None:
            dc_path = self.get_config().get("config", {}).get("disease_classes_path")
            if dc_path:
                full_path = self.module_dir.parent.parent / dc_path
                if not full_path.exists():
                    full_path = self.module_dir / "config" / "disease_classes.json"
                if full_path.exists():
                    with open(full_path, "r", encoding="utf-8") as f:
                        self._disease_classes = json.load(f)
                else:
                    self._disease_classes = {"classes": []}
            else:
                self._disease_classes = {"classes": []}
        return self._disease_classes.get("classes", [])

    def get_crop_config(self) -> Dict[str, Any]:
        """Load and return crop.json agronomic data."""
        if self._crop_config is None:
            cfg_path = self.get_config().get("config", {}).get("crop_config_path")
            if cfg_path:
                full_path = self.module_dir.parent.parent / cfg_path
                if not full_path.exists():
                    full_path = self.module_dir / "config" / "crop.json"
                if full_path.exists():
                    with open(full_path, "r", encoding="utf-8") as f:
                        self._crop_config = json.load(f)
                else:
                    self._crop_config = {}
            else:
                self._crop_config = {}
        return self._crop_config

    def get_cv_model_path(self) -> Optional[Path]:
        """Return Path to CV model .pth file, or None if missing."""
        cfg = self.get_config().get("cv_model", {})
        rel_path = cfg.get("path")
        if rel_path:
            full = self.module_dir.parent.parent / rel_path
            if full.exists():
                return full
        return None

    def get_risk_model_path(self) -> Optional[Path]:
        """Return Path to risk model .pkl file, or None if missing."""
        cfg = self.get_config().get("disease_risk_model", {})
        rel_path = cfg.get("path")
        if rel_path:
            full = self.module_dir.parent.parent / rel_path
            if full.exists():
                return full
        return None

    def get_knowledge_path(self) -> Path:
        """Return Path to knowledge/ directory."""
        return self.module_dir / "knowledge"

    def is_installed(self) -> bool:
        """Return True if module status is 'installed'."""
        return self.get_config().get("status") == "installed"

    def validate(self) -> List[str]:
        """Return list of validation errors (empty if valid)."""
        errors = []
        if not (self.module_dir / "metadata" / "module.json").exists():
            errors.append(f"Missing module.json in {self.module_dir}")
        if not (self.module_dir / "config" / "thresholds.json").exists():
            errors.append(f"Missing thresholds.json in {self.module_dir}")
        if not (self.module_dir / "config" / "disease_classes.json").exists():
            errors.append(f"Missing disease_classes.json in {self.module_dir}")
        return errors
