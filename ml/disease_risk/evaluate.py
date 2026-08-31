"""
Evaluation script for trained Disease Risk Models.
"""

import pickle
import argparse
from pathlib import Path
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from ml.disease_risk.train import generate_synthetic_training_data


def main():
    parser = argparse.ArgumentParser(description="Evaluate Disease Risk Models")
    parser.add_argument("--model-path", type=str, default="crops/tomato/models/disease_risk/rf_tomato_v1.pkl")
    args = parser.parse_args()

    model_path = Path(args.model_path)
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        return

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    X_test, y_test = generate_synthetic_training_data(500)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print(f"--- Model Evaluation for {model_path.name} ---")
    print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))


if __name__ == "__main__":
    main()
