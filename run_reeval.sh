#!/usr/bin/env bash
set -euo pipefail

# Re-run HYP generation, HYP normalization, WER/CER, Excel, and unaligned report
# Skips REF generation and REF normalization (already done)

BASE_DIR="/home/v-yujietu/Multilingual-ASR-Benchmark"
DATA_ROOT="/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark"
PYTHON_BIN="python3"
SKIP_EXISTING=0  # overwrite

run_module() {
    local module="$1"

    REF_OLD="$DATA_ROOT/$module/text/ref"
    HYP_OLD="$DATA_ROOT/$module/text/hyp"

    REF_OUT="$BASE_DIR/data/text/$module/ref"
    HYP_OUT="$BASE_DIR/data/text/$module/hyp"

    NORM_OUT="$BASE_DIR/data/text_normalized/$module"
    RESULTS_OUT="$BASE_DIR/data/results_$module"

    # Clean hyp and results (keep ref and normalized ref)
    rm -rf "$HYP_OUT" "$NORM_OUT/hyp" "$RESULTS_OUT"

    echo "=============================================="
    echo "Re-running pipeline for $module (HYP only, overwrite)"
    echo "=============================================="

    echo "Step 2/6: Build model-wise HYP json"
    "$PYTHON_BIN" "$BASE_DIR/data_process/generate_hyp_json_single.py" \
        --hyp_input_root "$HYP_OLD" \
        --out_hyp_root "$HYP_OUT" \
        --ref_root "$REF_OUT" \
        --skip_existing "$SKIP_EXISTING"

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
        --skip_existing "$SKIP_EXISTING"

    echo "Report: unaligned segments"
    "$PYTHON_BIN" "$BASE_DIR/scripts/report_unaligned.py" \
        --results_root "$RESULTS_OUT" \
        --out_txt "$RESULTS_OUT/unaligned_report.txt"

    echo "=============================================="
    echo "Pipeline finished for $module"
    echo "Results: $RESULTS_OUT"
    echo "Unaligned report: $RESULTS_OUT/unaligned_report.txt"
    echo "=============================================="
}

run_module "Low-Resource-Languages"
run_module "CH-EN-Dialects"

echo "ALL DONE"
