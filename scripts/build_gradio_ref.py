#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================
📌 ASR-Bench 增量汇总脚本（国家/Batch/汇总.json 模式）
================================================

功能：
- 输入：OLD_REF_ROOT/<country>/*.json (多个小文件)
- 输出：OUT_ROOT/<country>/batch_1/<country>.json (单个汇总大文件)
- 增量模式：仅处理新增段，避免重复
- 字段：保留 text, text_normalized, age_group, gender, emotion, speaker, english
"""

import os
import sys
import json
import time
import re
import traceback
from tqdm import tqdm

# =====================================================
# 1. 路径与配置
# =====================================================
OLD_REF_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/Low-Resource-Languages/text/ref"
OUT_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/ASRBench_gradio/Low-Resource-Languages/text/ref"

DEFAULT_BATCH_NAME = "ALL"

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
try:
    from text_norm import get_normalizer
except ImportError:
    print("[ERROR] 无法导入 text_norm，请检查 sys.path。")
    sys.exit(1)

# =====================================================
# 2. 国家映射表
# =====================================================
COUNTRY_TO_TEXTNORM = {
    "USA": "USA", "DZA": "DZA", "EGY": "EGY", "CHN": "CHN", "ARE": "ARE",
    "JPN": "JPN", "KOR": "KOR", "IDN": "IDN", "IRQ": "IRQ", "MAR": "MAR",
    "MYS": "MYS", "PHL": "PHL", "SAU": "SAU", "THA": "THA", "VNM": "VNM",
    "CHN-EN": "USA", "IDN-EN": "USA", "JIN": "CHN", "JPN-EN": "USA",
    "PHL-EN": "USA", "SCT-EN": "USA", "SGP-EN": "USA", "XIANG": "CHN",
    "SYR": "ARE", "WU": "CHN", "MIN": "CHN", "YUE": "CHN",
    "AGR-CH": "CHN", "AGR-EN": "USA", "AIT-CH": "CHN", "AIT-EN": "USA",
    "ART-CH": "CHN", "ART-EN": "USA", "BIO-CH": "CHN", "BIO-EN": "USA",
    "ECM-CH": "CHN", "ECM-EN": "USA", "EDU-CH": "CHN", "EDU-EN": "USA",
    "ENG-CH": "CHN", "ENG-EN": "USA", "ENT-CH": "CHN", "ENT-EN": "USA",
    "FIN-CH": "CHN", "FIN-EN": "USA", "HUM-CH": "CHN", "HUM-EN": "USA",
    "LAW-CH": "CHN", "LAW-EN": "USA", "MED-CH": "CHN", "MED-EN": "USA",
    "MIL-CH": "CHN", "MIL-EN": "USA", "JPN_hard":"JPN","KOR_hard":"KOR"
}

AUDIO_SUFFIX_REGEX = re.compile(r"(\.(wav|mp3|flac|ogg|m4a|aac|webm|mp4))+$", flags=re.IGNORECASE)

# =====================================================
# 3. 工具函数
# =====================================================
def extract_audio_name(item):
    audio_name = item.get("audio_name")
    if audio_name:
        return AUDIO_SUFFIX_REGEX.sub("", os.path.basename(audio_name.replace("\\", "/")))
    raw = item.get("path") or item.get("audio_path") or ""
    return AUDIO_SUFFIX_REGEX.sub("", os.path.basename(raw.replace("\\", "/")))

# =====================================================
# 4. 增量处理函数
# =====================================================
def process_country_incremental(country: str):
    """增量汇总国家 JSON"""
    try:
        country_src_dir = os.path.join(OLD_REF_ROOT, country)
        dst_dir = os.path.join(OUT_ROOT, country, DEFAULT_BATCH_NAME)
        os.makedirs(dst_dir, exist_ok=True)
        out_path = os.path.join(dst_dir, f"{country}.json")

        norm_key = COUNTRY_TO_TEXTNORM.get(country)
        if not norm_key:
            return f"⚠️ {country}: 映射表缺失"

        normalizer = get_normalizer(norm_key)

        # 读取已有汇总
        if os.path.exists(out_path):
            with open(out_path, "r", encoding="utf-8") as f:
                existing_segments = json.load(f)
        else:
            existing_segments = []

        existing_keys = set((seg["audio_name"], seg["start"], seg["end"]) for seg in existing_segments)

        new_segments = []
        json_files = [f for f in os.listdir(country_src_dir) if f.endswith(".json")]
        for jf_name in json_files:
            jf_path = os.path.join(country_src_dir, jf_name)
            with open(jf_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            audio_name = extract_audio_name(data)

            for seg in data.get("segments", []):
                if seg.get("status") == "invalid":
                    continue

                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", 0.0))
                key = (audio_name, start, end)
                if key in existing_keys:
                    continue  # 已存在，跳过

                raw_text = seg.get("text", "").strip()
                try:
                    norm_text = normalizer(raw_text)
                except:
                    norm_text = raw_text

                new_segments.append({
                    "audio_name": audio_name,
                    "start": start,
                    "end": end,
                    "text": raw_text,
                    "text_normalized": norm_text,
                    "age_group": seg.get("age_group", "unknown"),
                    "gender": seg.get("gender", "unknown"),
                    "emotion": seg.get("emotion", "unknown"),
                    "speaker": seg.get("speaker", "unknown"),
                    "english": seg.get("english", "unknown")
                })

        all_results = existing_segments + new_segments

        # 写回文件（覆盖原文件，但只新增）
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        return f"✅ {country}: 增量完成 ({len(new_segments)} 新段, 总计 {len(all_results)}) -> {out_path}"

    except Exception:
        return f"❌ {country} 失败: {traceback.format_exc()}"

# =====================================================
# 5. 主程序
# =====================================================
def main():
    countries = sorted([
        d for d in os.listdir(OLD_REF_ROOT)
        if os.path.isdir(os.path.join(OLD_REF_ROOT, d))
    ])

    print(f"🚀 开始增量汇总模式处理...")
    print(f"📂 目标结构: {OUT_ROOT}/<国家>/{DEFAULT_BATCH_NAME}/<国家>.json")

    t0 = time.time()
    for country in tqdm(countries, desc="Processing Countries"):
        r = process_country_incremental(country)
        if "❌" in r or "⚠️" in r:
            print(r)
    print(f"\n✨ 全部处理结束！耗时: {time.time() - t0:.2f}s")

if __name__ == "__main__":
    main()