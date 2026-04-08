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


def normalize_ref(ref_root: Path, out_root: Path, skip_existing: bool = False):
    out_ref = out_root / "ref"
    out_ref.mkdir(parents=True, exist_ok=True)

    for rf in sorted(ref_root.glob("*.json")):
        country = rf.stem
        normalizer = resolve_normalizer(country)

        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except Exception:
            print(f"[REF-NORM] skip unreadable: {rf}")
            continue

        if not isinstance(data, list):
            print(f"[REF-NORM] skip non-list: {rf}")
            continue

        for item in data:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                try:
                    item["text"] = normalizer(item["text"])
                except Exception:
                    pass

        out_path = out_ref / rf.name
        if skip_existing and out_path.exists():
            print(f"[REF-NORM] skip existing: {out_path}")
            continue
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REF-NORM] wrote: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize single-module REF json files.")
    parser.add_argument("--ref_root", required=True, help="Input ref root with <country>.json files")
    parser.add_argument("--out_root", required=True, help="Output root; ref files will be written to <out_root>/ref")
    parser.add_argument("--workers", type=int, default=1, help="Unused, kept for compatibility")
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=0,
                        help="1: skip existing output files; 0: overwrite")
    args = parser.parse_args()

    normalize_ref(Path(args.ref_root), Path(args.out_root), bool(args.skip_existing))
