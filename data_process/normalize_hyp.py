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


def _process_one_file(args):
    """Process a single hyp JSON file. Designed for multiprocessing."""
    hyp_path, out_path, country = args
    normalizer = resolve_normalizer(country)

    try:
        data = json.loads(hyp_path.read_text(encoding="utf-8"))
    except Exception:
        _log(f"[HYP-NORM] skip unreadable: {hyp_path}")
        return

    if not isinstance(data, list):
        _log(f"[HYP-NORM] skip non-list: {hyp_path}")
        return

    for item in data:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("text"), str):
            try:
                item["text"] = normalizer(item["text"])
            except Exception:
                pass
        if isinstance(item.get("model"), str):
            item["model"] = item["model"].upper()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"[HYP-NORM] {country}/{hyp_path.name}: WROTE {len(data)} segments")


def normalize_hyp(hyp_root: Path, out_root: Path, skip_existing: bool = False, workers: int = 1):
    out_hyp_root = out_root / "hyp"
    out_hyp_root.mkdir(parents=True, exist_ok=True)

    # Collect all tasks
    tasks = []
    for country_dir in sorted(hyp_root.iterdir()):
        if not country_dir.is_dir():
            continue
        country = country_dir.name
        out_country = out_hyp_root / country
        out_country.mkdir(parents=True, exist_ok=True)

        for hf in sorted(country_dir.glob("*.json")):
            out_path = out_country / hf.name
            if skip_existing and out_path.exists():
                _log(f"[HYP-NORM] {country}/{hf.name}: SKIP (exists)")
                continue
            tasks.append((hf, out_path, country))

    if not tasks:
        _log("[HYP-NORM] No files to process.")
        return

    _log(f"[HYP-NORM] {len(tasks)} files to normalize, workers={workers}")

    if workers > 1:
        with Pool(workers) as pool:
            pool.map(_process_one_file, tasks)
    else:
        for t in tasks:
            _process_one_file(t)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize single-module HYP json files.")
    parser.add_argument("--hyp_root", required=True, help="Input hyp root with <country>/*.json")
    parser.add_argument("--ref_root", default=None, help="Unused, kept for compatibility")
    parser.add_argument("--out_root", required=True, help="Output root; hyp files will be written to <out_root>/hyp")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of parallel workers (default: min(cpu_count, 16))")
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=0,
                        help="1: skip existing output files; 0: overwrite")
    args = parser.parse_args()

    w = args.workers if args.workers else min(cpu_count(), 16)
    normalize_hyp(Path(args.hyp_root), Path(args.out_root), bool(args.skip_existing), workers=w)
