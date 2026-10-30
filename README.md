# Modular Multimodal AI Crop Health & Yield Optimization Platform

> **Final Year AI/ML University Project**  
> A modular, full-stack agricultural AI decision-support platform combining Computer Vision, IoT sensor monitoring, Multimodal Machine Learning, and LLM-powered Retrieval-Augmented Generation (RAG).

---

## 🏛️ System Architecture

```text
                        CROP / PLANT
                              |
              +---------------+---------------+
              |                               |
        Leaf Imagery                     IoT Sensors
   (RGB Smartphone / Camera)      (Moisture, pH, Temp, Humid)
              |                               |
              v                               v
      Computer Vision                   FastAPI REST
     (EfficientNetB0)                 (Ingestion/Validate)
              |                               |
       Disease & Confidence                   |
              |                               |
              +---------------+---------------+
                              |
                              v
                   Multimodal ML Engine
                (Disease-Risk Fusion Model)
                              |
                              v
                  RAG + Ollama LLM Engine
              (Knowledge Grounded Advisory)
                              |
                              v
                    React + Vite Dashboard
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11+** with [uv](https://github.com/astral-sh/uv) or standard `pip`
- **Node.js 20+** with [pnpm](https://pnpm.io) or `npm`
- **Docker** & **Docker Compose**
- **Ollama** installed locally (or running in Docker)

### 2. Environment Setup
```bash
cp .env.example .env
```

### 3. Start Database & Backend
```bash
# Start PostgreSQL via Docker Compose
docker compose up postgres -d

# Start backend using uv
cd backend
uv sync
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start Frontend
```bash
cd frontend
pnpm install
pnpm dev
```

### 5. Local LLM Setup
Ensure Ollama is running and download the model:
```bash
ollama pull mistral
```

---

## 📦 Project Structure

```
FinalYearProject/
├── backend/                  # FastAPI backend application
│   ├── api/                  # REST API routes & dependencies
│   ├── core/                 # Config, Database engine, Logging
│   ├── models/               # SQLAlchemy 2.0 Async ORM models
│   ├── schemas/              # Pydantic v2 schemas
│   ├── services/             # Core service logic (CV, RAG, LLM, Risk, Sensor)
│   ├── migrations/           # Alembic database migrations
│   └── tests/                # Unit and Integration test suite
├── crops/                    # Modular crop definitions
│   ├── base.py               # AbstractCropModule base class
│   ├── __init__.py           # CropRegistry discovery system
│   ├── tomato/               # Fully implemented Tomato module
│   └── onion/                # Stub Onion module (demonstrating modularity)
├── ml/                       # Machine Learning codebase
│   ├── cv/                   # Computer Vision (EfficientNetB0, data loaders, training)
│   ├── disease_risk/         # Multimodal Disease Risk (RF, XGBoost, feature builder)
│   └── yield/                # Future Yield Optimization stub
├── frontend/                 # React 18 + Vite + TypeScript + TailwindCSS
├── esp32/                    # ESP32 Arduino firmware for IoT hardware
├── cad/                      # 3D design of the field unit (STEP, printable STLs, browser viewer)
├── scripts/                  # Seed scripts, data ingestion, benchmarks
└── docs/                     # Academic documentation & architecture guides
```

---

## 🧊 3D Design (CAD)

The `cad/` folder has a 3D model of the finished field unit: the ESP32-S3 case on a stake, the DHT22 shield and the soil probes in a tomato pot. You can view it in a browser without installing CAD software:

- **Printable parts:** click any `.stl` in [`cad/out/print/`](cad/out/print/) on GitHub to rotate it in 3D.
- **Full assembly:** drag `cad/out/field_unit_assembly.step` onto [3dviewer.net](https://3dviewer.net). It's free and needs no account.
- **Interactive viewer with labelled parts:** run this, and it opens in the Helium browser:

```bash
py cad/open_viewer.py
```

[`cad/README.md`](cad/README.md) has the full instructions, including Onshape and how to change the design.

---

## 🔬 Academic & Scientific Rigor

1. **Leakage-Aware Splits**: PlantVillage contains multiple photos of the same physical leaf. `scripts/data/setup_datasets.py` assigns each image its official `leaf_id` from the dataset's `leaf-map.json`, which covers 12,815 of 18,160 tomato images, so splits can be made by leaf instead of by image. See [DATASETS.md](DATASETS.md) for how the remaining unmapped images are handled.
2. **Transparent Model States**: Predictions clearly reflect their status (`ready`, `demo`, `unavailable`, `error`) in all API responses and UI badges.
3. **Data Provenance**: Every sensor reading records its `data_source` (`real`, `simulated`, `manual`) across the entire stack.
4. **Grounded RAG**: Advisory prompts are strictly grounded in agronomic knowledge bases without hallucinating unobserved parameters.
