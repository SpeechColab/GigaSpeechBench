#!/usr/bin/env bash
set -euo pipefail

# Re-run normalization + WER + Excel + report for all modules
# (ref/hyp JSON generation is kept; only re-normalize and re-evaluate)

BASE_DIR="/home/v-yujietu/Multilingual-ASR-Benchmark"
PYTHON_BIN="python3"

run_module() {
    local module="$1"

    REF_OUT="$BASE_DIR/data/text/$module/ref"
    HYP_OUT="$BASE_DIR/data/text/$module/hyp"
    NORM_OUT="$BASE_DIR/data/text_normalized/$module"
    RESULTS_OUT="$BASE_DIR/data/results_$module"

    # Clean normalized data and results (keep text/ref and text/hyp)
    rm -rf "$NORM_OUT" "$RESULTS_OUT"
    mkdir -p "$NORM_OUT"

    echo "=============================================="
    echo " Module: $module"
    echo "=============================================="

    echo "Step 3/6: Normalize REF"
    "$PYTHON_BIN" "$BASE_DIR/data_process/normalization_single_ref.py" \
        --ref_root "$REF_OUT" \
        --out_root "$NORM_OUT" \
        --workers 4 \
        --skip_existing 0

    echo "Step 4/6: Normalize HYP"
    "$PYTHON_BIN" "$BASE_DIR/data_process/normalization_single_hyp.py" \
        --hyp_root "$HYP_OUT" \
        --ref_root "$REF_OUT" \
        --out_root "$NORM_OUT" \
        --workers 4 \
        --skip_existing 0

    echo "Step 5/6: Compute WER/CER"
    "$PYTHON_BIN" "$BASE_DIR/scripts/compute_wer_single.py" \
        --ref_root "$NORM_OUT/ref" \
        --hyp_root "$NORM_OUT/hyp" \
        --out_root "$RESULTS_OUT" \
        --skip_existing 0

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
        --skip_existing 0

    echo "Report: unaligned segments"
    "$PYTHON_BIN" "$BASE_DIR/scripts/report_unaligned.py" \
        --results_root "$RESULTS_OUT" \
        --out_txt "$RESULTS_OUT/unaligned_report.txt"

    echo "=============================================="
    echo " Done: $module"
    echo "=============================================="
}

run_module "Low-Resource-Languages"
run_module "CH-EN-Dialects"
run_module "Vertical-Domain"

echo "ALL MODULES DONE"
