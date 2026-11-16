"""
Leakage-aware train/val/test splits for the PlantVillage tomato subset.

Groups images that must stay on the same side of a split:
  1. Same official leaf_id from PlantVillage's leaf-map.json (several photos of one leaf).
  2. Near-duplicate photos (dHash Hamming distance <= NEAR_DUP_BITS). This catches the
     29% of images missing from the leaf map, which otherwise have no grouping at all.
Groups are merged with union-find, then split ~70/15/15 with StratifiedGroupKFold so
every class keeps roughly the same share in each split.

Run:  python -m ml.cv.splits            (writes data/processed/tomato/cv/splits.csv)
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

INDEX = Path("data/processed/tomato/cv/plantvillage_index.csv")
OUT_DIR = Path("data/processed/tomato/cv")
NEAR_DUP_BITS = 4
SEED = 42


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
    first_of_leaf = {}
    for i, r in enumerate(rows):
        leaf = r["leaf_id"]
        if leaf in first_of_leaf:
            uf.union(first_of_leaf[leaf], i)
        else:
            first_of_leaf[leaf] = i
    hashes = np.array([int(r["dhash"], 16) for r in rows], dtype=np.uint64)
    near = 0
    for i, j in near_duplicate_pairs(hashes, max_bits):
        uf.union(i, j)
        near += 1
    return [uf.find(i) for i in range(len(rows))], near


def make_splits(rows, groups, seed=SEED):
    y = np.array([int(r["class_index"]) for r in rows])
    g = np.array(groups)
    idx = np.arange(len(rows))
    split = np.empty(len(rows), dtype=object)

    # ~15% test, then ~15% of the total as validation from the remainder
    outer = StratifiedGroupKFold(n_splits=7, shuffle=True, random_state=seed)
    rest, test = next(outer.split(idx, y, g))
    split[test] = "test"
    inner = StratifiedGroupKFold(n_splits=6, shuffle=True, random_state=seed)
    tr, va = next(inner.split(rest, y[rest], g[rest]))
    split[rest[tr]] = "train"
    split[rest[va]] = "val"
    return split


def main():
    parser = argparse.ArgumentParser(description="Build leakage-aware PlantVillage tomato splits")
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--near-dup-bits", type=int, default=NEAR_DUP_BITS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    with open(args.index, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    groups, near_pairs = build_groups(rows, args.near_dup_bits)
    split = make_splits(rows, groups, args.seed)

    # Sanity check: no group may appear in more than one split
    sides = defaultdict(set)
    for gid, s in zip(groups, split):
        sides[gid].add(s)
    leaking = sum(1 for s in sides.values() if len(s) > 1)
    if leaking:
        raise SystemExit(f"[splits] {leaking} groups span more than one split; refusing to write.")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.out_dir / "splits.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "class_id", "class_index", "group", "leaf_mapped", "split"])
        for r, gid, s in zip(rows, groups, split):
            w.writerow([r["path"], r["class_id"], r["class_index"], gid,
                        int(not r["leaf_id"].startswith("unmapped:")), s])

    summary = {
        "seed": args.seed,
        "near_duplicate_max_bits": args.near_dup_bits,
        "images": len(rows),
        "groups": len(set(groups)),
        "near_duplicate_pairs_merged": near_pairs,
        "groups_spanning_splits": leaking,
        "per_split": {s: dict(sorted(Counter(r["class_id"] for r, x in zip(rows, split) if x == s).items()))
                      for s in ("train", "val", "test")},
        "split_sizes": dict(Counter(split)),
        "test_leaf_mapped": int(sum(1 for r, x in zip(rows, split)
                                    if x == "test" and not r["leaf_id"].startswith("unmapped:"))),
    }
    (args.out_dir / "splits_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[splits] {summary['images']} images in {summary['groups']} groups "
          f"({near_pairs} near-duplicate pairs merged)")
    print(f"[splits] sizes: {summary['split_sizes']} -> {out_csv}")


if __name__ == "__main__":
    main()
