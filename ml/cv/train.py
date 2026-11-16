"""
Train EfficientNet-B0 on the tomato leaf datasets.

- Transfer learning from ImageNet weights
- Leakage-aware splits from ml/cv/splits.py (grouped by leaf and near-duplicate photo)
- Mixed precision on CUDA, cosine learning-rate schedule
- Early stopping on validation macro-F1 (classes are imbalanced, so accuracy alone misleads)
- Saves the best weights plus a model card JSON to crops/tomato/models/cv/

Versions:
  v1  PlantVillage only, light augmentation
        python -m ml.cv.train --version v1
  v2  PlantVillage + PlantDoc train split (repeated), field-photo augmentation; best epoch
      chosen on the mean of PlantVillage and PlantDoc validation macro-F1
        python -m ml.cv.train --version v2 --plantdoc-repeat 6 --strong-aug

  python -m ml.cv.train --dry-run   runs one batch end to end and saves nothing
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

from ml.cv.data_loader import PLANTDOC_SPLITS_CSV, LeafImageDataset, get_data_transforms, load_split
from ml.cv.models.efficientnet import build_efficientnet_b0

CLASSES_CONFIG = Path("crops/tomato/config/disease_classes.json")


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
        "macro_f1": f1_score(labels, preds, labels=sorted(set(labels)), average="macro", zero_division=0),
    }


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Train EfficientNet-B0 on tomato leaf images")
    parser.add_argument("--version", default="v1", help="Model version tag, e.g. v1 or v2")
    parser.add_argument("--plantdoc-repeat", type=int, default=0,
                        help="Add the PlantDoc train split, repeated N times per epoch (0 = PlantVillage only)")
    parser.add_argument("--strong-aug", action="store_true", help="Use field-photo augmentation")
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

    pv_train, pv_val = load_split("train"), load_split("val")
    use_pd = args.plantdoc_repeat > 0
    pd_train = load_split("train", PLANTDOC_SPLITS_CSV) if use_pd else []
    pd_val = load_split("val", PLANTDOC_SPLITS_CSV) if use_pd else []
    for s in pv_train[:50] + pv_val[:50] + pd_train[:50]:
        assert class_ids[s["label"]] == s["class_id"], "class_index in the splits doesn't match disease_classes.json"
    train_samples = pv_train + pd_train * args.plantdoc_repeat
    if args.dry_run:
        train_samples, pv_val, pd_val = train_samples[:16], pv_val[:16], pd_val[:16]
    print(f"[Train] {args.version}: {len(pv_train)} PlantVillage + {len(pd_train)} PlantDoc x{args.plantdoc_repeat} "
          f"train images; val {len(pv_val)} PlantVillage / {len(pd_val)} PlantDoc; strong aug {args.strong_aug}")

    train_tf, val_tf = get_data_transforms(strong=args.strong_aug)
    loader_kw = dict(batch_size=args.batch_size, num_workers=0 if args.dry_run else args.workers,
                     pin_memory=device.type == "cuda", persistent_workers=not args.dry_run and args.workers > 0)
    train_loader = DataLoader(LeafImageDataset(train_samples, train_tf), shuffle=True,
                              drop_last=not args.dry_run, **loader_kw)
    val_loaders = {"plantvillage": DataLoader(LeafImageDataset(pv_val, val_tf), shuffle=False, **loader_kw)}
    if use_pd:
        val_loaders["plantdoc"] = DataLoader(LeafImageDataset(pd_val, val_tf), shuffle=False, **loader_kw)

    model = build_efficientnet_b0(len(class_ids), pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    epochs = 1 if args.dry_run else args.epochs
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")

    best_score, best_epoch, history, stale = -1.0, 0, [], 0
    best_state = None
    started = time.time()
    for epoch in range(1, epochs + 1):
        t0 = time.time()
        tr = run_epoch(model, train_loader, criterion, device, optimizer, scaler)
        val = {name: run_epoch(model, loader, criterion, device) for name, loader in val_loaders.items()}
        scheduler.step()
        score = float(np.mean([v["macro_f1"] for v in val.values()]))
        history.append({"epoch": epoch, "train": tr, "val": val, "selection_score": score})
        val_text = "  ".join(f"{n} acc {v['accuracy']:.3f} F1 {v['macro_f1']:.4f}" for n, v in val.items())
        print(f"[Train] epoch {epoch:2d}/{epochs}  train loss {tr['loss']:.3f} acc {tr['accuracy']:.3f}  "
              f"val {val_text}  score {score:.4f}  ({time.time() - t0:.0f}s)")
        if score > best_score:
            best_score, best_epoch, stale = score, epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= args.patience:
                print(f"[Train] Early stop: no val gain for {args.patience} epochs.")
                break

    if args.dry_run:
        print("[Train] Dry run finished. Nothing was saved.")
        return

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    weights_name = f"efficientnet_tomato_{args.version}.pth"
    torch.save(best_state, out_dir / weights_name)
    card = {
        "version": f"tomato_cv_{args.version}.0",
        "architecture": "efficientnet_b0 (ImageNet pretrained, new 10-class head)",
        "weights_file": weights_name,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_commit": git_commit(),
        "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
        "classes": class_ids,
        "input": {"size": 224, "resize": "squash to 224x224", "normalize": "ImageNet mean/std"},
        "training": {k: getattr(args, k) for k in
                     ("epochs", "batch_size", "lr", "patience", "seed", "plantdoc_repeat", "strong_aug")},
        "training_minutes": round((time.time() - started) / 60, 1),
        "best_epoch": best_epoch,
        "selection_metric": "mean val macro-F1 over " + " + ".join(val_loaders),
        "best_selection_score": round(best_score, 4),
        "trained_on_plantdoc": use_pd,
        "history": history,
        "data": {"plantvillage_train": len(pv_train), "plantdoc_train": len(pd_train),
                 "plantvillage_val": len(pv_val), "plantdoc_val": len(pd_val)},
    }
    (out_dir / f"model_card_{args.version}.json").write_text(json.dumps(card, indent=2))
    print(f"[Train] Best epoch {best_epoch}, selection score {best_score:.4f}. Saved {out_dir / weights_name}")


if __name__ == "__main__":
    main()
