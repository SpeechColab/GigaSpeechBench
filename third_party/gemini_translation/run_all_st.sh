#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="/home/v-yujietu/Multilingual-ASR-Benchmark/data/st_results"
PYTHON="python3"
BATCH_SCRIPT="$SCRIPT_DIR/gemini_st_batch.py"
EVAL_SCRIPT="$SCRIPT_DIR/eval_st.py"

LANGS="ARE DZA EGY IDN IRQ MAR MYS PHL SAU THA VNM"
MAX_SEGS=450
SLEEP=4

mkdir -p "$OUTPUT_DIR"

echo "=== Gemini ST Batch Run ==="
echo "Languages: $LANGS"
echo "Max segs per lang per target: $MAX_SEGS"
echo "Sleep between calls: ${SLEEP}s"
echo ""

for target in en zh; do
    echo "=== Target: $target ==="
    for lang in $LANGS; do
        echo ""
        echo ">>> $lang -> $target ($(date))"
        $PYTHON "$BATCH_SCRIPT" \
            --lang "$lang" \
            --target "$target" \
            --max_segs "$MAX_SEGS" \
            --output_dir "$OUTPUT_DIR" \
            --sleep "$SLEEP" 2>&1
    done
done

echo ""
echo "=== Evaluation ==="
$PYTHON "$EVAL_SCRIPT" \
    --results_dir "$OUTPUT_DIR" \
    --output "$OUTPUT_DIR/eval_report.txt"

echo "=== ALL DONE ==="
