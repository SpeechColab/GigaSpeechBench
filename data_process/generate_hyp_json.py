#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import string
from tqdm import tqdm

# ============================
# 原始 batch 设置（完全不动）
# ============================

BATCHES = [
    "testbatch",
    "20251212",
    "20251205",
]

# 根路径（原样）
ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text"

# hyp 输入根路径（原样）
HYP_ROOT_PREFIX = (
    "/inspire/hdd/project/multilingualspeechrecognition/"
    "chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/text/hyp"
)

# ============================
# 文本清洗（原样）
# ============================

PUNCT_REGEX = re.compile(
    rf"[{re.escape(string.punctuation)}]"
    r"|[\u3000-\u303F]"
    r"|[\u2000-\u206F]"
    r"|[\uFF00-\uFFEF]"
    r"|[\uFE30-\uFE4F]"
    r"|[\u2E00-\u2E7F]"
)

def remove_punctuation(text: str) -> str:
    return PUNCT_REGEX.sub("", text)

def clean_text(t: str) -> str:
    t = t.strip()
    t = remove_punctuation(t)
    return t


# ============================
# REF 读取（原样）
# ============================

def load_ref(country: str, REF_ROOT: str):
    p = os.path.join(REF_ROOT, f"{country}.json")
    if not os.path.exists(p):
        return None, {}
    with open(p, "r", encoding="utf-8") as f:
        items = json.load(f)
    ref_index = {(d["audio_name"], float(d["start"])): True for d in items}
    return p, ref_index


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


# =====================================================
# 🔥 audio_name 计算（逐字逐句复刻你原来的）
# =====================================================

def extract_audio_name(item):
    # 尝试获取音频名称，优先使用 audio_name 字段
    audio_name = item.get("audio_name")
    if audio_name:
        return audio_name
    
    # 如果没有 audio_name，则使用 path 或 audio_path 字段
    raw_path = item.get("path") or item.get("audio_path") or ""
    raw_path = raw_path.replace("\\", "/")
    base = os.path.basename(raw_path)

    # 如果文件名是 .wav 格式，去掉后缀
    if base.lower().endswith(".wav"):
        return base[:-4]
    else:
        return None


# =====================================================
# 单文件处理（原逻辑，未改）
# =====================================================

def process_file(json_path: str, REF_ROOT: str, OUT_ROOT: str):

    filename = os.path.basename(json_path)
    country = filename[:3]

    ref_path, ref_index = load_ref(country, REF_ROOT)
    if ref_path is None:
        return False

    out_country_dir = os.path.join(OUT_ROOT, country)
    os.makedirs(out_country_dir, exist_ok=True)

    out_path = os.path.join(out_country_dir, filename)
    old_items, existed_keys = load_existing_hyp(out_path)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            hyp_items = json.load(f)
    except:
        return False

    new_items = []
    matched = 0
    empty_text = 0

    for item in hyp_items:

        audio_name = extract_audio_name(item)
        if audio_name is None:
            continue

        start = float(item.get("start_time", 0.0))
        end = float(item.get("end_time", 0.0))
        text = clean_text(item.get("text", ""))
        model = item.get("model", "")

        key = (audio_name, start)

        if key not in ref_index:
            continue

        if key in existed_keys:
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

    all_items = old_items + new_items

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"{country} {filename} added {matched}, empty {empty_text}, total {len(all_items)}")
    return matched > 0


# =====================================================
# ✅ 原始离线主程序（完全不动）
# =====================================================

def main():
    for batch in BATCHES:
        print(f"\n===== 批次开始：{batch} =====")

        REF_ROOT = f"{ROOT}/{batch}/ref"
        OUT_ROOT = f"{ROOT}/{batch}/hyp"

        os.makedirs(OUT_ROOT, exist_ok=True)

        HYP_ROOT = f"{HYP_ROOT_PREFIX}/{batch}"

        if not os.path.exists(HYP_ROOT):
            print(f"[{batch}] hyp不存在，跳过")
            continue

        files = [
            os.path.join(HYP_ROOT, f)
            for f in os.listdir(HYP_ROOT)
            if f.endswith(".json")
        ]

        modified = []

        for jf in tqdm(files, ncols=100):
            if process_file(jf, REF_ROOT, OUT_ROOT):
                modified.append(os.path.basename(jf))

        print("\n=== Modified files in batch ===")
        if modified:
            for name in modified:
                print(name)
        else:
            print("No file modified.")

        print(f"===== 批次结束：{batch} =====")


# =====================================================
# 🆕 Online / Gradio 专用（只处理 gradio_batch）
# =====================================================

def run_gradio(
    hyp_json_path: str,
    country: str,
    ref_roots: list,
    out_root: str
):
    """
    hyp_json_path:
        上传的 hyp json（原始，带 path / start_time）

    ref_roots:
        [
          data/text/testbatch/ref,
          data/text/20251212/ref,
          data/text/20251205/ref
        ]

    out_root:
        temp_root/text/gradio_batch/hyp
    """

    # 合并三个 batch 的 ref_index（和你脑子里的一样）
    ref_index = {}

    for REF_ROOT in ref_roots:
        _, idx = load_ref(country, REF_ROOT)
        ref_index.update(idx)

    out_country_dir = os.path.join(out_root, country)
    os.makedirs(out_country_dir, exist_ok=True)

    filename = os.path.basename(hyp_json_path)
    out_path = os.path.join(out_country_dir, filename)

    with open(hyp_json_path, "r", encoding="utf-8") as f:
        hyp_items = json.load(f)

    new_items = []

    for item in hyp_items:

        audio_name = extract_audio_name(item)
        if audio_name is None:
            continue

        start = float(item.get("start_time", 0.0))
        end = float(item.get("end_time", 0.0))
        text = clean_text(item.get("text", ""))
        model = item.get("model", "")

        key = (audio_name, start)
        if key not in ref_index:
            continue

        new_items.append({
            "audio_name": audio_name,
            "start": start,
            "end": end,
            "text": text,
            "model": model
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(new_items, f, ensure_ascii=False, indent=2)

    print(f"[GRADIO] wrote {len(new_items)} items to {out_path}")


# =====================================================
if __name__ == "__main__":
    main()
