#!/bin/bash
set -e

echo "========================"
echo " Step 1: Generate REF JSON"
echo "========================"
#python data_process/generate_ref_json.py

echo "========================"
echo " Step 2: Generate HYP JSON"
echo "========================"
#python data_process/generate_hyp_json.py

echo "========================"
echo " Step 3: Normalization"
echo "========================"
python data_process/normalization.py

echo "========================"
echo " Step 4: Compute WER"
echo "========================"
python scripts/compute_wer.py

echo "========================"
echo "✔ All steps completed successfully!"
echo "========================"
