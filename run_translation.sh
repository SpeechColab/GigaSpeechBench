#!/usr/bin/env bash

set -euo pipefail

# Translation quality evaluation script
# Usage:
#   STAGING_ROOT=/path/to/release bash run_translation.sh [extra args...]
#
# Requires: openstbench package (pip install openstbench)
# Evaluates translation results in $STAGING_ROOT/Low-Resource-Languages/results_trans/

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
STAGING_ROOT="${STAGING_ROOT:-}"

if [[ -z "$STAGING_ROOT" ]]; then
    echo "Error: STAGING_ROOT must be set"
    echo "Usage: STAGING_ROOT=/path/to/release bash run_translation.sh [extra args...]"
    exit 1
fi

TRANS_DATA="$STAGING_ROOT/Low-Resource-Languages/data"
TRANS_RESULTS="$STAGING_ROOT/Low-Resource-Languages/results_trans"

if [[ ! -d "$TRANS_DATA" ]]; then
    echo "Error: data directory not found: $TRANS_DATA"
    exit 1
fi

if [[ ! -d "$TRANS_RESULTS" ]]; then
    echo "Error: results_trans directory not found: $TRANS_RESULTS"
    exit 1
fi

echo "=== Translation Quality Evaluation ==="
echo "Data:    $TRANS_DATA"
echo "Results: $TRANS_RESULTS"
echo "======================================="

"$PYTHON_BIN" "$BASE_DIR/scripts/translation_eval/eval_translation.py" \
    --data_root "$TRANS_DATA" \
    --results_trans "$TRANS_RESULTS" \
    --out_dir "$BASE_DIR/scripts/translation_eval/results" \
    --excel_dir "$BASE_DIR/data/excel_output" \
    --log_dir "$BASE_DIR/log" \
    "$@"
