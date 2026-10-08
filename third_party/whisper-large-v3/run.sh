#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ASR_ENV="${ASR_ENV:-$SCRIPT_DIR/.venv}"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/' >&2
  exit 1
fi
if [[ ! -x "$ASR_ENV/bin/python" ]]; then
  uv venv --python 3.12 --seed "$ASR_ENV"
fi
uv pip install --python "$ASR_ENV/bin/python" -r "$SCRIPT_DIR/requirements.txt"
exec "$ASR_ENV/bin/python" "$SCRIPT_DIR/run.py" "$@"
