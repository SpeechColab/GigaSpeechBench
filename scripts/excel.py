#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从 data/results 中读取 summary 文件，
为每个 batch + total 生成 Excel
- 文件名 = batch 名 (testbatch.xlsx / total.xlsx)
- 模型名去掉前 4 字符（DZA_xxx → xxx）
- 覆盖写入
"""

import os
import re
import pandas as pd


EXCEL_COUNTRIES = [
    "IRQ","DZA","ARE","EGY","MAR","SAU",
    "IDN","MYS","PHL","VNM","THA","JPN",
    "KOR","CHN","USA"
]

# ⭐results 在 data 里（已修正）
RESULTS_ROOT = (
    "/inspire/hdd/project/multilingualspeechrecognition/"
    "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results"
)

def extract_value(path):
    """
    解析 summary：
    第二行形如：
    DZA_stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo 66.16
    按空格切割，返回右侧的数值
    """
    try:
        with open(path, "r", encoding="utf8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]

        if len(lines) < 2:
            return "-"

        # 第二行
        parts = lines[1].split()
        if len(parts) < 2:
            return "-"

        val = parts[-1].replace("%", "")  # 去掉百分号
        return float(val)
    except:
        return "-"




def normalize_model_name(model: str):
    """
    把模型名去掉前 4 字符（国家前缀 + 下划线）
    例：DZA_chirp_3 → chirp_3
    """
    if len(model) > 4:
        return model[4:]
    return model


def scan_one_batch(batch_path):
    """扫描单个 batch → DataFrame"""
    table = {}

    for country in EXCEL_COUNTRIES:
        c_dir = os.path.join(batch_path, country)
        if not os.path.isdir(c_dir):
            continue

        for model in os.listdir(c_dir):
            m_dir = os.path.join(c_dir, model)
            if not os.path.isdir(m_dir):
                continue

            # 找 summary 文件
            files = [f for f in os.listdir(m_dir) if "summary" in f and f.endswith(".txt")]
            if not files:
                continue

            summary_file = os.path.join(m_dir, files[0])
            val = extract_value(summary_file)

            model_clean = normalize_model_name(model)

            if model_clean not in table:
                table[model_clean] = {}
            table[model_clean][country] = val

    df = pd.DataFrame.from_dict(table, orient="index")
    df = df.reindex(columns=EXCEL_COUNTRIES)
    df = df.fillna("-")
    return df


def main():
    print(f"📂 搜索 results 目录: {RESULTS_ROOT}")
    batches = sorted([
        d for d in os.listdir(RESULTS_ROOT)
        if os.path.isdir(os.path.join(RESULTS_ROOT, d))
    ])

    print("➡️ 发现 batches:", batches)

    for batch in batches:
        batch_path = os.path.join(RESULTS_ROOT, batch)
        print(f"\n💡 处理批次: {batch}")

        df = scan_one_batch(batch_path)

        # ⭐文件名必须是 batch 名，直接覆盖
        out_xlsx = os.path.join(batch_path, f"{batch}.xlsx")
        df.to_excel(out_xlsx)
        print(f"   ✔️ Excel 已覆盖写入 → {out_xlsx}")


if __name__ == "__main__":
    main()
