#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   bash run.sh [MODULE] [SKIP_EXISTING] [SKIP_REF] [MATCHED_ONLY]
# MODULE: Low-Resource-Languages | CH-EN-Dialects | Vertical-Domain | Older-Children | translation | all
# SKIP_EXISTING: 1 skip existing outputs, 0 overwrite existing outputs
# SKIP_REF: 1 skip ref generate & ref normalize, 0 run all steps
# MATCHED_ONLY: 1 Excel only includes fully-matched (ref==matched), 0 include all

MODULE="${1:-CH-EN-Dialects}"
SKIP_EXISTING=1
SKIP_REF="${3:-0}"
MATCHED_ONLY="${4:-0}"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_ROOT="${DATA_ROOT:-}"
STAGING_ROOT="${STAGING_ROOT:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MODELS="${MODELS:-}"

if [[ "$SKIP_EXISTING" != "0" && "$SKIP_EXISTING" != "1" ]]; then
    echo "SKIP_EXISTING must be 0 or 1"
    exit 1
fi

run_one_module() {
    local module="$1"

    REF_OUT="$BASE_DIR/data/text/$module/ref"
    HYP_OUT="$BASE_DIR/data/text/$module/hyp"
    NORM_OUT="$BASE_DIR/data/text_normalized/$module"
    RESULTS_OUT="$BASE_DIR/data/results_$module"

    if [[ "$SKIP_EXISTING" == "0" ]]; then
        rm -rf "$BASE_DIR/data/text/$module" "$NORM_OUT" "$RESULTS_OUT"
    fi

    # Check if staging mode
    STAGING_MODULE=""
    if [[ -n "$STAGING_ROOT" ]]; then
        STAGING_MODULE="$STAGING_ROOT/$module"
        if [[ ! -d "$STAGING_MODULE/data" ]]; then
            # Try without module suffix (staging path already includes module)
            STAGING_MODULE="$STAGING_ROOT"
        fi
    fi

    echo "=============================================="
    echo "Running ASR Bench pipeline for $module"
    echo "SKIP_EXISTING = $SKIP_EXISTING"
    echo "SKIP_REF      = $SKIP_REF"
    echo "MATCHED_ONLY  = $MATCHED_ONLY"
    echo "BASE_DIR      = $BASE_DIR"
    if [[ -n "$STAGING_MODULE" ]]; then
        echo "STAGING       = $STAGING_MODULE"
    else
        echo "DATA_ROOT     = $DATA_ROOT"
    fi
    echo "=============================================="

    if [[ -n "$STAGING_MODULE" && -d "$STAGING_MODULE/data" ]]; then
        echo "Step 1/5: Convert staging to text format"
        local models_arg=""
        if [[ -n "$MODELS" ]]; then
            models_arg="--models $MODELS"
        fi
        "$PYTHON_BIN" "$BASE_DIR/data_process/convert_staging.py" \
            --staging_root "$STAGING_MODULE" \
            --module "$module" \
            --out_root "$BASE_DIR" \
            $models_arg
    else
        REF_OLD="$DATA_ROOT/$module/text/ref"
        HYP_OLD="$DATA_ROOT/$module/text/hyp"
        if [[ ! -d "$REF_OLD" || ! -d "$HYP_OLD" ]]; then
            echo "Input text directories not found under $DATA_ROOT/$module"
            exit 1
        fi
        echo "Step 1a/5: Build consolidated REF json"
        "$PYTHON_BIN" "$BASE_DIR/data_process/generate_ref.py" \
            --old_ref_root "$REF_OLD" \
            --out_ref_root "$REF_OUT" \
            --skip_existing "$SKIP_EXISTING"
        echo "Step 1b/5: Build model-wise HYP json"
        "$PYTHON_BIN" "$BASE_DIR/data_process/generate_hyp.py" \
            --hyp_input_root "$HYP_OLD" \
            --out_hyp_root "$HYP_OUT" \
            --ref_root "$REF_OUT" \
            --skip_existing "$SKIP_EXISTING"
    fi

echo "Step 2/5: Normalize REF"
"$PYTHON_BIN" "$BASE_DIR/data_process/normalize_ref.py" \
    --ref_root "$REF_OUT" \
    --out_root "$NORM_OUT" \
    --skip_existing "$SKIP_EXISTING"

echo "Step 3/5: Normalize HYP"
"$PYTHON_BIN" "$BASE_DIR/data_process/normalize_hyp.py" \
    --hyp_root "$HYP_OUT" \
    --ref_root "$REF_OUT" \
    --out_root "$NORM_OUT" \
    --skip_existing "$SKIP_EXISTING"

echo "Step 4/5: Compute WER/CER"
"$PYTHON_BIN" "$BASE_DIR/scripts/compute_wer.py" \
    --ref_root "$NORM_OUT/ref" \
    --hyp_root "$NORM_OUT/hyp" \
    --out_root "$RESULTS_OUT" \
    --skip_existing "$SKIP_EXISTING"

# Duration-filtered pipeline
MIN_DURATION="${MIN_DURATION:-0.5}"
NORM_MINDUR="$BASE_DIR/data/text_normalized_mindur/$module"
RESULTS_MINDUR="$BASE_DIR/data/results_${module}_mindur"

echo "Step 4b/5: Filter by duration > ${MIN_DURATION}s"
"$PYTHON_BIN" "$BASE_DIR/scripts/filter_duration.py" \
    --norm_root "$NORM_OUT" \
    --out_root "$NORM_MINDUR" \
    --min_duration "$MIN_DURATION"

echo "Step 4c/5: Compute WER/CER (filtered)"
"$PYTHON_BIN" "$BASE_DIR/scripts/compute_wer.py" \
    --ref_root "$NORM_MINDUR/ref" \
    --hyp_root "$NORM_MINDUR/hyp" \
    --out_root "$RESULTS_MINDUR" \
    --skip_existing "$SKIP_EXISTING"

echo "Step 5/5: Build Excel"
mapfile -t EXCEL_COUNTRIES < <(find "$NORM_OUT/ref" -maxdepth 1 -name '*.json' -printf '%f\n' | sed 's/\.json$//' | sort)
if [[ ${#EXCEL_COUNTRIES[@]} -eq 0 ]]; then
    echo "No normalized ref files found in $NORM_OUT/ref"
    exit 1
fi

"$PYTHON_BIN" "$BASE_DIR/scripts/build_excel.py" \
    --results_root "$RESULTS_OUT" \
    --ref_root "$NORM_OUT/ref" \
    --excel_countries "${EXCEL_COUNTRIES[@]}" \
    --skip_existing "$SKIP_EXISTING" \
    --matched_only "$MATCHED_ONLY"

echo "=============================================="
echo "Pipeline finished for $module"
echo "Results: $RESULTS_OUT"
echo "=============================================="

# Hotword WER: only for Vertical-Domain when release metadata has entities
ENTITY_REF_DIR="$STAGING_ROOT/Vertical-Domain/data"
if [[ "$module" == "Vertical-Domain" && -n "$STAGING_ROOT" && -d "$ENTITY_REF_DIR" ]]; then
    local hotword_hyp="$NORM_OUT/hyp"
    echo "Step Extra: Hotword WER evaluation"
    local skip_flag=""
    if [[ "$SKIP_EXISTING" == "1" ]]; then
        skip_flag="--skip_existing"
    fi
    "$PYTHON_BIN" "$BASE_DIR/scripts/hotword_wer.py" \
        --result_dir "$ENTITY_REF_DIR" \
        --hyp_dir "$hotword_hyp" \
        --norm_ref_dir "$NORM_OUT/ref" \
        --out_dir "$BASE_DIR/data/results_hotword" \
        $skip_flag

    echo "Step Extra: Hotword WER evaluation (duration > ${MIN_DURATION}s)"
    "$PYTHON_BIN" "$BASE_DIR/scripts/hotword_wer.py" \
        --result_dir "$ENTITY_REF_DIR" \
        --hyp_dir "$NORM_MINDUR/hyp" \
        --norm_ref_dir "$NORM_MINDUR/ref" \
        --out_dir "$BASE_DIR/data/results_hotword_mindur" \
        $skip_flag
fi

# Translation evaluation is handled separately by run_translation.sh

# Generate merged all_results Excel
echo "Step Extra: Merge all_results Excel"
"$PYTHON_BIN" "$BASE_DIR/scripts/merge_excel.py" --base_dir "$BASE_DIR" || true

}

case "$MODULE" in
    "CH-EN-Dialects"|"Low-Resource-Languages"|"Vertical-Domain"|"Older-Children")
        run_one_module "$MODULE"
        ;;
    "all")
        run_one_module "Low-Resource-Languages"
        run_one_module "CH-EN-Dialects"
        run_one_module "Vertical-Domain"
        run_one_module "Older-Children"
        echo "Step 7: Merge all results into all_results.xlsx"
        "$PYTHON_BIN" "$BASE_DIR/scripts/merge_excel.py" --base_dir "$BASE_DIR"
        ;;
    *)
        echo "Unsupported MODULE: $MODULE"
        echo "Supported: Low-Resource-Languages | CH-EN-Dialects | Vertical-Domain | Older-Children | all"
        exit 1
        ;;
esac