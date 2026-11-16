"""
Leakage-aware train/val/test splits for the tomato CV datasets.

Groups images that must stay on the same side of a split:
  1. Same leaf_id. For PlantVillage this is the official leaf-map.json (several photos of
     one leaf); for PlantDoc it is per image, so exact duplicates share one id.
  2. Near-duplicate photos (dHash Hamming distance <= NEAR_DUP_BITS). This catches the
     29% of PlantVillage images missing from the leaf map, and duplicated PlantDoc photos.
Groups are merged with union-find, then split with StratifiedGroupKFold so every class
keeps roughly the same share in each split.

  PlantVillage  ~70 / 15 / 15  ->  data/processed/tomato/cv/splits.csv
  PlantDoc      ~60 / 15 / 25  ->  data/processed/tomato/cv/plantdoc_splits.csv
PlantDoc's own test/ folder has only 69 images (and 5 duplicates of train/ images), so
all 746 PlantDoc photos are pooled and re-split here to get a usable real-world test set.

Run:  python -m ml.cv.splits
"""

import argparse
import csv
import json
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

OUT_DIR = Path("data/processed/tomato/cv")
NEAR_DUP_BITS = 4
SEED = 42

# dataset -> (index file, output stem, outer folds (test share = 1/n), inner folds (val share of rest))
DATASETS = {
    "plantvillage": ("plantvillage_index.csv", "splits", 7, 6),
    "plantdoc": ("plantdoc_index.csv", "plantdoc_splits", 4, 5),
}


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def near_duplicate_pairs(hashes: np.ndarray, max_bits: int, chunk: int = 1024):
    """Yield (i, j) index pairs with i < j whose 64-bit dHashes differ by <= max_bits."""
    for start in range(0, len(hashes), chunk):
        block = hashes[start:start + chunk]
        dist = np.bitwise_count(block[:, None] ^ hashes[None, :])
        for bi, j in zip(*np.nonzero(dist <= max_bits)):
            i = start + bi
            if i < j:
                yield i, j


def build_groups(rows, max_bits=NEAR_DUP_BITS):
    uf = UnionFind(len(rows))
    first_of_key = {}
    for i, r in enumerate(rows):
        for key in (r["leaf_id"], "md5:" + r["md5"]):
            if key in first_of_key:
                uf.union(first_of_key[key], i)
            else:
                first_of_key[key] = i
    hashes = np.array([int(r["dhash"], 16) for r in rows], dtype=np.uint64)
    near = 0
    for i, j in near_duplicate_pairs(hashes, max_bits):
        uf.union(i, j)
        near += 1
    return [uf.find(i) for i in range(len(rows))], near


def make_splits(rows, groups, outer_folds, inner_folds, seed=SEED):
    y = np.array([int(r["class_index"]) for r in rows])
    g = np.array(groups)
    idx = np.arange(len(rows))
    split = np.empty(len(rows), dtype=object)

    with warnings.catch_warnings():
        # PlantDoc has a 2-image class (spider mites); sklearn warns it can't be in every fold
        warnings.filterwarnings("ignore", message="The least populated class")
        outer = StratifiedGroupKFold(n_splits=outer_folds, shuffle=True, random_state=seed)
        rest, test = next(outer.split(idx, y, g))
        inner = StratifiedGroupKFold(n_splits=inner_folds, shuffle=True, random_state=seed)
        tr, va = next(inner.split(rest, y[rest], g[rest]))
    split[test] = "test"
    split[rest[tr]] = "train"
    split[rest[va]] = "val"
    return split


def build(dataset, out_dir, max_bits, seed):
    index_name, stem, outer_folds, inner_folds = DATASETS[dataset]
    with open(out_dir / index_name, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    groups, near_pairs = build_groups(rows, max_bits)
    split = make_splits(rows, groups, outer_folds, inner_folds, seed)

    # Sanity check: no group may appear in more than one split
    sides = defaultdict(set)
    for gid, s in zip(groups, split):
        sides[gid].add(s)
    leaking = sum(1 for s in sides.values() if len(s) > 1)
    if leaking:
        raise SystemExit(f"[splits] {dataset}: {leaking} groups span more than one split; refusing to write.")

    out_csv = out_dir / f"{stem}.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "class_id", "class_index", "group", "leaf_mapped", "split"])
        for r, gid, s in zip(rows, groups, split):
            mapped = dataset == "plantvillage" and not r["leaf_id"].startswith("unmapped:")
            w.writerow([r["path"], r["class_id"], r["class_index"], gid, int(mapped), s])

    summary = {
        "dataset": dataset,
        "seed": seed,
        "near_duplicate_max_bits": max_bits,
        "images": len(rows),
        "groups": len(set(groups)),
        "near_duplicate_pairs_merged": near_pairs,
        "groups_spanning_splits": leaking,
        "split_sizes": dict(Counter(split)),
        "per_split": {s: dict(sorted(Counter(r["class_id"] for r, x in zip(rows, split) if x == s).items()))
                      for s in ("train", "val", "test")},
    }
    if dataset == "plantvillage":
        summary["test_leaf_mapped"] = int(sum(1 for r, x in zip(rows, split)
                                              if x == "test" and not r["leaf_id"].startswith("unmapped:")))
    (out_dir / f"{stem}_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[splits] {dataset}: {summary['images']} images in {summary['groups']} groups "
          f"({near_pairs} near-duplicate pairs merged); sizes {summary['split_sizes']} -> {out_csv}")


def main():
    parser = argparse.ArgumentParser(description="Build leakage-aware tomato CV splits")
    parser.add_argument("--dataset", choices=[*DATASETS, "all"], default="all")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--near-dup-bits", type=int, default=NEAR_DUP_BITS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    for dataset in (DATASETS if args.dataset == "all" else [args.dataset]):
        build(dataset, args.out_dir, args.near_dup_bits, args.seed)


if __name__ == "__main__":
    main()
