#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_ref_json.py

读取 ref/testbatch 下所有国家文件夹里的 json，
筛选出 status=="valid" 的片段，提取 audio_name/start/end/text，
自动去除所有标点符号。
生成到：
/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/ref/{country}.json
"""

import os
import json
import re
import string
from tqdm import tqdm

REF_ROOT = "/root/shared-nvme/yujietu/data/ASR-Bench/Multilingual-ASR-Benchmark/text/ref/testbatch"
OUT_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/ref"

os.makedirs(OUT_ROOT, exist_ok=True)

# ------------------ 标点清洗函数（与 hyp 完全一致） ------------------

PUNCT_REGEX = re.compile(
    rf"[{re.escape(string.punctuation)}]"         # 英文标点
    r"|[\u3000-\u303F]"                           # CJK 符号
    r"|[\u2000-\u206F]"                           # 常用符号
    r"|[\uFF00-\uFFEF]"                           # 全角标点
    r"|[\uFE30-\uFE4F]"                           # 全角 CJK
    r"|[\u2E00-\u2E7F]"                           # Supplemental punctuation
)

def remove_punctuation(text: str) -> str:
    if not text:
        return text
    return PUNCT_REGEX.sub("", text)


# ------------------ 处理单个国家目录 ------------------

def process_country(country_dir: str, country: str):
    all_results = []

    json_files = [
        os.path.join(country_dir, f)
        for f in os.listdir(country_dir)
        if f.endswith(".json")
    ]

    for jf in tqdm(json_files, desc=f"Processing {country}", ncols=100):
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] 读取失败: {jf} - {e}")
            continue

        audio_name = data.get("audio_name", "")

        for seg in data.get("segments", []):
            if seg.get("status") != "valid":
                continue

            text_clean = remove_punctuation(seg.get("text", "").strip())

            item = {
                "audio_name": audio_name,
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "text": text_clean
            }
            all_results.append(item)

    # 输出文件
    out_path = os.path.join(OUT_ROOT, f"{country}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"✔ 已生成：{out_path}  （共 {len(all_results)} 条 valid 片段）")


# ------------------ 主程序 ------------------

def main():
    countries = [
        d for d in os.listdir(REF_ROOT)
        if os.path.isdir(os.path.join(REF_ROOT, d))
    ]

    print(f"找到 {len(countries)} 个国家目录：{countries}")

    for country in countries:
        c_dir = os.path.join(REF_ROOT, country)
        process_country(c_dir, country)


if __name__ == "__main__":
    main()
