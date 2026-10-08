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
  "${MODEL_PATH:-FunAudioLLM/Fun-ASR-Nano-2512-vllm}" \
  --served-model-name "${SERVED_MODEL_NAME:-fun-asr-nano}" \
  --host "${HOST:-127.0.0.1}" --port "${PORT:-18102}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.60}" --revision "${MODEL_REVISION:-a4362c943d48951f98ca2a62181cc028970270c5}" \
  --dtype float32 --enforce-eager --max-model-len 8192 \
  --max-num-seqs "${MAX_NUM_SEQS:-32}" --max-num-batched-tokens "${MAX_NUM_BATCHED_TOKENS:-16384}" \
  --no-enable-prefix-caching --mm-processor-cache-gb 0 "$@"
