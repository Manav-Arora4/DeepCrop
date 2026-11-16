"""
Evaluate the trained tomato CV model on held-out data.

Test sets:
  plantvillage_test          PlantVillage test split (lab photos, same source as training)
  plantvillage_test_mapped   the part of that split with an official leaf-map entry (strictest
                             leakage control; has no Mosaic Virus, whose images are all unmapped)
  plantdoc                   PlantDoc tomato images (real-world photos, never trained on)

Writes crops/tomato/models/cv/metrics_v1.json, plus a markdown report and
confusion-matrix images in docs/results/.

Run:  python -m ml.cv.evaluate
"""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader

from ml.cv.data_loader import LeafImageDataset, get_data_transforms, load_plantdoc, load_split
from ml.cv.models.efficientnet import build_efficientnet_b0

CLASSES_CONFIG = Path("crops/tomato/config/disease_classes.json")


def predict(model, samples, device, batch_size=64):
    _, tf = get_data_transforms()
    loader = DataLoader(LeafImageDataset(samples, tf), batch_size=batch_size, num_workers=4)
    preds = []
    model.eval()
    with torch.no_grad():
        for images, _, _ in loader:
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                preds.append(model(images.to(device)).argmax(1).cpu())
    return torch.cat(preds).numpy()


def score(y_true, y_pred, class_ids):
    present = sorted(set(y_true))
    report = classification_report(y_true, y_pred, labels=present, target_names=[class_ids[i] for i in present],
                                   output_dict=True, zero_division=0)
    return {
        "images": int(len(y_true)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)), 4),
        "classes_present": [class_ids[i] for i in present],
        "per_class": {class_ids[i]: {k: round(v, 4) if isinstance(v, float) else v
                                     for k, v in report[class_ids[i]].items()} for i in present},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(range(len(class_ids)))).tolist(),
    }


def plot_confusion(cm, class_names, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cm = np.array(cm)
    rows = cm.sum(1, keepdims=True)
    norm = np.divide(cm, rows, out=np.zeros_like(cm, dtype=float), where=rows > 0)
    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    ax.imshow(norm, cmap="Greens", vmin=0, vmax=1)
    ax.set_xticks(range(len(class_names)), class_names, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(class_names)), class_names, fontsize=8)
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=7,
                        color="white" if norm[i, j] > 0.5 else "black")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_report(metrics, card, path):
    names = {"plantvillage_test": "PlantVillage test (all)",
             "plantvillage_test_mapped": "PlantVillage test (leaf-map verified)",
             "plantdoc": "PlantDoc (real-world, external)"}
    lines = [
        f"# Tomato CV model results: {card['version']}",
        "",
        f"EfficientNet-B0 fine-tuned on {card['data']['train_images']:,} PlantVillage tomato images "
        f"({card['best_epoch']} epochs to best validation macro-F1 {card['best_val_macro_f1']}), "
        f"trained {card['trained_at'][:10]} on {card['device']} in {card['training_minutes']} min, code commit `{card['code_commit']}`.",
        "",
        "## Summary",
        "",
        "| Test set | Images | Accuracy | Macro-F1 |",
        "|---|---:|---:|---:|",
    ]
    for key, m in metrics.items():
        lines.append(f"| {names[key]} | {m['images']:,} | {m['accuracy']:.1%} | {m['macro_f1']:.3f} |")
    lines += [
        "",
        "## How to read these numbers",
        "",
        "- **Splits are grouped:**",
        "  - Every photo of the same leaf (from PlantVillage's official leaf map) stays in one split.",
        "  - So does every near-duplicate photo.",
        "  - See `ml/cv/splits.py`.",
        "- **29% of PlantVillage images have no leaf-map entry.** This covers all Mosaic Virus images and about half of Yellow Leaf Curl and Late Blight.",
        "  - For those images, different photos of the same leaf can still land in both train and test.",
        "  - So the *all* score may be slightly optimistic.",
        "  - The *leaf-map verified* row only counts test images whose leaf is known.",
        "- **PlantDoc is the honest real-world number.**",
        "  - Its images are field photos with backgrounds, lighting changes and several leaves per photo, and the model never saw them in training.",
        "  - A large drop from PlantVillage is expected, and is widely reported in the literature.",
        "  - PlantDoc has no Target Spot images and only 2 Spider Mite images.",
        "",
    ]
    for key, m in metrics.items():
        lines += [f"## {names[key]}", "", f"![Confusion matrix](cv_tomato_v1_{key}_confusion.png)", "",
                  "| Class | Precision | Recall | F1 | Images |", "|---|---:|---:|---:|---:|"]
        for cid, r in m["per_class"].items():
            lines.append(f"| {cid.replace('tomato_', '')} | {r['precision']:.3f} | {r['recall']:.3f} | "
                         f"{r['f1-score']:.3f} | {int(r['support'])} |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Evaluate the tomato CV model")
    parser.add_argument("--model-dir", type=Path, default=Path("crops/tomato/models/cv"))
    parser.add_argument("--report-dir", type=Path, default=Path("docs/results"))
    args = parser.parse_args()

    card = json.loads((args.model_dir / "model_card_v1.json").read_text())
    class_ids = card["classes"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_efficientnet_b0(len(class_ids))
    model.load_state_dict(torch.load(args.model_dir / card["weights_file"], map_location="cpu", weights_only=True))
    model.to(device)

    test = load_split("test")
    sets = {
        "plantvillage_test": test,
        "plantvillage_test_mapped": [s for s in test if s["leaf_mapped"]],
        "plantdoc": load_plantdoc(),
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    metrics = {}
    for key, samples in sets.items():
        y_true = np.array([s["label"] for s in samples])
        y_pred = predict(model, samples, device)
        metrics[key] = score(y_true, y_pred, class_ids)
        plot_confusion(metrics[key]["confusion_matrix"], [c.replace("tomato_", "") for c in class_ids],
                       key, args.report_dir / f"cv_tomato_v1_{key}_confusion.png")
        print(f"[Eval] {key:26s} n={metrics[key]['images']:5d}  acc {metrics[key]['accuracy']:.4f}  "
              f"macro-F1 {metrics[key]['macro_f1']:.4f}")

    (args.model_dir / "metrics_v1.json").write_text(json.dumps({"version": card["version"], **metrics}, indent=2))
    write_report(metrics, card, args.report_dir / "cv_tomato_v1.md")
    print(f"[Eval] Wrote {args.model_dir / 'metrics_v1.json'} and {args.report_dir / 'cv_tomato_v1.md'}")


if __name__ == "__main__":
    main()
