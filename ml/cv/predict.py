"""
Standalone CLI prediction utility for disease classification.
"""

import sys
import json
import argparse
from pathlib import Path
from ml.cv.models.efficientnet import EfficientNetCVModel
from ml.cv.models.demo import DemoCVModel


def main():
    parser = argparse.ArgumentParser(description="Classify plant disease from leaf image")
    parser.add_argument("image_path", type=str, help="Path to input image file")
    parser.add_argument("--crop", type=str, default="tomato")
    args = parser.parse_args()

    img_path = Path(args.image_path)
    if not img_path.exists():
        print(f"Error: Image not found at {img_path}")
        sys.exit(1)

    classes_file = Path(f"crops/{args.crop}/config/disease_classes.json")
    if not classes_file.exists():
        print(f"Error: Crop config not found for {args.crop}")
        sys.exit(1)

    with open(classes_file) as f:
        classes = json.load(f).get("classes", [])

    # The active model is whatever metadata/module.json's cv_model points to (same as the backend)
    cv_cfg = json.loads(Path(f"crops/{args.crop}/metadata/module.json").read_text()).get("cv_model", {})
    model_pth = Path(cv_cfg.get("path", f"crops/{args.crop}/models/cv/efficientnet_{args.crop}_v1.pth"))
    version = cv_cfg.get("version", "v1.0")
    if model_pth.exists():
        model = EfficientNetCVModel(model_pth, args.crop, classes, version=version)
    else:
        print("[Info] Trained weights not found. Using Demo model simulator.")
        model = DemoCVModel(args.crop, classes)

    with open(img_path, "rb") as f:
        image_bytes = f.read()

    result = model.predict(image_bytes)
    print("\n--- Disease Prediction Result ---")
    print(f"Crop:        {result.crop.title()}")
    print(f"Disease:     {result.disease}")
    print(f"Confidence:  {result.confidence:.2%}")
    print(f"Status:      {result.model_status}")
    print(f"Model Ver:   {result.model_version}")


if __name__ == "__main__":
    main()
