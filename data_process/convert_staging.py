#!/usr/bin/env python3
"""
Convert WebDataset or legacy metadata releases to pipeline text format.

Staging format:
  data/{LANG}/test/*.tar             (paired WAV and JSON records)
  data/{LANG}/metadata.json          (legacy annotations)
  results/{MODEL}.json               (merged format: {audios:[{aid, segments:[{begin_time, end_time, text}]}]})

Output format:
  data/text/{MODULE}/ref/{LANG}.json      (flat list of {audio_name, start, end, text})
  data/text/{MODULE}/hyp/{LANG}/{LANG}_{model}.json  (flat list)

Usage:
  python convert_staging.py --staging_root /path/to/staging/MODULE --module MODULE --out_root /path/to/Dev [--langs JPN_hard,KOR_hard] [--models volc.bigasr.auc,volc.seedasr.auc]
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_process.release_data import iter_audio_records


# Lang name mapping: normalize hyp lang prefix to match ref folder names
LANG_MAP = {
    "JPN-hard": "JPN_hard",
    "KOR-hard": "KOR_hard",
}


def _log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def convert_staging(staging_root, module_name, out_root, langs=None, models=None,
                    skip_existing=True, skip_ref=False, ref_only=False, hyp_file=None):
    data_dir = os.path.join(staging_root, "data")
    results_dir = os.path.join(staging_root, "results")

    ref_out = os.path.join(out_root, "data", "text", module_name, "ref")
    hyp_out = os.path.join(out_root, "data", "text", module_name, "hyp")
    os.makedirs(ref_out, exist_ok=True)
    os.makedirs(hyp_out, exist_ok=True)

    # Step 1: Generate ref
    _log(f"[convert_staging] ref: {data_dir} -> {ref_out}")
    if langs:
        _log(f"[convert_staging] langs: {langs}")

    for lang in ([] if skip_ref else sorted(os.listdir(data_dir))):
        if langs and lang not in langs:
            continue
        lang_dir = os.path.join(data_dir, lang)
        if not os.path.isdir(lang_dir):
            continue

        out_path = os.path.join(ref_out, f"{lang}.json")
        if skip_existing and os.path.exists(out_path):
            _log(f"  [REF] {lang}.json: SKIP (exists)")
            continue
        ref_segs = []
        audio_count = 0
        for audio in iter_audio_records(lang_dir):
            audio_count += 1
            audio_name = audio.get("audio_name", audio.get("aid", ""))
            for seg in audio.get("segments", []):
                if seg.get("status") == "valid" or "status" not in seg:
                    ref_segs.append({
                        "audio_name": audio_name,
                        "start": seg.get("start", seg.get("begin_time", 0)),
                        "end": seg.get("end", seg.get("end_time", 0)),
                        "text": seg.get("text", "")
                    })
        _log(f"  [REF] {lang}: read {audio_count} audio annotations")

        if ref_segs:
            out_path = os.path.join(ref_out, f"{lang}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(ref_segs, f, ensure_ascii=False, indent=2)
            _log(f"  [REF] {lang}.json: WROTE {len(ref_segs)} segments")
        else:
            _log(f"  [REF] {lang}: SKIP (0 valid segments)")

    if ref_only:
        return

    # Step 2: Generate hyp
    _log(f"[convert_staging] hyp: {results_dir} -> {hyp_out}")
    if models:
        _log(f"[convert_staging] models filter: {models}")
    if not hyp_file and not os.path.isdir(results_dir):
        _log(f"  No results dir")
        return

    total_hyp = 0

    # Only support merged file format: {model}.json with audios[] format
    result_files = [Path(hyp_file)] if hyp_file else sorted(Path(results_dir).glob("*.json"))
    for result_file in result_files:
        fn = result_file.name
        model_name = result_file.stem
        if models and model_name not in models:
            continue
        flat_path = result_file
        with open(flat_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict) or "audios" not in raw:
            _log(f"  skip {fn}: unexpected format")
            continue
        # Group segments by lang
        lang_segs = {}
        for audio in raw["audios"]:
            aid = audio.get("aid", "")
            # Clean path-contaminated aids (e.g. /Users/.../AGR-CH#NA#xxx)
            if "/" in aid:
                aid = os.path.basename(aid)
            # Skip aids without # separator (cannot determine lang)
            if "#" not in aid:
                continue
            lang = aid.split("#")[0]
            lang = LANG_MAP.get(lang, lang)
            if langs and lang not in langs:
                continue
            for seg in audio.get("segments", []):
                lang_segs.setdefault(lang, []).append({
                    "audio_name": aid,
                    "start": seg.get("begin_time", 0),
                    "end": seg.get("end_time", 0),
                    "text": seg.get("text", ""),
                    "model": model_name
                })
        skipped = 0
        wrote = 0
        for lang, segs in sorted(lang_segs.items()):
            lang_hyp_dir = os.path.join(hyp_out, lang)
            os.makedirs(lang_hyp_dir, exist_ok=True)
            out_path = os.path.join(lang_hyp_dir, f"{lang}_{model_name}.json")
            if skip_existing and os.path.exists(out_path):
                _log(f"    [HYP] {lang}/{lang}_{model_name}.json: SKIP (exists)")
                skipped += 1
                total_hyp += 1
                continue
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(segs, f, ensure_ascii=False, indent=2)
            _log(f"    [HYP] {lang}/{lang}_{model_name}.json: WROTE {len(segs)} segments")
            wrote += 1
            total_hyp += 1
        if lang_segs:
            total_segs = sum(len(v) for v in lang_segs.values())
            _log(f"  [HYP] {model_name}: {total_segs} segs, {len(lang_segs)} langs (wrote={wrote}, skipped={skipped})")

    _log(f"  Total hyp files: {total_hyp}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging_root", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--out_root", required=True)
    parser.add_argument("--langs", default="", help="Comma-separated langs (empty=all)")
    parser.add_argument("--models", default="", help="Comma-separated model names to include (empty=all)")
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=1)
    parser.add_argument("--skip_ref", type=int, choices=[0, 1], default=0)
    parser.add_argument("--ref_only", action="store_true")
    parser.add_argument("--hyp_file", help="Evaluate one result JSON without copying it into the release")
    args = parser.parse_args()
    langs = [l.strip() for l in args.langs.split(",") if l.strip()] or None
    models = [m.strip() for m in args.models.split(",") if m.strip()] or None
    convert_staging(args.staging_root, args.module, args.out_root, langs=langs, models=models,
                    skip_existing=bool(args.skip_existing), skip_ref=bool(args.skip_ref),
                    ref_only=args.ref_only, hyp_file=args.hyp_file)


if __name__ == "__main__":
    main()
