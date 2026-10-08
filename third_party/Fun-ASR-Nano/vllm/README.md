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

## CUDA driver check

This environment installs Torch's **CUDA 13.0** wheel. Check `nvidia-smi` first:
a native compatible driver is normally **R580 or newer**; a driver adequate for
the CUDA 12 Qwen/Whisper environments is not sufficient by itself.
[NVIDIA's version requirements](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)
and [forward-compatibility restrictions](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html)
apply. Prefer a supported native driver. Compatibility packages are only an option
for supported hardware/driver combinations, not a general fix for any old GPU.

Our clean H100 test on host driver 550.127.08 failed with `NVIDIA driver ... too old`.
It required explicitly configured 580.65.06 user-space compatibility libraries.
R550 is no longer listed as a supported target in NVIDIA's current matrix; this
local observation is not a support guarantee. The runner does not install or
silently inject driver libraries.

For an administrator-approved CUDA 13.0 compatibility deployment on Linux x86-64,
the exact package used in that test can be unpacked without changing the host driver:

```bash
mkdir -p ./runtime/cuda13
curl --fail --location --output ./runtime/cuda13/package.deb \
  https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-compat-13-0_580.65.06-0ubuntu1_amd64.deb
printf '%s  %s\n' \
  11a067e09aeb3d16b025c77225d26493857926edc17104dc1bdcfa63f9293e48 \
  ./runtime/cuda13/package.deb | sha256sum --check
dpkg-deb --extract ./runtime/cuda13/package.deb ./runtime/cuda13
GSB_COMPAT_DIR="$(pwd)/runtime/cuda13/usr/local/cuda-13.0/compat"
LD_LIBRARY_PATH="$GSB_COMPAT_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  CUDA_VISIBLE_DEVICES=0 bash serve.sh
```

Run this example from the model directory after environment setup. For the
category runner, prefix its command with the same `LD_LIBRARY_PATH` assignment.
Keep this setting scoped to that invocation. A compatibility library copied into
a directory has no effect until the loader is explicitly configured.

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
