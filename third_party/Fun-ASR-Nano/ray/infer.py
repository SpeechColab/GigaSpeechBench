"""Persistent Ray/FunASR MLT replicas; references never enter worker processes."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_common"))
from client import atomic_json, language_code, load_manifest

MODEL_REPO = "FunAudioLLM/Fun-ASR-MLT-Nano-2512"
MODEL_REVISION = "2c088f535108689beff7e11cdc3d792af7d56552"
LANGUAGE_NAMES = {
    "zh": "\u4e2d\u6587", "en": "\u82f1\u6587", "ja": "\u65e5\u6587",
    "ko": "\u97e9\u6587", "vi": "\u8d8a\u5357\u6587", "id": "\u5370\u5c3c\u6587",
    "th": "\u6cf0\u6587", "ms": "\u9a6c\u6765\u6587", "tl": "\u83f2\u5f8b\u5bbe\u6587",
    "ar": "\u963f\u62c9\u4f2f\u6587", "yue": "\u7ca4\u8bed",
}


class Worker:
    def __init__(self, model_path: str):
        import torch
        from funasr import AutoModel
        import funasr.models.fun_asr_nano.model  # Register the packaged model implementation.

        torch.set_num_threads(2)
        self.model = AutoModel(model=model_path, device="cuda:0", disable_update=True,
                               trust_remote_code=False, ctc_decoder=None)

    def ready(self) -> dict:
        import importlib.metadata
        return {"pid": os.getpid(), "visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                "versions": {name: importlib.metadata.version(name)
                             for name in ("funasr", "ray", "torch", "transformers")}}

    def transcribe(self, path: str, language: str, empty_retries: int) -> dict:
        import soundfile as sf
        import torch

        started = time.perf_counter()
        result = {"hyp_text": "", "status": "error", "inference": {"backend": "ray-funasr", "attempts": []}}
        runtime = result["inference"]
        try:
            info = sf.info(path)
            if info.samplerate != 16000 or info.channels != 1 or not 0 < info.duration <= 30:
                raise ValueError("Expected a 16 kHz mono clip no longer than 30 seconds")
            samples, _ = sf.read(path, dtype="float32")
            runtime["audio_seconds"] = info.duration
            runtime["request_language"] = language
            for _ in range(empty_retries + 1):
                raw = self.model.generate(input=[torch.from_numpy(samples)], cache={}, batch_size=1,
                                          language=LANGUAGE_NAMES[language], hotwords=[], itn=True,
                                          max_length=512, llm_kwargs={"do_sample": False})
                text = raw[0]["text"]
                if not isinstance(text, str):
                    raise TypeError("Model text must be a string")
                runtime["attempts"].append({"raw_text": text})
                result.update(hyp_text=text if text.strip() else "", status="done")
                if text.strip():
                    break
        except Exception as exc:
            runtime["error"] = f"{type(exc).__name__}: {exc}"
        runtime["latency_seconds"] = time.perf_counter() - started
        return result


def run_group(manifest: Path, output: Path, actors: list, args: argparse.Namespace,
              model_path: str) -> int:
    import ray

    rows = load_manifest(manifest)
    for row in rows:
        if language_code(row["language"], "funasr-mlt") not in LANGUAGE_NAMES:
            raise ValueError(f"Unsupported benchmark language: {row['language']}")
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        spec = {"manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "client_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "model": MODEL_REPO, "revision": args.revision, "model_path": model_path,
                "backend": "ray-funasr", "empty_retries": args.empty_retries,
                "itn": True, "do_sample": False, "max_new_tokens": 512, "ctc_decoder": None}
        marker = output / "run_spec.json"
        dest = output / "output_raw.jsonl"
        if marker.exists():
            if not args.resume or json.loads(marker.read_text()) != spec:
                raise ValueError(f"Existing or incompatible run: {output}; use --resume or a fresh output")
        else:
            if dest.exists():
                raise ValueError("Output exists without a run specification")
            atomic_json(marker, spec)
        latest = {}
        if dest.exists():
            for line in dest.read_text().splitlines():
                record = json.loads(line)
                latest[record["segment_key"]] = record
        if latest.keys() - {r["segment_key"] for r in rows}:
            raise ValueError("Unexpected keys in output")
        pending = iter(r for r in rows if r["segment_key"] not in latest or (
            args.retry_errors and latest[r["segment_key"]]["status"] == "error"))
        active = {}

        def schedule(actor):
            row = next(pending, None)
            if row is not None:
                # Only path and language are passed to Ray, never the source row.
                ref = actor.transcribe.remote(str((manifest.parent / row["audio_path"]).resolve()),
                    language_code(row["language"], "funasr-mlt"), args.empty_retries)
                active[ref] = (actor, row)

        started = time.perf_counter()
        attempted = 0
        with dest.open("a", encoding="utf-8") as writer:
            for actor in actors:
                schedule(actor)
            while active:
                ready, _ = ray.wait(list(active), num_returns=1)
                for ref in ready:
                    actor, row = active.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {"hyp_text": "", "status": "error", "inference": {"error": str(exc)}}
                    record = dict(row, **result, model="Fun-ASR-MLT-Nano-2512")
                    writer.write(json.dumps(record, ensure_ascii=False) + "\n")
                    writer.flush()
                    latest[row["segment_key"]] = record
                    attempted += 1
                    if attempted % 100 == 0:
                        print(f"{manifest.parent.name}: completed={len(latest)}/{len(rows)}", flush=True)
                    schedule(actor)
        summary = {"total": len(rows), "completed": len(latest), "attempted_current": attempted,
                   "errors": sum(r["status"] == "error" for r in latest.values()),
                   "empty_outputs": sum(r["status"] == "done" and not r["hyp_text"] for r in latest.values()),
                   "remaining": len(rows) - len(latest), "wall_seconds_current": time.perf_counter() - started}
        atomic_json(output / "summary.json", summary)
        print(json.dumps(summary), flush=True)
        return int(summary["errors"] > 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--revision", default=MODEL_REVISION)
    parser.add_argument("--actors-per-gpu", type=int, default=2)
    parser.add_argument("--num-gpus", type=int, default=1)
    parser.add_argument("--empty-retries", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()
    if min(args.num_gpus, args.actors_per_gpu) < 1 or args.empty_retries < 0:
        parser.error("GPU/actor counts must be positive and retries nonnegative")
    if args.retry_errors and not args.resume:
        parser.error("--retry-errors requires --resume")
    manifests = sorted(args.input_root.rglob("input_prepare.json"))
    if not manifests:
        parser.error("No input manifests found")
    if args.model_path:
        model_path = str(args.model_path.resolve())
    else:
        from huggingface_hub import snapshot_download
        model_path = snapshot_download(MODEL_REPO, revision=args.revision)
    import ray

    os.environ.setdefault("RAY_USAGE_STATS_ENABLED", "0")
    ray.init(address="local", num_gpus=args.num_gpus, include_dashboard=False,
             num_cpus=max(2, args.num_gpus * args.actors_per_gpu * 2), object_store_memory=512 * 1024**2)
    try:
        actor_type = ray.remote(num_gpus=1 / args.actors_per_gpu, num_cpus=1,
                               max_restarts=0, max_task_retries=0)(Worker)
        actors = [actor_type.remote(model_path) for _ in range(args.num_gpus * args.actors_per_gpu)]
        actor_info = ray.get([actor.ready.remote() for actor in actors])
        args.output_root.mkdir(parents=True, exist_ok=True)
        atomic_json(args.output_root / "actors.json", actor_info)
        failures = sum(run_group(p, args.output_root / p.parent.relative_to(args.input_root), actors,
                                 args, model_path) for p in manifests)
    finally:
        ray.shutdown()
    raise SystemExit(int(failures > 0))


if __name__ == "__main__":
    main()
