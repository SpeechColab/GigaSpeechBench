#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   bash example.sh [MODULE] [SKIP_EXISTING] [SKIP_REF] [MATCHED_ONLY]
# MODULE: CH-EN-Dialects | Low-Resource-Languages | Vertical-Domain | all
# SKIP_EXISTING: 1 skip existing outputs, 0 overwrite existing outputs
# SKIP_REF: 1 skip ref generate & ref normalize, 0 run all steps
# MATCHED_ONLY: 1 Excel only includes fully-matched (ref==matched), 0 include all

MODULE="${1:-CH-EN-Dialects}"
SKIP_EXISTING="${2:-${SKIP_EXISTING:-1}}"
SKIP_REF="${3:-0}"
MATCHED_ONLY="${4:-0}"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_ROOT="${DATA_ROOT:-/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ "$SKIP_EXISTING" != "0" && "$SKIP_EXISTING" != "1" ]]; then
    echo "SKIP_EXISTING must be 0 or 1"
    exit 1
fi

run_one_module() {
    local module="$1"

    REF_OLD="$DATA_ROOT/$module/text/ref"
    HYP_OLD="$DATA_ROOT/$module/text/hyp"

    REF_OUT="$BASE_DIR/data/text/$module/ref"
    HYP_OUT="$BASE_DIR/data/text/$module/hyp"

    NORM_OUT="$BASE_DIR/data/text_normalized/$module"
    RESULTS_OUT="$BASE_DIR/data/results_$module"

    if [[ "$SKIP_EXISTING" == "0" ]]; then
        rm -rf "$BASE_DIR/data/text/$module" "$NORM_OUT" "$RESULTS_OUT"
    fi

    echo "=============================================="
    echo "Running ASR Bench pipeline for $module"
    echo "SKIP_EXISTING = $SKIP_EXISTING"
    echo "SKIP_REF      = $SKIP_REF"
    echo "MATCHED_ONLY  = $MATCHED_ONLY"
    echo "BASE_DIR   = $BASE_DIR"
    echo "DATA_ROOT  = $DATA_ROOT"
    echo "REF_OLD    = $REF_OLD"
    echo "HYP_OLD    = $HYP_OLD"
    echo "=============================================="

    if [[ ! -d "$REF_OLD" || ! -d "$HYP_OLD" ]]; then
        echo "Input text directories not found under $DATA_ROOT/$module"
        exit 1
    fi

echo "Step 1/6: Build consolidated REF json"
if [[ "$SKIP_REF" == "1" ]]; then
    echo "  ⏭️ Skipped (SKIP_REF=1)"
else
"$PYTHON_BIN" "$BASE_DIR/data_process/generate_ref_json_single.py" \
    --old_ref_root "$REF_OLD" \
    --out_ref_root "$REF_OUT" \
    --skip_existing "$SKIP_EXISTING"
fi

echo "Step 2/6: Build model-wise HYP json"
"$PYTHON_BIN" "$BASE_DIR/data_process/generate_hyp_json_single.py" \
    --hyp_input_root "$HYP_OLD" \
    --out_hyp_root "$HYP_OUT" \
    --ref_root "$REF_OUT" \
    --skip_existing "$SKIP_EXISTING"

echo "Step 3/6: Normalize REF"
if [[ "$SKIP_REF" == "1" ]]; then
    echo "  ⏭️ Skipped (SKIP_REF=1)"
else
"$PYTHON_BIN" "$BASE_DIR/data_process/normalization_single_ref.py" \
    --ref_root "$REF_OUT" \
    --out_root "$NORM_OUT" \
    --workers 4 \
    --skip_existing "$SKIP_EXISTING"
fi

echo "Step 4/6: Normalize HYP"
"$PYTHON_BIN" "$BASE_DIR/data_process/normalization_single_hyp.py" \
    --hyp_root "$HYP_OUT" \
    --ref_root "$REF_OUT" \
    --out_root "$NORM_OUT" \
    --workers 4 \
    --skip_existing "$SKIP_EXISTING"

echo "Step 5/6: Compute WER/CER"
"$PYTHON_BIN" "$BASE_DIR/scripts/compute_wer_single.py" \
    --ref_root "$NORM_OUT/ref" \
    --hyp_root "$NORM_OUT/hyp" \
    --out_root "$RESULTS_OUT" \
    --skip_existing "$SKIP_EXISTING"

echo "Step 6/6: Build Excel"
mapfile -t EXCEL_COUNTRIES < <(find "$NORM_OUT/ref" -maxdepth 1 -name '*.json' -printf '%f\n' | sed 's/\.json$//' | sort)
if [[ ${#EXCEL_COUNTRIES[@]} -eq 0 ]]; then
    echo "No normalized ref files found in $NORM_OUT/ref"
    exit 1
fi

"$PYTHON_BIN" "$BASE_DIR/scripts/excel_single.py" \
    --results_root "$RESULTS_OUT" \
    --ref_root "$NORM_OUT/ref" \
    --excel_countries "${EXCEL_COUNTRIES[@]}" \
    --skip_existing "$SKIP_EXISTING" \
    --matched_only "$MATCHED_ONLY"

echo "=============================================="
echo "Pipeline finished for $module"
echo "Results: $RESULTS_OUT"
echo "=============================================="

}

case "$MODULE" in
    "CH-EN-Dialects"|"Low-Resource-Languages"|"Vertical-Domain")
        run_one_module "$MODULE"
        ;;
    "all")
        run_one_module "CH-EN-Dialects"
        run_one_module "Low-Resource-Languages"
        run_one_module "Vertical-Domain"
        echo "Step 7: Merge all results into all_results.xlsx"
        "$PYTHON_BIN" "$BASE_DIR/scripts/merge_excel.py" --base_dir "$BASE_DIR"
        ;;
    *)
        echo "Unsupported MODULE: $MODULE"
        echo "Supported: CH-EN-Dialects | Low-Resource-Languages | Vertical-Domain | all"
        exit 1
        ;;
esac