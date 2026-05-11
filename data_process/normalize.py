#!/usr/bin/env python3
"""
Text normalization for REF and HYP JSON files.

Features:
  - Parallel processing with multiprocessing
  - Incremental caching: reuses existing non-empty normalized text
  - Processes both ref/{LANG}.json and hyp/{LANG}/*.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from multiprocessing import Pool, cpu_count

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from text_norm import get_normalizer  # noqa: E402


def _get_normalizer(country: str):
    try:
        return get_normalizer(country)
    except Exception:
        return lambda x: x


def _normalize_items(items, normalizer, existing_items=None):
    """Normalize text in items. Reuse cached non-empty text from existing_items."""
    changed = 0
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            continue
        # Cache hit: reuse existing non-empty normalized text
        if existing_items and i < len(existing_items):
            old = existing_items[i].get("text", "")
            if old.strip():
                item["text"] = old
                continue
        try:
            item["text"] = normalizer(item["text"])
            changed += 1
        except Exception:
            pass
    return changed


def _process_file(args):
    """Worker function for parallel normalization."""
    in_path, out_path, country, uppercase_model = args

    try:
        data = json.loads(Path(in_path).read_text(encoding="utf-8"))
    except Exception:
        return f"skip unreadable: {in_path}"

    if not isinstance(data, list):
        return f"skip non-list: {in_path}"

    normalizer = _get_normalizer(country)

    # Load existing output for caching
    existing = None
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if not isinstance(existing, list) or len(existing) != len(data):
                existing = None
        except Exception:
            existing = None

    changed = _normalize_items(data, normalizer, existing)

    if uppercase_model:
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("model"), str):
                item["model"] = item["model"].upper()

    if existing and changed == 0:
        return f"cached: {out_path.name}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"wrote ({changed} normalized): {out_path.name}"


def normalize_all(text_root: str, out_root: str, workers: int, skip_existing: bool):
    text_root = Path(text_root)
    out_root = Path(out_root)
    tasks = []

    # REF files: text_root/ref/{LANG}.json -> out_root/ref/{LANG}.json
    ref_dir = text_root / "ref"
    if ref_dir.is_dir():
        out_ref = out_root / "ref"
        out_ref.mkdir(parents=True, exist_ok=True)
        for rf in sorted(ref_dir.glob("*.json")):
            out_path = out_ref / rf.name
            tasks.append((str(rf), out_path, rf.stem, False))

    # HYP files: text_root/hyp/{LANG}/*.json -> out_root/hyp/{LANG}/*.json
    hyp_dir = text_root / "hyp"
    if hyp_dir.is_dir():
        for country_dir in sorted(hyp_dir.iterdir()):
            if not country_dir.is_dir():
                continue
            country = country_dir.name
            out_country = out_root / "hyp" / country
            out_country.mkdir(parents=True, exist_ok=True)
            for hf in sorted(country_dir.glob("*.json")):
                out_path = out_country / hf.name
                tasks.append((str(hf), out_path, country, True))

    if not tasks:
        print("No files to normalize.")
        return

    print(f"Normalizing {len(tasks)} files with {workers} workers...")

    if workers <= 1:
        for t in tasks:
            r = _process_file(t)
            print(f"  {r}")
    else:
        with Pool(workers) as pool:
            for r in pool.imap_unordered(_process_file, tasks):
                print(f"  {r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize REF and HYP text with caching and parallelism.")
    parser.add_argument("--text_root", required=True, help="Input root with ref/ and hyp/ subdirs")
    parser.add_argument("--out_root", required=True, help="Output root for normalized files")
    parser.add_argument("--workers", type=int, default=0, help="Number of workers (0=auto, 1=sequential)")
    parser.add_argument("--skip_existing", type=int, default=1, choices=[0, 1])
    args = parser.parse_args()

    w = args.workers if args.workers > 0 else min(cpu_count(), 8)
    normalize_all(args.text_root, args.out_root, w, bool(args.skip_existing))
