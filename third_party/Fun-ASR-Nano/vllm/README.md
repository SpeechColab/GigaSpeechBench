# Base checkpoint with vLLM

Uses `FunAudioLLM/Fun-ASR-Nano-2512-vllm`, revision
`a4362c943d48951f98ca2a62181cc028970270c5`, for Chinese/English benchmark groups.
This environment is independent of the MLT/Ray environment. vLLM 0.27.1 requires
Torch 2.13.0; the CUDA 13 wheel requires a compatible host driver. Follow the
upstream vLLM/PyTorch installation requirements for your hardware. Driver libraries
are not installed or injected by these scripts.

Use the [category entry point](../README.md) for HF data. For prepared manifests:

```bash
cd third_party/Fun-ASR-Nano/vllm
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -r requirements.txt
CUDA_VISIBLE_DEVICES=0 bash serve.sh
# In another terminal in this directory:
.venv/bin/python infer.py --input-root ./prepared --output-root ./outputs/raw
```

Defaults use float32, eager execution and temperature 0. Lower-precision trials
produced repetitive text; float32 is retained for this checkpoint. No repetition
cleanup is applied. Set `GPU_MEMORY_UTILIZATION`, `MAX_NUM_SEQS`,
`MAX_NUM_BATCHED_TOKENS` and client `--workers` for your GPU capacity.
`MODEL_PATH`, `MODEL_REVISION`, `PYTHON_BIN`, `HOST`, and `PORT` are optional
overrides. Extra vLLM options may be passed to `serve.sh`.
