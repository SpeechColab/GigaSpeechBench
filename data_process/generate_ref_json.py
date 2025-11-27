#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import re
import string
from tqdm import tqdm

REF_ROOT = "/root/shared-nvme/yujietu/data/ASR-Bench/Multilingual-ASR-Benchmark/text/ref/testbatch"
OUT_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/ref"
os.makedirs(OUT_ROOT, exist_ok=True)


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
        except:
            continue

        audio_name = data.get("audio_name", "")

        for seg in data.get("segments", []):
            if seg.get("status") == "invalid":
                continue

            item = {
                "audio_name": audio_name,
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "text": clean_text(seg.get("text", ""))
            }
            all_results.append(item)

    out_path = os.path.join(OUT_ROOT, f"{country}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"Generated: {out_path}, {len(all_results)} items")

def main():
    countries = [
        d for d in os.listdir(REF_ROOT)
        if os.path.isdir(os.path.join(REF_ROOT, d))
    ]
    for country in countries:
        c_dir = os.path.join(REF_ROOT, country)
        process_country(c_dir, country)

if __name__ == "__main__":
    main()
