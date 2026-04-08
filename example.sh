#!/bin/bash
# ==========================================
# run_all.sh
# 依次运行 ASR Bench 流程，MODULE 内置
# ==========================================

# ===== 内置 MODULE 选项 =====
# 可修改这里选择要跑的模块：
# 选择 CH-EN-Dialects / Low-Resource-Languages / Vertical-Domain
MODULE="fleurs"

BASE_DIR="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark"

case $MODULE in
    "CH-EN-Dialects")
        REF_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/CH-EN-Dialects/text/ref"
        HYP_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/CH-EN-Dialects/text/hyp"
        REF_NORM_OUT="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/CH-EN-Dialects"
        HYP_NORM_OUT="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/CH-EN-Dialects"
        REF_OUT="$BASE_DIR/data/text/CH-EN-Dialects/ref"
        HYP_OUT="$BASE_DIR/data/text/CH-EN-Dialects/hyp"
        RESULTS_OUT="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results_CH-EN-Dialects"
        EXCEL_COUNTRIES=("CHN-EN" "IDN-EN" "JPN-EN" "PHL-EN" "SCT-EN" "SGP-EN" "XIANG" "JIN" "GAN" "MIN" "YUE" "WU")
        ;;
    "Low-Resource-Languages")
        REF_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/Low-Resource-Languages/text/ref"
        HYP_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/Low-Resource-Languages/text/hyp"
        REF_NORM_OUT="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/Low-Resource-Languages"
        HYP_NORM_OUT="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/Low-Resource-Languages"
        REF_OUT="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text/Low-Resource-Languages/ref"
        HYP_OUT="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text/Low-Resource-Languages/hyp"
        RESULTS_OUT="$BASE_DIR/data/results_Low-Resource-Languages"
        EXCEL_COUNTRIES=("IRQ" "DZA" "ARE" "EGY" "MAR" "SAU" "SYR" "IDN" "MYS" "PHL" "VNM" "THA" "JPN" "JPN_hard" "KOR"	"KOR_hard")
        ;;
    "Vertical-Domain")
        REF_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/Vertical-Domain/text/ref"
        HYP_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/Vertical-Domain/text/hyp"
        REF_OUT="$BASE_DIR/data/text/Vertical-Domain/ref"
        HYP_OUT="$BASE_DIR/data/text/Vertical-Domain/hyp"
        REF_NORM_OUT="$BASE_DIR/data/text_normalized/Vertical-Domain"
        HYP_NORM_OUT="$BASE_DIR/data/text_normalized/Vertical-Domain"
        RESULTS_OUT="$BASE_DIR/data/results_Vertical-Domain"
        EXCEL_COUNTRIES=("AGR-CH" "AIT-CH" "ART-CH" "BIO-CH" "ECM-CH" "ENG-CH" "ENT-CH" "FIN-CH" "HUM-CH" "LAW-CH" "MED-CH" "MIL-CH" "AGR-EN" "AIT-EN" "ART-EN" "BIO-EN" "ECM-EN" "ENG-EN" "ENT-EN" "FIN-EN" "HUM-EN" "LAW-EN" "MED-EN" "MIL-EN")
        ;;
    "fleurs")
        REF_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/fleurs/text/ref"
        HYP_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/fleurs/text/hyp"
        REF_OUT="$BASE_DIR/data/text/fleurs/ref"
        HYP_OUT="$BASE_DIR/data/text/fleurs/hyp"
        REF_NORM_OUT="$BASE_DIR/data/text_normalized/fleurs"
        HYP_NORM_OUT="$BASE_DIR/data/text_normalized/fleurs"
        RESULTS_OUT="$BASE_DIR/data/results_fleurs"
        EXCEL_COUNTRIES=("EGY" "IDN" "MYS" "PHL" "VNM" "THA" "JPN" "KOR")
        ;;
    "cv")
        REF_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/common-voice/text/ref"
        HYP_OLD="/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/common-voice/text/hyp"
        REF_OUT="$BASE_DIR/data/text/common-voice/ref"
        HYP_OUT="$BASE_DIR/data/text/common-voice/hyp"
        REF_NORM_OUT="$BASE_DIR/data/text_normalized/common-voice"
        HYP_NORM_OUT="$BASE_DIR/data/text_normalized/common-voice"
        RESULTS_OUT="$BASE_DIR/data/results_common-voice"
        EXCEL_COUNTRIES=("AR" "IDN" "VNM" "THA" "JPN" "KOR")
        ;;
    *)
        echo "Invalid MODULE: $MODULE"
        exit 1
        ;;
esac

echo "=============================================="
echo "Running ASR Bench pipeline for $MODULE"
echo "=============================================="

# Step 1: 生成 REF
echo "💡 Step 1: Non-batch REF generation"
#python3 $BASE_DIR/data_process/generate_ref_json_single.py --old_ref_root $REF_OLD --out_ref_root $REF_OUT

# Step 2: 生成 HYP
echo "💡 Step 2: Non-batch HYP generation"
python3 $BASE_DIR/data_process/generate_hyp_json_single.py --hyp_input_root $HYP_OLD --out_hyp_root $HYP_OUT

# Step 3: REF 文本归一化
echo "💡 Step 3: REF normalization"
#python3 $BASE_DIR/data_process/normalization_single_ref.py --ref_root $REF_OUT --out_root $REF_NORM_OUT --workers 4

# Step 4: HYP 文本归一化
echo "💡 Step 4: HYP normalization"
python3 $BASE_DIR/data_process/normalization_single_hyp.py --hyp_root $HYP_OUT --ref_root $REF_OUT --out_root $HYP_NORM_OUT --workers 4

# Step 5: 单 batch WER/CER
echo "💡 Step 5: WER/CER evaluation"
python3 $BASE_DIR/scripts/compute_wer_single.py --ref_root "$REF_NORM_OUT/ref" --hyp_root "$HYP_NORM_OUT/hyp" --out_root $RESULTS_OUT

# Step 6: Excel 汇总
echo "💡 Step 6: Excel generation"
python3 $BASE_DIR/scripts/excel_single.py --results_root $RESULTS_OUT --ref_root "$REF_NORM_OUT/ref" --excel_countries ${EXCEL_COUNTRIES[@]}

echo "=============================================="
echo "✅ Pipeline finished for $MODULE"
echo "=============================================="