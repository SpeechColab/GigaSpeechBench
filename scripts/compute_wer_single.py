#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Single-batch ASR 评测脚本（可传参）

- 支持命令行指定 REF/HYP/OUT 根目录
- 单 batch
- model 名来自 hyp item["model"]
- audio_name 去 .wav
- 输出 ref/hyp/matched 段数一致性检查
- 支持 WER/CER 自动判断
"""

import os
import json
import logging
from pathlib import Path
from collections import defaultdict
import kaldialign
import gc
import argparse

# =========================
# 日志
# =========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# =========================
# 常量
# =========================
WER_LANGS = ["IRQ","DZA","ARE","EGY","MAR","SAU","IDN","MYS","PHL","VNM","SYR","USA",
             "CHN-EN","IDN-EN","JPN-EN","PHL-EN","SCT-EN","SGP-EN","AGR-EN","AIT-EN",
             "ART-EN","BIO-EN","ECM-EN","EDU-EN","ENG-EN","ENT-EN","FIN-EN","HUM-EN",
             "LAW-EN","MED-EN","MIL-EN"]
CER_LANGS = ["JPN","JPN_hard","KOR","KOR_hard","THA","CHN","JIN","XIANG","YUE","WU",
             "MIN","AGR-CH","AIT-CH","ART-CH","BIO-CH","ECM-CH","EDU-CH","ENG-CH","ENT-CH",
             "FIN-CH","HUM-CH","LAW-CH","MED-CH","MIL-CH"]
ERR = "*"

# =========================
# 工具函数
# =========================
def norm_audio_name(name: str) -> str:
    name = name.replace("\\", "/")
    base = os.path.basename(name)
    for ext in [".wav", ".mp3", ".mp4"]:
        if base.lower().endswith(ext):
            base = base[:-len(ext)]
    return base

def process_one_ref_hyp(ref_items, hyp_items, compute_CER, recogs_f, stats):
    hyp_index = defaultdict(list)
    for h in hyp_items:
        name = norm_audio_name(h["audio_name"])
        start = float(h["start"])
        hyp_index[name].append((start, h["text"]))

    valid = 0
    dur_sec = 0.0
    for r in ref_items:
        name = norm_audio_name(r["audio_name"])
        start_ref = float(r["start"])

        if name not in hyp_index:
            continue

        hyp_val = None
        match_start = None
        for start_hyp, text in hyp_index[name]:
            if abs(start_ref - start_hyp) <= 0.1:
                hyp_val = text
                match_start = start_hyp
                break

        if hyp_val is None:
            continue
        hyp_index[name].remove((match_start, hyp_val))

        valid += 1
        dur_sec += float(r["end"]) - float(r["start"])

        ref_tok = r["text"].strip().split()
        hyp_tok = hyp_val.strip().split() if hyp_val else []

        if compute_CER:
            ref_tok = list("".join(ref_tok))
            hyp_tok = list("".join(hyp_tok))

        cut_id = f"{r['audio_name']}_{r['start']}"
        print(f"{cut_id}:\tref={' '.join(ref_tok)}", file=recogs_f)
        print(f"{cut_id}:\thyp={' '.join(hyp_tok)}", file=recogs_f)

        ali = kaldialign.align(ref_tok, hyp_tok, ERR)
        for a, b in ali:
            if a == ERR:
                stats["I"] += 1
            elif b == ERR:
                stats["D"] += 1
                stats["N"] += 1
            elif a != b:
                stats["S"] += 1
                stats["N"] += 1
            else:
                stats["C"] += 1
                stats["N"] += 1
    return valid, dur_sec / 3600.0

def write_errs_and_summary(out_dir, country, model, stats, compute_CER):
    N = stats["N"]
    err = stats["S"] + stats["D"] + stats["I"]
    wer = 100.0 * err / N if N > 0 else 0.0
    with open(out_dir / f"errs-{country}-{model}.txt", "w", encoding="utf8") as f:
        print(f"%WER = {wer:.2f}", file=f)
        print(f"Errors: {stats['I']} insertions, {stats['D']} deletions, {stats['S']} substitutions, over {N} units ({stats['C']} correct)", file=f)
    metric = "cer" if compute_CER else "wer"
    with open(out_dir / f"{metric}-summary-{country}-{model}.txt", "w", encoding="utf8") as f:
        print("model\tWER/CER", file=f)
        print(f"{model}\t{wer:.2f}", file=f)

# =========================
# 主入口（单 batch，可传参）
# =========================
def main(REF_ROOT, HYP_ROOT, OUT_ROOT):
    logging.info("====== Single Batch Evaluation ======")
    # 🔹 打印目录路径
    print(f"🔹 REF 根目录: {REF_ROOT}")
    print(f"🔹 HYP 根目录: {HYP_ROOT}")

    for fn in os.listdir(REF_ROOT):
        if not fn.endswith(".json"):
            continue
        country = fn[:-5]
        compute_CER = country in CER_LANGS
        with open(os.path.join(REF_ROOT, fn), "r", encoding="utf8") as f:
            ref_items = json.load(f)

        hyp_country_dir = os.path.join(HYP_ROOT, country)
        if not os.path.isdir(hyp_country_dir):
            continue

        hyp_by_model = defaultdict(list)
        for hfn in os.listdir(hyp_country_dir):
            if not hfn.endswith(".json"):
                continue
            with open(os.path.join(hyp_country_dir, hfn), "r", encoding="utf8") as f:
                items = json.load(f)
            for it in items:
                model = it.get("model", "UNKNOWN").upper()
                hyp_by_model[model].append(it)

        for model, hyp_items in hyp_by_model.items():
            stats = defaultdict(int)
            out_dir = Path(OUT_ROOT) / country / model
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_dir / f"recogs-{country}-{model}.txt", "w", encoding="utf8") as rec_f:
                valid, dur_h = process_one_ref_hyp(ref_items, hyp_items, compute_CER, rec_f, stats)
            write_errs_and_summary(out_dir, country, model, stats, compute_CER)

            ref_n = len(ref_items)
            hyp_n = len(hyp_items)
            with open(out_dir / "segment_check.txt", "w", encoding="utf8") as f:
                f.write(f"ref_segments={ref_n}\n")
                f.write(f"hyp_segments={hyp_n}\n")
                f.write(f"matched_segments={valid}\n")
            logging.info(f"[CHECK] {country}/{model}: ref={ref_n} hyp={hyp_n} matched={valid}")
        del ref_items
        gc.collect()
    logging.info("✅ 单 batch 评测完成")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Single-batch ASR evaluation")
    parser.add_argument("--ref_root", type=str, required=True)
    parser.add_argument("--hyp_root", type=str, required=True)
    parser.add_argument("--out_root", type=str, required=True)
    args = parser.parse_args()
    main(REF_ROOT=args.ref_root, HYP_ROOT=args.hyp_root, OUT_ROOT=args.out_root)