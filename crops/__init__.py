from pathlib import Path
from typing import Dict, List, Optional
from crops.base import AbstractCropModule


class GenericCropModule(AbstractCropModule):
    """Dynamic concrete implementation for discovered crop directories."""
    def __init__(self, module_dir: Path, crop_id: str):
        super().__init__(module_dir)
        self._crop_id = crop_id

    def get_crop_id(self) -> str:
        return self._crop_id


class CropRegistry:
    """
    Discovers and manages crop modules dynamically from the crops directory.
    """

    def __init__(self, crops_dir: Path | str = "./crops"):
        self.crops_dir = Path(crops_dir)
        self._modules: Dict[str, AbstractCropModule] = {}
        self.discover()

    def discover(self) -> None:
        """Scan subdirectories of crops_dir for valid module.json files."""
        self._modules.clear()
        if not self.crops_dir.exists():
            return

        for sub in self.crops_dir.iterdir():
            if sub.is_dir():
                module_json = sub / "metadata" / "module.json"
                if module_json.exists():
                    crop_id = sub.name.lower()
                    module = GenericCropModule(sub, crop_id)
                    self._modules[crop_id] = module

    def get(self, crop_id: str) -> Optional[AbstractCropModule]:
        return self._modules.get(crop_id.lower())

    def list_all(self) -> List[AbstractCropModule]:
        return list(self._modules.values())

    def list_installed(self) -> List[AbstractCropModule]:
        return [m for m in self._modules.values() if m.is_installed()]

    def get_crop_config(self, crop_id: str) -> Dict:
        """Return merged configuration for a crop."""
        module = self.get(crop_id)
        if not module:
            return {}
        return {
            "module": module.get_config(),
            "thresholds": module.get_thresholds(),
            "disease_classes": module.get_disease_classes(),
            "crop": module.get_crop_config(),
        }
