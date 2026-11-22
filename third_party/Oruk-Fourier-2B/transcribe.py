"""Run Fourier locally on the benchmark's own pre-cut English clips and emit scorer input."""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import soundfile as sf
from vllm import LLM, SamplingParams

MODEL = "oruk/oruk-fourier-2b"
REV = "8c2a8871f1304aa2f634da4fb95e24438c4945b9"
PROMPT = "<|im_start|>user\n<|audio_start|><|audio_pad|><|audio_end|><|im_end|>\n<|im_start|>assistant\nlanguage English<asr_text>"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    items = json.loads((args.prepared / "input_prepare.json").read_text())
    total = len(items)
    print(
        "DESIGN",
        json.dumps(
            {
                "count": total,
                "audio_seconds": sum(item["meta"]["duration"] for item in items),
                "audio_recordings": len(
                    {item["meta"]["ref_audio_name"] for item in items}
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
        max_num_seqs=32,
        limit_mm_per_prompt={"audio": 1},
        gpu_memory_utilization=0.84,
    )
    sampling = SamplingParams(temperature=0.0, max_tokens=256)
    recordings = {}
    start = time.perf_counter()
    finish_reasons = Counter()
    for offset in range(0, total, 96):
        group = items[offset : offset + 96]
        examples = []
        for item in group:
            waveform, rate = sf.read(
                args.prepared / item["audio_path"], dtype="float32"
            )
            assert rate == 16000 and waveform.ndim == 1
            examples.append(
                {"prompt": PROMPT, "multi_modal_data": {"audio": (waveform, rate)}}
            )
        batch = engine.generate(examples, sampling, use_tqdm=False)
        assert len(batch) == len(group)
        for row, response in zip(group, batch):
            recording_id = row["meta"]["ref_audio_name"]
            annotation = row["meta"]["source_segment"]
            prediction = {
                key: annotation[key] for key in ("sid", "begin_time", "end_time")
            }
            prediction["text"] = response.outputs[0].text.strip()
            finish_reasons[response.outputs[0].finish_reason] += 1
            recordings.setdefault(
                recording_id,
                {"aid": recording_id, "language": "PHL-EN", "segments": []},
            )["segments"].append(prediction)
        if offset % 960 == 0 or offset + 96 >= total:
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
                "finish_reasons": finish_reasons,
                "seconds": round(time.perf_counter() - start, 2),
                "records": len(recordings),
            }
        ),
        flush=True,
    )
    target = args.stage / "CH-EN-Dialects/results"
    target.mkdir(parents=True, exist_ok=True)
    (target / "Oruk-Fourier-2B.json").write_text(
        json.dumps({"audios": list(recordings.values())}, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
