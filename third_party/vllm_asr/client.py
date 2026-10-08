"""Resumable audio-only batch inference for locally hosted vLLM ASR models."""

from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
import fcntl
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any

import httpx
import soundfile as sf


@dataclass(frozen=True)
class Profile:
    model: str
    port: int
    workers: int
    max_tokens: int = 0


PROFILES = {
    "qwen": Profile("Qwen3-ASR-1.7B", 18100, 128, 512),
    "whisper": Profile("whisper-large-v3", 18101, 48),
    "funasr": Profile("fun-asr-nano", 18102, 16),
    "funasr-mlt": Profile("fun-asr-mlt-nano", 18102, 1),
}
LANGUAGES = {
    "CH": "zh", "CHN": "zh", "EN": "en", "ENG": "en", "USA": "en",
    "JPN": "ja", "KOR": "ko", "VNM": "vi", "THA": "th", "IDN": "id",
    "IND": "id", "MYS": "ms", "FIL": "tl", "PHL": "tl", "GAN": "zh", "JIN": "zh",
    "MIN": "zh", "WU": "zh", "XIANG": "zh", "YUE": "zh",
    "ARE": "ar", "DZA": "ar", "EGY": "ar", "IRQ": "ar", "MAR": "ar",
    "SAU": "ar", "SYR": "ar",
}


def language_code(value: str, profile: str) -> str:
    suffix = value.upper().rsplit("-", 1)[-1]
    code = LANGUAGES.get(suffix, value.lower())
    if profile == "funasr-mlt" and value.upper() == "YUE":
        return "yue"
    if not (len(code) == 2 and code.isascii() and code.isalpha()):
        raise ValueError(f"Use an explicit ISO language code, got {value!r}")
    if profile == "funasr" and code not in {"zh", "en", "ja"}:
        raise ValueError("Fun-ASR-Nano base supports zh/en/ja; this is not the MLT model")
    return code


