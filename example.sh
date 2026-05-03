#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# GigaSpeechBench Evaluation Pipeline
# ============================================================
#
# Usage:
#   bash example.sh <DATASET_ROOT> [OPTIONS]
#
# Arguments:
#   DATASET_ROOT    Path to dataset directory containing:
#                     data/{LANG}/metadata.json   -- GigaSpeech-style ref annotations
#                     data/{LANG}/audio/*.wav      -- audio files
#                     results/{MODEL}.json          -- GigaSpeech-style model hypotheses
#
# Options:
#   --skip-existing  Skip files that already exist (default: on)
#   --force          Force overwrite all outputs
#   --workers N      Number of parallel workers for normalization (default: auto)
#
# Example:
#   bash example.sh /path/to/dataset
#   bash example.sh /path/to/dataset --force --workers 8

DATASET_ROOT="${1:?Usage: bash example.sh <DATASET_ROOT> [--force] [--workers N]}"
shift || true

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SKIP_EXISTING=1
WORKERS=0  # 0 = auto

# Parse optional flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)        SKIP_EXISTING=0; shift ;;
        --skip-existing) SKIP_EXISTING=1; shift ;;
        --workers)      WORKERS="$2"; shift 2 ;;
        *)              echo "Unknown option: $1"; exit 1 ;;
    esac
done

TEXT_DIR="$BASE_DIR/data/text"
NORM_DIR="$BASE_DIR/data/text_normalized"
RESULTS_DIR="$BASE_DIR/data/results"

echo "=============================================="
echo "GigaSpeechBench Evaluation Pipeline"
echo "  DATASET  = $DATASET_ROOT"
echo "  BASE_DIR = $BASE_DIR"
echo "  WORKERS  = $WORKERS (0=auto)"
echo "  FORCE    = $( [[ $SKIP_EXISTING -eq 0 ]] && echo yes || echo no )"
echo "=============================================="

# Step 1: Convert GigaSpeech-style JSON to flat format
echo ""
echo "Step 1/4: Convert data"
"$PYTHON_BIN" "$BASE_DIR/data_process/convert_data.py" \
    --data_root "$DATASET_ROOT/data" \
    --results_root "$DATASET_ROOT/results" \
    --out_dir "$TEXT_DIR" \
    --skip_existing "$SKIP_EXISTING"

# Step 2: Normalize text (ref + hyp, parallel, cached)
echo ""
echo "Step 2/4: Normalize text"
"$PYTHON_BIN" "$BASE_DIR/data_process/normalize.py" \
    --text_root "$TEXT_DIR" \
    --out_root "$NORM_DIR" \
    --workers "$WORKERS" \
    --skip_existing "$SKIP_EXISTING"

# Step 3: Compute WER/CER
echo ""
echo "Step 3/4: Compute WER/CER"
"$PYTHON_BIN" "$BASE_DIR/scripts/compute_wer_single.py" \
    --ref_root "$NORM_DIR/ref" \
    --hyp_root "$NORM_DIR/hyp" \
    --out_root "$RESULTS_DIR" \
    --skip_existing "$SKIP_EXISTING"

# Step 4: Build Excel
echo ""
echo "Step 4/4: Build Excel"
mapfile -t COUNTRIES < <(find "$NORM_DIR/ref" -maxdepth 1 -name '*.json' -printf '%f\n' | sed 's/\.json$//' | sort)

if [[ ${#COUNTRIES[@]} -eq 0 ]]; then
    echo "No ref files found."
    exit 1
fi

"$PYTHON_BIN" "$BASE_DIR/scripts/excel_single.py" \
    --results_root "$RESULTS_DIR" \
    --ref_root "$NORM_DIR/ref" \
    --excel_countries "${COUNTRIES[@]}" \
    --skip_existing 0 \
    --matched_only 0

"$PYTHON_BIN" "$BASE_DIR/scripts/merge_excel.py" --base_dir "$BASE_DIR"

echo ""
echo "=============================================="
echo "Done. Results: $RESULTS_DIR"
echo "=============================================="
