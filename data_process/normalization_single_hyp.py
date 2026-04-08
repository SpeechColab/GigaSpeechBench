#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from text_norm import get_normalizer  # noqa: E402


def resolve_normalizer(country: str):
    try:
        return get_normalizer(country)
    except Exception:
        return lambda x: x


def normalize_hyp(hyp_root: Path, out_root: Path, skip_existing: bool = False):
    out_hyp_root = out_root / "hyp"
    out_hyp_root.mkdir(parents=True, exist_ok=True)

    for country_dir in sorted(hyp_root.iterdir()):
        if not country_dir.is_dir():
            continue
        country = country_dir.name
        normalizer = resolve_normalizer(country)

        out_country = out_hyp_root / country
        out_country.mkdir(parents=True, exist_ok=True)

        for hf in sorted(country_dir.glob("*.json")):
            try:
                data = json.loads(hf.read_text(encoding="utf-8"))
            except Exception:
                print(f"[HYP-NORM] skip unreadable: {hf}")
                continue

            if not isinstance(data, list):
                print(f"[HYP-NORM] skip non-list: {hf}")
                continue

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

            out_path = out_country / hf.name
            if skip_existing and out_path.exists():
                print(f"[HYP-NORM] skip existing: {out_path}")
                continue
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[HYP-NORM] wrote: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize single-module HYP json files.")
    parser.add_argument("--hyp_root", required=True, help="Input hyp root with <country>/*.json")
    parser.add_argument("--ref_root", default=None, help="Unused, kept for compatibility")
    parser.add_argument("--out_root", required=True, help="Output root; hyp files will be written to <out_root>/hyp")
    parser.add_argument("--workers", type=int, default=1, help="Unused, kept for compatibility")
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=0,
                        help="1: skip existing output files; 0: overwrite")
    args = parser.parse_args()

    normalize_hyp(Path(args.hyp_root), Path(args.out_root), bool(args.skip_existing))
