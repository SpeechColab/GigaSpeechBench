# Whisper large-v3: local inference

Requires Linux, `uv`, and an NVIDIA GPU/driver supported by vLLM 0.14.1.
Dependencies are local to this directory. vLLM selects its matching PyTorch and
CUDA packages; configure the host driver using upstream installation guidance.
The default checkpoint revision is `06f233fe06e710322aca913c1bc4249a0d71fce1`.

## Run a category

```bash
cd third_party/whisper-large-v3
bash run.sh --subset low-resource --data-root ../../../datasets/GigaSpeechBench \
  --work-dir ./outputs/low_resource --gpus 0
bash run.sh --subset zh-en --data-root ../../../datasets/GigaSpeechBench \
  --work-dir ./outputs/zh_en --gpus 0
```

`run.sh` creates a Python 3.12 `.venv`, installs this model's `requirements.txt`,
prepares audio, starts a local service, transcribes, exports, and stops the service.
Set `ASR_ENV` to place the environment elsewhere. With an installed environment,
run `python run.py` with the same arguments to skip package installation.

Input is a downloaded [GigaSpeechBench](https://huggingface.co/datasets/speechcolab/GigaSpeechBench)
snapshot: `CATEGORY/data/GROUP/metadata.json` plus `audio.tar.gz` (or `audio/`).
All command-line paths are relative to the caller's working directory. Add
`--download` to fetch selected inputs at revision
`680d3057641b7507a1ef14974407c7b0a7964e64`.

- `--subset`: `low-resource`, `zh-en`, `vertical-domain`, `dialects`, `all`, or
  `older-children`. Older-Children requires a compatible local release; it is
  absent from the pinned public snapshot.
- `--groups KOR --limit-per-group 2`: small smoke test; omit the limit for a full run.
- `--resume`: continue an unchanged run; add `--retry-errors` for failed requests.
- `--empty-retries 10`: allow ten extra attempts on empty text. Persistent empties
  remain `""`; references are never included in inference requests.
- `--workers`, `--gpus`, `--port`: client concurrency and device/service selection.
  `GPU_MEMORY_UTILIZATION` controls server memory fraction. Tune for your GPU.
- `--model-path`: local weights; `MODEL_REVISION` overrides the default HF revision.

Preparation creates 16 kHz mono clips and preserves annotation timestamps. Up to
10 ms of end-time rounding is clamped and recorded in `preparation_report.json`;
use `--end-tolerance-ms 0` for strict bounds. Failed or incomplete runs are not
exported as completed results.

## Results and existing services

`WORK/raw/` contains predictions and diagnostics. `WORK/staging/` uses the
repository's staging schema; `WORK/pipeline/data/text/` contains flat ref/hyp JSON
for its existing evaluation pipeline. Evaluation dependencies and scoring are
managed by that pipeline, separately from this inference environment.

For already prepared `input_prepare.json` manifests, start `bash serve.sh` and run:

```bash
.venv/bin/python infer.py --input-root ./prepared --output-root ./outputs/raw
```

Use `--base-url` for an existing endpoint. `python run.py --help` and
`python infer.py --help` list the remaining options.
