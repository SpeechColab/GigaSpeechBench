#!/usr/bin/env python3
"""
Convert GigaSpeech-style dataset to pipeline-internal flat JSON format.

Dataset layout (input, GigaSpeech-style):
  data/{LANG}/metadata.json           -- {"audios": [{"aid":..., "segments":[{sid,begin_time,end_time,text,...}]}]}
  data/{LANG}/audio/*.wav             -- audio files
  results/{model}.json                -- {"audios": [{"aid":..., "segments":[{sid,begin_time,end_time,text,lang}]}]}

Pipeline layout (output):
  {out}/ref/{LANG}.json               -- [{audio_name, start, end, text}]
  {out}/hyp/{LANG}/{LANG}_{model}.json -- [{audio_name, start, end, text, model}]
"""

import argparse
import json
import os
import glob
from collections import defaultdict


def convert_refs(data_root: str, out_dir: str, skip_existing: bool):
    """Read data/{LANG}/metadata.json -> {out}/ref/{LANG}.json"""
    ref_out = os.path.join(out_dir, "ref")
    os.makedirs(ref_out, exist_ok=True)
    changed_langs = []

    for lang in sorted(os.listdir(data_root)):
        meta_path = os.path.join(data_root, lang, "metadata.json")
        if not os.path.isfile(meta_path):
            continue
        out_path = os.path.join(ref_out, f"{lang}.json")

        meta = json.load(open(meta_path, encoding="utf-8"))
        segments = []
        for audio in meta.get("audios", []):
            aid = audio.get("aid", "")
            for seg in audio.get("segments", []):
                segments.append({
                    "audio_name": aid,
                    "start": seg.get("begin_time", 0),
                    "end": seg.get("end_time", 0),
                    "text": seg.get("text", ""),
                })

        new_content = json.dumps(segments, ensure_ascii=False, indent=2)
        if os.path.exists(out_path):
            old_content = open(out_path, encoding="utf-8").read()
            if old_content == new_content:
                print(f"[REF] unchanged: {lang} ({len(segments)} segments)")
                continue

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        changed_langs.append(lang)
        print(f"[REF] {lang}: {len(segments)} segments")

    return changed_langs


def convert_hyps(results_root: str, out_dir: str, skip_existing: bool):
    """Read results/{model}.json -> {out}/hyp/{LANG}/{LANG}_{model}.json"""
    hyp_out = os.path.join(out_dir, "hyp")
    os.makedirs(hyp_out, exist_ok=True)
    changed_models = []  # list of (lang, model)

    # Load ref indices for filtering
    ref_out = os.path.join(out_dir, "ref")
    ref_indices = {}
    for rf in glob.glob(os.path.join(ref_out, "*.json")):
        lang = os.path.basename(rf).replace(".json", "")
        data = json.load(open(rf, encoding="utf-8"))
        ref_indices[lang] = {
            (s["audio_name"], round(s["start"], 3), round(s["end"], 3))
            for s in data
        }

    for model_file in sorted(glob.glob(os.path.join(results_root, "*.json"))):
        model = os.path.basename(model_file).replace(".json", "")
        hyp_data = json.load(open(model_file, encoding="utf-8"))

        # Group segments by lang
        by_lang = defaultdict(list)
        for audio in hyp_data.get("audios", []):
            aid = audio.get("aid", "")
            for seg in audio.get("segments", []):
                lang = seg.get("lang", "")
                if lang:
                    by_lang[lang].append({
                        "audio_name": aid,
                        "start": seg.get("begin_time", 0),
                        "end": seg.get("end_time", 0),
                        "text": seg.get("text", ""),
                    })

        for lang, items in sorted(by_lang.items()):
            country_dir = os.path.join(hyp_out, lang)
            os.makedirs(country_dir, exist_ok=True)
            out_path = os.path.join(country_dir, f"{lang}_{model}.json")

            ref_idx = ref_indices.get(lang, set())
            matched = []
            for h in items:
                key = (h["audio_name"], round(h["start"], 3), round(h["end"], 3))
                if key in ref_idx:
                    matched.append({
                        "audio_name": h["audio_name"],
                        "start": h["start"],
                        "end": h["end"],
                        "text": h["text"],
                        "model": model,
                    })

            new_content = json.dumps(matched, ensure_ascii=False, indent=2)
            if os.path.exists(out_path):
                old_content = open(out_path, encoding="utf-8").read()
                if old_content == new_content:
                    continue

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            if matched:
                changed_models.append((lang, model))
                print(f"[HYP] {model}/{lang}: {len(matched)}/{len(ref_idx)}")

    return changed_models


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert GigaSpeech-style JSON dataset to pipeline flat format."
    )
    parser.add_argument("--data_root", required=True,
                        help="Path to data/ dir with {LANG}/metadata.json")
    parser.add_argument("--results_root", required=True,
                        help="Path to results/ dir with {model}.json")
    parser.add_argument("--out_dir", required=True,
                        help="Output directory for flat JSON files")
    parser.add_argument("--skip_existing", type=int, default=1, choices=[0, 1])
    args = parser.parse_args()

    convert_refs(args.data_root, args.out_dir, bool(args.skip_existing))
    convert_hyps(args.results_root, args.out_dir, bool(args.skip_existing))
