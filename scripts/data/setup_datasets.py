"""
Dataset setup for crop modules: download, extract, validate, and document.

Usage (from the repository root):
    .venv/Scripts/python scripts/data/setup_datasets.py --list
    .venv/Scripts/python scripts/data/setup_datasets.py --crop tomato
    .venv/Scripts/python scripts/data/setup_datasets.py --crop tomato --force

Only the requested crop's datasets are fetched. Each dataset is pulled with a
shallow, blob-less git clone and only the needed files are exported, so the full
multi-GB repositories are never downloaded. Exported filenames are sanitized for
Windows (PlantDoc contains names like "x.jpg?itok=abc.jpg").

Outputs:
    data/external/<dataset>/images/...           exported images
    data/external/<dataset>/meta/...             license / citation / metadata files
    data/processed/<crop>/cv/<dataset>_index.csv one row per image (class, leaf_id, md5, ...)
    data/processed/<crop>/cv/quality_report.json dataset quality checks
    data/dataset_manifest.json                   provenance for every installed dataset

Requires: git, Python 3.11+, Pillow (pip install -r scripts/data/requirements.txt).
"""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("[Setup] Pillow is required: pip install -r scripts/data/requirements.txt")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
EXTERNAL_DIR = DATA_DIR / "external"
CACHE_DIR = EXTERNAL_DIR / ".cache"
MANIFEST_PATH = DATA_DIR / "dataset_manifest.json"
CROPS_DIR = REPO_ROOT / "crops"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
INVALID_FILENAME_CHARS = re.compile(r'[<>:"\\|?*\x00-\x1f]')

# -----------------------------------------------------------------------------
# Dataset registry. Class maps go from the source folder name to our class id
# in crops/<crop>/config/disease_classes.json.
# -----------------------------------------------------------------------------
REGISTRY = {
    "tomato": [
        {
            "id": "plantvillage",
            "name": "PlantVillage (color, tomato subset)",
            "source": "https://github.com/spMohanty/PlantVillage-Dataset",
            "license": "CC BY-SA 3.0 (stated on the Hugging Face dataset card mohanty/PlantVillage; "
                       "the GitHub repository has no LICENSE file)",
            "citation": "Mohanty, S. P., Hughes, D. P., & Salathé, M. (2016). Using deep learning for "
                        "image-based plant disease detection. Frontiers in Plant Science, 7, 1419. "
                        "https://doi.org/10.3389/fpls.2016.01419",
            "role": "train_validation",
            "image_dirs": ["raw/color/{folder}"],
            "meta_files": ["leaf-map.json", "CITATION.cff", "README.md", "README_HF.md"],
            "leaf_map": "leaf-map.json",
            # PlantVillage folder names are the hf_label values in disease_classes.json
            "class_map": "hf_label",
        },
        {
            "id": "plantdoc",
            "name": "PlantDoc (cropped classification set, tomato classes)",
            "source": "https://github.com/pratikkayal/PlantDoc-Dataset",
            "license": "CC BY 4.0",
            "citation": "Singh, D., Jain, N., Jain, P., Kayal, P., Kumawat, S., & Batra, N. (2020). "
                        "PlantDoc: A Dataset for Visual Plant Disease Detection. Proceedings of the 7th "
                        "ACM IKDD CoDS and 25th COMAD, 249-253. https://doi.org/10.1145/3371158.3371196",
            # Real-world images: used only to test generalization, never for training
            "role": "external_test",
            "image_dirs": ["train/{folder}", "test/{folder}"],
            "meta_files": ["LICENSE.txt", "README.md"],
            "leaf_map": None,
            "class_map": {
                "Tomato leaf bacterial spot": "tomato_bacterial_spot",
                "Tomato Early blight leaf": "tomato_early_blight",
                "Tomato leaf late blight": "tomato_late_blight",
                "Tomato mold leaf": "tomato_leaf_mold",
                "Tomato Septoria leaf spot": "tomato_septoria_leaf_spot",
                "Tomato two spotted spider mites leaf": "tomato_spider_mites",
                "Tomato leaf yellow virus": "tomato_yellow_leaf_curl_virus",
                "Tomato leaf mosaic virus": "tomato_mosaic_virus",
                "Tomato leaf": "tomato_healthy",
                # PlantDoc has no Target Spot class
            },
        },
    ],
}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def git(*args, cwd=None, input_bytes=None) -> bytes:
    result = subprocess.run(["git", *args], cwd=cwd, input=input_bytes, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.decode(errors='replace')}")
    return result.stdout


