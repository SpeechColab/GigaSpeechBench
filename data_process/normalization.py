#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from glob import glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from text_norm import get_normalizer

LANGS = ["IRQ", "DZA", "ARE", "EGY", "MAR", "SAU", "IDN", "MYS", "PHL", "THA", "VNM", "JPN", "KOR"]
#LANGS = ["IRQ"]

REF_IN = "data/text/testbatch/ref"
HYP_IN = "data/text/testbatch/hyp"

REF_OUT = "data/text_normalized/testbatch/ref"
HYP_OUT = "data/text_normalized/testbatch/hyp"

os.makedirs(REF_OUT, exist_ok=True)
os.makedirs(HYP_OUT, exist_ok=True)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_text(country, text):
    """调用对应语言的 normalize 函数"""
    try:
        normalize = get_normalizer(country)
    except Exception:
        return None  
    return normalize(text)


def process_ref(country):
    infile = f"{REF_IN}/{country}.json"
    if not os.path.exists(infile):
        return

    outfile = f"{REF_OUT}/{country}.json"
    if os.path.exists(outfile):
        print(f"[REF SKIP] {outfile} already exists")
        return

    normalized = []
    for item in load_json(infile):
        new_text = normalize_text(country, item["text"])
        if new_text is None:
            return
        item["text"] = new_text
        normalized.append(item)

    save_json(outfile, normalized)
    print(f"[REF OK] {outfile}")


def process_hyp(country):
    pattern = f"{HYP_IN}/{country}/{country}_*.json"
    files = glob(pattern)

    for file_path in files:
        base = os.path.basename(file_path) 
        model_name = base.replace(f"{country}_", "").replace(".json", "")

        out_dir = f"{HYP_OUT}/{country}"
        os.makedirs(out_dir, exist_ok=True)
        outfile = f"{out_dir}/{base}"

        if os.path.exists(outfile):
            print(f"[HYP SKIP] {outfile} already exists")
            continue

        normalized = []
        for item in load_json(file_path):
            new_text = normalize_text(country, item["text"])
            if new_text is None:
                return
            item["text"] = new_text
            normalized.append(item)

        save_json(outfile, normalized)
        print(f"[HYP OK] {outfile}")


def main():
    for country in LANGS:
        print(f"\n=== Processing {country} ===")

        # 没 normalizer → 整个语言直接跳过
        try:
            _ = get_normalizer(country)
        except Exception:
            print(f"[SKIP] No normalizer for {country}")
            continue

        process_ref(country)
        process_hyp(country)


if __name__ == "__main__":
    main()
