#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Strict non-batch version:

- 只扫描一次评测结果目录
- 强白名单 model
- 非白名单 model 全流程忽略
- 输出单一 Excel（WER / CER）
"""

import os
import re
import json
import pandas as pd

# =========================
# 常量
# =========================

EXCEL_COUNTRIES = [
    "IRQ","DZA","ARE","EGY","MAR","SAU",
    "IDN","MYS","PHL","VNM","THA","JPN",
    "KOR","CHN","USA","CHN-EN","IDN-EN","JPN-EN","PHL-EN","SCT-EN","SGP-EN","XIANG","JIN"
]

#RESULTS_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results_CH-EN-Dialects"
#RESULTS_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results_Low-Resource-Languages"
RESULTS_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results_fleurs"
#RESULTS_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results_common-voice"

#REF_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/CH-EN-Dialects/ref"
#REF_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/Low-Resource-Languages/ref"
REF_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/fleurs/ref"
#REF_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/common-voice/ref"

# =========================
# 白名单（唯一合法 model）
# =========================

COVERAGE_MODELS = {
    "AZURE",
    "BIGASR_V400",
    "CHIRP3",
    "DOLPHIN_SMALL",
    "DOLPHIN_BASE",
    "ELEVENLABS_SCRIBE_V2",
    "FUN-ASR-MLT-NANO",
    "GEMINI_3_0_FLASH",
    "GPT4O-TRANSCRIBE",
    "OMNIASR_LLM_3B",
    "QWEN3-ASR-FLASH",
    "STT_AR_FASTCONFORMER_HYBRID_LARGE_PCD_V1.0.NEMO",
    "WHISPER",
    "STT_KR_CONFORMER_TRANSDUCER_LARGE",
    "PARAKEET-TDT_CTC-0.6B-JA",
    "NVIDIA-NEMO",
    "WHISPER-LARGE-V3",
    "GEMINI",
    "SEEDASR_2.0",
    "GEMINI-3-FLASH-PREVIEW",
    "QWEN3-ASR-1.7B"
}

# =========================
# 工具函数
# =========================

def extract_value(path: str):
    """从 err* 文件中提取 %WER（CER 文件也可能写 %WER）"""
    try:
        with open(path, "r", encoding="utf8") as f:
            for raw in f:
                line = raw.strip()
                if line.startswith("%WER"):
                    m = re.search(r"%WER\s*=\s*([0-9]+(?:\.[0-9]+)?)", line)
                    if m:
                        return float(m.group(1))
        return "-"
    except Exception:
        return "-"


def normalize_model_name(model: str):
    """裁掉可能的 XXX_ 前缀"""
    if re.match(r"^[A-Z]{3}_", model):
        return model[4:]
    return model


def pick_err_file(m_dir: str):
    """优先 err*，否则 fallback 任意 .txt"""
    if not os.path.isdir(m_dir):
        return None

    names = [
        n for n in os.listdir(m_dir)
        if os.path.isfile(os.path.join(m_dir, n))
    ]
    if not names:
        return None

    err = [n for n in names if n.lower().startswith("err")]
    if err:
        txts = [n for n in err if n.lower().endswith(".txt")]
        return os.path.join(m_dir, sorted(txts or err)[0])

    txts = sorted(n for n in names if n.lower().endswith(".txt"))
    return os.path.join(m_dir, txts[0]) if txts else None


# =========================
# 扫描结果（non-batch）
# =========================

def scan_results(results_root: str):
    """
    结构：
      results_root/<COUNTRY>/<MODEL>/
    """
    table = {}

    for country in EXCEL_COUNTRIES:
        c_dir = os.path.join(results_root, country)
        if not os.path.isdir(c_dir):
            continue

        for model in os.listdir(c_dir):
            m_dir = os.path.join(c_dir, model)
            if not os.path.isdir(m_dir):
                continue

            model_clean = normalize_model_name(model)

            # ⛔ 强白名单
            if model_clean not in COVERAGE_MODELS:
                continue

            err_path = pick_err_file(m_dir)
            if not err_path:
                continue

            val = extract_value(err_path)
            table.setdefault(model_clean, {})[country] = val

    df = pd.DataFrame.from_dict(table, orient="index")
    df = df.reindex(columns=EXCEL_COUNTRIES)
    return df.fillna("-")


# =========================
# ref 段数统计
# =========================

def load_ref_counts():
    ref_count = {}

    for fn in os.listdir(REF_ROOT):
        if not fn.endswith(".json"):
            continue

        country = fn[:-5]
        path = os.path.join(REF_ROOT, fn)

        try:
            with open(path, "r", encoding="utf8") as f:
                data = json.load(f)
            if isinstance(data, list):
                ref_count[country] = len(data)
        except Exception:
            continue

    return ref_count


# =========================
# 主入口
# =========================

def main():
    print(f"📂 扫描 results 目录: {RESULTS_ROOT}")

    ref_count = load_ref_counts()
    df = scan_results(RESULTS_ROOT)

    out_xlsx = os.path.join(RESULTS_ROOT, "results.xlsx")
    df.to_excel(out_xlsx)

    print(f"✔️ WER/CER Excel → {out_xlsx}")
    print("\n📊 ref 段数统计：")
    for c, n in sorted(ref_count.items()):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