def load_manifest(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    rows = json.loads(source) if source.lstrip().startswith("[") else [
        json.loads(line) for line in source.splitlines() if line.strip()
    ]
    keys = set()
    for row in rows:
        key = row["segment_key"]
        if not isinstance(key, str) or not key or key in keys:
            raise ValueError(f"Invalid or duplicate segment_key: {key!r}")
        keys.add(key)
        if not isinstance(row.get("audio_path"), str) or not isinstance(row.get("language"), str):
            raise ValueError(f"Missing audio_path/language for {key}")
        if not isinstance(row.get("meta", {}), dict):
            raise ValueError(f"meta must be an object: {key}")
        if "status" in row or "inference" in row:
            raise ValueError("Input must be a source manifest, not inference output")
    return rows


def atomic_json(path: Path, value: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def transcribe(row: dict[str, Any], manifest: Path, args: argparse.Namespace,
               client: httpx.Client) -> dict[str, Any]:
    result = dict(row, hyp_text="", status="error", model=args.model)
    runtime: dict[str, Any] = {"attempts": []}
    result["inference"] = runtime
    started = time.perf_counter()
    try:
        path = manifest.parent / row["audio_path"]
        language = language_code(args.language or row["language"], args.profile)
        info = sf.info(path)
        if info.samplerate != 16000 or info.channels != 1 or not 0 < info.duration <= 30:
            raise ValueError("Expected a pre-cropped 16 kHz mono clip, 0 < duration <= 30 seconds")
        runtime["audio_seconds"] = info.duration
        runtime["request_language"] = language
        data = {"model": args.model, "language": language,
                "temperature": str(args.temperature), "response_format": "json"}
        if args.max_completion_tokens:
            data["max_completion_tokens"] = str(args.max_completion_tokens)
        audio = path.read_bytes()
        errors = empty = 0
        while True:
            attempt: dict[str, Any] = {}
            runtime["attempts"].append(attempt)
            try:
                response = client.post(args.base_url.rstrip("/") + "/audio/transcriptions",
                                       data=data, files={"file": (path.name, audio, "audio/wav")})
                attempt["http_status"] = response.status_code
                attempt["request_id"] = response.headers.get("x-request-id", "")
                response.raise_for_status()
                raw = response.json()["text"]
                if not isinstance(raw, str):
                    raise ValueError("Response text must be a string")
                text = raw.split("<asr_text>", 1)[-1].strip() if args.profile == "qwen" else raw
                text = text if text.strip() else ""
                attempt["raw_text"] = raw
                result.update(hyp_text=text, status="done")
                if text or empty >= args.empty_retries:
                    break
                empty += 1
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                attempt["error"] = str(exc)
                # Preserve a valid empty transcription if a later retry fails.
                if errors >= args.retries:
                    break
                errors += 1
                time.sleep(min(2 ** (errors - 1), 8))
    except Exception as exc:
        runtime["error"] = f"{type(exc).__name__}: {exc}"
    runtime["latency_seconds"] = time.perf_counter() - started
    return result


def run_manifest(manifest: Path, output: Path, args: argparse.Namespace) -> int:
    rows = load_manifest(manifest)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(manifest, output, rows, args)


def run_locked(manifest: Path, output: Path, rows: list[dict[str, Any]],
               args: argparse.Namespace) -> int:
    settings = {key: getattr(args, key) for key in (
        "profile", "model", "base_url", "language", "temperature", "max_completion_tokens",
        "retries", "empty_retries", "timeout",
    )}
    spec = {"manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "client_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "settings": settings}
    spec_path = output / "run_spec.json"
    dest = output / "output_raw.jsonl"
    if spec_path.exists():
        if not args.resume:
            raise ValueError(f"Existing run: {output}; use --resume or a new output root")
        if json.loads(spec_path.read_text()) != spec:
            raise ValueError("Run specification changed; use a new output root")
    else:
        if dest.exists():
            raise ValueError("Raw output exists without its run specification")
        atomic_json(spec_path, spec)
    latest = {}
    if dest.exists():
        for line in dest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                latest[record["segment_key"]] = record
    if latest.keys() - {row["segment_key"] for row in rows}:
        raise ValueError("Output contains keys absent from the input")
    pending = [row for row in rows if row["segment_key"] not in latest or (
        args.retry_errors and latest[row["segment_key"]]["status"] == "error"
    )]
    if args.max_items is not None:
        pending = pending[:args.max_items]
    completed = 0
    audio_seconds = 0.0
    started = time.perf_counter()
    records = iter(pending)
    limits = httpx.Limits(max_connections=args.workers, max_keepalive_connections=args.workers)
    with httpx.Client(timeout=args.timeout, limits=limits, trust_env=False) as client, \
            dest.open("a", encoding="utf-8") as writer, \
            ThreadPoolExecutor(max_workers=args.workers) as executor:
        active = set()

        def schedule() -> None:
            row = next(records, None)
            if row is not None:
                active.add(executor.submit(transcribe, row, manifest, args, client))

        for _ in range(args.workers):
            schedule()
        while active:
            finished, active = wait(active, return_when=FIRST_COMPLETED)
            for future in finished:
                row = future.result()
                writer.write(json.dumps(row, ensure_ascii=False) + "\n")
                writer.flush()
                latest[row["segment_key"]] = row
                completed += 1
                if row["status"] == "done":
                    audio_seconds += row["inference"].get("audio_seconds", 0)
                if completed % args.log_every == 0:
                    print(f"{manifest.parent.name}: {completed}/{len(pending)}", flush=True)
                schedule()
    wall = time.perf_counter() - started
    summary = {"total": len(rows), "completed": len(latest), "attempted_current": completed,
               "errors": sum(r["status"] == "error" for r in latest.values()),
               "empty_outputs": sum(r["status"] == "done" and not r["hyp_text"] for r in latest.values()),
               "remaining": len(rows) - len(latest), "wall_seconds_current": wall,
               "audio_seconds_current": audio_seconds, "rtfx_current": audio_seconds / max(wall, 1e-9)}
    atomic_json(output / "summary.json", summary)
    print(json.dumps({"dataset": manifest.parent.name, **summary}), flush=True)
    return int(summary["errors"] > 0)


def main(profile: str) -> None:
    defaults = PROFILES[profile]
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-json", type=Path, help="One JSON-list or JSONL manifest")
    source.add_argument("--input-root", type=Path, help="Recursively find input_prepare.json files")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--base-url", default=f"http://127.0.0.1:{defaults.port}/v1")
    parser.add_argument("--model", default=defaults.model)
    parser.add_argument("--language", help="Explicit ISO language override for this invocation")
    parser.add_argument("--workers", type=int, default=defaults.workers)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max-completion-tokens", type=int, default=defaults.max_tokens)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--retries", type=int, default=0, help="Additional requests after HTTP/response errors")
    parser.add_argument("--empty-retries", type=int, default=0, help="Additional requests after empty text")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--log-every", type=int, default=1000)
    args = parser.parse_args()
    args.profile = profile
    if min(args.workers, args.log_every) < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("workers, log-every and timeout must be positive")
    if min(args.retries, args.empty_retries, args.max_completion_tokens) < 0:
        parser.error("Retry counts and token limit must be nonnegative")
    if not math.isfinite(args.temperature) or args.temperature < 0:
        parser.error("temperature must be finite and nonnegative")
    if args.max_items is not None and args.max_items < 1:
        parser.error("max-items must be positive")
    if args.retry_errors and not args.resume:
        parser.error("--retry-errors requires --resume")
    manifests = [args.input_json] if args.input_json else sorted(args.input_root.rglob("input_prepare.json"))
    if not manifests:
        parser.error("No input manifests found")
    failures = 0
    for manifest in manifests:
        # Preserve relative dataset hierarchy to avoid collisions between suites.
        relative = Path() if args.input_json else manifest.parent.relative_to(args.input_root)
        failures += run_manifest(manifest, args.output_root / relative, args)
    raise SystemExit(int(failures > 0))


if __name__ == "__main__":
    import sys
    selected = sys.argv.pop(1)
    if selected not in PROFILES:
        raise SystemExit(f"Unknown profile: {selected}")
    main(selected)
