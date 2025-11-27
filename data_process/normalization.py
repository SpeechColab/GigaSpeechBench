#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from glob import glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from text_norm import get_normalizer
#LANGS = ["IRQ", "DZA", "ARE", "EGY", "MAR", "SAU", "IDN", "MYS", "PHL", "THA", "VNM", "JPN", "KOR","CHN","USA"]
LANGS = ["USA"]

REF_IN = "data/text/testbatch/ref"
HYP_IN = "data/text/testbatch/hyp"

REF_OUT = "data/text_normalized/testbatch/ref"
HYP_OUT = "data/text_normalized/testbatch/hyp"

os.makedirs(REF_OUT, exist_ok=True)
os.makedirs(HYP_OUT, exist_ok=True)


def load_json(path):
    print(f"[DEBUG] Loading JSON: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[DEBUG] Loaded {len(data)} items from {path}")
    return data


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"[DEBUG] Saving normalized JSON → {path} (items={len(data)})")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[DEBUG] Save OK: {path}")


def normalize_text(country, text):
    """调用对应语言的 normalize()"""
    try:
        normalize = get_normalizer(country)
    except Exception as e:
        print(f"[ERROR] Could not load normalizer for {country}: {e}")
        return None

    new_text = normalize(text)
    return new_text


def process_ref(country):
    infile = f"{REF_IN}/{country}.json"
    print(f"[DEBUG] REF infile = {infile}")

    if not os.path.exists(infile):
        print(f"[WARN] REF file not found: {infile}")
        return

    outfile = f"{REF_OUT}/{country}.json"
    print(f"[DEBUG] REF outfile = {outfile}")

    if os.path.exists(outfile):
        print(f"[REF SKIP] {outfile} already exists")
        return

    data = load_json(infile)
    normalized = []

    for idx, item in enumerate(data):

        new_text = normalize_text(country, item["text"])
        if new_text is None:
            continue   
        item["text"] = new_text
        normalized.append(item)

    save_json(outfile, normalized)
    print(f"[REF OK] Saved: {outfile}")


def process_hyp(country):
    pattern = f"{HYP_IN}/{country}/{country}_*.json"
    print(f"[DEBUG] HYP search pattern: {pattern}")

    files = glob(pattern)
    print(f"[DEBUG] Found {len(files)} hyp files for {country}")

    for file_path in files:
        base = os.path.basename(file_path)
        print(f"\n[DEBUG] Processing HYP file = {file_path}")

        # 解析模型名
        model_name = base.replace(f"{country}_", "").replace(".json", "")
        print(f"[DEBUG] Model name inferred = {model_name}")

        out_dir = f"{HYP_OUT}/{country}"
        os.makedirs(out_dir, exist_ok=True)

        outfile = f"{out_dir}/{base}"
        print(f"[DEBUG] HYP outfile = {outfile}")

        if os.path.exists(outfile):
            print(f"[HYP SKIP] {outfile} already exists")
            continue

        data = load_json(file_path)
        normalized = []

        for idx, item in enumerate(data):

            new_text = normalize_text(country, item["text"])
            if new_text is None:
                continue

            item["text"] = new_text
            normalized.append(item)

        save_json(outfile, normalized)
        print(f"[HYP OK] Saved: {outfile}")


def main():
    for country in LANGS:
        print(f"\n==============================")
        print(f"=== Processing {country} ===")
        print(f"==============================")

        # 检查 normalizer
        try:
            _ = get_normalizer(country)
            print(f"[DEBUG] Normalizer loaded for {country}")
        except Exception:
            print(f"[SKIP] No normalizer found for {country}")
            continue

        process_ref(country)
        process_hyp(country)


if __name__ == "__main__":
    main()
