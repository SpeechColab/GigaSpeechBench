"""Run or rescore the Oruk Fourier 2B Filipino-accented English evaluation."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODULE = "CH-EN-Dialects"
GROUP = "PHL-EN"
MODEL = "Oruk-Fourier-2B"
SOURCE_ID_SHA = "57855f374d6945ad00eb35b5ad87474c5fb8f2f298b3fde77fae17c5dd44c2b3"
WEIGHT_SHA = "e64765ffdd90c83704c0951e0d88b7f2ed84499af5c208f7ddf8d922cf08441c"
REVISION = "8c2a8871f1304aa2f634da4fb95e24438c4945b9"
MODEL_FILES = [
    "model.safetensors",
    "config.json",
    "generation_config.json",
    "processor_config.json",
    "tokenizer_config.json",
    "tokenizer.json",
    "chat_template.jinja",
]


def validate_predictions(path, expected):
    with path.open(encoding="utf-8") as handle:
        predictions = json.load(handle)["audios"]
    actual = [
        (recording["aid"], segment["sid"], segment["begin_time"], segment["end_time"])
        for recording in predictions
        for segment in recording["segments"]
    ]
    if actual != expected:
        raise ValueError(
            "Prediction recording IDs, segment IDs or boundaries differ from the release"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="The CH-EN-Dialects/data/PHL-EN directory from the release",
    )
    parser.add_argument("--out", type=Path, required=True, help="New output directory")
    parser.add_argument(
        "--score-only",
        type=Path,
        metavar="PREDICTIONS",
        help="Rescore a complete result JSON on CPU",
    )
    args = parser.parse_args()
    benchmark = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(benchmark))
    from data_process.release_data import iter_audio_records
    from text_norm import get_normalizer
    from text_norm.USA import normalize as english_normalize

    if get_normalizer(GROUP) is not english_normalize:
        raise RuntimeError("The benchmark's English normalizer is unavailable")

    source_data = args.data.resolve(strict=True)
    expected = [
        (
            recording.get("aid", recording.get("audio_name")),
            seg["sid"],
            seg["begin_time"],
            seg["end_time"],
        )
        for recording in iter_audio_records(source_data)
        for seg in recording["segments"]
        if seg.get("status", "valid") == "valid"
    ]
    ids = "\n".join(segment[1] for segment in expected)
    if (
        len(expected) != 8637
        or hashlib.sha256(ids.encode()).hexdigest() != SOURCE_ID_SHA
    ):
        raise ValueError(
            "The supplied data does not match the complete pinned PHL-EN release"
        )

    if args.score_only:
        validate_predictions(args.score_only, expected)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    stage = out / "stage"
    group = stage / MODULE / "data" / GROUP
    group.parent.mkdir(parents=True)
    group.symlink_to(source_data, target_is_directory=True)
    result = stage / MODULE / "results" / f"{MODEL}.json"
    if args.score_only:
        result.parent.mkdir(parents=True)
        shutil.copyfile(args.score_only, result)
    else:
        from huggingface_hub import snapshot_download

        sys.path.insert(0, str(benchmark / "third_party" / "Qwen3-ASR-1.7B"))
        from prepare import prepare_group

        snapshot = Path(
            snapshot_download(
                "oruk/oruk-fourier-2b", revision=REVISION, allow_patterns=MODEL_FILES
            )
        )
        with (snapshot / "model.safetensors").open("rb") as tensor:
            if hashlib.file_digest(tensor, "sha256").hexdigest() != WEIGHT_SHA:
                raise ValueError("The model weights do not match the pinned checkpoint")
        prepared = out / "prepared"
        manifest = prepare_group(source_data, prepared, GROUP)
        rows = json.loads(manifest.read_text())
        if [row["segment_key"] for row in rows] != [segment[1] for segment in expected]:
            raise ValueError("Prepared clips disagree with the original segment IDs")
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("transcribe.py")),
                "--prepared",
                str(prepared),
                "--stage",
                str(stage),
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
        validate_predictions(result, expected)
    reports = out / "scored"
    subprocess.run(
        ["bash", str(benchmark / "run_ASR.sh"), MODULE, "0"],
        check=True,
        env={
            **os.environ,
            "STAGING_ROOT": str(stage),
            "OUT_ROOT": str(reports),
            "MODELS": MODEL,
            "PYTHON_BIN": sys.executable,
        },
    )
    for title, variant in (("All segments", ""), ("Duration > 0.5 s", "_mindur")):
        directory = (
            reports / "data" / f"results_{MODULE}{variant}" / GROUP / MODEL.upper()
        )
        print(
            title,
            (directory / f"errs-{GROUP}-{MODEL.upper()}.txt").read_text().strip(),
            (directory / "segment_check.txt").read_text().strip(),
            sep="\n",
        )
    print(f"Prediction file: {result}")


if __name__ == "__main__":
    main()