def load_crop_classes(crop: str) -> list:
    path = CROPS_DIR / crop / "config" / "disease_classes.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["classes"]


def resolve_class_map(dataset: dict, classes: list) -> dict:
    """Return {source_folder: class_id}."""
    if dataset["class_map"] == "hf_label":
        return {c["hf_label"]: c["id"] for c in classes}
    known_ids = {c["id"] for c in classes}
    unknown = set(dataset["class_map"].values()) - known_ids
    if unknown:
        raise ValueError(f"{dataset['id']}: class ids not in disease_classes.json: {sorted(unknown)}")
    return dict(dataset["class_map"])


def safe_filename(name: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("_", name).rstrip(" .")
    return cleaned or "unnamed"


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def dhash(image: Image.Image) -> str:
    """64-bit difference hash; identical values indicate near-duplicate images."""
    small = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    px = small.tobytes()
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (px[row * 9 + col] > px[row * 9 + col + 1])
    return f"{bits:016x}"


# -----------------------------------------------------------------------------
# Download / export
# -----------------------------------------------------------------------------
def dataset_dir(dataset: dict) -> Path:
    return EXTERNAL_DIR / dataset["id"]


def completion_marker(dataset: dict) -> Path:
    return dataset_dir(dataset) / ".complete.json"


def is_installed(dataset: dict) -> bool:
    return completion_marker(dataset).exists()


def download_dataset(dataset: dict, class_map: dict) -> dict:
    """Blob-less clone, export only the class folders and meta files, then drop the clone."""
    cache = CACHE_DIR / dataset["id"]
    if not (cache / ".git").exists():
        print(f"[Setup] Cloning {dataset['source']} (tree only, no file contents)...")
        cache.parent.mkdir(parents=True, exist_ok=True)
        git("clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
            dataset["source"] + ".git", str(cache))

    commit = git("rev-parse", "HEAD", cwd=cache).decode().strip()
    commit_date = git("log", "-1", "--format=%cs", cwd=cache).decode().strip()

    # Select blobs: folder prefix -> source class folder name
    wanted_prefixes = {}
    for folder in class_map:
        for pattern in dataset["image_dirs"]:
            wanted_prefixes[pattern.format(folder=folder) + "/"] = folder

    entries = []  # (oid, source_path, source_class)
    meta = []     # (oid, source_path)
    tree = git("ls-tree", "-r", "-z", "HEAD", cwd=cache).split(b"\0")
    for raw in tree:
        if not raw:
            continue
        info, path = raw.decode("utf-8").split("\t", 1)
        _mode, obj_type, oid = info.split()
        if obj_type != "blob":
            continue
        if path in dataset["meta_files"]:
            meta.append((oid, path))
            continue
        for prefix, folder in wanted_prefixes.items():
            if path.startswith(prefix) and "/" not in path[len(prefix):]:
                if Path(path).suffix.lower() in IMAGE_EXTENSIONS:
                    entries.append((oid, path, folder))
                break

    if not entries:
        raise RuntimeError(f"{dataset['id']}: no images matched the class map")

    # Fetch all missing blobs in a few batched requests instead of one per file
    oids = [oid for oid, *_ in entries] + [oid for oid, _ in meta]
    check = subprocess.run(["git", "cat-file", "--batch-check"], cwd=cache, capture_output=True,
                           input="\n".join(oids).encode() + b"\n",
                           env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})
    missing = [line.split()[0] for line in check.stdout.decode().splitlines() if line.endswith(" missing")]
    if missing:
        print(f"[Setup] Fetching {len(missing)} files from {dataset['source']}...")
        for i in range(0, len(missing), 2000):
            batch = "\n".join(missing[i:i + 2000]).encode() + b"\n"
            git("-c", "fetch.negotiationAlgorithm=noop", "fetch", "-q", "origin", "--no-tags",
                "--no-write-fetch-head", "--recurse-submodules=no", "--filter=blob:none", "--stdin",
                cwd=cache, input_bytes=batch)

    target = dataset_dir(dataset)
    images_dir = target / "images"
    meta_dir = target / "meta"
    if target.exists():
        shutil.rmtree(target)
    images_dir.mkdir(parents=True)
    meta_dir.mkdir(parents=True)

    print(f"[Setup] Exporting {len(entries)} images to {rel(images_dir)}...")
    renamed = 0
    file_rows = []
    used_names = set()
    blobs = read_blobs(cache, [oid for oid, *_ in entries])
    for oid, source_path, folder in entries:
        data = blobs[oid]
        parent = Path(source_path).parent.as_posix()
        name = safe_filename(Path(source_path).name)
        if (parent, name.lower()) in used_names:
            name = f"{md5_bytes(data)[:8]}_{name}"
        used_names.add((parent, name.lower()))
        if name != Path(source_path).name:
            renamed += 1
        out = images_dir / parent / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        file_rows.append({"path": rel(out), "source_path": source_path, "source_class": folder})

    meta_blobs = read_blobs(cache, [oid for oid, _ in meta])
    for oid, source_path in meta:
        (meta_dir / safe_filename(Path(source_path).name)).write_bytes(meta_blobs[oid])

    with open(target / "files.json", "w", encoding="utf-8") as f:
        json.dump(file_rows, f, indent=0)

    marker = {
        "commit": commit,
        "commit_date": commit_date,
        "download_date": date.today().isoformat(),
        "image_count": len(entries),
        "renamed_for_windows": renamed,
    }
    with open(completion_marker(dataset), "w", encoding="utf-8") as f:
        json.dump(marker, f, indent=2)

    shutil.rmtree(cache, onerror=_force_remove)
    print(f"[Setup] {dataset['id']}: {len(entries)} images exported ({renamed} renamed for Windows).")
    return marker


