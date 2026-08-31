"""
Model Benchmark Suite: Measures inference latency and memory footprints.
"""

import time
import io
import numpy as np
from PIL import Image
from ml.cv.models.demo import DemoCVModel
from ml.disease_risk.models.random_forest import RandomForestRiskModel


def benchmark_cv_demo():
    print("[Benchmark] Testing Demo CV Inference Latency (100 iterations)...")
    model = DemoCVModel("tomato", [{"id": "tomato_early_blight", "display": "Early Blight"}])
    img = Image.new("RGB", (224, 224), color=(0, 128, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    data = buf.getvalue()

    start = time.perf_counter()
    for _ in range(100):
        model.predict(data)
    elapsed = (time.perf_counter() - start) / 100 * 1000
    print(f"-> Demo CV Model Latency: {elapsed:.3f} ms / image")


def benchmark_disease_risk():
    print("[Benchmark] Testing Multimodal Risk Model Inference Latency (100 iterations)...")
    model = RandomForestRiskModel()
    features = {
        "sensor": {"moisture": 45.0, "ph": 6.2, "temperature": 25.0, "humidity": 65.0},
        "cv": {"disease": "Early Blight", "disease_id": "tomato_early_blight", "confidence": 0.88},
        "thresholds": {},
    }
    start = time.perf_counter()
    for _ in range(100):
        model.predict(features)
    elapsed = (time.perf_counter() - start) / 100 * 1000
    print(f"-> Disease Risk Model Latency: {elapsed:.3f} ms / prediction")


if __name__ == "__main__":
    benchmark_cv_demo()
    benchmark_disease_risk()
