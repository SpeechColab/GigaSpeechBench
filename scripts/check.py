#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path
from collections import defaultdict

# =========================
# Official configuration
# =========================

COUNTRY_LIST = {
    "IRQ", "DZA", "ARE", "EGY", "MAR", "SAU",
    "IDN", "MYS", "PHL", "VNM", "THA", "JPN", "KOR"
}

MODEL_WHITELIST = {
    "azure",
    "chirp3",
    "elevenlabs_scribe_v2",
    "omniASR_LLM_3B",
    "qwen3-asr-flash",
    "nvidia-nemo",
    "gpt4o-transcribe",
    "gemini_3_0_flash",
    "whisper",
    "dolphin_small",
    "dolphin_base",
    "fun-asr-mlt-nano",
}

EXPECTED_SEGMENTS = {
    "ARE": 18313,
    "DZA": 20060,
    "EGY": 18248,
    "IDN": 24178,
    "IRQ": 16408,
    "JPN": 14272,
    "KOR": 12166,
    "MAR": 15963,
    "MYS": 26519,
    "PHL": 17937,
    "SAU": 13286,
    "THA": 20122,
    "VNM": 15996,
}

REQUIRED_KEYS = {
    "audio_name",
    "text",
    "language",
    "model",
    "start_time",
    "end_time",
}


# =========================
# Validate a single JSON file
# =========================

def check_json(json_path: Path):
    problems = set()

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {f"JSON parse failed: {e}"}

    if not isinstance(data, list):
        return {"JSON top-level must be a list"}

    # language and segment count validation
    langs = {seg.get("language") for seg in data if isinstance(seg, dict)}
    langs = {l for l in langs if isinstance(l, str)}

    if len(langs) != 1:
        problems.add("language must be unique (one country per JSON)")
    else:
        lang = next(iter(langs))
        if lang not in COUNTRY_LIST:
            problems.add(f"language not in country list: {lang}")
        else:
            expected = EXPECTED_SEGMENTS[lang]
            if len(data) != expected:
                problems.add(f"segment count mismatch (expected {expected}, actual {len(data)}）")

    for seg in data:
        if not isinstance(seg, dict):
            problems.add("found non-dict segment")
            break

        missing = REQUIRED_KEYS - seg.keys()
        if missing:
            problems.add("found segment with missing fields")
            break

        if not isinstance(seg["audio_name"], str) or not seg["audio_name"].endswith(".wav"):
            problems.add("found segment where audio_name does not end with .wav")

        if not isinstance(seg["text"], str):
            problems.add("found segment where text is not a string")

        if not isinstance(seg["model"], str) or seg["model"] not in MODEL_WHITELIST:
            problems.add("found segment with model not in whitelist")

        try:
            st = float(seg["start_time"])
            et = float(seg["end_time"])
            if et <= st or st < 0:
                problems.add("found invalid time range (start_time / end_time)")
        except Exception:
            problems.add("found segment with non-numeric start_time / end_time")

    return problems


# =========================
# Main entry
# =========================

def main():
    if len(sys.argv) != 2:
        print("Usage: python check.py <submission_dir>")
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"[❌ ERROR] {root} is not a directory")
        sys.exit(1)

    json_files = sorted(root.glob("*.json"))
    if not json_files:
        print("[❌ ERROR] no JSON files found in directory")
        sys.exit(1)

    all_errors = {}

    for p in json_files:
        probs = check_json(p)
        if probs:
            all_errors[p.name] = sorted(probs)

    if not all_errors:
        print("🎉 [PASS] All JSON validation passed. Ready to submit.")
        sys.exit(0)

    print(f"\n❌ Validation failed: {len(all_errors)} files have issues\n")

    for fname, probs in all_errors.items():
        print(f"{fname}:")
        for msg in probs:
            print(f"  - {msg}")
        print()

    sys.exit(2)


if __name__ == "__main__":
    main()
