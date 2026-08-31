import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from backend.schemas.crop import CropSummary, CropDetail


class CropManager:
    """
    Manages crop module discovery, config parsing, and runtime state.
    Scans the crops directory for module.json metadata.
    """

    def __init__(self, crops_dir: str = "./crops"):
        self.crops_dir = Path(crops_dir)
        self._modules: Dict[str, Dict[str, Any]] = {}
        self.discover_modules()

    def discover_modules(self) -> List[Dict[str, Any]]:
        self._modules.clear()
        if not self.crops_dir.exists():
            return []

        for sub in self.crops_dir.iterdir():
            if sub.is_dir():
                module_json = sub / "metadata" / "module.json"
                if module_json.exists():
                    try:
                        with open(module_json, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            self._modules[data["id"]] = data
                    except Exception as e:
                        print(f"[CropManager] Error loading {module_json}: {e}")

        return list(self._modules.values())

    def list_crops(self) -> List[CropSummary]:
        summaries = []
        for data in self._modules.values():
            summaries.append(CropSummary(
                id=data["id"],
                name=data["name"],
                installed=(data.get("status") == "installed"),
                version=data.get("version", "0.1.0"),
                description=data.get("description", ""),
                growth_stages=data.get("growth_stages", []),
            ))
        return summaries

    def get_crop(self, crop_id: str) -> Optional[Dict[str, Any]]:
        return self._modules.get(crop_id.lower())

    def get_crop_detail(self, crop_id: str) -> Optional[CropDetail]:
        data = self.get_crop(crop_id)
        if not data:
            return None

        thresholds = self.get_thresholds(crop_id)
        disease_classes = self.get_disease_classes(crop_id)
        cv_status = data.get("cv_model", {}).get("status", "unavailable")
        risk_status = data.get("disease_risk_model", {}).get("status", "unavailable")

        return CropDetail(
            id=data["id"],
            name=data["name"],
            installed=(data.get("status") == "installed"),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            growth_stages=data.get("growth_stages", []),
            thresholds=thresholds,
            disease_classes=disease_classes,
            cv_model_status=cv_status,
            risk_model_status=risk_status,
        )

    def get_thresholds(self, crop_id: str) -> Optional[Dict[str, Any]]:
        data = self.get_crop(crop_id)
        if not data:
            return None

        t_path = data.get("config", {}).get("thresholds_path")
        if t_path:
            full_path = Path(t_path)
            if not full_path.exists():
                full_path = self.crops_dir / crop_id / "config" / "thresholds.json"
            if full_path.exists():
                with open(full_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        return None

    def get_disease_classes(self, crop_id: str) -> Optional[List[Dict[str, Any]]]:
        data = self.get_crop(crop_id)
        if not data:
            return None

        dc_path = data.get("config", {}).get("disease_classes_path")
        if dc_path:
            full_path = Path(dc_path)
            if not full_path.exists():
                full_path = self.crops_dir / crop_id / "config" / "disease_classes.json"
            if full_path.exists():
                with open(full_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("classes", [])
        return None

    def validate_crop_exists(self, crop_id: str) -> bool:
        return crop_id.lower() in self._modules
