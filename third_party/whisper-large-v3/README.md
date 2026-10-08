# whisper-large-v3: local vLLM inference

This directory replaces the previous Transformers/OpenAI-Whisper scripts with
local vLLM serving and concurrent transcription requests. The old
`auto_infer.py`, `auto_infer_with_segments.py`, and `uv sync` entry points have
been replaced by the commands below; do not use their old configuration constants.

The tested environment uses `vllm==0.14.1`, `torch==2.9.1`, and
`transformers==4.57.6`. We observed increasing GPU memory usage with Whisper on
vLLM 0.14.0; use the pinned 0.14.1 environment, which completed an 18,040-request
local stability check without that growth. This is a report of our tested setup,
not a guarantee for every driver/hardware combination. Do not merge this environment
with the Qwen runner's 0.14.0 environment.

Upstream: [Whisper large-v3](https://huggingface.co/openai/whisper-large-v3).

## One-command HF dataset workflow

From the repository root:

```bash
bash third_party/vllm_asr/run.sh --model whisper --subset low-resource \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/whisper_low_resource_r1 --gpus 0

bash third_party/vllm_asr/run.sh --model whisper --subset zh-en \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/whisper_zh_en_r1 --gpus 0
```

Add `--download` to download the selected HF inputs. This entry point handles
setup, cropping, server startup/shutdown, inference, and export automatically.
See [all options and limitations](../vllm_asr/ONE_CLICK.md). The manual commands
below are for users who already have cropped manifests or a running server.

## Setup

Linux, an NVIDIA GPU with sufficient memory, `uv`, and Python 3.12 are required.
The original runs used H100 80 GB GPUs. Create a **separate** environment for each
model; these vLLM versions are intentionally different. Run from the repository root:

```bash
cd third_party/whisper-large-v3
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -r requirements.txt
CUDA_VISIBLE_DEVICES=0 bash serve.sh
```

The launcher downloads the public model into `.cache/huggingface` on first use.
To use a downloaded checkpoint instead:

```bash
MODEL_PATH=./models/whisper-large-v3 CUDA_VISIBLE_DEVICES=0 bash serve.sh
```

The venv and cache defaults resolve relative to `serve.sh`. A relative `MODEL_PATH`
resolves against the caller's working directory. `PYTHON_BIN`, `HOST`, `PORT`,
`SERVED_MODEL_NAME`, `GPU_MEMORY_UTILIZATION`, and `HF_HOME` may be overridden.
Extra server options can be passed after `serve.sh`. No network-interface name or
physical GPU assignment is hardcoded. The default bind address is loopback.

## Batch inference

In another terminal, from this model directory:

```bash
curl --fail http://127.0.0.1:18101/health
.venv/bin/python infer.py \
  --input-root ../../data/prepared/Older-Children \
  --output-root ./outputs/run_001 \
  --workers 48
```

`--input-root` finds all nested `input_prepare.json` files and preserves their
relative directory hierarchy in the output. For a single JSON-list or JSONL file,
use `--input-json` instead; its results go directly in `--output-root`.
All CLI paths resolve against the current working directory; audio paths resolve
against their manifest directory.

The endpoint defaults to `http://127.0.0.1:18101/v1` and the request model to
`whisper-large-v3`. Change `--base-url` and `--model` when overriding the server settings.
Use `--max-items 8` and a fresh output directory for a small smoke test.

See the [shared input/output, retry, export, and evaluation guide](../vllm_asr/README.md).

The default checkpoint revision is `06f233fe06e710322aca913c1bc4249a0d71fce1`, matching the fresh
README reproduction. Set `MODEL_REVISION` explicitly to test a different revision.
