"""One-command HF preparation, model setup, inference and official-format export."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

from infer import PROFILES, atomic_json, language_code
from export import collect
from prepare import prepare_group

HERE = Path(__file__).resolve().parent
DATASET = "speechcolab/GigaSpeechBench"
REVISION = "680d3057641b7507a1ef14974407c7b0a7964e64"
SUBSETS = {
    "low-resource": ["Low-Resource-Languages"],
    "zh-en": ["Vertical-Domain", "CH-EN-Dialects"],
    "vertical-domain": ["Vertical-Domain"],
    "dialects": ["CH-EN-Dialects"],
    "older-children": ["Older-Children"],
    "all": ["Low-Resource-Languages", "Vertical-Domain", "CH-EN-Dialects"],
}
MODEL = "qwen"
LABEL = "Qwen3-ASR-1.7B"

SOURCE_FILES = (
    'run.py',
    'requirements.txt',
    'infer.py',
    'prepare.py',
    'export.py',
    'serve.sh',
)


def setup_python(args: argparse.Namespace) -> Path:
    if args.python_bin:
        # Resolving this symlink would bypass the venv and invoke system Python.
        python = args.python_bin.absolute()
        if not python.is_file():
            raise FileNotFoundError(python)
        return python
    return Path(sys.executable).absolute()


@contextmanager
def serving(profile: str, python: Path, args: argparse.Namespace, log: Path):
    port = args.port or PROFILES[profile].port
    # Refuse to accidentally use or stop another user's server.
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"Port {port} is in use; choose --port") from exc
    env = dict(os.environ, PYTHON_BIN=str(python), CUDA_VISIBLE_DEVICES=args.gpus,
               HOST="127.0.0.1", PORT=str(port), SERVED_MODEL_NAME=PROFILES[profile].model)
    if args.model_path:
        env["MODEL_PATH"] = str(args.model_path.resolve())
    with log.open("a") as writer:
        process = subprocess.Popen(["bash", str(HERE / "serve.sh")],
                                   env=env, stdout=writer, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + args.startup_timeout
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"Server exited ({process.returncode}); see {log}")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Server startup timed out; see {log}")
                time.sleep(2)
            yield f"http://127.0.0.1:{port}/v1"
        finally:
            # A second Ctrl-C must not interrupt cleanup of the detached server.
            previous = {sig: signal.signal(sig, signal.SIG_IGN)
                        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
            try:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
                # The API process can exit before its engine workers do.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)


def export_module(prepared: Path, raw_root: Path, work: Path, module: str, label: str) -> None:
    audios = {}
    for manifest in sorted(prepared.glob("*/input_prepare.json")):
        group = manifest.parent.name
        refs, hyps = collect(manifest, raw_root / group / "output_raw.jsonl")
        text = work / "pipeline/data/text" / module
        (text / "ref").mkdir(parents=True, exist_ok=True)
        (text / "hyp" / group).mkdir(parents=True, exist_ok=True)
        atomic_json(text / "ref" / f"{group}.json", refs)
        atomic_json(text / "hyp" / group / f"{group}_{label}.json", hyps)
        source_audios = {}
        for row, hyp in zip(json.loads(manifest.read_text()), hyps):
            aid = row["meta"]["ref_audio_name"]
            if not aid.startswith(group + "#"):
                raise ValueError(f"Official staging requires group-prefixed aid: {aid}")
            source_audios.setdefault(aid, {"aid": aid, "segments": []})["segments"].append(
                row["meta"]["source_segment"])
            audios.setdefault(aid, {"aid": aid, "segments": []})["segments"].append({
                "begin_time": hyp["start"], "end_time": hyp["end"], "text": hyp["text"]})
        meta = work / "staging" / module / "data" / group
        meta.mkdir(parents=True, exist_ok=True)
        atomic_json(meta / "metadata.json", {"audios": list(source_audios.values())})
    result = work / "staging" / module / "results"
    result.mkdir(parents=True, exist_ok=True)
    atomic_json(result / f"{label}.json", {"audios": list(audios.values())})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", required=True, choices=SUBSETS)
    parser.add_argument("--data-root", type=Path, required=True, help="Downloaded HF snapshot root")
    parser.add_argument("--work-dir", type=Path, required=True, help="Fresh run directory outside the source data")
    parser.add_argument("--download", action="store_true", help="Download only selected module/group inputs")
    parser.add_argument("--dataset-repo", default=DATASET)
    parser.add_argument("--dataset-revision", default=REVISION)
    parser.add_argument("--groups", nargs="+", help="Optional subgroup names, e.g. KOR JPN or ECM-CH ECM-EN")
    parser.add_argument("--limit-per-group", type=int, help="Smoke test only; changes the evaluated subset")
    parser.add_argument("--end-tolerance-ms", type=float, default=10.0,
                        help="Maximum rounding overrun to clamp at recording end; default 10 ms")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--empty-retries", type=int, default=0)
    parser.add_argument("--gpus", default="0")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--port", type=int)
    parser.add_argument("--startup-timeout", type=float, default=900)
    parser.add_argument("--model-path", type=Path, help="Local model checkpoint")
    parser.add_argument("--python-bin", type=Path, help="Use an already installed model environment")
    args = parser.parse_args()
    if not math.isfinite(args.end_tolerance_ms) or args.end_tolerance_ms < 0:
        parser.error("end-tolerance-ms must be finite and nonnegative")
    if args.limit_per_group is not None and args.limit_per_group < 1:
        parser.error("limit-per-group must be positive")
    if args.startup_timeout <= 0:
        parser.error("startup-timeout must be positive")
    if args.empty_retries < 0 or (args.workers is not None and args.workers < 1):
        parser.error("Invalid retry/worker counts")
    if args.retry_errors and not args.resume:
        parser.error("--retry-errors requires --resume")
    if not args.gpus or any(not part.isdigit() for part in args.gpus.split(",")):
        parser.error("--gpus must be comma-separated physical GPU indices")
    modules = SUBSETS[args.subset]
    args.work_dir = args.work_dir.resolve()
    args.data_root = args.data_root.resolve()
    if args.work_dir == args.data_root or args.data_root.is_relative_to(args.work_dir):
        parser.error("work-dir must not contain the input dataset")
    if args.download:
        from huggingface_hub import snapshot_download
        patterns = [f"{module}/data/{group}/{name}" for module in modules
                    for group in (args.groups or ["*"]) for name in ("metadata.json", "audio.tar.gz")]
        snapshot_download(args.dataset_repo, repo_type="dataset", revision=args.dataset_revision,
                          local_dir=args.data_root, allow_patterns=patterns)
    selected = {module: sorted((args.data_root / module / "data").glob("*/metadata.json")) for module in modules}
    selected = {module: [p for p in paths if not args.groups or p.parent.name in args.groups]
                for module, paths in selected.items()}
    if args.groups:
        found = {p.parent.name for paths in selected.values() for p in paths}
        if set(args.groups) - found:
            parser.error(f"Requested groups missing: {sorted(set(args.groups) - found)}")
        selected = {m: p for m, p in selected.items() if p}
    for module, paths in selected.items():
        if not paths:
            parser.error(f"No metadata for {module}. The pinned public snapshot does not include Older-Children; "
                         "supply a local release in MODULE/data/GROUP/{metadata.json,audio.tar.gz} format.")
    config = {"model": MODEL, "subset": args.subset, "groups": args.groups,
              "limit_per_group": args.limit_per_group, "empty_retries": args.empty_retries,
              "end_tolerance_ms": args.end_tolerance_ms,
              "data_root": str(args.data_root), "dataset_repo": args.dataset_repo,
              "dataset_revision_requested": args.dataset_revision,
              "model_path": str(args.model_path.resolve()) if args.model_path else None,
              "source_hashes": {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (HERE / name for name in SOURCE_FILES)},
              "routing": {m: {"profile": MODEL, "model_label": LABEL,
                               "backend": "vllm"}
                          for m in selected}}
    args.work_dir.mkdir(parents=True, exist_ok=True)
    run_lock = (args.work_dir / ".lock").open("a")
    fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    marker = args.work_dir / "run.json"
    if marker.exists():
        if not args.resume or json.loads(marker.read_text()) != config:
            parser.error("Existing run or changed settings; use --resume with unchanged settings or a fresh work-dir")
    atomic_json(marker, config)
    for module, metadata_paths in selected.items():
        profile = MODEL
        print(f"{module}: {LABEL} via {config['routing'][module]['backend']}", flush=True)
        prepared = args.work_dir / "prepared" / module
        for metadata in metadata_paths:
            group = metadata.parent.name
            language_code(group, profile)
            prepare_group(metadata.parent, prepared / group, group, args.limit_per_group, args.end_tolerance_ms)
        if args.prepare_only:
            continue
        python = setup_python(args)
        raw = args.work_dir / "raw" / module / LABEL
        common = ["--input-root", str(prepared), "--output-root", str(raw), "--empty-retries", str(args.empty_retries)]
        if args.resume:
            common.append("--resume")
        if args.retry_errors:
            common.append("--retry-errors")
        with serving(profile, python, args, args.work_dir / f"{module}.server.log") as endpoint:
            command = [str(python), str(HERE / "infer.py"), *common, "--base-url", endpoint]
            if args.workers:
                command += ["--workers", str(args.workers)]
            # /health may pass even when audio preprocessing dependencies are missing.
            first = next(iter(sorted(prepared.glob("*/input_prepare.json"))))
            probe = list(command)
            source_index = probe.index("--input-root")
            probe[source_index:source_index + 2] = ["--input-json", str(first)]
            probe[probe.index("--output-root") + 1] = str(raw / first.parent.name)
            subprocess.run(probe + ["--max-items", "1"], check=True)
            if "--resume" not in command:
                command.append("--resume")
            subprocess.run(command, check=True)
        export_module(prepared, raw, args.work_dir, module, LABEL)
    print(f"Completed. Run record: {marker}", flush=True)


def interrupted(signum, frame):
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    for stop_signal in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(stop_signal, interrupted)
    main()
