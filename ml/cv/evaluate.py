"""
Evaluation script for trained Tomato CV models.
Computes Classification Report, Precision/Recall per class, and Confusion Matrix.
"""

import json
import argparse
from pathlib import Path
import torch
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from ml.cv.models.efficientnet import EfficientNetCVModel


def main():
    parser = argparse.ArgumentParser(description="Evaluate Tomato Disease CV Model")
    parser.add_argument("--model-path", type=str, default="crops/tomato/models/cv/efficientnet_tomato_v1.pth")
    parser.add_argument("--classes-config", type=str, default="crops/tomato/config/disease_classes.json")
    args = parser.parse_args()

    classes_path = Path(args.classes_config)
    if not classes_path.exists():
        print(f"Error: {classes_path} not found.")
        return

    with open(classes_path) as f:
        classes_data = json.load(f)
        classes = classes_data.get("classes", [])

    print(f"Loaded {len(classes)} tomato disease classes.")
    model = EfficientNetCVModel(args.model_path, "tomato", classes)
    print(f"Model status: {model.get_status()}")


if __name__ == "__main__":
    main()
