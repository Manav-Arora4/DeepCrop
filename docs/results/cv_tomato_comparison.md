# Tomato CV model comparison

Same held-out test sets for every version (fixed seeds in `ml/cv/splits.py`).

| Version | Training data | PlantVillage test acc | PlantVillage macro-F1 | PlantDoc test acc (95% CI) | PlantDoc macro-F1 |
|---|---|---:|---:|---:|---:|
| tomato_cv_v1.0 | PlantVillage | 99.6% | 0.994 | 27.1% (21.3%–33.9%) | 0.154 |
| tomato_cv_v2.0 | PlantVillage + PlantDoc train, field aug | 99.5% | 0.993 | 63.3% (56.2%–69.9%) | 0.666 |

Per-version detail: [v1](cv_tomato_v1.md), [v2](cv_tomato_v2.md).