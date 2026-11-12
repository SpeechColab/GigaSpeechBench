#!/usr/bin/env bash
set -euo pipefail

# bash run_ASR.sh [MODULE] [SKIP_EXISTING=1] [SKIP_REF=0] [MATCHED_ONLY=0]
MODULE="${1:-CH-EN-Dialects}"
SKIP_EXISTING="${2:-1}"
SKIP_REF="${3:-0}"
MATCHED_ONLY="${4:-0}"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_ROOT="${OUT_ROOT:-$BASE_DIR}"
DATA_ROOT="${DATA_ROOT:-}"
STAGING_ROOT="${STAGING_ROOT:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MODELS="${MODELS:-}"
WORKERS="${WORKERS:-4}"
MIN_DURATION="${MIN_DURATION:-0.5}"

for option in SKIP_EXISTING SKIP_REF MATCHED_ONLY; do
    if [[ "${!option}" != "0" && "${!option}" != "1" ]]; then
        echo "$option must be 0 or 1"
        exit 1
    fi
done

run_one_module() {
    local module="$1"
    local ref_out="$OUT_ROOT/data/text/$module/ref"
    local hyp_out="$OUT_ROOT/data/text/$module/hyp"
    local norm_out="$OUT_ROOT/data/text_normalized/$module"
    local results_out="$OUT_ROOT/data/results_$module"
    local norm_mindur="$OUT_ROOT/data/text_normalized_mindur/$module"
    local results_mindur="$OUT_ROOT/data/results_${module}_mindur"
    local staging_module=""

    if [[ "$SKIP_REF" == "1" && ! -d "$norm_out/ref" ]]; then
        echo "Normalized references not found: $norm_out/ref"
        exit 1
    fi
    if [[ "$SKIP_EXISTING" == "0" ]]; then
        rm -rf "$hyp_out" "$norm_out/hyp" "$results_out" "$norm_mindur" "$results_mindur"
        if [[ "$SKIP_REF" == "0" ]]; then
            rm -rf "$ref_out" "$norm_out/ref"
        fi
    fi
    if [[ -n "$STAGING_ROOT" ]]; then
        staging_module="$STAGING_ROOT/$module"
        if [[ ! -d "$staging_module/data" ]]; then
            staging_module="$STAGING_ROOT"
        fi
    fi
    echo "Running $module: SKIP_EXISTING = $SKIP_EXISTING, SKIP_REF = $SKIP_REF"

    if [[ -n "$staging_module" && -d "$staging_module/data" ]]; then
        local model_args=()
        if [[ -n "$MODELS" ]]; then
            model_args=(--models "$MODELS")
        fi
        "$PYTHON_BIN" "$BASE_DIR/data_process/convert_staging.py" \
            --staging_root "$staging_module" --module "$module" --out_root "$OUT_ROOT" \
            --skip_existing "$SKIP_EXISTING" --skip_ref "$SKIP_REF" "${model_args[@]}"
    else
        local old_ref="$DATA_ROOT/$module/text/ref"
        local old_hyp="$DATA_ROOT/$module/text/hyp"
        if [[ ! -d "$old_hyp" || ( "$SKIP_REF" == "0" && ! -d "$old_ref" ) ]]; then
            echo "Input text directories not found under $DATA_ROOT/$module"
            exit 1
        fi
        if [[ "$SKIP_REF" == "0" ]]; then
            "$PYTHON_BIN" "$BASE_DIR/data_process/generate_ref.py" \
                --old_ref_root "$old_ref" --out_ref_root "$ref_out" --skip_existing "$SKIP_EXISTING"
        fi
        "$PYTHON_BIN" "$BASE_DIR/data_process/generate_hyp.py" \
            --hyp_input_root "$old_hyp" --out_hyp_root "$hyp_out" \
            --ref_root "$ref_out" --skip_existing "$SKIP_EXISTING"
    fi

    if [[ "$SKIP_REF" == "0" ]]; then
        "$PYTHON_BIN" "$BASE_DIR/data_process/normalize_ref.py" \
            --ref_root "$ref_out" --out_root "$norm_out" \
            --skip_existing "$SKIP_EXISTING" --workers "$WORKERS"
    fi
    "$PYTHON_BIN" "$BASE_DIR/data_process/normalize_hyp.py" \
        --hyp_root "$hyp_out" --out_root "$norm_out" \
        --skip_existing "$SKIP_EXISTING" --workers "$WORKERS"
    "$PYTHON_BIN" "$BASE_DIR/scripts/compute_wer.py" \
        --ref_root "$norm_out/ref" --hyp_root "$norm_out/hyp" --out_root "$results_out" \
        --skip_existing "$SKIP_EXISTING" --min_duration "$MIN_DURATION" --workers "$WORKERS"
    "$PYTHON_BIN" "$BASE_DIR/scripts/filter_duration.py" \
        --norm_root "$norm_out" --out_root "$norm_mindur" --min_duration "$MIN_DURATION"
    "$PYTHON_BIN" "$BASE_DIR/scripts/compute_wer.py" \
        --ref_root "$norm_mindur/ref" --hyp_root "$norm_mindur/hyp" --out_root "$results_mindur" \
        --skip_existing "$SKIP_EXISTING" --min_duration "$MIN_DURATION" --workers "$WORKERS"

    local countries=()
    mapfile -t countries < <(find "$norm_out/ref" -maxdepth 1 -name '*.json' -printf '%f\n' | sed 's/\.json$//' | sort)
    if [[ ${#countries[@]} -eq 0 ]]; then
        echo "No normalized ref files found in $norm_out/ref"
        exit 1
    fi
    local variant root ref
    for variant in all mindur; do
        root="$results_out"; ref="$norm_out/ref"
        if [[ "$variant" == "mindur" ]]; then
            root="$results_mindur"; ref="$norm_mindur/ref"
        fi
        "$PYTHON_BIN" "$BASE_DIR/scripts/build_excel.py" \
            --results_root "$root" --ref_root "$ref" --excel_countries "${countries[@]}" \
            --skip_existing "$SKIP_EXISTING" --matched_only "$MATCHED_ONLY"
    done

    if [[ "$module" == "Vertical-Domain" && -n "$staging_module" ]]; then
        local skip_args=()
        if [[ "$SKIP_EXISTING" == "1" ]]; then skip_args=(--skip_existing); fi
        "$PYTHON_BIN" "$BASE_DIR/scripts/hotword_wer.py" \
            --result_dir "$staging_module/data" --hyp_dir "$norm_out/hyp" \
            --norm_ref_dir "$norm_out/ref" --out_dir "$OUT_ROOT/data/results_hotword" "${skip_args[@]}"
        "$PYTHON_BIN" "$BASE_DIR/scripts/hotword_wer.py" \
            --result_dir "$staging_module/data" --hyp_dir "$norm_mindur/hyp" \
            --norm_ref_dir "$norm_mindur/ref" --out_dir "$OUT_ROOT/data/results_hotword_mindur" "${skip_args[@]}"
    fi
    echo "Results: $results_mindur"
}

case "$MODULE" in
    CH-EN-Dialects|Low-Resource-Languages|Vertical-Domain|Older-Children)
        run_one_module "$MODULE" ;;
    all)
        for module in Low-Resource-Languages CH-EN-Dialects Vertical-Domain Older-Children; do
            run_one_module "$module"
        done ;;
    *)
        echo "Supported: Low-Resource-Languages | CH-EN-Dialects | Vertical-Domain | Older-Children | all"
        exit 1 ;;
esac
"$PYTHON_BIN" "$BASE_DIR/scripts/merge_excel.py" --base_dir "$OUT_ROOT"
