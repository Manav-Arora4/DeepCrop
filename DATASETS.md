# Datasets Guide & Data Provenance

All the datasets the platform uses: where each one comes from, how it is downloaded and checked, its license, and how it may be used for training and testing.

The machine-readable record is [`data/dataset_manifest.json`](data/dataset_manifest.json). The setup script generates it.

---

## Setup

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r scripts/data/requirements.txt
.venv/Scripts/python scripts/data/setup_datasets.py --list
.venv/Scripts/python scripts/data/setup_datasets.py --crop tomato
```

What the script does:
- **Downloads only what the crop needs.** It makes a shallow git clone without file contents, fetches only the selected crop's class folders, and exports them. The full multi-GB repositories are never downloaded.
- **Skips datasets that are already installed.** Use `--force` to re-download, or `--recheck` to rerun the quality checks only.
- **Renames files Windows can't store.** Some PlantDoc filenames contain characters like `?`. The original repository path is kept in the index.

| Output | Tracked in git |
|---|---|
| `data/external/<dataset>/images/` (exported images) | No |
| `data/external/<dataset>/meta/` (license, citation, leaf map) | No |
| `data/processed/<crop>/cv/<dataset>_index.csv` (one row per image: class, `leaf_id`, md5, size, dHash) | No |
| `data/processed/<crop>/cv/quality_report.json` | No |
| `data/dataset_manifest.json` | **Yes** |

---

## 1. PlantVillage — tomato subset (training / validation)

| | |
|---|---|
| **Source** | https://github.com/spMohanty/PlantVillage-Dataset, `raw/color/Tomato___*` |
| **Version** | git commit `7f7ecc7` (2026-02-05) |
| **License** | CC BY-SA 3.0, as stated on the Hugging Face dataset card `mohanty/PlantVillage`. The GitHub repository itself has no LICENSE file. |
| **Citation** | Mohanty, S. P., Hughes, D. P., & Salathé, M. (2016). Using deep learning for image-based plant disease detection. *Frontiers in Plant Science*, 7, 1419. https://doi.org/10.3389/fpls.2016.01419 |
| **Images** | 18,160 lab-condition RGB leaf images, 10 classes, 0 corrupt |
| **Role** | Training and validation for the tomato CV model |

| Class (`disease_classes.json`) | Source folder | Images |
|---|---|---:|
| `tomato_bacterial_spot` | `Tomato___Bacterial_spot` | 2,127 |
| `tomato_early_blight` | `Tomato___Early_blight` | 1,000 |
| `tomato_late_blight` | `Tomato___Late_blight` | 1,909 |
| `tomato_leaf_mold` | `Tomato___Leaf_Mold` | 952 |
| `tomato_septoria_leaf_spot` | `Tomato___Septoria_leaf_spot` | 1,771 |
| `tomato_spider_mites` | `Tomato___Spider_mites Two-spotted_spider_mite` | 1,676 |
| `tomato_target_spot` | `Tomato___Target_Spot` | 1,404 |
| `tomato_yellow_leaf_curl_virus` | `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | 5,357 |
| `tomato_mosaic_virus` | `Tomato___Tomato_mosaic_virus` | 373 |
| `tomato_healthy` | `Tomato___healthy` | 1,591 |

The classes are imbalanced: Yellow Leaf Curl Virus has 14× more images than Mosaic Virus. Report per-class metrics and macro-F1, not just accuracy.

### ⚠️ Leakage-aware splitting with the official leaf map

PlantVillage contains several photos of the same physical leaf. A random image-level split puts the same leaf in both train and test and inflates the metrics.

The repository's `leaf-map.json` assigns each image to a leaf, and the setup script writes this as `leaf_id` in `plantvillage_index.csv`:
- A filename looks like `<uuid>___RS_Erly.B 8389.JPG`.
- The part after `___`, lowercased and without its extension, is the key into `leaf-map.json`.
- The value looks like `"Tomato___Early_blight:::12.0"`, meaning class and leaf number.

| Leaf grouping (tomato) | Images |
|---|---:|
| Mapped to a leaf | 12,815 (3,205 distinct leaves) |
| — of which via filename alias (see below) | 1,404 |
| **Not in the leaf map** | **5,345** |
| Mapped to a different class | 0 |

- **Target Spot alias.** Target Spot files are named `Com.G_TgS_FL 8360.JPG`, while the map uses `com.g_fl 8360`. Dropping `_tgs` matches all 1,404 images one-to-one to the 1,404 Target Spot map entries. The alias is applied only when the direct lookup fails, and the class must still agree.
- **Unmapped images.** These are the Yellow Leaf Curl Virus `UF.GRC_YLCV_Lab` files (2,619), Late Blight `GHLB2` (989), Septoria (771), healthy `GH_HL` (592) and all Mosaic Virus images (373), plus 1 Early Blight.
  - The official map has no entries for them, so each gets its own `leaf_id`. Leakage between photos of the same leaf is therefore **not** prevented for these 29% of images.
  - Phase 3 must deal with this, for example by checking test results on mapped images only, or by grouping unmapped images by near-duplicate similarity. The report must say which approach was used.
