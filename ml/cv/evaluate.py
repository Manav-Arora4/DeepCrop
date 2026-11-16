"""
Evaluate a trained tomato CV model on held-out data.

Test sets:
  plantvillage_test          PlantVillage test split (lab photos, same source as training)
  plantvillage_test_mapped   the part of that split with an official leaf-map entry (strictest
                             leakage control; has no Mosaic Virus, whose images are all unmapped)
  plantdoc_test              PlantDoc test split (real-world photos, held out from every model)
  plantdoc_all               all 746 PlantDoc photos, only for models never trained on PlantDoc

Writes crops/tomato/models/cv/metrics_<version>.json, a markdown report with confusion-matrix
images in docs/results/, and docs/results/cv_tomato_comparison.md across all evaluated versions.

Run:  python -m ml.cv.evaluate --version v2
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader

from ml.cv.data_loader import PLANTDOC_SPLITS_CSV, LeafImageDataset, get_data_transforms, load_plantdoc, load_split
from ml.cv.models.efficientnet import build_efficientnet_b0

SET_NAMES = {
    "plantvillage_test": "PlantVillage test (all)",
    "plantvillage_test_mapped": "PlantVillage test (leaf-map verified)",
    "plantdoc_test": "PlantDoc test (real-world, held out)",
    "plantdoc_all": "PlantDoc, all 746 (real-world, never trained on)",
}


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


def wilson_interval(correct, n, z=1.96):
    """95% Wilson score interval for a proportion; stays sensible for small test sets."""
    if n == 0:
        return (0.0, 0.0)
    p = correct / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(centre - half, 4), round(centre + half, 4))


def score(y_true, y_pred, class_ids):
    present = sorted(set(y_true))
    report = classification_report(y_true, y_pred, labels=present, target_names=[class_ids[i] for i in present],
                                   output_dict=True, zero_division=0)
    return {
        "images": int(len(y_true)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "accuracy_ci95": wilson_interval(int((y_true == y_pred).sum()), len(y_true)),
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


def describe_training(card):
    """One sentence on how a model was trained; handles v1 cards, which predate the PlantDoc fields."""
    data = card["data"]
    pv = data.get("plantvillage_train", data.get("train_images"))
    pd = data.get("plantdoc_train", 0)
    repeat = card["training"].get("plantdoc_repeat", 0)
    aug = "field-photo augmentation" if card["training"].get("strong_aug") else "light augmentation"
    source = f"{pv:,} PlantVillage" + (f" + {pd} PlantDoc (×{repeat})" if pd else "") + " tomato images"
    best = card.get("best_selection_score", card.get("best_val_macro_f1"))
    return (f"EfficientNet-B0 fine-tuned on {source} with {aug}. Best epoch {card['best_epoch']} "
            f"(selection score {best}), trained {card['trained_at'][:10]} on {card['device']} "
            f"in {card['training_minutes']} min, code commit `{card['code_commit']}`.")


def write_report(metrics, card, version, path):
    lines = [
        f"# Tomato CV model results: {card['version']}",
        "",
        describe_training(card),
        "",
        "## Summary",
        "",
        "| Test set | Images | Accuracy (95% CI) | Macro-F1 |",
        "|---|---:|---:|---:|",
    ]
    for key, m in metrics.items():
        lo, hi = m["accuracy_ci95"]
        lines.append(f"| {SET_NAMES[key]} | {m['images']:,} | {m['accuracy']:.1%} ({lo:.1%}–{hi:.1%}) | {m['macro_f1']:.3f} |")
    lines += [
        "",
        "## How to read these numbers",
        "",
        "- **Splits are grouped:**",
        "  - Every photo of the same leaf (PlantVillage's official leaf map) stays in one split.",
        "  - So does every exact or near-duplicate photo.",
        "  - See `ml/cv/splits.py`.",
        "- **29% of PlantVillage images have no leaf-map entry.** This covers all Mosaic Virus images and about half of Yellow Leaf Curl and Late Blight.",
        "  - For those images, different photos of the same leaf can still land in both train and test.",
        "  - The *leaf-map verified* row only counts test images whose leaf is known.",
        "- **PlantDoc is the real-world number.**",
        "  - Its photos have backgrounds, lighting changes and several leaves per photo.",
        "  - All 746 PlantDoc photos were pooled and split 60/15/25 by group. The 188-photo test split is held out from every model.",
        "  - PlantDoc has no Target Spot images and only 2 Spider Mite images, so those classes can't be judged on it.",
        "- **The test set is small, so the confidence interval matters.** With 188 PlantDoc test photos, differences inside the 95% interval aren't meaningful.",
        "",
    ]
    for key, m in metrics.items():
        lines += [f"## {SET_NAMES[key]}", "", f"![Confusion matrix](cv_tomato_{version}_{key}_confusion.png)", "",
                  "| Class | Precision | Recall | F1 | Images |", "|---|---:|---:|---:|---:|"]
        for cid, r in m["per_class"].items():
            lines.append(f"| {cid.replace('tomato_', '')} | {r['precision']:.3f} | {r['recall']:.3f} | "
                         f"{r['f1-score']:.3f} | {int(r['support'])} |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_comparison(model_dir, report_dir):
    rows = []
    for metrics_file in sorted(model_dir.glob("metrics_v*.json")):
        m = json.loads(metrics_file.read_text())
        version = metrics_file.stem.split("_")[1]
        card = json.loads((model_dir / f"model_card_{version}.json").read_text())
        rows.append((version, card, m))
    if len(rows) < 2:
        return
    lines = ["# Tomato CV model comparison", "",
             "Same held-out test sets for every version (fixed seeds in `ml/cv/splits.py`).", "",
             "| Version | Training data | PlantVillage test acc | PlantVillage macro-F1 | PlantDoc test acc (95% CI) | PlantDoc macro-F1 |",
             "|---|---|---:|---:|---:|---:|"]
    for version, card, m in rows:
        pv, pd = m.get("plantvillage_test"), m.get("plantdoc_test")
        data = "PlantVillage" + (" + PlantDoc train" if card.get("trained_on_plantdoc") else "")
        aug = ", field aug" if card["training"].get("strong_aug") else ""
        pd_text = (f"{pd['accuracy']:.1%} ({pd['accuracy_ci95'][0]:.1%}–{pd['accuracy_ci95'][1]:.1%})", f"{pd['macro_f1']:.3f}") \
            if pd else ("–", "–")
        lines.append(f"| {card['version']} | {data}{aug} | {pv['accuracy']:.1%} | {pv['macro_f1']:.3f} | {pd_text[0]} | {pd_text[1]} |")
    lines += ["", "Per-version detail: " + ", ".join(f"[{v}](cv_tomato_{v}.md)" for v, _, _ in rows) + "."]
    (report_dir / "cv_tomato_comparison.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Evaluate a tomato CV model")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--model-dir", type=Path, default=Path("crops/tomato/models/cv"))
    parser.add_argument("--report-dir", type=Path, default=Path("docs/results"))
    args = parser.parse_args()

    card = json.loads((args.model_dir / f"model_card_{args.version}.json").read_text())
    class_ids = card["classes"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_efficientnet_b0(len(class_ids))
    model.load_state_dict(torch.load(args.model_dir / card["weights_file"], map_location="cpu", weights_only=True))
    model.to(device)

    test = load_split("test")
    sets = {
        "plantvillage_test": test,
        "plantvillage_test_mapped": [s for s in test if s["leaf_mapped"]],
        "plantdoc_test": load_split("test", PLANTDOC_SPLITS_CSV),
    }
    if not card.get("trained_on_plantdoc"):
        sets["plantdoc_all"] = load_plantdoc()

    args.report_dir.mkdir(parents=True, exist_ok=True)
    metrics = {}
    for key, samples in sets.items():
        y_true = np.array([s["label"] for s in samples])
        y_pred = predict(model, samples, device)
        metrics[key] = score(y_true, y_pred, class_ids)
        plot_confusion(metrics[key]["confusion_matrix"], [c.replace("tomato_", "") for c in class_ids],
                       f"{args.version}: {key}", args.report_dir / f"cv_tomato_{args.version}_{key}_confusion.png")
        lo, hi = metrics[key]["accuracy_ci95"]
        print(f"[Eval] {args.version} {key:26s} n={metrics[key]['images']:5d}  acc {metrics[key]['accuracy']:.4f} "
              f"[{lo:.3f}-{hi:.3f}]  macro-F1 {metrics[key]['macro_f1']:.4f}")

    (args.model_dir / f"metrics_{args.version}.json").write_text(json.dumps({"version": card["version"], **metrics}, indent=2))
    write_report(metrics, card, args.version, args.report_dir / f"cv_tomato_{args.version}.md")
    write_comparison(args.model_dir, args.report_dir)
    print(f"[Eval] Wrote metrics_{args.version}.json and docs/results/cv_tomato_{args.version}.md")


if __name__ == "__main__":
    main()
