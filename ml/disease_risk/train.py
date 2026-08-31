"""
Training pipeline for Multimodal Disease Risk Models (Random Forest & XGBoost).
"""

import pickle
import argparse
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score


def generate_synthetic_training_data(n_samples: int = 2000):
    """
    Generates synthetic agricultural multimodal feature dataset based on domain logic.
    Used to pretrain the baseline models before real IoT field deployments.
    """
    np.random.seed(42)
    moisture = np.random.uniform(10, 90, n_samples)
    ph = np.random.uniform(4.5, 8.5, n_samples)
    temp = np.random.uniform(8, 40, n_samples)
    humidity = np.random.uniform(20, 95, n_samples)
    cv_conf = np.random.uniform(0.5, 0.99, n_samples)
    cv_is_disease = np.random.choice([0.0, 1.0], size=n_samples, p=[0.4, 0.6])

    moisture_stress = np.maximum(0, 30 - moisture) + np.maximum(0, moisture - 70)
    temp_stress = np.maximum(0, 10 - temp) + np.maximum(0, temp - 30)
    es = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (humidity / 100.0)
    vpd = es - ea

    X = np.column_stack([
        moisture, ph, temp, humidity, cv_conf, cv_is_disease, moisture_stress, temp_stress, vpd
    ])

    # Probability of disease risk based on domain formulas
    logit = (
        0.05 * (humidity - 60)
        + 0.08 * temp_stress
        + 0.06 * moisture_stress
        + 1.5 * cv_is_disease * cv_conf
        + 0.1 * np.abs(ph - 6.5) * 10
        - 2.0
    )
    probs = 1.0 / (1.0 + np.exp(-logit))
    y = (probs > 0.5).astype(int)

    return X, y


def main():
    parser = argparse.ArgumentParser(description="Train Multimodal Disease Risk Model")
    parser.add_argument("--algorithm", choices=["rf", "xgb", "both"], default="both")
    parser.add_argument("--output-dir", type=str, default="crops/tomato/models/disease_risk")
    args = parser.parse_args()

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("[DiseaseRisk] Generating synthetic domain dataset (2,000 samples)...")
    X, y = generate_synthetic_training_data(2000)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    if args.algorithm in ("rf", "both"):
        print("[DiseaseRisk] Training Random Forest Classifier...")
        rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        rf.fit(X_train, y_train)
        y_pred = rf.predict(X_test)
        auc = roc_auc_score(y_test, rf.predict_proba(X_test)[:, 1])
        print(f"[RandomForest] Test ROC-AUC: {auc:.4f}")
        print(classification_report(y_test, y_pred))

        rf_path = out_path / "rf_tomato_v1.pkl"
        with open(rf_path, "wb") as f:
            pickle.dump(rf, f)
        print(f"[RandomForest] Saved model to {rf_path}")

    if args.algorithm in ("xgb", "both"):
        try:
            import xgboost as xgb
            print("[DiseaseRisk] Training XGBoost Classifier...")
            model_xgb = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)
            model_xgb.fit(X_train, y_train)
            auc = roc_auc_score(y_test, model_xgb.predict_proba(X_test)[:, 1])
            print(f"[XGBoost] Test ROC-AUC: {auc:.4f}")

            xgb_path = out_path / "xgb_tomato_v1.pkl"
            with open(xgb_path, "wb") as f:
                pickle.dump(model_xgb, f)
            print(f"[XGBoost] Saved model to {xgb_path}")
        except ImportError:
            print("[DiseaseRisk] xgboost not installed. Skipping XGBoost training.")


if __name__ == "__main__":
    main()
