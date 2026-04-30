#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
from pathlib import Path


def _load_json_tolerant(path: Path):
    """Load JSON with tolerance for trailing commas."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return json.loads(text)


def iter_ref_segments(country_dir: Path):
    for jf in sorted(country_dir.glob("*.json")):
        try:
            data = _load_json_tolerant(jf)
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

            yield {
                "audio_name": audio_name,
                "start": start,
                "end": end,
                "text": text,
            }


def convert_ref(old_ref_root: Path, out_ref_root: Path, skip_existing: bool = False):
    out_ref_root.mkdir(parents=True, exist_ok=True)

    country_dirs = [p for p in sorted(old_ref_root.iterdir()) if p.is_dir()]
    if not country_dirs:
        raise RuntimeError(f"No country directories found under: {old_ref_root}")

    for country_dir in country_dirs:
        country = country_dir.name
        items = list(iter_ref_segments(country_dir))
        out_path = out_ref_root / f"{country}.json"
        if skip_existing and out_path.exists():
            print(f"[REF] skip existing: {out_path}")
            continue
        out_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REF] {country}: {len(items)} segments -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert raw ref folder into consolidated per-country JSON files.")
    parser.add_argument("--old_ref_root", required=True, help="Path like .../text/ref")
    parser.add_argument("--out_ref_root", required=True, help="Output folder for consolidated ref JSON")
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=0,
                        help="1: skip existing output files; 0: overwrite")
    args = parser.parse_args()

    convert_ref(Path(args.old_ref_root), Path(args.out_ref_root), bool(args.skip_existing))
