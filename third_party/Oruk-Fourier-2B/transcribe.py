"""Run Fourier locally on GigaSpeechBench pre-cut English clips and emit scorer input."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import soundfile as sf
from vllm import LLM, SamplingParams

MODEL = "oruk/oruk-fourier-2b"
REV = "8c2a8871f1304aa2f634da4fb95e24438c4945b9"
PROMPT = (
    "<|im_start|>user\n<|audio_start|><|audio_pad|><|audio_end|><|im_end|>\n"
    "<|im_start|>assistant\nlanguage English<asr_text>"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prepared",
        type=Path,
        nargs="+",
        required=True,
        help="One or more prepared group directories containing input_prepare.json",
    )
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument(
        "--module",
        default="CH-EN-Dialects",
        help="Target GigaSpeechBench module (CH-EN-Dialects, Vertical-Domain, Older-Children)",
    )
    parser.add_argument("--batch-size", type=int, default=96)
    args = parser.parse_args()

    items: list[tuple[Path, dict]] = []
    for prep_dir in args.prepared:
        rows = json.loads((prep_dir / "input_prepare.json").read_text(encoding="utf-8"))
        for row in rows:
            items.append((prep_dir, row))

    total = len(items)
    print(
        "DESIGN",
        json.dumps(
            {
                "module": args.module,
                "groups": sorted({row["language"] for _, row in items}),
                "count": total,
                "audio_seconds": round(
                    sum(row["meta"]["duration"] for _, row in items), 2
                ),
                "audio_recordings": len(
                    {row["meta"]["ref_audio_name"] for _, row in items}
                ),
            }
        ),
        flush=True,
    )
    engine = LLM(
        model=MODEL,
        revision=REV,
        tokenizer_revision=REV,
        dtype="bfloat16",
        enforce_eager=True,
        max_model_len=1536,
        max_num_seqs=64,
        limit_mm_per_prompt={"audio": 1},
        gpu_memory_utilization=0.84,
    )
    sampling = SamplingParams(temperature=0.0, max_tokens=256)
    recordings: dict[str, dict] = {}
    start = time.perf_counter()
    finish_reasons: Counter = Counter()
    bs = args.batch_size
    for offset in range(0, total, bs):
        group = items[offset : offset + bs]
        examples = []
        for prep_dir, item in group:
            waveform, rate = sf.read(prep_dir / item["audio_path"], dtype="float32")
            assert rate == 16000 and waveform.ndim == 1
            examples.append(
                {"prompt": PROMPT, "multi_modal_data": {"audio": (waveform, rate)}}
            )
        batch = engine.generate(examples, sampling, use_tqdm=False)
        assert len(batch) == len(group)
        for (_prep_dir, row), response in zip(group, batch):
            recording_id = row["meta"]["ref_audio_name"]
            annotation = row["meta"]["source_segment"]
            prediction = {
                key: annotation[key] for key in ("sid", "begin_time", "end_time")
            }
            prediction["text"] = response.outputs[0].text.strip()
            finish_reasons[response.outputs[0].finish_reason] += 1
            recordings.setdefault(
                recording_id,
                {"aid": recording_id, "language": row["language"], "segments": []},
            )["segments"].append(prediction)
        if offset % (bs * 10) == 0 or offset + bs >= total:
            print(
                "PROGRESS",
                offset + len(group),
                total,
                round(time.perf_counter() - start, 2),
                flush=True,
            )
    print(
        "FINISH",
        json.dumps(
            {
                "module": args.module,
                "finish_reasons": dict(finish_reasons),
                "seconds": round(time.perf_counter() - start, 2),
                "records": len(recordings),
            }
        ),
        flush=True,
    )
    target = args.stage / args.module / "results"
    target.mkdir(parents=True, exist_ok=True)
    (target / "Oruk-Fourier-2B.json").write_text(
        json.dumps({"audios": list(recordings.values())}, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
