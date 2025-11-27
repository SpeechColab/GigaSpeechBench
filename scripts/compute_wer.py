#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
output files:
- recogs-COUNTRY-MODEL.txt
- errs-COUNTRY-MODEL.txt
- {wer|cer}-summary-COUNTRY-MODEL.txt
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import logging
import kaldialign

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

REF_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/testbatch/ref"
HYP_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/testbatch/hyp"
OUT_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/results/testbatch"

# -----------------------------
# 显式定义哪些语言用 WER，哪些用 CER
# -----------------------------
WER_LANGS = ["IRQ", "DZA", "ARE", "EGY", "MAR", "SAU", "IDN", "MYS", "PHL", "VNM","USA"]
CER_LANGS = ["JPN", "KOR", "THA","CHN"]


def store_transcripts(filename: Path, texts):
    with open(filename, "w", encoding="utf8") as f:
        for cut_id, ref, hyp in texts:
            print(f"{cut_id}:\tref={' '.join(ref)}", file=f)
            print(f"{cut_id}:\thyp={' '.join(hyp)}", file=f)


def write_error_stats(f, test_set_name, results, compute_CER=False):
    ERR = "*"
    subs = defaultdict(int)
    ins = defaultdict(int)
    dels = defaultdict(int)
    num_corr = 0

    # --- CER 模式：转为字符序列 ---
    if compute_CER:
        tmp = []
        for cut_id, ref_words, hyp_words in results:
            ref_chars = list("".join(ref_words))
            hyp_chars = list("".join(hyp_words))
            tmp.append((cut_id, ref_chars, hyp_chars))
        results = tmp

    # --- 对齐统计 ---
    for cut_id, ref, hyp in results:
        ali = kaldialign.align(ref, hyp, ERR)
        for ref_w, hyp_w in ali:
            if ref_w == ERR:
                ins[hyp_w] += 1
            elif hyp_w == ERR:
                dels[ref_w] += 1
            elif ref_w != hyp_w:
                subs[(ref_w, hyp_w)] += 1
            else:
                num_corr += 1

    ref_len = sum(len(r) for _, r, _ in results)
    sub_errs = sum(subs.values())
    ins_errs = sum(ins.values())
    del_errs = sum(dels.values())
    tot_errs = sub_errs + ins_errs + del_errs

    wer = 100.0 * tot_errs / ref_len if ref_len > 0 else 0.0

    print(f"%WER = {wer:.2f}", file=f)
    print(
        f"Errors: {ins_errs} insertions, {del_errs} deletions, "
        f"{sub_errs} substitutions, over {ref_len} units ({num_corr} correct)",
        file=f,
    )

    logging.info(f"[{test_set_name}] %WER {wer:.2f}")

    return wer


def evaluate_model(country: str, model: str, ref_items, hyp_items, compute_CER=False):

    out_dir = Path(OUT_ROOT) / country / model
    out_dir.mkdir(parents=True, exist_ok=True)

    hyp_index = {(item["audio_name"], float(item["start"])): item["text"] for item in hyp_items}

    results = []
    for ref in ref_items:
        key = (ref["audio_name"], float(ref["start"]))
        if key not in hyp_index:
            continue

        ref_text = ref["text"].strip()
        hyp_text = hyp_index[key].strip()
        cut_id = f"{ref['audio_name']}_{ref['start']}"

        ref_words = ref_text.split()
        hyp_words = hyp_text.split()

        results.append((cut_id, ref_words, hyp_words))

    metric_name = "cer" if compute_CER else "wer"

    recogs_path = out_dir / f"recogs-{country}-{model}.txt"
    errs_path = out_dir / f"errs-{country}-{model}.txt"
    summary_path = out_dir / f"{metric_name}-summary-{country}-{model}.txt"

    store_transcripts(recogs_path, results)
    logging.info(f"generate recogs: {recogs_path}")

    with open(errs_path, "w", encoding="utf8") as f:
        wer = write_error_stats(f, f"{country}-{model}", results, compute_CER)

    with open(summary_path, "w", encoding="utf8") as f:
        print(f"model\t{metric_name.upper()}", file=f)
        print(f"{model}\t{wer:.2f}", file=f)

    logging.info(f"generate summary: {summary_path}")

    return wer


def main():
    countries = [f[:-5] for f in os.listdir(REF_ROOT) if f.endswith(".json")]
    logging.info(f"Find countries:{countries}")

    for country in countries:
        ref_path = os.path.join(REF_ROOT, f"{country}.json")
        ref_items = json.load(open(ref_path, "r", encoding="utf-8"))

        hyp_country_dir = os.path.join(HYP_ROOT, country)
        if not os.path.exists(hyp_country_dir):
            logging.warning(f"{country} No hyp, skipped.")
            continue

        models = [
            f[:-5]  # 去掉最后 .json，不做任何 split
            for f in os.listdir(hyp_country_dir)
            if f.endswith(".json")
        ]

        logging.info(f"[{country}] model list: {models}")

        compute_CER = country in CER_LANGS

        for model in models:
            model_file = f"{model}.json"
            hyp_path = os.path.join(hyp_country_dir, model_file)

            hyp_items = json.load(open(hyp_path, "r", encoding="utf-8"))

            logging.info(f"Begin Evaluating {country}-{model}")
            evaluate_model(country, model, ref_items, hyp_items, compute_CER)


if __name__ == "__main__":
    main()