def read_blobs(cache: Path, oids: list) -> dict:
    """Read many blobs through one `git cat-file --batch` process."""
    out = subprocess.run(["git", "cat-file", "--batch"], cwd=cache, capture_output=True,
                         input="\n".join(oids).encode() + b"\n").stdout
    blobs, pos = {}, 0
    while pos < len(out):
        header_end = out.index(b"\n", pos)
        oid, _obj_type, size = out[pos:header_end].decode().split()
        start = header_end + 1
        blobs[oid] = out[start:start + int(size)]
        pos = start + int(size) + 1  # content is followed by a newline
    missing = set(oids) - set(blobs)
    if missing:
        raise RuntimeError(f"{len(missing)} blobs could not be read from {cache}")
    return blobs


def _force_remove(func, path, _exc):
    # git pack files are read-only on Windows
    os.chmod(path, stat.S_IWRITE)
    func(path)


# -----------------------------------------------------------------------------
# Indexing and quality checks
# -----------------------------------------------------------------------------
# Filenames that were renamed after leaf-map.json was built. Target Spot images are
# "Com.G_TgS_FL 8360.JPG" while the map has "com.g_fl 8360"; dropping "_tgs" matches
# all 1404 images one-to-one to the 1404 Target Spot map entries (checked 2026-10-30).
# Class agreement is still enforced after aliasing.
LEAF_MAP_KEY_ALIASES = [("_tgs_fl", "_fl")]


def load_leaf_map(dataset: dict) -> dict:
    path = dataset_dir(dataset) / "meta" / dataset["leaf_map"]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_leaf_id(source_path: str, folder: str, leaf_map: dict, stats: Counter) -> str:
    """
    Official PlantVillage leaf grouping. Filenames look like "<uuid>___RS_Erly.B 8389.JPG";
    the part after "___", lowercased without extension, keys leaf-map.json, whose values
    are ["<Class>:::<leaf number>"]. Images of the same physical leaf share one leaf_id.
    """
    name = Path(source_path).name
    key = name.split("___", 1)[1] if "___" in name else name
    key = key.rsplit(".", 1)[0].lower().strip()
    candidates = leaf_map.get(key)
    if not candidates:
        for old, new in LEAF_MAP_KEY_ALIASES:
            if old in key and leaf_map.get(key.replace(old, new)):
                candidates = leaf_map[key.replace(old, new)]
                stats["via_alias"] += 1
                break
    if not candidates:
        stats["unmapped"] += 1
        return f"unmapped:{folder}:{key}"
    matching = [c for c in candidates if c.split(":::")[0] == folder]
    if len(candidates) > 1:
        stats["ambiguous"] += 1
    if not matching:
        stats["class_mismatch"] += 1
        return f"mismatch:{folder}:{key}"
    stats["mapped"] += 1
    return matching[0]


