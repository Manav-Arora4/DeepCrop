import pytest
from pathlib import Path
from backend.services.crop_manager import CropManager


def test_crop_manager_discovery():
    manager = CropManager(crops_dir="./crops")
    crops = manager.list_crops()
    crop_ids = [c.id for c in crops]

    assert "tomato" in crop_ids
    assert "onion" in crop_ids

    tomato_detail = manager.get_crop_detail("tomato")
    assert tomato_detail is not None
    assert tomato_detail.installed is True
    assert len(tomato_detail.disease_classes) == 10
    assert tomato_detail.thresholds is not None
    assert "moisture" in tomato_detail.thresholds
