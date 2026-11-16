"""
Train EfficientNet-B0 on the PlantVillage tomato subset.

- Transfer learning from ImageNet weights
- Leakage-aware splits from ml/cv/splits.py (grouped by leaf and near-duplicate photo)
- Mixed precision on CUDA, cosine learning-rate schedule
- Early stopping on validation macro-F1 (classes are imbalanced, so accuracy alone misleads)
- Saves the best weights plus a model card JSON to crops/tomato/models/cv/

Run:  python -m ml.cv.train                 (full training)
      python -m ml.cv.train --dry-run       (one batch end to end; saves nothing)
"""

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader

from ml.cv.data_loader import LeafImageDataset, get_data_transforms, load_split
from ml.cv.models.efficientnet import build_efficientnet_b0

CLASSES_CONFIG = Path("crops/tomato/config/disease_classes.json")
MODEL_VERSION = "tomato_cv_v1.0"
WEIGHTS_NAME = "efficientnet_tomato_v1.pth"


def run_epoch(model, loader, criterion, device, optimizer=None, scaler=None):
    training = optimizer is not None
    model.train(training)
    total_loss, preds, labels = 0.0, [], []
    with torch.set_grad_enabled(training):
        for images, y, _ in loader:
            images, y = images.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                logits = model(images)
                loss = criterion(logits, y)
            if training:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            total_loss += loss.item() * images.size(0)
            preds.append(logits.argmax(1).cpu())
            labels.append(y.cpu())
    preds, labels = torch.cat(preds).numpy(), torch.cat(labels).numpy()
    return {
        "loss": total_loss / len(labels),
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average="macro"),
    }


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Train EfficientNet-B0 on PlantVillage tomato")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--patience", type=int, default=4, help="Epochs without val macro-F1 gain before stopping")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default="crops/tomato/models/cv")
    parser.add_argument("--dry-run", action="store_true", help="Run one batch end to end and save nothing")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Train] Device: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else ""))

    classes = json.loads(CLASSES_CONFIG.read_text())["classes"]
    class_ids = [c["id"] for c in sorted(classes, key=lambda c: c["index"])]

    train_samples, val_samples = load_split("train"), load_split("val")
    for s in train_samples[:50] + val_samples[:50]:
        assert class_ids[s["label"]] == s["class_id"], "class_index in splits.csv doesn't match disease_classes.json"
    if args.dry_run:
        train_samples, val_samples = train_samples[:16], val_samples[:16]
    print(f"[Train] {len(train_samples)} train / {len(val_samples)} val images, {len(class_ids)} classes")

    train_tf, val_tf = get_data_transforms()
    loader_kw = dict(batch_size=args.batch_size, num_workers=0 if args.dry_run else args.workers,
                     pin_memory=device.type == "cuda", persistent_workers=not args.dry_run and args.workers > 0)
    train_loader = DataLoader(LeafImageDataset(train_samples, train_tf), shuffle=True,
                              drop_last=not args.dry_run, **loader_kw)
    val_loader = DataLoader(LeafImageDataset(val_samples, val_tf), shuffle=False, **loader_kw)

    model = build_efficientnet_b0(len(class_ids), pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    epochs = 1 if args.dry_run else args.epochs
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")

    out_dir = Path(args.output_dir)
    best_f1, best_epoch, history, stale = -1.0, 0, [], 0
    best_state = None
    started = time.time()
    for epoch in range(1, epochs + 1):
        t0 = time.time()
        tr = run_epoch(model, train_loader, criterion, device, optimizer, scaler)
        va = run_epoch(model, val_loader, criterion, device)
        scheduler.step()
        history.append({"epoch": epoch, "train": tr, "val": va})
        print(f"[Train] epoch {epoch:2d}/{epochs}  train loss {tr['loss']:.3f} acc {tr['accuracy']:.3f}  "
              f"val loss {va['loss']:.3f} acc {va['accuracy']:.3f} macro-F1 {va['macro_f1']:.4f}  ({time.time() - t0:.0f}s)")
        if va["macro_f1"] > best_f1:
            best_f1, best_epoch, stale = va["macro_f1"], epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= args.patience:
                print(f"[Train] Early stop: no val macro-F1 gain for {args.patience} epochs.")
                break

    if args.dry_run:
        print("[Train] Dry run finished. Nothing was saved.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    weights_path = out_dir / WEIGHTS_NAME
    torch.save(best_state, weights_path)
    split_summary = json.loads(Path("data/processed/tomato/cv/splits_summary.json").read_text())
    card = {
        "version": MODEL_VERSION,
        "architecture": "efficientnet_b0 (ImageNet pretrained, new 10-class head)",
        "weights_file": WEIGHTS_NAME,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_commit": git_commit(),
        "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
        "classes": class_ids,
        "input": {"size": 224, "resize": "squash to 224x224", "normalize": "ImageNet mean/std"},
        "training": {k: getattr(args, k) for k in ("epochs", "batch_size", "lr", "patience", "seed")},
        "training_minutes": round((time.time() - started) / 60, 1),
        "best_epoch": best_epoch,
        "best_val_macro_f1": round(best_f1, 4),
        "history": history,
        "data": {"train_images": len(train_samples), "val_images": len(val_samples),
                 "split_seed": split_summary["seed"], "groups": split_summary["groups"]},
    }
    (out_dir / "model_card_v1.json").write_text(json.dumps(card, indent=2))
    print(f"[Train] Best epoch {best_epoch}, val macro-F1 {best_f1:.4f}. Saved {weights_path}")


if __name__ == "__main__":
    main()
