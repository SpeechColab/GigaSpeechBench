#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# GigaSpeechBench Evaluation Pipeline
# ============================================================
#
# Usage:
#   bash example.sh <STAGING_ROOT> [MODULE] [OPTIONS]
#
# Arguments:
#   STAGING_ROOT    Path to staging directory containing module subdirs:
#                     {MODULE}/data/{LANG}/metadata.json
#                     {MODULE}/results/{MODEL}.json
#   MODULE          Module to evaluate (default: all)
#                     Low-Resource-Languages | CH-EN-Dialects | Vertical-Domain |
#                     fleurs | common-voice | all
#
# Options:
#   --force          Force overwrite all outputs
#   --workers N      Number of parallel workers for normalization (default: auto)
#
# Example:
#   bash example.sh /path/to/staging Low-Resource-Languages
#   bash example.sh /path/to/staging all --workers 8

STAGING_ROOT="${1:?Usage: bash example.sh <STAGING_ROOT> [MODULE] [--force] [--workers N]}"
shift || true

MODULE="${1:-all}"
if [[ "$MODULE" != "--"* && -n "$MODULE" ]]; then
    shift || true
else
    MODULE="all"
fi

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

ALL_MODULES=(Low-Resource-Languages CH-EN-Dialects Vertical-Domain fleurs common-voice Older-Children)
LOG_DIR="$BASE_DIR/data/log"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%Y%m%d_%H%M%S).log"

echo "=============================================="
echo "GigaSpeechBench Evaluation Pipeline"
echo "  STAGING  = $STAGING_ROOT"
echo "  MODULE   = $MODULE"
echo "  BASE_DIR = $BASE_DIR"
echo "  WORKERS  = $WORKERS (0=auto)"
echo "  FORCE    = $( [[ $SKIP_EXISTING -eq 0 ]] && echo yes || echo no )"
echo "  LOG      = $LOG_FILE"
echo "=============================================="

# Tee all output (stdout + stderr) to log file
exec > >(tee -a "$LOG_FILE") 2> >(tee -a "$LOG_FILE" >&2)

