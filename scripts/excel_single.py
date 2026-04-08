#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Strict non-batch Excel 生成脚本（可传参）

- 扫描 results_root/<COUNTRY>/<MODEL>/ 
- 强白名单 model
- 输出单一 Excel（WER / CER）
- 支持命令行指定 RESULTS_ROOT, REF_ROOT, EXCEL_COUNTRIES
"""

import os
import re
import json
import pandas as pd
import argparse

# =========================
# 默认白名单 model
# =========================
COVERAGE_MODELS = {
    "AZURE","BIGASR_V400","CHIRP3","DOLPHIN_SMALL","DOLPHIN_BASE",
    "ELEVENLABS_SCRIBE_V2","FUN-ASR-MLT-NANO","GEMINI_3_0_FLASH","GPT4O-TRANSCRIBE",
    "OMNIASR_LLM_3B","QWEN3-ASR-FLASH","STT_AR_FASTCONFORMER_HYBRID_LARGE_PCD_V1.0.NEMO",
    "WHISPER","STT_KR_CONFORMER_TRANSDUCER_LARGE","PARAKEET-TDT_CTC-0.6B-JA",
    "NVIDIA-NEMO","WHISPER-LARGE-V3","GEMINI","SEEDASR_2.0","GEMINI-3-FLASH-PREVIEW",
    "QWEN3-ASR-1.7B","FUN-ASR-NANO","SEEDASR2","SEEDASR"
}

# =========================
# 工具函数
# =========================
def extract_value(path: str):
    """从 err* 文件中提取 %WER/CER"""
    try:
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("%WER"):
                    m = re.search(r"%WER\s*=\s*([0-9]+(?:\.[0-9]+)?)", line)
                    if m:
                        return float(m.group(1))
        return "-"
    except Exception:
        return "-"

def normalize_model_name(model: str):
    if re.match(r"^[A-Z]{3}_", model):
        return model[4:]
    return model

def pick_err_file(m_dir: str):
    if not os.path.isdir(m_dir):
        return None
    names = [n for n in os.listdir(m_dir) if os.path.isfile(os.path.join(m_dir, n))]
    if not names:
        return None
    err = [n for n in names if n.lower().startswith("err")]
    if err:
        txts = [n for n in err if n.lower().endswith(".txt")]
        return os.path.join(m_dir, sorted(txts or err)[0])
    txts = sorted(n for n in names if n.lower().endswith(".txt"))
    return os.path.join(m_dir, txts[0]) if txts else None

# =========================
# 扫描结果
# =========================
def scan_results(results_root: str, excel_countries):
    table = {}
    for country in excel_countries:
        c_dir = os.path.join(results_root, country)
        if not os.path.isdir(c_dir):
            continue
        for model in os.listdir(c_dir):
            m_dir = os.path.join(c_dir, model)
            if not os.path.isdir(m_dir):
                continue
            model_clean = normalize_model_name(model)
            if model_clean not in COVERAGE_MODELS:
                continue
            err_path = pick_err_file(m_dir)
            if not err_path:
                continue
            val = extract_value(err_path)
            table.setdefault(model_clean, {})[country] = val
    df = pd.DataFrame.from_dict(table, orient="index")
    df = df.reindex(columns=excel_countries)
    return df.fillna("-")

# =========================
# REF 段数统计
# =========================
def load_ref_counts(ref_root: str):
    ref_count = {}
    for fn in os.listdir(ref_root):
        if not fn.endswith(".json"):
            continue
        country = fn[:-5]
        path = os.path.join(ref_root, fn)
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
def main(results_root: str, ref_root: str, excel_countries):
    print(f"📂 扫描 results 目录: {results_root}")
    ref_count = load_ref_counts(ref_root)
    df = scan_results(results_root, excel_countries)
    out_xlsx = os.path.join(results_root, "results.xlsx")
    df.to_excel(out_xlsx)
    print(f"✔️ WER/CER Excel → {out_xlsx}")
    print("\n📊 ref 段数统计：")
    for c, n in sorted(ref_count.items()):
        print(f"  {c}: {n}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strict non-batch Excel generator")
    parser.add_argument("--results_root", type=str, required=True)
    parser.add_argument("--ref_root", type=str, required=True)
    parser.add_argument("--excel_countries", type=str, nargs="+", required=True,
                        help="列出要生成 Excel 的国家/区域，如 AGR-CH AIT-CH ...")
    args = parser.parse_args()
    main(args.results_root, args.ref_root, args.excel_countries)