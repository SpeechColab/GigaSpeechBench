#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
from datetime import datetime
from multiprocessing import Pool, cpu_count
from pathlib import Path


def _log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from text_norm import get_normalizer  # noqa: E402


def resolve_normalizer(country: str):
    try:
        return get_normalizer(country)
    except Exception:
        return lambda x: x


def _process_one_ref(args):
    """Process a single ref JSON file. Designed for multiprocessing."""
    rf, out_path = args
    country = rf.stem
    normalizer = resolve_normalizer(country)

    try:
        data = json.loads(rf.read_text(encoding="utf-8"))
    except Exception:
        _log(f"[REF-NORM] skip unreadable: {rf}")
        return

    if not isinstance(data, list):
        _log(f"[REF-NORM] skip non-list: {rf}")
        return

    for item in data:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            try:
                item["text"] = normalizer(item["text"])
            except Exception:
                pass

    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"[REF-NORM] {rf.name}: WROTE {len(data)} segments")


def normalize_ref(ref_root: Path, out_root: Path, skip_existing: bool = False, workers: int = 1):
    out_ref = out_root / "ref"
    out_ref.mkdir(parents=True, exist_ok=True)

    tasks = []
    for rf in sorted(ref_root.glob("*.json")):
        out_path = out_ref / rf.name
        if skip_existing and out_path.exists():
            _log(f"[REF-NORM] {rf.name}: SKIP (exists)")
            continue
        tasks.append((rf, out_path))

    if not tasks:
        _log("[REF-NORM] No files to process.")
        return

    _log(f"[REF-NORM] {len(tasks)} files to normalize, workers={workers}")

    if workers > 1:
        with Pool(workers) as pool:
            pool.map(_process_one_ref, tasks)
    else:
        for t in tasks:
            _process_one_ref(t)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize single-module REF json files.")
    parser.add_argument("--ref_root", required=True, help="Input ref root with <country>.json files")
    parser.add_argument("--out_root", required=True, help="Output root; ref files will be written to <out_root>/ref")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of parallel workers (default: min(cpu_count, 16))")
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=0,
                        help="1: skip existing output files; 0: overwrite")
    args = parser.parse_args()

    w = args.workers if args.workers else min(cpu_count(), 16)
    normalize_ref(Path(args.ref_root), Path(args.out_root), bool(args.skip_existing), workers=w)