run_one_module() {
    local mod="$1"
    local DATASET_ROOT="$STAGING_ROOT/$mod"

    if [[ ! -d "$DATASET_ROOT/data" ]]; then
        echo "⚠️  Skip $mod: $DATASET_ROOT/data not found"
        return
    fi

    local TEXT_DIR="$BASE_DIR/data/text_${mod}"
    local NORM_DIR="$BASE_DIR/data/text_normalized_${mod}"
    local RESULTS_DIR="$BASE_DIR/data/results_${mod}"

    echo ""
    echo "=============================================="
    echo "Module: $mod"
    echo "  DATASET  = $DATASET_ROOT"
    echo "=============================================="

    # Step 1: Convert
    echo "Step 1/4: Convert data"
    "$PYTHON_BIN" "$BASE_DIR/data_process/convert_data.py" \
        --data_root "$DATASET_ROOT/data" \
        --results_root "$DATASET_ROOT/results" \
        --out_dir "$TEXT_DIR" \
        --skip_existing "$SKIP_EXISTING"

    # Step 2: Normalize
    echo ""
    echo "Step 2/4: Normalize text"
    "$PYTHON_BIN" "$BASE_DIR/data_process/normalize.py" \
        --text_root "$TEXT_DIR" \
        --out_root "$NORM_DIR" \
        --workers "$WORKERS" \
        --skip_existing "$SKIP_EXISTING"

    # Step 3: WER/CER
    echo ""
    echo "Step 3/4: Compute WER/CER"
    "$PYTHON_BIN" "$BASE_DIR/scripts/compute_wer_single.py" \
        --ref_root "$NORM_DIR/ref" \
        --hyp_root "$NORM_DIR/hyp" \
        --out_root "$RESULTS_DIR" \
        --skip_existing "$SKIP_EXISTING"

    # Step 4: Excel
    echo ""
    echo "Step 4/4: Build Excel"

    # Per-module country order (if defined); fallback to sorted ref files
    local -a COUNTRIES
    case "$mod" in
        "Low-Resource-Languages")
            COUNTRIES=(IRQ DZA ARE EGY MAR SAU SYR IDN MYS PHL PHL_EN PHL_noEN VNM THA JPN JPN_hard JPN_0502 KOR KOR_hard KOR_0502)
            ;;
        "Older-Children")
            COUNTRIES=(CHILD-EN)
            ;;
        "Vertical-Domain")
            COUNTRIES=(AGR-CH AGR-EN AIT-CH AIT-EN ART-CH ART-EN BIO-CH BIO-EN ECM-CH ECM-EN ENG-CH ENG-EN ENT-CH ENT-EN FIN-CH FIN-EN HUM-CH HUM-EN LAW-CH LAW-EN MED-CH MED-EN MIL-CH MIL-EN)
            ;;
        "CH-EN-Dialects")
            COUNTRIES=(CHN-EN IDN-EN JPN-EN PHL-EN SCT-EN SGP-EN JIN MIN WU XIANG YUE)
            ;;
        *)
            mapfile -t COUNTRIES < <(find "$NORM_DIR/ref" -maxdepth 1 -name '*.json' -printf '%f\n' | sed 's/\.json$//' | sort)
            ;;
    esac

    # Filter to only countries that have ref files, and exclude EDU
    local -a VALID_COUNTRIES=()
    for c in "${COUNTRIES[@]}"; do
        if [[ -f "$NORM_DIR/ref/${c}.json" && ! "$c" =~ ^EDU ]]; then
            VALID_COUNTRIES+=("$c")
        fi
    done
    COUNTRIES=("${VALID_COUNTRIES[@]}")

    if [[ ${#COUNTRIES[@]} -eq 0 ]]; then
        echo "No ref files found for $mod."
        return
    fi

    # Vertical-Domain: split into CH and EN Excel files
    if [[ "$mod" == "Vertical-Domain" ]]; then
        local -a CH_COUNTRIES=()
        local -a EN_COUNTRIES=()
        for c in "${COUNTRIES[@]}"; do
            if [[ "$c" == *-CH ]]; then
                CH_COUNTRIES+=("$c")
            elif [[ "$c" == *-EN ]]; then
                EN_COUNTRIES+=("$c")
            fi
        done

        if [[ ${#CH_COUNTRIES[@]} -gt 0 ]]; then
            "$PYTHON_BIN" "$BASE_DIR/scripts/excel_single.py" \
                --results_root "$RESULTS_DIR" \
                --ref_root "$NORM_DIR/ref" \
                --excel_countries "${CH_COUNTRIES[@]}" \
                --module_name "${mod}-CH" \
                --skip_existing 0 \
                --matched_only 0
        fi

        if [[ ${#EN_COUNTRIES[@]} -gt 0 ]]; then
            "$PYTHON_BIN" "$BASE_DIR/scripts/excel_single.py" \
                --results_root "$RESULTS_DIR" \
                --ref_root "$NORM_DIR/ref" \
                --excel_countries "${EN_COUNTRIES[@]}" \
                --module_name "${mod}-EN" \
                --skip_existing 0 \
                --matched_only 0
        fi
    else
        "$PYTHON_BIN" "$BASE_DIR/scripts/excel_single.py" \
            --results_root "$RESULTS_DIR" \
            --ref_root "$NORM_DIR/ref" \
            --excel_countries "${COUNTRIES[@]}" \
            --module_name "$mod" \
            --skip_existing 0 \
            --matched_only 0
    fi

    echo ""
    echo "Pipeline finished for $mod"
    echo "Results: $RESULTS_DIR"
}

case "$MODULE" in
    "Low-Resource-Languages"|"CH-EN-Dialects"|"Vertical-Domain"|"fleurs"|"common-voice"|"Older-Children")
        run_one_module "$MODULE"
        ;;
    "all")
        for mod in "${ALL_MODULES[@]}"; do
            run_one_module "$mod"
        done
        echo ""
        echo "Step 5: Merge all results"
        "$PYTHON_BIN" "$BASE_DIR/scripts/merge_excel.py" --base_dir "$BASE_DIR"
        ;;
    *)
        echo "Unknown module: $MODULE"
        echo "Supported: Low-Resource-Languages | CH-EN-Dialects | Vertical-Domain | fleurs | common-voice | all"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "Done. Log: $LOG_FILE"
echo "=============================================="
