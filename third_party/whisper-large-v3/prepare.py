"""Prepare cropped manifests directly from the public HF GigaSpeechBench layout."""

from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import tarfile
from typing import Any

import numpy as np
from scipy.signal import resample_poly
import soundfile as sf

from infer import atomic_json


def prepare_group(source: Path, output: Path, language: str,
                  limit: int | None = None, end_tolerance_ms: float = 10.0) -> Path:
    if not math.isfinite(end_tolerance_ms) or end_tolerance_ms < 0:
        raise ValueError("end_tolerance_ms must be finite and nonnegative")
    metadata = source / "metadata.json"
    content = metadata.read_bytes()
    spec = {"metadata_sha256": hashlib.sha256(content).hexdigest(),
            "prepare_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "language": language, "limit": limit, "sample_rate": 16000,
            "end_tolerance_ms": end_tolerance_ms}
    manifest = output / "input_prepare.json"
    marker = output / "prepare_spec.json"
    if marker.exists():
        if json.loads(marker.read_text()) != spec:
            raise ValueError(f"Preparation settings changed: use a new work directory ({output})")
        rows = json.loads(manifest.read_text())
        if not all((output / row["audio_path"]).is_file() for row in rows):
            raise ValueError(f"Prepared audio is missing in {output}")
        return manifest
    selected: dict[str, list[dict[str, Any]]] = {}
    rows = []
    keys = set()
    identities = set()
    for audio in json.loads(content)["audios"]:
        aid = audio.get("aid", audio.get("audio_name"))
        if not isinstance(aid, str) or not aid or Path(aid).name != aid:
            raise ValueError(f"Invalid recording identity: {aid!r}")
        for index, segment in enumerate(audio["segments"]):
            if segment.get("status", "valid") != "valid":
                continue
            start = float(segment.get("begin_time", segment.get("start")))
            end = float(segment.get("end_time", segment.get("end")))
            if not all(map(math.isfinite, (start, end))) or not 0 <= start < end or end - start > 30:
                raise ValueError(f"Invalid or >30s segment: {aid}: {start}, {end}")
            key = segment.get("sid", f"{aid}|{index}|{start}|{end}")
            identity = (aid, start, end)
            if key in keys or identity in identities:
                raise ValueError(f"Duplicate segment identity: {key}")
            keys.add(key)
            identities.add(identity)
            row = {"segment_key": key,
                   "audio_path": "cropped_audios/" + hashlib.sha256(key.encode()).hexdigest() + ".wav",
                   "language": language, "ref_text": segment["text"],
                   "meta": {"ref_audio_name": aid, "start_time": start, "end_time": end,
                            "duration": end - start, "source_segment": segment}}
            rows.append(row)
            selected.setdefault(aid, []).append(row)
            if limit and len(rows) >= limit:
                break
        if limit and len(rows) >= limit:
            break
    if not rows:
        raise ValueError(f"No valid segments: {metadata}")
    (output / "cropped_audios").mkdir(parents=True, exist_ok=True)
    remaining = set(selected)
    clamped = []

    def crop(aid: str, stream: Any) -> None:
        with sf.SoundFile(stream) as audio:
            rate = audio.samplerate
            for row in selected[aid]:
                start = round(row["meta"]["start_time"] * rate)
                end = round(row["meta"]["end_time"] * rate)
                overrun = end - len(audio)
                if overrun > round(end_tolerance_ms * rate / 1000) or start >= len(audio):
                    raise ValueError(f"Segment exceeds recording: {row['segment_key']}")
                if overrun > 0:
                    adjustment = {"segment_key": row["segment_key"], "source_sample_rate": rate,
                                  "overrun_frames": overrun, "overrun_ms": overrun * 1000 / rate}
                    clamped.append(adjustment)
                    row["meta"]["end_clamp"] = adjustment
                end = min(end, len(audio))
                if end <= start:
                    raise ValueError(f"Empty segment after rounding: {row['segment_key']}")
                audio.seek(start)
                samples = audio.read(end - start, dtype="float32", always_2d=True).mean(axis=1)
                if rate != 16000:
                    divisor = math.gcd(rate, 16000)
                    samples = resample_poly(samples, 16000 // divisor, rate // divisor)
                if not np.isfinite(samples).all():
                    raise ValueError(f"Non-finite audio: {aid}")
                dest = output / row["audio_path"]
                temp = dest.with_suffix(".tmp.wav")
                sf.write(temp, samples, 16000, subtype="PCM_16")
                temp.replace(dest)
        remaining.remove(aid)

    # Prefer an already extracted audio directory. Never modify the source tree.
    audio_root = source / "audio"
    if audio_root.is_dir():
        matches = {}
        for path in audio_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".wav", ".flac", ".mp3", ".ogg"}:
                if path.stem in matches:
                    raise ValueError(f"Ambiguous recording filename: {path.stem}")
                matches[path.stem] = path
        for aid in list(remaining):
            if aid in matches:
                crop(aid, str(matches[aid]))
    archive = source / "audio.tar.gz"
    if remaining and archive.exists():
        # Read members directly instead of extracting paths supplied by an archive.
        with tarfile.open(archive, "r|gz") as tar:
            for member in tar:
                aid = Path(member.name).stem
                if member.isfile() and aid in remaining:
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise ValueError(f"Unreadable archive member: {member.name}")
                    crop(aid, io.BytesIO(stream.read()))
                if not remaining:
                    break
    if remaining:
        raise FileNotFoundError(f"Missing recordings in {source}: {sorted(remaining)[:5]}")
    atomic_json(manifest, rows)
    atomic_json(output / "preparation_report.json", {"segments": len(rows),
                "end_tolerance_ms": end_tolerance_ms, "clamped_count": len(clamped), "clamped": clamped})
    atomic_json(marker, spec)
    print(f"Prepared {source.parent.parent.name}/{source.name}: {len(rows)} clips", flush=True)
    return manifest
