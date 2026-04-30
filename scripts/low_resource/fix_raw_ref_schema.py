#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path


def to_segment_record(data: dict) -> dict | None:
    audio_name = data.get("audio_name")
    text = data.get("text")
    start = data.get("start", data.get("start_time"))
    end = data.get("end", data.get("end_time"))

    if not isinstance(audio_name, str) or not isinstance(text, str):
        return None

    try:
        start = float(start)
        end = float(end)
    except Exception:
        return None

    if end < start:
        return None

    segment = {
        "start": start,
        "end": end,
        "text": text,
        "status": "valid" if text.strip() else "invalid",
        "age_group": str(data.get("age", "") or ""),
        "gender": str(data.get("gender", "") or ""),
        "emotion": str(data.get("emotion", "") or ""),
        "speaker": str(data.get("speaker", "") or ""),
    }

    fixed = {
        "audio_name": audio_name,
        "segments": [segment],
    }

    if "language" in data:
        fixed["language"] = data["language"]
    if "model" in data:
        fixed["model"] = data["model"]

    return fixed


def repair_file(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False

    if isinstance(data, dict) and isinstance(data.get("segments"), list):
        return False

    if not isinstance(data, dict):
        return False

    fixed = to_segment_record(data)
    if fixed is None:
        return False

    path.write_text(json.dumps(fixed, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="Repair raw ref JSON files into audio_name+segments schema.")
    parser.add_argument("--root", required=True, help="Root like .../text/ref")
    parser.add_argument("--countries", nargs="+", required=True, help="Country folders to repair")
    args = parser.parse_args()

    root = Path(args.root)
    repaired = 0
    scanned = 0

    for country in args.countries:
        country_dir = root / country
        for path in sorted(country_dir.glob("*.json")):
            scanned += 1
            if repair_file(path):
                repaired += 1
        print(f"[FIX] {country}: scanned={len(list(country_dir.glob('*.json')))}")

    print(f"repaired={repaired}")
    print(f"scanned={scanned}")


if __name__ == "__main__":
    main()
