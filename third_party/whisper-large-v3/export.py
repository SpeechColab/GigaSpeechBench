"""Export one complete raw run to the official flat reference/hypothesis schema."""

import argparse
import json
from pathlib import Path

from infer import load_manifest


def collect(manifest: Path, raw: Path, allow_errors: bool = False) -> tuple[list, list]:
    rows = load_manifest(manifest)
    latest = {}
    for line in raw.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            latest[row["segment_key"]] = row
    if set(latest) != {r["segment_key"] for r in rows}:
        raise ValueError("Raw output must cover exactly the source manifest keys")
    refs, hyps = [], []
    seen = set()
    for row in rows:
        prediction = latest[row["segment_key"]]
        if prediction["status"] != "done" and not allow_errors:
            raise ValueError("Failed requests remain; retry them or use --allow-errors explicitly")
        for key in ("audio_path", "language", "meta", "ref_text"):
            if prediction.get(key) != row.get(key):
                raise ValueError(f"Source metadata mismatch: {row['segment_key']}: {key}")
        meta = row["meta"]
        entry = {"audio_name": meta["ref_audio_name"], "start": meta["start_time"], "end": meta["end_time"]}
        key = (entry["audio_name"], entry["start"], entry["end"])
        if key in seen:
            raise ValueError(f"Duplicate evaluation identity: {key}")
        seen.add(key)
        text = prediction["hyp_text"]
        if not isinstance(text, str):
            raise ValueError("hyp_text must be a string")
        refs.append(dict(entry, text=row["ref_text"]))
        hyps.append(dict(entry, text=text))
    return refs, hyps


def export(manifest: Path, raw: Path, output: Path, allow_errors: bool = False) -> None:
    refs, hyps = collect(manifest, raw, allow_errors)
    output.mkdir(parents=True, exist_ok=False)
    for name, values in (("ref.json", refs), ("hyp.json", hyps)):
        (output / name).write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-errors", action="store_true")
    args = parser.parse_args()
    export(args.input_json, args.raw, args.output_dir, args.allow_errors)