def build_index(crop: str, dataset: dict, class_map: dict, classes: list) -> list:
    class_index = {c["id"]: c["index"] for c in classes}
    with open(dataset_dir(dataset) / "files.json", encoding="utf-8") as f:
        files = json.load(f)

    leaf_map = load_leaf_map(dataset) if dataset["leaf_map"] else None
    leaf_stats = Counter()
    rows, corrupt = [], []
    print(f"[Quality] Checking {len(files)} images in {dataset['id']}...")
    for item in files:
        path = REPO_ROOT / item["path"]
        class_id = class_map.get(item["source_class"])
        data = path.read_bytes()
        row = {
            "path": item["path"],
            "dataset": dataset["id"],
            "role": dataset["role"],
            "source_path": item["source_path"],
            "source_class": item["source_class"],
            "class_id": class_id or "",
            "class_index": class_index.get(class_id, ""),
            "leaf_id": "",
            "md5": md5_bytes(data),
            "width": "",
            "height": "",
            "mode": "",
            "dhash": "",
        }
        try:
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img:
                img.load()
                row["width"], row["height"], row["mode"] = img.width, img.height, img.mode
                row["dhash"] = dhash(img)
        except Exception as exc:  # noqa: BLE001 - any decode failure counts as corrupt
            corrupt.append({"path": item["path"], "error": str(exc)})
        if leaf_map is not None:
            row["leaf_id"] = resolve_leaf_id(item["source_path"], item["source_class"], leaf_map, leaf_stats)
        else:
            # No leaf grouping available: every image is its own group
            row["leaf_id"] = f"{dataset['id']}:{row['md5']}"
        rows.append(row)

    out_dir = DATA_DIR / "processed" / crop / "cv"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{dataset['id']}_index.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    dataset["_leaf_stats"] = dict(leaf_stats)
    dataset["_corrupt"] = corrupt
    return rows


def duplicate_groups(rows: list, key: str) -> list:
    groups = defaultdict(list)
    for r in rows:
        if r[key]:
            groups[r[key]].append(r)
    return [g for g in groups.values() if len(g) > 1]


def quality_report(dataset: dict, rows: list, classes: list) -> dict:
    counts = Counter(r["class_id"] for r in rows)
    sizes = Counter(f"{r['width']}x{r['height']}" for r in rows if r["width"] != "")
    modes = Counter(r["mode"] for r in rows if r["mode"])
    invalid = [r["path"] for r in rows if not r["class_id"]]

    exact = duplicate_groups(rows, "md5")
    near = duplicate_groups(rows, "dhash")
    exact_cross_class = [g for g in exact if len({r["class_id"] for r in g}) > 1]
    near_cross_class = [g for g in near if len({r["class_id"] for r in g}) > 1]
    # Duplicates with different leaf_ids could land in different splits and leak
    exact_cross_leaf = [g for g in exact if len({r["leaf_id"] for r in g}) > 1]
    near_cross_leaf = [g for g in near if len({r["leaf_id"] for r in g}) > 1]

    def sample(groups, n=10):
        return [[r["path"] for r in g] for g in groups[:n]]

    report = {
        "role": dataset["role"],
        "total_images": len(rows),
        "class_counts": {c["id"]: counts.get(c["id"], 0) for c in classes},
        "classes_missing": [c["id"] for c in classes if counts.get(c["id"], 0) == 0],
        "invalid_labels": invalid,
        "corrupt_files": dataset["_corrupt"],
        "image_modes": dict(modes),
        "image_sizes_top": dict(sizes.most_common(10)),
        "distinct_image_sizes": len(sizes),
        "exact_duplicates": {
            "groups": len(exact),
            "extra_copies": sum(len(g) - 1 for g in exact),
            "groups_with_conflicting_labels": len(exact_cross_class),
            "groups_spanning_leaf_ids": len(exact_cross_leaf),
            "examples": sample(exact),
        },
        "near_duplicates_dhash": {
            "groups": len(near),
            "images_in_groups": sum(len(g) for g in near),
            "groups_with_conflicting_labels": len(near_cross_class),
            "groups_spanning_leaf_ids": len(near_cross_leaf),
            "examples": sample(near),
        },
    }
    if dataset["leaf_map"]:
        stats = dataset["_leaf_stats"]
        report["leaf_grouping"] = {
            "source": "official leaf-map.json from the PlantVillage repository",
            "images_mapped": stats.get("mapped", 0),
            "images_unmapped": stats.get("unmapped", 0),
            "images_class_mismatch": stats.get("class_mismatch", 0),
            "images_with_multiple_map_entries": stats.get("ambiguous", 0),
            "images_mapped_via_filename_alias": stats.get("via_alias", 0),
            "unmapped_by_class": dict(Counter(r["source_class"] for r in rows
                                              if r["leaf_id"].startswith("unmapped:"))),
            "distinct_leaves": len({r["leaf_id"] for r in rows
                                    if not r["leaf_id"].startswith(("unmapped:", "mismatch:"))}),
            "note": "Unmapped/mismatched images get a per-image leaf_id, so each forms its own group.",
        }
    return report


def read_index(crop: str, dataset: dict) -> list:
    path = DATA_DIR / "processed" / crop / "cv" / f"{dataset['id']}_index.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# -----------------------------------------------------------------------------
