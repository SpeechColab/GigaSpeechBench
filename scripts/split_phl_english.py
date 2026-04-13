#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split PHL ref/hyp into PHL_EN (english=yes) and PHL_noEN (english=no) subsets.

This script:
1. Reads raw PHL ref files, splits segments by 'english' field
2. Generates consolidated ref JSON for PHL_EN and PHL_noEN
3. Filters corresponding hyp files to only keep matched segments

Usage:
    python3 split_phl_english.py \
        --raw_ref_dir  .../Low-Resource-Languages/text/ref/PHL \
        --hyp_dir      .../Low-Resource-Languages/text/hyp \
        --out_ref_root .../data/text/Low-Resource-Languages/ref \
        --out_hyp_root .../data/text/Low-Resource-Languages/hyp
"""

import argparse
import json
import os
from pathlib import Path
from collections import defaultdict


MATCH_TOL = 0.1


def load_raw_ref_segments(raw_ref_dir: Path):
    """Load raw ref segments and split by english field."""
    en_segments = []
    noen_segments = []

    for jf in sorted(raw_ref_dir.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        audio_name = str(data.get("audio_name", "")).strip()
        if not audio_name:
            continue
        segments = data.get("segments", [])
        if not isinstance(segments, list):
            continue

        for seg in segments:
            if not isinstance(seg, dict):
                continue
            if seg.get("status") == "invalid":
                continue
            text = str(seg.get("text", "")).strip()
            if not text:
                continue
            try:
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", 0.0))
            except Exception:
                continue
            if end <= start:
                continue

            item = {
                "audio_name": audio_name,
                "start": start,
                "end": end,
                "text": text,
            }

            english = seg.get("english", "").lower().strip()
            if english == "yes":
                en_segments.append(item)
            elif english == "no":
                noen_segments.append(item)
            # segments without english field are skipped from both subsets

    return en_segments, noen_segments


def build_ref_key(item):
    """Build a matching key from audio_name + start + end."""
    name = os.path.basename(str(item["audio_name"]).replace("\\", "/"))
    for ext in [".wav", ".mp3", ".mp4", ".webm"]:
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
    return (name, float(item["start"]), float(item["end"]))


def filter_hyp_by_ref_keys(hyp_items, ref_keys):
    """Filter hyp items to only those matching ref keys (audio_name + start/end within tolerance)."""
    # Build index from ref_keys
    ref_by_name = defaultdict(list)
    for name, start, end in ref_keys:
        ref_by_name[name].append((start, end))

    filtered = []
    for h in hyp_items:
        name = os.path.basename(str(h.get("audio_name", "")).replace("\\", "/"))
        for ext in [".wav", ".mp3", ".mp4", ".webm"]:
            if name.lower().endswith(ext):
                name = name[:-len(ext)]
        h_start = float(h.get("start", 0.0))
        h_end = float(h.get("end", 0.0))
        for r_start, r_end in ref_by_name.get(name, []):
            if abs(r_start - h_start) <= MATCH_TOL and abs(r_end - h_end) <= MATCH_TOL:
                filtered.append(h)
                break
    return filtered


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_ref_dir", required=True, help="Raw PHL ref directory")
    parser.add_argument("--hyp_dir", required=True, help="BenchData hyp directory (flat, contains PHL_*.json)")
    parser.add_argument("--out_ref_root", required=True, help="Output ref root (will create PHL_EN.json, PHL_noEN.json)")
    parser.add_argument("--out_hyp_root", required=True, help="Output hyp root (will create PHL_EN/, PHL_noEN/ dirs)")
    args = parser.parse_args()

    raw_ref_dir = Path(args.raw_ref_dir)
    hyp_dir = Path(args.hyp_dir)
    out_ref_root = Path(args.out_ref_root)
    out_hyp_root = Path(args.out_hyp_root)

    # Step 1: Split ref
    en_refs, noen_refs = load_raw_ref_segments(raw_ref_dir)
    print(f"PHL_EN ref segments:   {len(en_refs)}")
    print(f"PHL_noEN ref segments: {len(noen_refs)}")

    # Write ref JSONs
    out_ref_root.mkdir(parents=True, exist_ok=True)
    for subset_name, ref_items in [("PHL_EN", en_refs), ("PHL_noEN", noen_refs)]:
        out_path = out_ref_root / f"{subset_name}.json"
        out_path.write_text(json.dumps(ref_items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REF] wrote {subset_name}: {len(ref_items)} segments -> {out_path}")

    # Build ref keys for filtering hyp
    en_keys = set(build_ref_key(r) for r in en_refs)
    noen_keys = set(build_ref_key(r) for r in noen_refs)

    # Step 2: Filter hyp files
    phl_hyp_files = sorted(hyp_dir.glob("PHL_*.json"))
    print(f"\nFound {len(phl_hyp_files)} PHL hyp files")

    for subset_name, ref_keys in [("PHL_EN", en_keys), ("PHL_noEN", noen_keys)]:
        out_hyp_dir = out_hyp_root / subset_name
        out_hyp_dir.mkdir(parents=True, exist_ok=True)

        for hyp_file in phl_hyp_files:
            with open(hyp_file, "r", encoding="utf-8") as f:
                hyp_items = json.load(f)

            filtered = filter_hyp_by_ref_keys(hyp_items, ref_keys)
            if not filtered:
                continue

            # Update language field
            for item in filtered:
                item["language"] = subset_name

            # Output filename: replace PHL_ with PHL_EN_ or PHL_noEN_
            out_name = hyp_file.name.replace("PHL_", f"{subset_name}_", 1)
            out_path = out_hyp_dir / out_name
            out_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[HYP] {subset_name}/{out_name}: {len(filtered)} segments")


if __name__ == "__main__":
    main()
