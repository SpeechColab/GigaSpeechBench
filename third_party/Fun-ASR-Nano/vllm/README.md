# Fun-ASR-Nano: local vLLM inference

This runner uses **Fun-ASR-Nano-2512 base** through native vLLM serving.
It does not use the older Ray/ModelScope process pool and does not use the
31-language Fun-ASR-MLT-Nano checkpoint. The base model supports Chinese,
English, and Japanese; the recovered full batch validated Chinese and English.

The tested environment uses `vllm==0.27.1`, `torch==2.13.0` (CUDA 13 wheel), and
`transformers==5.18.0`. The model is
`FunAudioLLM/Fun-ASR-Nano-2512-vllm`, pinned to revision
`a4362c943d48951f98ca2a62181cc028970270c5`. No local weight conversion is needed.

Defaults reproduce the selected full-batch settings: float32, eager execution,
16 client workers, max model length 8192, max sequences 32, GPU memory fraction
0.60, prefix caching off, multimodal processor caching off, FlashInfer sampling
off, temperature 0. Lower-precision trials produced repetitive outputs on some
samples; these defaults deliberately retain the validated configuration. Rare
repetitive or empty outputs can still occur and are not silently cleaned up.

Use a driver compatible with the installed CUDA wheel. The original H100 setup
used CUDA compatibility libraries 580.65.06. Those host-specific libraries are not
bundled or injected here. If your system needs CUDA forward compatibility,
configure it through your system administrator before starting the server.

Upstream: [native vLLM checkpoint](https://huggingface.co/FunAudioLLM/Fun-ASR-Nano-2512-vllm).

## Setup

Linux, an NVIDIA GPU with sufficient memory, `uv`, and Python 3.12 are required.
The original runs used H100 80 GB GPUs. Create a **separate** environment for each
model; these vLLM versions are intentionally different. Run from the repository root:

```bash
cd third_party/Fun-ASR-Nano/vllm
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -r requirements.txt
CUDA_VISIBLE_DEVICES=0 bash serve.sh
```

The launcher downloads the public model into `.cache/huggingface` on first use.
To use a downloaded checkpoint instead:

```bash
MODEL_PATH=./models/Fun-ASR-Nano CUDA_VISIBLE_DEVICES=0 bash serve.sh
```

The venv and cache defaults resolve relative to `serve.sh`. A relative `MODEL_PATH`
resolves against the caller's working directory. `PYTHON_BIN`, `HOST`, `PORT`,
`SERVED_MODEL_NAME`, `GPU_MEMORY_UTILIZATION`, and `HF_HOME` may be overridden.
Extra server options can be passed after `serve.sh`. No network-interface name or
physical GPU assignment is hardcoded. The default bind address is loopback.

## Batch inference

In another terminal, from this model directory:

```bash
curl --fail http://127.0.0.1:18102/health
.venv/bin/python infer.py \
  --input-root ../../../data/prepared/Older-Children \
  --output-root ./outputs/run_001 \
  --workers 16
```

`--input-root` finds all nested `input_prepare.json` files and preserves their
relative directory hierarchy in the output. For a single JSON-list or JSONL file,
use `--input-json` instead; its results go directly in `--output-root`.
All CLI paths resolve against the current working directory; audio paths resolve
against their manifest directory.

The endpoint defaults to `http://127.0.0.1:18102/v1` and the request model to
`fun-asr-nano`. Change `--base-url` and `--model` when overriding the server settings.
Use `--max-items 8` and a fresh output directory for a small smoke test.

See the [shared input/output, retry, export, and evaluation guide](../../vllm_asr/README.md).