- **Leaf numbers are per class.** A leaf number such as `Tomato___Early_blight:::1.0` can combine leaves from different photo batches of the same class. That over-groups images, which is the safe direction for avoiding leakage.

Other quality checks:
- 14 exact duplicate copies and 14 near-duplicate (dHash) groups.
- None of these groups span different leaf IDs or different classes.

## 2. PlantDoc — tomato classes (external test only)

| | |
|---|---|
| **Source** | https://github.com/pratikkayal/PlantDoc-Dataset, `train/Tomato*` and `test/Tomato*` |
| **Version** | git commit `5467f60` (2021-05-02) |
| **License** | CC BY 4.0 (LICENSE.txt in the repository) |
| **Citation** | Singh, D., Jain, N., Jain, P., Kayal, P., Kumawat, S., & Batra, N. (2020). PlantDoc: A Dataset for Visual Plant Disease Detection. *Proc. 7th ACM IKDD CoDS and 25th COMAD*, 249–253. https://doi.org/10.1145/3371158.3371196 |
| **Images** | 746 real-world tomato images (field photos and web images), 0 corrupt |
| **Role** | **External test set only. Never used for training or model selection.** PlantDoc's own train and test folders are both used as one test pool. |

| Class | Source folder | Images |
|---|---|---:|
| `tomato_bacterial_spot` | `Tomato leaf bacterial spot` | 110 |
| `tomato_early_blight` | `Tomato Early blight leaf` | 88 |
| `tomato_late_blight` | `Tomato leaf late blight` | 111 |
| `tomato_leaf_mold` | `Tomato mold leaf` | 91 |
| `tomato_septoria_leaf_spot` | `Tomato Septoria leaf spot` | 151 |
| `tomato_spider_mites` | `Tomato two spotted spider mites leaf` | 2 |
| `tomato_target_spot` | *(no PlantDoc class)* | 0 |
| `tomato_yellow_leaf_curl_virus` | `Tomato leaf yellow virus` | 76 |
| `tomato_mosaic_virus` | `Tomato leaf mosaic virus` | 54 |
| `tomato_healthy` | `Tomato leaf` | 63 |

Notes:
- **Missing and tiny classes.** There is no Target Spot class, and only 2 spider-mite images. Leave Target Spot out of PlantDoc metrics, and don't report a per-class figure for spider mites.
- **Label noise.** 1 exact-duplicate group and 7 near-duplicate groups carry conflicting labels. Fixing them is out of scope, but mention it when you discuss the PlantDoc results.
- **No overlap with PlantVillage.** No image file appears in both datasets (cross-dataset md5 overlap is 0).

## 3. Tomato IoT / environmental data (reference only)

No public tomato sensor dataset is downloaded. These papers are **references** for how environmental disease-risk data can be structured:
- *"Integrating IoT for Soil Monitoring and Hybrid Machine Learning in Predicting Tomato Crop Disease in a Typical South India Station"*: timestamp, NPK, temperature, humidity, pH and disease status. This is the paper named in the project plan. No verified public download is known, so none is listed.
- *"IoT-based real-time tomato plant monitoring system with deep learning"* (PMC11479041): https://pmc.ncbi.nlm.nih.gov/articles/PMC11479041/

If either paper's data becomes legitimately available, add it to the registry in `scripts/data/setup_datasets.py` with its real source and license.

The multimodal disease-risk experiments (Phase 6) use **our own synchronized observations**: images and ESP32 readings of the same plant at the same time, stored under `data/user_collected/tomato/`.

The backend's `SimulationService` produces simulated readings (`data_source: simulated`). They are for testing the software only and must not be used as training or evaluation data for the research question.

**pH readings are uncalibrated.** No buffer calibration is planned, so pH values from the prototype show relative differences only. See `esp32/README.md`.

## 4. Agronomic Knowledge Base (RAG)

- **Location:** `crops/tomato/knowledge/`
- **Content:** curated Markdown notes on the 10 tomato classes, general cultivation and irrigation.
- **Vector storage:** embedded with `BAAI/bge-small-en-v1.5` into the ChromaDB collection `crophealth_tomato`.
- **Sources:** each document must name the real, checkable source it was written from, such as a university extension service, government agricultural department, FAO or peer-reviewed paper. Documents without one should not be used for grounded recommendations. Adding sources to the existing notes is a Phase 7 task.
