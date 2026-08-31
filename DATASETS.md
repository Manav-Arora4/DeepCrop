# Datasets Guide & Data Provenance

This document outlines all datasets used across the platform, acquisition procedures, and academic data integrity considerations.

---

## 1. PlantVillage Tomato Disease Dataset

- **Source**: `mohanty/PlantVillage` on Hugging Face (or original Penn State / EPFL PlantVillage repository)
- **Modality**: RGB leaf images
- **Classes**: 10 Tomato classes:
  1. `Tomato___Bacterial_spot`
  2. `Tomato___Early_blight`
  3. `Tomato___Late_blight`
  4. `Tomato___Leaf_Mold`
  5. `Tomato___Septoria_leaf_spot`
  6. `Tomato___Spider_mites Two-spotted_spider_mite` *(Note space between mites and Two)*
  7. `Tomato___Target_Spot`
  8. `Tomato___Tomato_Yellow_Leaf_Curl_Virus`
  9. `Tomato___Tomato_mosaic_virus`
  10. `Tomato___healthy`

### ⚠️ Critical Academic Consideration: Leaf ID Group Splitting
PlantVillage contains multiple photograph angles/captures of the exact same leaf. A standard random train/val split leads to significant data leakage (same physical leaf in train and validation sets) and produces inflated evaluation metrics.

Our training script (`ml/cv/train.py` & `ml/cv/data_loader.py`) enforces group splitting based on `leaf_id` derived from image hashes or naming conventions where available.

---

## 2. Tomato IoT Environmental Sensor Dataset

- **Reference Paper**: *"IoT-based real-time tomato plant monitoring system with deep learning"* (PMC11479041)
- **URL**: https://pmc.ncbi.nlm.nih.gov/articles/PMC11479041/
- **Modality**: Time-series sensor data (Soil Moisture, pH, Temperature, Humidity)
- **Status**: Requires manual acquisition / author request if supplementary CSVs are not bundled.
- **Acquisition Procedure**: See `data/raw/tomato_iot/MANUAL_ACQUISITION.md`.
- **Synthetic Simulation**: In absence of physical sensors or private dataset downloads, our built-in `SimulationService` generates physically plausible, evidence-based agricultural sensor streams across 5 test scenarios (`optimal`, `drought`, `overwatered`, `disease_risk`, `random`).

---

## 3. Agronomic Knowledge Base (RAG)

- **Location**: `crops/tomato/knowledge/`
- **Modality**: Curated Markdown documentation across plant pathology, irrigation requirements, growth stages, nutrient requirements, and IPM (Integrated Pest Management).
- **Sources**: FAO, University Extension Services (Cornell, UF/IFAS, UC Davis).
- **Vector Storage**: Ingested via `BAAI/bge-small-en-v1.5` embeddings into ChromaDB collection `crophealth_tomato`.
