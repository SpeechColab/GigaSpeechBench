#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
evaluate_asr_bench.py

自动从 ref/hyp 加载所有国家、模型，对每个组合计算 WER，
输出到结果目录：
/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/results/testbatch/{country}/{model}/

生成三个文件：
- recogs-COUNTRY-MODEL.txt
- errs-COUNTRY-MODEL.txt
- wer-summary-COUNTRY-MODEL.txt
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import logging
import kaldialign

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

REF_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/ref"
HYP_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/text/testbatch/hyp"
OUT_ROOT = "/root/shared-nvme/yujietu/Multilingual-ASR-Benchmark/data/results/testbatch"


def store_transcripts(filename: Path, texts):
    with open(filename, "w", encoding="utf8") as f:
        for cut_id, ref, hyp in texts:
            print(f"{cut_id}:\tref={' '.join(ref)}", file=f)
            print(f"{cut_id}:\thyp={' '.join(hyp)}", file=f)


def write_error_stats(f, test_set_name, results):
    subs = defaultdict(int)
    ins = defaultdict(int)
    dels = defaultdict(int)
    words = defaultdict(lambda: [0, 0, 0, 0, 0])
    ERR = "*"

    num_corr = 0

    for cut_id, ref, hyp in results:
        ali = kaldialign.align(ref, hyp, ERR)
        for ref_word, hyp_word in ali:
            if ref_word == ERR:
                ins[hyp_word] += 1
            elif hyp_word == ERR:
                dels[ref_word] += 1
            elif hyp_word != ref_word:
                subs[(ref_word, hyp_word)] += 1
            else:
                num_corr += 1

    ref_len = sum(len(r) for _, r, _ in results)
    sub_errs = sum(subs.values())
    ins_errs = sum(ins.values())
    del_errs = sum(dels.values())

    tot_errs = sub_errs + ins_errs + del_errs
    wer = 100.0 * tot_errs / ref_len if ref_len > 0 else 0.0

    print(f"%WER = {wer:.2f}", file=f)
    print(f"Errors: {ins_errs} insertions, {del_errs} deletions, "
          f"{sub_errs} substitutions, over {ref_len} words ({num_corr} correct)", file=f)

    logging.info(f"[{test_set_name}] %WER {wer:.2f}")

    return wer


def evaluate_model(country: str, model: str, ref_items, hyp_items):

    out_dir = Path(OUT_ROOT) / country / model
    out_dir.mkdir(parents=True, exist_ok=True)

    hyp_index = {
        (item["audio_name"], float(item["start"])): item["text"]
        for item in hyp_items
    }

    results = []

    for ref in ref_items:
        key = (ref["audio_name"], float(ref["start"]))
        if key not in hyp_index:
            continue

        ref_text = ref["text"].strip()
        hyp_text = hyp_index[key].strip()

        ref_words = ref_text.split()
        hyp_words = hyp_text.split()

        cut_id = f"{ref['audio_name']}_{ref['start']}"

        results.append((cut_id, ref_words, hyp_words))

    recogs_path = out_dir / f"recogs-{country}-{model}.txt"
    errs_path = out_dir / f"errs-{country}-{model}.txt"
    summary_path = out_dir / f"wer-summary-{country}-{model}.txt"

    store_transcripts(recogs_path, results)
    logging.info(f"生成 recogs: {recogs_path}")

    with open(errs_path, "w", encoding="utf8") as f:
        wer = write_error_stats(f, f"{country}-{model}", results)
    logging.info(f"生成 errs: {errs_path}")

    with open(summary_path, "w", encoding="utf8") as f:
        print("model\tWER", file=f)
        print(f"{model}\t{wer:.2f}", file=f)
    logging.info(f"生成 summary: {summary_path}")

    return wer


def main():
    countries = [f[:-5] for f in os.listdir(REF_ROOT) if f.endswith(".json")]
    logging.info(f"发现国家：{countries}")

    for country in countries:
        ref_path = os.path.join(REF_ROOT, f"{country}.json")
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_items = json.load(f)

        hyp_country_dir = os.path.join(HYP_ROOT, country)
        if not os.path.exists(hyp_country_dir):
            logging.warning(f"{country} 没有 hyp，跳过")
            continue

        models = [f[:-5] for f in os.listdir(hyp_country_dir) if f.endswith(".json")]
        logging.info(f"[{country}] 模型列表：{models}")

        for model_file in models:
            model = model_file.split(".", 1)[0]
            hyp_path = os.path.join(hyp_country_dir, f"{model_file}.json") \
                if not model_file.endswith(".json") else os.path.join(hyp_country_dir, model_file)

            with open(hyp_path, "r", encoding="utf-8") as f:
                hyp_items = json.load(f)

            logging.info(f"开始评估 {country}-{model}")
            evaluate_model(country, model, ref_items, hyp_items)


if __name__ == "__main__":
    main()
