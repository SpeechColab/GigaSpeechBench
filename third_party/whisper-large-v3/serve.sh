#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_HOME="${HF_HOME:-$SCRIPT_DIR/.cache/huggingface}"
export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-$SCRIPT_DIR/.cache/vllm}"
export TOKENIZERS_PARALLELISM=false
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
mkdir -p "$HF_HOME" "$VLLM_CACHE_ROOT"
exec "${PYTHON_BIN:-$SCRIPT_DIR/.venv/bin/python}" -m vllm.entrypoints.cli.main serve \
  "${MODEL_PATH:-openai/whisper-large-v3}" \
  --served-model-name "${SERVED_MODEL_NAME:-whisper-large-v3}" \
  --host "${HOST:-127.0.0.1}" --port "${PORT:-18101}" \
  --revision "${MODEL_REVISION:-06f233fe06e710322aca913c1bc4249a0d71fce1}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.90}" --tensor-parallel-size "${TENSOR_PARALLEL_SIZE:-1}" --disable-log-requests "$@"
