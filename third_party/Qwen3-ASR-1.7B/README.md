# Qwen3-ASR-1.7B: local vLLM inference

This runner hosts the open-weight **Qwen3-ASR-1.7B** model locally. It is separate from
[`../Qwen3ASR`](../Qwen3ASR), which contains the existing hosted API integration.

The tested environment uses `qwen-asr==0.0.6`, `vllm==0.14.0`,
`torch==2.9.1`, and `transformers==4.57.6`. The launcher uses
`qwen_asr.cli.serve` to register the model with this vLLM version.
Use `Qwen/Qwen3-ASR-1.7B`, not the later `-hf` checkpoint with a different layout.
The client strips the `<asr_text>` metadata prefix, retaining the original response
in `inference.attempts`. The default decoding cap is 512 tokens.

Upstream: [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR).

## One-command HF dataset workflow

From the repository root:

```bash
bash third_party/vllm_asr/run.sh --model qwen --subset low-resource \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/qwen_low_resource_r1 --gpus 0

bash third_party/vllm_asr/run.sh --model qwen --subset zh-en \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/qwen_zh_en_r1 --gpus 0
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
cd third_party/Qwen3-ASR-1.7B
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -r requirements.txt
CUDA_VISIBLE_DEVICES=0 bash serve.sh
```

The launcher downloads the public model into `.cache/huggingface` on first use.
To use a downloaded checkpoint instead:

```bash
MODEL_PATH=./models/Qwen3-ASR-1.7B CUDA_VISIBLE_DEVICES=0 bash serve.sh
```

The venv and cache defaults resolve relative to `serve.sh`. A relative `MODEL_PATH`
resolves against the caller's working directory. `PYTHON_BIN`, `HOST`, `PORT`,
`SERVED_MODEL_NAME`, `GPU_MEMORY_UTILIZATION`, and `HF_HOME` may be overridden.
Extra server options can be passed after `serve.sh`. No network-interface name or
physical GPU assignment is hardcoded. The default bind address is loopback.

## Batch inference

In another terminal, from this model directory:

```bash
curl --fail http://127.0.0.1:18100/health
.venv/bin/python infer.py \
  --input-root ../../data/prepared/Older-Children \
  --output-root ./outputs/run_001 \
  --workers 128
```

`--input-root` finds all nested `input_prepare.json` files and preserves their
relative directory hierarchy in the output. For a single JSON-list or JSONL file,
use `--input-json` instead; its results go directly in `--output-root`.
All CLI paths resolve against the current working directory; audio paths resolve
against their manifest directory.

The endpoint defaults to `http://127.0.0.1:18100/v1` and the request model to
`Qwen3-ASR-1.7B`. Change `--base-url` and `--model` when overriding the server settings.
Use `--max-items 8` and a fresh output directory for a small smoke test.

See the [shared input/output, retry, export, and evaluation guide](../vllm_asr/README.md).
