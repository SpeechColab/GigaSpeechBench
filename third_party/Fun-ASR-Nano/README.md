# Fun-ASR-Nano: local inference

The two backends use separate checkpoints and environments:

| Category | Checkpoint | Backend dependencies |
| --- | --- | --- |
| Low-Resource-Languages | Fun-ASR-MLT-Nano-2512 | [ray/requirements.txt](ray/requirements.txt) |
| Vertical-Domain, CH-EN-Dialects, Older-Children | Fun-ASR-Nano-2512 base | [vllm/requirements.txt](vllm/requirements.txt) |

## Run a category

Requires Linux, `uv`, and a compatible NVIDIA GPU/driver. From the repository root:

```bash
cd third_party/Fun-ASR-Nano
bash run.sh --subset low-resource --data-root ../../../datasets/GigaSpeechBench \
  --work-dir ./outputs/mlt --gpus 0 --actors-per-gpu 2
bash run.sh --subset zh-en --data-root ../../../datasets/GigaSpeechBench \
  --work-dir ./outputs/base --gpus 0
```

`run.sh` creates a lightweight Python 3.12 environment for data preparation.
The selected backend is installed separately under `ray/.venv` or `vllm/.venv`;
it loads the model once per category, transcribes all selected groups, and exports.
The root `requirements.txt` contains only this model's preparation dependencies;
each backend adds its own inference packages. `ASR_ENV` moves the preparation
venv; `--env-root` moves backend venvs. `python run.py` uses an already installed
preparation environment; `--python-bin` selects an existing backend interpreter.

Input is a downloaded [GigaSpeechBench](https://huggingface.co/datasets/speechcolab/GigaSpeechBench)
snapshot: `CATEGORY/data/GROUP/metadata.json` and `audio.tar.gz` (or `audio/`).
Paths resolve from the caller's working directory. Add `--download` to fetch
selected groups at revision `680d3057641b7507a1ef14974407c7b0a7964e64`.

- `--subset`: `low-resource`, `zh-en`, `vertical-domain`, `dialects`, `all`, or
  `older-children`. The pinned public dataset has no Older-Children category;
  supply a local release with the same layout.
- `--groups KOR --limit-per-group 2`: smoke test; omit the limit for full inference.
- `--resume`: continue; add `--retry-errors` to resubmit failed requests.
- `--empty-retries 10`: retry empty predictions; persistent empties stay `""`.
- `--gpus 0,1 --actors-per-gpu 2`: Ray replicas; every actor holds a complete model.
- `--workers`, `--port`, `GPU_MEMORY_UTILIZATION`: vLLM concurrency and resources.
- `--model-path`: local checkpoint for a single backend. Mixed base/MLT runs require
  their separate checkpoints and environments.

Preparation writes 16 kHz mono clips. End-time overruns up to 10 ms are clamped
and logged without changing reference timestamps (`--end-tolerance-ms 0` is strict).
References never enter inference requests. `WORK/raw/` holds diagnostics;
`WORK/staging/` and `WORK/pipeline/data/text/` provide the existing repository's
staging and flat JSON formats. Failed/incomplete runs cannot be exported as complete.
Scoring and evaluation dependencies remain with the existing evaluation pipeline.

## Model limitations

MLT uses the traditional FunASR implementation with persistent Ray replicas; this
integration does not provide native-vLLM MLT weights. Base is not substituted for
MLT. Their result labels are `Fun-ASR-Nano-2512` and `Fun-ASR-MLT-Nano-2512`.
MLT disables the optional CTC alignment branch because its checkpoint lacks those
weights; this is text-only ASR. See [Ray setup](ray/README.md) and
[vLLM setup](vllm/README.md) for backend-specific requirements.
