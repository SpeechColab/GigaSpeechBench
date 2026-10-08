#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_ENV="${GSB_TOOLS_ENV:-$SCRIPT_DIR/.venv}"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/' >&2
  exit 1
fi
if [[ ! -x "$TOOLS_ENV/bin/python" ]]; then
  uv venv --python 3.12 --seed "$TOOLS_ENV"
fi
uv pip install --python "$TOOLS_ENV/bin/python" -r "$SCRIPT_DIR/requirements.txt"
exec "$TOOLS_ENV/bin/python" "$SCRIPT_DIR/run_benchmark.py" "$@"
