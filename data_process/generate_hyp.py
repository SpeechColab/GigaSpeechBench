#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path


MATCH_TOL = 0.1


def normalize_audio_name(name: str) -> str:
    base = os.path.basename(str(name).replace("\\", "/"))
    changed = True
    while changed:
        changed = False
        for ext in (".wav", ".mp3", ".mp4", ".webm"):
            if base.lower().endswith(ext):
                base = base[:-len(ext)]
                changed = True
                break
    if base.endswith("#raw"):
        base = base[:-4]
    if base.endswith("_raw"):
        base = base[:-4]
    # Normalize separators: replace _ with # for consistent matching
    base = base.replace("_", "#")
    return base


def load_ref_index(ref_root: Path):
    idx = defaultdict(lambda: defaultdict(list))
    for rf in sorted(ref_root.glob("*.json")):
        country = rf.stem
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            audio = normalize_audio_name(item.get("audio_name", ""))
            try:
                start = float(item.get("start", 0.0))
                end = float(item.get("end", 0.0))
            except Exception:
                continue
            if end <= start:
                continue
            if audio:
                idx[country][audio].append((start, end))

    for country in idx:
        for audio in idx[country]:
            idx[country][audio].sort(key=lambda x: (x[0], x[1]))
    return idx


def has_ref_match(ref_audio_index, audio_name: str, start: float, end: float, tol: float = MATCH_TOL) -> bool:
    audio = normalize_audio_name(audio_name)
    for ref_start, ref_end in ref_audio_index.get(audio, []):
        if abs(start - ref_start) <= tol and abs(end - ref_end) <= tol:
            return True
    return False


def detect_country_from_filename(stem: str, known_countries: set[str] | None = None) -> str:
    if not known_countries:
        return stem.split("_")[0]

    if stem in known_countries:
        return stem

    # Prefer the longest matching country prefix to correctly handle names such as JPN_hard.
    candidates = [c for c in known_countries if stem.startswith(c + "_")]
    if candidates:
        return sorted(candidates, key=len, reverse=True)[0]

    return stem.split("_")[0]


def convert_hyp(hyp_input_root: Path, out_hyp_root: Path, ref_root: Path | None = None, skip_existing: bool = False):
    out_hyp_root.mkdir(parents=True, exist_ok=True)
    ref_index = load_ref_index(ref_root) if ref_root else defaultdict(set)

    hyp_files = sorted(p for p in hyp_input_root.glob("*.json") if p.is_file())
    if not hyp_files:
        raise RuntimeError(f"No hyp json files found under: {hyp_input_root}")

    stats = defaultdict(int)
    known_countries = set(ref_index.keys()) if ref_index else None

    for jf in hyp_files:
        stem = jf.stem
        country = detect_country_from_filename(stem, known_countries)
        out_country_dir = out_hyp_root / country
        out_country_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_country_dir / jf.name
        try:
            raw = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(raw, list):
            continue

        cleaned = []
        for item in raw:
            if not isinstance(item, dict):
                continue

            audio_name = item.get("audio_name") or item.get("path") or item.get("audio_path") or ""
            audio_name = str(audio_name)
            if not audio_name:
                continue

            start = item.get("start", item.get("start_time"))
            end = item.get("end", item.get("end_time"))
            if start is None or end is None:
                continue

            try:
                start = float(start)
                end = float(end)
            except Exception:
                continue

            # If end<=start (e.g. end_time=-1 sentinel), try to recover from ref
            if end <= start and ref_index and ref_index.get(country):
                audio_key = normalize_audio_name(audio_name)
                ref_segs = ref_index[country].get(audio_key, [])
                if len(ref_segs) == 1:
                    start, end = ref_segs[0]
                elif ref_segs:
                    # multiple ref segs for same audio, try start match
                    matched = [(s, e) for s, e in ref_segs if abs(s - start) <= MATCH_TOL]
                    if len(matched) == 1:
                        start, end = matched[0]
                    else:
                        continue
                else:
                    continue

            if end <= start:
                continue

            text = str(item.get("text", "")).strip()
            model = str(item.get("model", "UNKNOWN")).strip() or "UNKNOWN"

            if ref_index and ref_index.get(country):
                if not has_ref_match(ref_index[country], audio_name, start, end):
                    stats[f"{country}_filtered"] += 1
                    continue

            cleaned.append(
                {
                    "audio_name": audio_name,
                    "start": start,
                    "end": end,
                    "text": text,
                    "model": model,
                }
            )

        new_content = json.dumps(cleaned, ensure_ascii=False, indent=2)
        if out_path.exists():
            old_content = out_path.read_text(encoding="utf-8")
            if old_content == new_content:
                print(f"[HYP] unchanged: {jf.name} ({len(cleaned)} segments)")
                continue
        out_path.write_text(new_content, encoding="utf-8")
        stats[f"{country}_kept"] += len(cleaned)
        print(f"[HYP] {country}: {jf.name} -> {len(cleaned)} segments")

    if stats:
        print("[HYP] summary:")
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert raw hyp JSON files into per-country folder format.")
    parser.add_argument("--hyp_input_root", required=True, help="Path like .../text/hyp")
    parser.add_argument("--out_hyp_root", required=True, help="Output root like .../data/text/<module>/hyp")
    parser.add_argument("--ref_root", default=None, help="Optional ref root with consolidated <country>.json files")
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=0,
                        help="1: skip existing output files; 0: overwrite")
    args = parser.parse_args()

    convert_hyp(
        Path(args.hyp_input_root),
        Path(args.out_hyp_root),
        Path(args.ref_root) if args.ref_root else None,
        bool(args.skip_existing),
    )