# Manifest
# -----------------------------------------------------------------------------
def update_manifest(crop: str, dataset: dict, marker: dict, report: dict) -> None:
    manifest = {"description": "Provenance of external datasets. Generated by scripts/data/setup_datasets.py.",
                "datasets": {}}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

    manifest["datasets"][dataset["id"]] = {
        "name": dataset["name"],
        "crop": crop,
        "role": dataset["role"],
        "source": dataset["source"],
        "version": {"git_commit": marker["commit"], "commit_date": marker["commit_date"]},
        "download_date": marker["download_date"],
        "license": dataset["license"],
        "citation": dataset["citation"],
        "location": rel(dataset_dir(dataset) / "images"),
        "index": f"data/processed/{crop}/cv/{dataset['id']}_index.csv",
        "num_samples": report["total_images"],
        "classes": report["class_counts"],
        "classes_missing": report["classes_missing"],
        "files_renamed_for_windows": marker["renamed_for_windows"],
    }
    manifest["datasets"] = dict(sorted(manifest["datasets"].items()))
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def list_datasets() -> None:
    for crop, datasets in REGISTRY.items():
        print(f"{crop}:")
        for d in datasets:
            status = "installed" if is_installed(d) else "not installed"
            print(f"  - {d['id']:<14} {d['role']:<17} {status:<14} {d['source']}")


def setup_crop(crop: str, force: bool, recheck: bool) -> None:
    if crop not in REGISTRY:
        sys.exit(f"[Setup] Unknown crop '{crop}'. Available: {', '.join(REGISTRY)}")
    classes = load_crop_classes(crop)

    reports, all_rows = {}, {}
    for dataset in REGISTRY[crop]:
        class_map = resolve_class_map(dataset, classes)
        if force or not is_installed(dataset):
            marker = download_dataset(dataset, class_map)
            rows = []
        else:
            with open(completion_marker(dataset), encoding="utf-8") as f:
                marker = json.load(f)
            print(f"[Setup] {dataset['id']}: already installed (commit {marker['commit'][:7]}), skipping download.")
            rows = [] if (force or recheck) else read_index(crop, dataset)

        if not rows or len(rows) != marker["image_count"]:
            rows = build_index(crop, dataset, class_map, classes)
            reports[dataset["id"]] = quality_report(dataset, rows, classes)
        all_rows[dataset["id"]] = rows
        if dataset["id"] in reports:
            update_manifest(crop, dataset, marker, reports[dataset["id"]])

    report_path = DATA_DIR / "processed" / crop / "cv" / "quality_report.json"
    if not reports and report_path.exists():
        print(f"[Quality] Up to date: {rel(report_path)} (use --recheck to rerun checks).")
        return

    existing = {}
    if report_path.exists():
        with open(report_path, encoding="utf-8") as f:
            existing = json.load(f).get("datasets", {})
    existing.update(reports)

    # External test images must never also appear in the training data
    by_md5 = defaultdict(set)
    for ds_id, rows in all_rows.items():
        for r in rows:
            by_md5[r["md5"]].add(ds_id)
    overlap = sorted(m for m, ds in by_md5.items() if len(ds) > 1)

    final = {
        "crop": crop,
        "datasets": existing,
        "cross_dataset_exact_overlap": {"datasets": sorted(all_rows), "count": len(overlap),
                                        "md5": overlap[:50]},
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[Quality] Report written to {rel(report_path)}")
    for ds_id, r in existing.items():
        line = (f"  {ds_id}: {r['total_images']} images, {len(r['corrupt_files'])} corrupt, "
                f"{r['exact_duplicates']['extra_copies']} exact duplicate copies, "
                f"{r['near_duplicates_dhash']['groups']} near-duplicate groups")
        if "leaf_grouping" in r:
            lg = r["leaf_grouping"]
            line += f", {lg['distinct_leaves']} leaves, {lg['images_unmapped']} unmapped"
        print(line)
    print(f"  cross-dataset exact overlap: {len(overlap)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and validate crop datasets.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--crop", help="Crop to set up, e.g. tomato")
    group.add_argument("--list", action="store_true", help="List registered datasets and install status")
    parser.add_argument("--force", action="store_true", help="Re-download even if already installed")
    parser.add_argument("--recheck", action="store_true", help="Rerun quality checks without re-downloading")
    args = parser.parse_args()

    if args.list:
        list_datasets()
    else:
        setup_crop(args.crop, args.force, args.recheck)


if __name__ == "__main__":
    main()
