#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import string
from tqdm import tqdm

HYP_ROOT = "/root/shared-nvme/yujietu/data/ASR-Bench/Multilingual-ASR-Benchmark/text/hyp/testbatch"
REF_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/ref"
OUT_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/hyp"

os.makedirs(OUT_ROOT, exist_ok=True)

normalize_numbers = True

PUNCT_REGEX = re.compile(
    rf"[{re.escape(string.punctuation)}]"
    r"|[\u3000-\u303F]"
    r"|[\u2000-\u206F]"
    r"|[\uFF00-\uFFEF]"
    r"|[\uFE30-\uFE4F]"
    r"|[\u2E00-\u2E7F]"
)

num_map = {
    "0":"zero","1":"one","2":"two","3":"three","4":"four","5":"five","6":"six","7":"seven","8":"eight","9":"nine",
    "一":"one","二":"two","三":"three","四":"four","五":"five","六":"six","七":"seven","八":"eight","九":"nine","十":"ten"
}

def remove_punctuation(text: str) -> str:
    return PUNCT_REGEX.sub("", text)

def normalize_num(text: str) -> str:
    if not normalize_numbers:
        return text
    return "".join(num_map.get(ch, ch) for ch in text)

def clean_text(t: str) -> str:
    t = t.strip()
    t = remove_punctuation(t)
    t = normalize_num(t)
    return t

def load_ref(country: str):
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

def process_file(json_path: str):
    filename = os.path.basename(json_path)
    country = filename[:3]

    ref_path, ref_index = load_ref(country)
    if ref_path is None:
        return

    out_country_dir = os.path.join(OUT_ROOT, country)
    os.makedirs(out_country_dir, exist_ok=True)
    out_path = os.path.join(out_country_dir, filename)

    old_items, existed_keys = load_existing_hyp(out_path)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            hyp_items = json.load(f)
    except:
        return

    new_items = []
    matched = 0
    empty_text = 0

    for item in hyp_items:
        path = item.get("path", "").replace("\\", "/")
        base = os.path.basename(path)

        if base.lower().endswith(".wav"):
            audio_name = base[:-4]
        else:
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

def main():
    files = [
        os.path.join(HYP_ROOT, f)
        for f in os.listdir(HYP_ROOT)
        if f.endswith(".json")
    ]
    for jf in tqdm(files, ncols=100):
        process_file(jf)

if __name__ == "__main__":
    main()
