# Shared vLLM batch client

This module packages the audio-only HTTP workflow used for the three local ASR
runs: [Qwen3-ASR-1.7B](../Qwen3-ASR-1.7B),
[Whisper large-v3](../whisper-large-v3), and [Fun-ASR-Nano](../Fun-ASR-Nano).
Each model has its own pinned environment and server launcher. The Python client
and evaluation exporter are shared to keep the input/output contract consistent.
This is a portability refactor of the October 2026 batch scripts, not a new model
implementation. It does not change the repository's hosted Qwen3ASR integration.

## Input

Prepare clips before running inference. One JSON list or JSONL manifest contains
one row per segment. `--input-root` recursively discovers files named
`input_prepare.json`. Audio must already be 16 kHz, mono, and no longer than 30 s.
The client does not crop, resample, apply VAD, or read source timestamps to slice
audio at request time. Passing a full recording with segment timestamps would
transcribe that full recording, so always point `audio_path` at the actual clip.

Example `data/prepared/Older-Children/CHILD-EN/input_prepare.json`:

```json
[
  {
    "segment_key": "CHILD-EN#example|1000|2500",
    "audio_path": "cropped_audios/example_1000_2500.wav",
    "language": "en",
    "ref_text": "Example reference.",
    "meta": {
      "ref_audio_name": "example",
      "start_time": 1.0,
      "end_time": 2.5,
      "duration": 1.5
    }
  }
]
```

`segment_key`, `audio_path`, and `language` are required. `ref_text` and `meta`
are optional for inference but required for evaluation export as shown above.
Unknown input fields are preserved. Reference text, previous hypotheses, source
timestamps, and other metadata are never sent to the server. Only audio bytes,
model, language, temperature, response format, and an optional token cap are sent.

Use explicit language codes (`zh`, `en`, `ja`, etc.). Historical GSB suffixes
such as `CHILD-CH`, `OLD-EN`, `ECM-CH`, `JPN`, and `KOR` are also accepted.
The historical GAN/JIN/MIN/WU/XIANG/YUE mapping to `zh` is retained for reproduction;
use `--language` to explicitly override it for a new experiment. That override
is recorded in the run specification. Model language coverage still applies.
Fun-ASR-Nano rejects languages outside zh/en/ja.

## Output and resume

Each input manifest produces `run_spec.json`, append-only `output_raw.jsonl`,
and `summary.json`. Raw rows preserve input fields and add `hyp_text`, `status`,
`model`, and `inference` request details. Blank predictions are exactly `""`;
no placeholder or diagnostic marker is inserted into the transcript.

Use a fresh output root per experiment. An existing run requires `--resume` and
matching manifest content, client code, endpoint, model, and decoding settings.
The lock file prevents two local clients from writing the same output concurrently.
Successful and failed rows are skipped on resume by default. To resubmit failures,
add `--resume --retry-errors`. Completed empty predictions are successful rows and
remain skipped on resume. Malformed/truncated JSONL is rejected for manual review.
The process exits nonzero if any request errors remain, after saving all results.
`--max-items` limits pending requests for a smoke test; the summary reports how
many segments remain. Export rejects incomplete runs.

Request retries default to zero. `--retries N` allows up to N additional requests
after HTTP/response errors. `--empty-retries 10` allows ten additional requests
after an empty prediction, stopping at the first nonempty prediction. Each attempt
is retained in `inference.attempts`; persistent empty predictions remain `""`.
A valid empty response is preserved if a later retry fails. Repeated empty output
does not establish that the audio contains no speech. Declare the retry policy
when comparing benchmark results. `--temperature` defaults to zero; no random
temperature changes or repetition cleanup happen automatically.

Client wall time excludes server startup. `rtfx_current` is successfully processed
audio seconds divided by this invocation's client wall seconds. It includes
inspection, uploads, queuing, decoding, and retries. Concurrency defaults reproduce
the earlier H100 runs, but should be tuned for available memory and hardware.

## Export for the official evaluation pipeline

Run from a model directory using that model's venv:

```bash
.venv/bin/python ../vllm_asr/export.py \
  --input-json ../../data/prepared/Older-Children/CHILD-EN/input_prepare.json \
  --raw outputs/run_001/CHILD-EN/output_raw.jsonl \
  --output-dir outputs/export_001/CHILD-EN
```

This writes `ref.json` and `hyp.json` as lists of
`{"audio_name": ..., "start": ..., "end": ..., "text": ...}`, using the original
recording identity/timestamps from `meta`. It checks complete key coverage,
unchanged metadata, and unique evaluation identities, then takes the latest row
for each segment. Failures require an explicit `--allow-errors`; their stored
empty hypothesis is then exported. Empty hypotheses are never dropped.

For each group `GROUP` and model label `MODEL`, place the files under the official
pipeline layout (paths here are relative to the repository root):

```text
data/text/Older-Children/ref/GROUP.json
data/text/Older-Children/hyp/GROUP/GROUP_MODEL.json
```

Use the existing `data_process/normalize_ref.py`, `normalize_hyp.py`,
`scripts/filter_duration.py`, and `scripts/compute_wer.py` commands shown in
`run_ASR.sh`, starting at its normalization stage. `run_ASR.sh` also supports
staging/raw-input conversion, so do not point its `DATA_ROOT` at these flat exports.
The client does not normalize or score text. Use the repository's language-specific
normalization and its duration filter (`duration > 0.5 s` in the recovered run).
Hotword BWER/BCER additionally requires the benchmark's entity annotations; ordinary
reference text alone is not a substitute for those annotations.

## Verification

From any model directory, after installing requirements:

```bash
.venv/bin/python -m unittest discover -s ../vllm_asr -p 'test_*.py'
```

Tests use a temporary local HTTP server and synthetic audio. They cover actual
multipart requests, reference exclusion, relative paths, retries, resume checks,
and export compatibility without loading GPU models. Real-model smoke testing is
a separate deployment check after the server becomes healthy.

Validation on 2026-10-08: all eight HTTP contract tests passed. Each of the three
launchers also served four real clips (two Chinese, two English; 39.437 seconds
total audio) on an H100, using its existing pinned environment. All twelve
transcriptions succeeded, with no empty outputs; flat export and no-op resume
were verified for each model. The requirements were independently resolved with
`uv pip compile`. A fresh full installation and a new full-dataset benchmark
were not run during this portability check.
