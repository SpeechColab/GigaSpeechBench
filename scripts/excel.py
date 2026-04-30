#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Strict version:
- 白名单 model = 唯一合法 model 集合
- 非白名单 model 在整个 pipeline 中直接忽略
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
    "KOR","CHN","USA"
]

RESULTS_ROOT = (
    "/inspire/hdd/project/multilingualspeechrecognition/"
    "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results"
)

TEXT_NORM_ROOT = (
    "/inspire/hdd/project/multilingualspeechrecognition/"
    "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized"
)

# =========================
# 白名单（唯一合法 model）
# =========================

COVERAGE_MODELS = {
    "AZURE",
    "CHIRP_3",
    "DOLPHIN_BASE",
    "DOLPHIN_SMALL",
    "ELEVENLABS_SCRIBE_V2",
    "FUN-ASR-MLT-NANO",
    "FUN-ASR",
    "FUNASR_V1.5",
    "QWEN3.5-OMNI-FLASH",
    "GEMINI",
    "GPT4O-TRANSCRIBE",
    "OMNIASR_LLM_3B",
    "QWEN3-ASR-FLASH",
    "QWEN3-ASR-1.7B",
    "STT_AR_FASTCONFORMER_HYBRID_LARGE_PCD_V1.0.NEMO",
    "WHISPER",
    "STT_KR_CONFORMER_TRANSDUCER_LARGE",
    "PARAKEET-TDT_CTC-0.6B-JA",
    "NVIDIA-NEMO"
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
    """只在存在 XXX_ 前缀时裁掉"""
    if re.match(r"^[A-Z]{3}_", model):
        return model[4:]
    return model


def pick_err_file(m_dir: str):
    """优先 err*，否则 fallback 任意 .txt"""
    names = [
        n for n in os.listdir(m_dir)
        if os.path.isfile(os.path.join(m_dir, n))
    ]
    if not names:
        return None

    err = [n for n in names if n.lower().startswith("err")]
    if err:
        err_txt = [n for n in err if n.lower().endswith(".txt")]
        return os.path.join(m_dir, sorted(err_txt or err)[0])

    txts = sorted(n for n in names if n.lower().endswith(".txt"))
    return os.path.join(m_dir, txts[0]) if txts else None


# =========================
# WER / CER 扫描（强白名单）
# =========================

def scan_one_batch(batch_path: str):
    table = {}

    for country in EXCEL_COUNTRIES:
        c_dir = os.path.join(batch_path, country)
        if not os.path.isdir(c_dir):
            continue

        for model in os.listdir(c_dir):
            m_dir = os.path.join(c_dir, model)
            if not os.path.isdir(m_dir):
                continue

            model_clean = normalize_model_name(model)

            # ⛔ 非白名单，直接忽略
            if model_clean not in COVERAGE_MODELS:
                continue

            target = pick_err_file(m_dir)
            if not target:
                continue

            val = extract_value(target)
            table.setdefault(model_clean, {})[country] = val

    df = pd.DataFrame.from_dict(table, orient="index")
    df = df.reindex(columns=EXCEL_COUNTRIES)
    return df.fillna("-")


# =========================
# ref 统计（跨子目录累加）
# =========================

def load_ref_counts():
    ref_count = {}

    for root, _, files in os.walk(TEXT_NORM_ROOT):
        if os.path.basename(root) != "ref":
            continue

        for fn in files:
            if not fn.lower().endswith(".json"):
                continue

            country = fn[:-5]
            path = os.path.join(root, fn)

            try:
                with open(path, "r", encoding="utf8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    ref_count[country] = ref_count.get(country, 0) + len(data)
            except Exception:
                continue

    return ref_count


# =========================
# Coverage 读取（强白名单）
# =========================

def load_total_coverage(txt_path: str, ref_count: dict):
    rows = []
    coverage_ok = {}

    with open(txt_path, "r", encoding="utf8") as f:
        lines = [l.strip() for l in f if l.strip()]

    for line in lines[1:]:
        parts = re.split(r"\s+", line)
        if len(parts) < 6:
            continue

        country, model, valid, _, _, dur_h = parts[:6]
        model_clean = normalize_model_name(model)

        # ⛔ 非白名单，直接忽略
        if model_clean not in COVERAGE_MODELS:
            continue

        valid_i = int(valid)
        total_ref = ref_count.get(country, 0)
        ratio = valid_i / total_ref if total_ref > 0 else 0.0

        coverage_ok[(model_clean, country)] = ratio >= 0.9

        rows.append({
            "country": country,
            "model": model_clean,
            "valid": valid_i,
            "ref_total": total_ref,
            "ratio": ratio,
            "dur_h": float(dur_h),
        })

    return coverage_ok, pd.DataFrame(rows)


# =========================
# 主入口
# =========================

def main():
    print(f"📂 扫描 results 目录: {RESULTS_ROOT}")

    ref_count = load_ref_counts()

    batches = sorted(
        d for d in os.listdir(RESULTS_ROOT)
        if os.path.isdir(os.path.join(RESULTS_ROOT, d))
    )

    print("➡️ 发现 batches:", batches)

    for batch in batches:
        batch_path = os.path.join(RESULTS_ROOT, batch)
        print(f"\n💡 处理批次: {batch}")

        df = scan_one_batch(batch_path)

        if batch == "total":
            cov_txt = os.path.join(batch_path, "segment_coverage.txt")
            if os.path.exists(cov_txt):
                coverage_ok, cov_df = load_total_coverage(cov_txt, ref_count)

                for (model, country), ok in coverage_ok.items():
                    if (
                        not ok
                        and model in df.index
                        and country in df.columns
                    ):
                        df.loc[model, country] = "-"

                out_cov = os.path.join(batch_path, "total_coverage.xlsx")
                cov_df.to_excel(out_cov, index=False)
                print(f"   ✔️ Coverage Excel → {out_cov}")

        out_xlsx = os.path.join(batch_path, f"{batch}.xlsx")
        df.to_excel(out_xlsx)
        print(f"   ✔️ WER/CER Excel → {out_xlsx}")


if __name__ == "__main__":
    main()
