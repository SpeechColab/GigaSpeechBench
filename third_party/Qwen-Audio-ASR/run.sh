#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
env_dir="${ASR_ENV:-$script_dir/.venv}"
if [[ ! -x "$env_dir/bin/python" ]]; then
    uv venv --python 3.12 --seed "$env_dir"
fi
uv pip install --python "$env_dir/bin/python" -r "$script_dir/requirements.txt"
exec "$env_dir/bin/python" "$script_dir/run.py" "$@"
