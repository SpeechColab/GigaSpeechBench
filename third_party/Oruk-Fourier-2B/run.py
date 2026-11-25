"""Run or rescore Oruk Fourier 2B across English GigaSpeechBench splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODEL = "Oruk-Fourier-2B"
MODEL_ID = "oruk/oruk-fourier-2b"
REVISION = "8c2a8871f1304aa2f634da4fb95e24438c4945b9"
WEIGHT_BYTES = 4_076_193_080
WEIGHT_SHA = "e64765ffdd90c83704c0951e0d88b7f2ed84499af5c208f7ddf8d922cf08441c"
TOKENIZER_SHA = "bd2a97b55c8f7f9c328c73ee9b9178771037e9f566dfca8e238a063d41cbac92"
MODEL_FILES = [
    "model.safetensors",
    "config.json",
    "generation_config.json",
    "processor_config.json",
    "tokenizer_config.json",
    "tokenizer.json",
    "chat_template.jinja",
]

ENGLISH_GROUPS: dict[str, tuple[str, ...]] = {
    "CH-EN-Dialects": ("CHN-EN", "IND-EN", "JPN-EN", "PHL-EN", "SCT-EN", "SGP-EN"),
    "Vertical-Domain": (
        "AGR-EN",
        "AIT-EN",
        "ART-EN",
        "BIO-EN",
        "ECM-EN",
        "ENG-EN",
        "ENT-EN",
        "FIN-EN",
        "HUM-EN",
        "LAW-EN",
        "MED-EN",
        "MIL-EN",
    ),
    "Older-Children": ("CHILD-EN", "OLD-EN"),
}


def sha256_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest()


def resolve_group_dirs(
    data_path: Path, module: str, groups_arg: str | None
) -> list[tuple[str, Path]]:
    """Resolve either a single group directory (PR #14 compatible) or a module data root."""
    allowed = ENGLISH_GROUPS[module]
    if groups_arg and groups_arg.lower() != "all":
        requested = [g.strip() for g in groups_arg.split(",") if g.strip()]
    else:
        requested = None

    # Backward-compatible single-group path (e.g. .../CH-EN-Dialects/data/PHL-EN)
    if data_path.name in allowed and (
        (data_path / "metadata.json").is_file() or (data_path / "test").is_dir()
    ):
        if requested and requested != [data_path.name]:
            raise ValueError(
                f"--data points to single group {data_path.name}, which conflicts with --groups={groups_arg}"
            )
        return [(data_path.name, data_path)]

    # Module data root (e.g. .../CH-EN-Dialects/data or release root .../CH-EN-Dialects)
    base = data_path / "data" if (data_path / "data").is_dir() else data_path
    if (base / module / "data").is_dir():
        base = base / module / "data"

    target_groups = requested or list(allowed)
    resolved: list[tuple[str, Path]] = []
    for grp in target_groups:
        if grp not in allowed:
            raise ValueError(f"Unsupported English group {grp!r} for module {module!r}")
        gdir = base / grp
        if not gdir.is_dir():
            raise FileNotFoundError(f"Missing release group directory: {gdir}")
        resolved.append((grp, gdir.resolve(strict=True)))
    return resolved


def validate_predictions(path: Path, expected_by_group: dict[str, list[tuple]]) -> None:
    with path.open(encoding="utf-8") as handle:
        predictions = json.load(handle)["audios"]

    actual_by_group: dict[str, list[tuple]] = {}
    for recording in predictions:
        aid = recording["aid"]
        grp = recording.get("language") or aid.split("#", 1)[0]
        if grp not in expected_by_group:
            continue
        bucket = actual_by_group.setdefault(grp, [])
        for segment in recording["segments"]:
            bucket.append(
                (aid, segment["sid"], segment["begin_time"], segment["end_time"])
            )

    for grp, expected in expected_by_group.items():
        actual = actual_by_group.get(grp, [])
        if actual != expected:
            raise ValueError(
                f"Prediction recording IDs, segment IDs or boundaries differ from the release for {grp} "
                f"(expected {len(expected)} segments, got {len(actual)})"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--module",
        choices=tuple(ENGLISH_GROUPS.keys()),
        default="CH-EN-Dialects",
        help="GigaSpeechBench module (default: CH-EN-Dialects)",
    )
    parser.add_argument(
        "--groups",
        default=None,
        help="Comma-separated English group codes or 'all' (default: inferred from --data or all English groups)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Single group dir (e.g. CH-EN-Dialects/data/PHL-EN), module data dir, or release root",
    )
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument(
        "--score-only",
        type=Path,
        metavar="PREDICTIONS",
        help="Rescore a complete merged result JSON on CPU",
    )
    args = parser.parse_args()

    benchmark = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(benchmark))
    from data_process.release_data import iter_audio_records
    from text_norm import get_normalizer
    from text_norm.USA import normalize as english_normalize

    group_dirs = resolve_group_dirs(args.data.resolve(strict=True), args.module, args.groups)
    expected_by_group: dict[str, list[tuple]] = {}
    for grp, gdir in group_dirs:
        if get_normalizer(grp) is not english_normalize:
            raise RuntimeError(
                f"The benchmark's English normalizer is unavailable for {grp}"
            )
        expected = [
            (
                recording.get("aid", recording.get("audio_name")),
                seg["sid"],
                seg["begin_time"],
                seg["end_time"],
            )
            for recording in iter_audio_records(gdir)
            for seg in recording["segments"]
            if seg.get("status", "valid") == "valid"
        ]
        if not expected:
            raise ValueError(f"No valid segments found in {gdir}")
        expected_by_group[grp] = expected

    if args.score_only:
        validate_predictions(args.score_only, expected_by_group)

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    stage = out / "stage"
    for grp, gdir in group_dirs:
        dst = stage / args.module / "data" / grp
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(gdir, target_is_directory=True)

    result = stage / args.module / "results" / f"{MODEL}.json"
    if args.score_only:
        result.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.score_only, result)
    else:
        from huggingface_hub import snapshot_download

        sys.path.insert(0, str(benchmark / "third_party" / "Qwen3-ASR-1.7B"))
        from prepare import prepare_group

        snapshot = Path(
            snapshot_download(
                MODEL_ID, revision=REVISION, allow_patterns=MODEL_FILES
            )
        )
        wbytes, wsha = sha256_file(snapshot / "model.safetensors")
        if wbytes != WEIGHT_BYTES or wsha != WEIGHT_SHA:
            raise ValueError("The model weights do not match the pinned checkpoint")
        _, tsha = sha256_file(snapshot / "tokenizer.json")
        if tsha != TOKENIZER_SHA:
            raise ValueError("The tokenizer does not match the pinned checkpoint")

        prepared_dirs: list[Path] = []
        for grp, gdir in group_dirs:
            prep_dir = out / "prepared" / grp
            manifest = prepare_group(gdir, prep_dir, grp)
            rows = json.loads(manifest.read_text())
            expected = expected_by_group[grp]
            if [row["segment_key"] for row in rows] != [seg[1] for seg in expected]:
                raise ValueError(f"Prepared clips disagree with release segment IDs for {grp}")
            prepared_dirs.append(prep_dir)

        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("transcribe.py")),
                "--module",
                args.module,
                "--stage",
                str(stage),
                "--prepared",
                *[str(p) for p in prepared_dirs],
            ],
            check=True,
            env={
                **os.environ,
                "HF_HUB_OFFLINE": "1",
                "VLLM_NO_USAGE_STATS": "1",
                "TOKENIZERS_PARALLELISM": "false",
                "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
            },
        )
        validate_predictions(result, expected_by_group)

    reports = out / "scored"
    subprocess.run(
        ["bash", str(benchmark / "run_ASR.sh"), args.module, "0"],
        check=True,
        env={
            **os.environ,
            "STAGING_ROOT": str(stage),
            "OUT_ROOT": str(reports),
            "MODELS": MODEL,
            "PYTHON_BIN": sys.executable,
        },
    )
    for grp, _ in group_dirs:
        print(f"=== {args.module}/{grp} ===")
        for title, variant in (("All segments", ""), ("Duration > 0.5 s", "_mindur")):
            directory = (
                reports / "data" / f"results_{args.module}{variant}" / grp / MODEL.upper()
            )
            print(
                title,
                (directory / f"errs-{grp}-{MODEL.upper()}.txt").read_text().strip(),
                (directory / "segment_check.txt").read_text().strip(),
                sep="\n",
            )
    print(f"Prediction file: {result}")


if __name__ == "__main__":
    main()
