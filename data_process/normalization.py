#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
from glob import glob
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from text_norm import get_normalizer

LANGS = ["IRQ","DZA","ARE","EGY","MAR","SAU",
         "IDN","MYS","PHL","THA","VNM",
         "JPN","KOR","CHN","USA"]

BATCHES = ["testbatch","20251212","20251205"]

REMOVE_TAGS = [
    r"\[breath\]",
    r"\[chocking\]",
    r"\[humph\]",
    r"\[sigh\]",
    r"\[laugh\]",
    r"\[cough\]",
    r"\[hissing\]",
    r"\[Throat clear\]",
]
REMOVE_TAGS_RE = re.compile("|".join(REMOVE_TAGS), flags=re.IGNORECASE)

def pre_clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.split("#")[0]
    text = REMOVE_TAGS_RE.sub("",text)
    return text.strip()

def load_json(path):
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def save_json(path,data):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def normalize_text(country,text):
    normalize = get_normalizer(country)
    return normalize(text)

def process_country(args):
    country,REF_IN,HYP_IN,REF_OUT,HYP_OUT = args

    # REF normalize
    ref_path = f"{REF_IN}/{country}.json"
    if os.path.exists(ref_path):
        ref_items = load_json(ref_path)
        new_ref=[]
        for item in ref_items:
            raw=pre_clean_text(item["text"])
            if not raw:
                continue
            text=normalize_text(country,raw)
            if text:
                item["text"]=text
                new_ref.append(item)
        save_json(f"{REF_OUT}/{country}.json",new_ref)

    # HYP normalize
    hyp_files = sorted(glob(f"{HYP_IN}/{country}/{country}_*.json"))
    for p in hyp_files:
        items=load_json(p)
        new_items=[]
        for item in items:
            raw=pre_clean_text(item["text"])
            if not raw:
                continue
            text=normalize_text(country,raw)
            if text:
                item["text"]=text
                new_items.append(item)

        out_dir=f"{HYP_OUT}/{country}"
        os.makedirs(out_dir,exist_ok=True)
        save_json(f"{out_dir}/{os.path.basename(p)}",new_items)

    return country   # 用于 tqdm 计数


def run_batch(batch):

    REF_IN  = f"data/text/{batch}/ref"
    HYP_IN  = f"data/text/{batch}/hyp"

    REF_OUT = f"data/text_normalized/{batch}/ref"
    HYP_OUT = f"data/text_normalized/{batch}/hyp"

    os.makedirs(REF_OUT, exist_ok=True)
    os.makedirs(HYP_OUT, exist_ok=True)

    with Pool(cpu_count()) as pool:
        tasks=[
            (c,REF_IN,HYP_IN,REF_OUT,HYP_OUT)
            for c in LANGS
        ]

        for _ in tqdm(pool.imap_unordered(process_country,tasks),
                      total=len(tasks),
                      desc=f"batch {batch}"):
            pass


def main():
    for batch in BATCHES:
        run_batch(batch)

if __name__ == "__main__":
    main()
