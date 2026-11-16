"""
Tomato leaf image datasets for CV training and evaluation.

Samples come from the index files written by scripts/data/setup_datasets.py and
the leakage-aware splits written by ml/cv/splits.py:
  data/processed/tomato/cv/splits.csv          PlantVillage train / val / test
  data/processed/tomato/cv/plantdoc_index.csv  PlantDoc external test (never trained on)
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

SPLITS_CSV = Path("data/processed/tomato/cv/splits.csv")
PLANTDOC_INDEX = Path("data/processed/tomato/cv/plantdoc_index.csv")


def load_split(split: str, splits_csv: Path = SPLITS_CSV) -> List[Dict[str, Any]]:
    """Return PlantVillage samples for 'train', 'val' or 'test'."""
    if not splits_csv.exists():
        raise FileNotFoundError(f"{splits_csv} not found. Run: python -m ml.cv.splits")
    with open(splits_csv, encoding="utf-8") as f:
        return [
            {"path": r["path"], "label": int(r["class_index"]), "class_id": r["class_id"],
             "group": r["group"], "leaf_mapped": r["leaf_mapped"] == "1"}
            for r in csv.DictReader(f) if r["split"] == split
        ]


def load_plantdoc(index_csv: Path = PLANTDOC_INDEX) -> List[Dict[str, Any]]:
    """Return PlantDoc tomato samples (external, real-world test set)."""
    with open(index_csv, encoding="utf-8") as f:
        return [{"path": r["path"], "label": int(r["class_index"]), "class_id": r["class_id"]}
                for r in csv.DictReader(f)]


class LeafImageDataset(Dataset):
    """PyTorch Dataset over index samples; returns (image_tensor, label, index)."""

    def __init__(self, samples: List[Dict[str, Any]], transform: Optional[transforms.Compose] = None):
        self.samples = samples
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, int]:
        item = self.samples[idx]
        image = Image.open(item["path"]).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, item["label"], idx


def get_data_transforms(image_size: int = 224) -> Tuple[transforms.Compose, transforms.Compose]:
    """Return training (with augmentation) and evaluation transforms."""
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(image_size, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.02),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # Must match the inference transform in ml/cv/models/efficientnet.py
    val_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    return train_transform, val_transform
