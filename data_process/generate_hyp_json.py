#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_hyp_json_incremental.py

增强功能：
- text 为空也会写入
- 增量写入：同一国家/模型，重复的 (audio_name, start_time) 不会重复写入
- 适配 Windows 路径：替换反斜杠，basename 正确提取
- 移除所有中英标点、全角符号
"""

import os
import json
import re
import string
from tqdm import tqdm

HYP_ROOT = "/root/shared-nvme/yujietu/data/ASR-Bench/Multilingual-ASR-Benchmark/text/hyp/testbatch"
REF_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/ref"
OUT_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/hyp"

os.makedirs(OUT_ROOT, exist_ok=True)

# ----------- 标点符号过滤 -------------------

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


# ---------------------------------------------------
# 加载 ref 索引
# ---------------------------------------------------
def load_ref(country: str):
    ref_path = os.path.join(REF_ROOT, f"{country}.json")
    if not os.path.exists(ref_path):
        return None, {}

    with open(ref_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    ref_index = {(d["audio_name"], float(d["start"])): True for d in items}
    return ref_path, ref_index


# ---------------------------------------------------
# 加载已有 hyp（增量避免重复）
# ---------------------------------------------------
def load_existing_hyp(out_path: str):
    if not os.path.exists(out_path):
        return [], set()

    try:
        with open(out_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except:
        return [], set()

    existed = {(d["audio_name"], float(d["start"])) for d in items}
    return items, existed


# ---------------------------------------------------
# 处理单个 hyp 文件
# ---------------------------------------------------
def process_file(json_path: str):
    filename = os.path.basename(json_path)
    country = filename[:3]

    # 加载 ref
    ref_path, ref_index = load_ref(country)
    if ref_path is None:
        print(f"[WARN] 无 ref 匹配: {country} (跳过 {filename})")
        return

    # 输出目录
    out_country_dir = os.path.join(OUT_ROOT, country)
    os.makedirs(out_country_dir, exist_ok=True)
    out_path = os.path.join(out_country_dir, filename)

    # 载入旧数据（增量模式）
    old_items, existed_keys = load_existing_hyp(out_path)

    # 读取 hyp
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            hyp_items = json.load(f)
    except Exception as e:
        print(f"[ERROR] 文件读取失败 {filename}: {e}")
        return

    new_items = []
    matched = 0
    empty_text = 0
    skipped_existing = 0
    skipped_no_ref = 0

    for item in hyp_items:
        path = item.get("path", "").replace("\\", "/")
        base = os.path.basename(path)

        # 提取 audio_name
        if base.lower().endswith(".wav"):
            audio_name = base[:-4]
        else:
            continue

        start = float(item.get("start_time", 0.0))
        end = float(item.get("end_time", 0.0))
        text = item.get("text", "").strip()
        text = remove_punctuation(text)   # <<< 新增标点清洗
        model = item.get("model", "")

        key = (audio_name, start)
        if key not in ref_index:
            skipped_no_ref += 1
            continue

        if key in existed_keys:
            skipped_existing += 1
            continue

        matched += 1
        if text == "":
            empty_text += 1

        new_items.append({
            "audio_name": audio_name,
            "start": start,
            "end": end,
            "text": text,
            "model": model
        })

    # 写回（旧 + 新）
    all_items = old_items + new_items
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"\n✔ 国家 {country} / 文件 {filename}")
    print(f"  新增写入: {matched}")
    print(f"  text 为空: {empty_text}")
    print(f"  跳过(已存在): {skipped_existing}")
    print(f"  跳过(未匹配 ref): {skipped_no_ref}")
    print(f"  最终总量: {len(all_items)}")
    print(f"  输出到: {out_path}\n")


# ---------------------------------------------------
# 主程序
# ---------------------------------------------------
def main():
    all_files = [
        os.path.join(HYP_ROOT, f)
        for f in os.listdir(HYP_ROOT)
        if f.endswith(".json")
    ]

    print(f"共发现 {len(all_files)} 个 hyp 文件")

    for jf in tqdm(all_files, ncols=100):
        process_file(jf)


if __name__ == "__main__":
    main()
