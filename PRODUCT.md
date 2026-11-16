# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: examiners and the project supervisor.** The student presents the working system, usually from a laptop or projector. They need to see the whole pipeline working and understand it quickly: sensors → leaf-photo AI → disease risk → grounded advice.
- **Secondary (the scenario the system is built for):** a tomato grower checking plant health and getting advice.

## Product Purpose

DeepCrop is a final-year AI/ML university project: a modular multimodal crop-health platform, built for tomato first.

- It combines a leaf-photo disease classifier, ESP32 soil and air sensors, a disease-risk model that fuses both, and an LLM that gives advice grounded in a crop-specific knowledge base (RAG).
- The research question: does fusing photo and sensor data predict disease risk better than either alone?
- Success means examiners see a credible, working end-to-end system, with results that are reported honestly.

## Positioning

Most student projects do one of three things: classify a leaf photo, monitor soil with an ESP32, or wrap a chatbot. DeepCrop does all three, links them on the same plant at the same time, and reports where each part is strong or weak.

## Operating Context

- Demoed live on a laptop or projector, with the backend and dashboard running locally (FastAPI + Postgres + React/Vite).
- One physical sensor node exists: an ESP32-S3 in a 3D-printable case on a stake, with a DHT22, a resistive soil-moisture probe and an uncalibrated pH probe.
- The CAD model of this node lives in `cad/`.
- Sensor data may be real (`real`), simulated (`simulated`) or manual (`manual`).

## Capabilities and Constraints

- **Leaf-photo model:** `tomato_cv_v2.0` (EfficientNet-B0), 10 tomato classes.
  - 99.5% accuracy on PlantVillage lab photos.
  - 63.3% on real-world PlantDoc photos (95% CI 56–70%).
  - Its weak field classes are Bacterial Spot, Early Blight and Mosaic Virus.
- **Disease-risk model:** a synthetic demo only, until real paired data arrives (Phase 6). Never present its outputs as research results.
- **pH:** uncalibrated, relative only. Show it as such, and never as absolute soil pH.
- **Labels:**
  - Every prediction shows its model status (`ready`, `demo`, `unavailable`, `error`).
  - Every reading shows its data source.
  - Simulated or synthetic data must always be labelled.
- **Modular crops:** Tomato is active, and Onion is a stub that demonstrates modularity.

## Brand Commitments

- Name in the UI: currently "AgriHealth AI" in the frontend, and "DeepCrop" in the repository and CAD. Undecided which one to keep.
- The user supplied two visual references for the dashboard (a light greenhouse-monitoring dashboard and a mint eco-score dashboard). These belong to the design phase, not this file.

## Evidence on Hand

- **Model metrics:** `docs/results/cv_tomato_comparison.md`, `docs/results/cv_tomato_v2.md`, and confusion matrices in `docs/results/`.
- **Dataset provenance:** `DATASETS.md`, `data/dataset_manifest.json`.
- **3D field-unit model:** `cad/out/` (STEP, STL, viewer meshes), `cad/viewer.html`.
- **Roadmap:** `docs/ROADMAP.md`.
- **Not available yet:** real paired field data, a real disease-risk model, and live ESP32 data. Don't fabricate any of them.

## Product Principles

1. **Show the pipeline, not just the parts.** Every screen should make clear where a number came from and what it feeds next.
2. **Honest labels beat impressive numbers.** Model status, data source, uncertainty and known weaknesses are always visible.
3. **A demo should work cold.** Empty states explain how to get data in, and nothing breaks when the backend has no data yet.
4. **The physical device is real.** The sensor node and its readings are central, not decoration.
