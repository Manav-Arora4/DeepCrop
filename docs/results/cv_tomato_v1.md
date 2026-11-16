# Tomato CV model results: tomato_cv_v1.0

EfficientNet-B0 fine-tuned on 12,968 PlantVillage tomato images (14 epochs to best validation macro-F1 0.997), trained 2026-11-16 on NVIDIA GeForce RTX 4060 Laptop GPU in 7.6 min, code commit `9e52ca7`.

## Summary

| Test set | Images | Accuracy | Macro-F1 |
|---|---:|---:|---:|
| PlantVillage test (all) | 2,594 | 99.6% | 0.994 |
| PlantVillage test (leaf-map verified) | 1,832 | 99.5% | 0.994 |
| PlantDoc (real-world, external) | 746 | 28.7% | 0.169 |

## How to read these numbers

- **Splits are grouped:**
  - Every photo of the same leaf (from PlantVillage's official leaf map) stays in one split.
  - So does every near-duplicate photo.
  - See `ml/cv/splits.py`.
- **29% of PlantVillage images have no leaf-map entry.** This covers all Mosaic Virus images and about half of Yellow Leaf Curl and Late Blight.
  - For those images, different photos of the same leaf can still land in both train and test.
  - So the *all* score may be slightly optimistic.
  - The *leaf-map verified* row only counts test images whose leaf is known.
- **PlantDoc is the honest real-world number.**
  - Its images are field photos with backgrounds, lighting changes and several leaves per photo, and the model never saw them in training.
  - A large drop from PlantVillage is expected, and is widely reported in the literature.
  - PlantDoc has no Target Spot images and only 2 Spider Mite images.

## PlantVillage test (all)

![Confusion matrix](cv_tomato_v1_plantvillage_test_confusion.png)

| Class | Precision | Recall | F1 | Images |
|---|---:|---:|---:|---:|
| bacterial_spot | 1.000 | 1.000 | 1.000 | 304 |
| early_blight | 0.978 | 0.964 | 0.971 | 140 |
| late_blight | 0.986 | 0.993 | 0.989 | 273 |
| leaf_mold | 1.000 | 1.000 | 1.000 | 136 |
| septoria_leaf_spot | 1.000 | 1.000 | 1.000 | 253 |
| spider_mites | 1.000 | 0.992 | 0.996 | 240 |
| target_spot | 0.990 | 0.995 | 0.993 | 200 |
| yellow_leaf_curl_virus | 0.999 | 1.000 | 0.999 | 766 |
| mosaic_virus | 1.000 | 1.000 | 1.000 | 54 |
| healthy | 0.996 | 0.996 | 0.996 | 228 |

## PlantVillage test (leaf-map verified)

![Confusion matrix](cv_tomato_v1_plantvillage_test_mapped_confusion.png)

| Class | Precision | Recall | F1 | Images |
|---|---:|---:|---:|---:|
| bacterial_spot | 1.000 | 1.000 | 1.000 | 304 |
| early_blight | 0.985 | 0.964 | 0.975 | 140 |
| late_blight | 0.970 | 0.992 | 0.981 | 132 |
| leaf_mold | 1.000 | 1.000 | 1.000 | 136 |
| septoria_leaf_spot | 1.000 | 1.000 | 1.000 | 144 |
| spider_mites | 1.000 | 0.992 | 0.996 | 240 |
| target_spot | 0.990 | 0.995 | 0.993 | 200 |
| yellow_leaf_curl_virus | 0.998 | 1.000 | 0.999 | 392 |
| healthy | 1.000 | 1.000 | 1.000 | 144 |

## PlantDoc (real-world, external)

![Confusion matrix](cv_tomato_v1_plantdoc_confusion.png)

| Class | Precision | Recall | F1 | Images |
|---|---:|---:|---:|---:|
| bacterial_spot | 0.000 | 0.000 | 0.000 | 110 |
| early_blight | 0.189 | 0.864 | 0.310 | 88 |
| late_blight | 0.360 | 0.577 | 0.443 | 111 |
| leaf_mold | 0.222 | 0.022 | 0.040 | 91 |
| septoria_leaf_spot | 0.463 | 0.371 | 0.412 | 151 |
| spider_mites | 0.000 | 0.000 | 0.000 | 2 |
| yellow_leaf_curl_virus | 0.469 | 0.197 | 0.278 | 76 |
| mosaic_virus | 1.000 | 0.018 | 0.036 | 54 |
| healthy | 0.000 | 0.000 | 0.000 | 63 |
