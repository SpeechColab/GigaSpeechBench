#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从多个 batch 读取 ref/hyp，
- 每个 batch 各自算一套 WER/CER，输出到 results/{batch}/
- 再把所有 batch 合在一起算一套 total，输出到 results/total/
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import logging
import kaldialign

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

WER_LANGS = ["IRQ", "DZA", "ARE", "EGY", "MAR", "SAU",
             "IDN", "MYS", "PHL", "VNM", "USA"]
CER_LANGS = ["JPN", "KOR", "THA", "CHN"]


def store_transcripts(filename: Path, texts):
    """保存 recogs 文件（cut_id + ref/hyp）"""
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

    # 如果是 CER，则把 token 换成 char 级别
    if compute_CER:
        tmp = []
        for cut_id, ref_words, hyp_words in results:
            tmp.append(
                (cut_id, list("".join(ref_words)), list("".join(hyp_words)))
            )
        results = tmp

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
    total_err = sub_errs + ins_errs + del_errs

    wer = 100.0 * total_err / ref_len if ref_len > 0 else 0.0

    print(f"%WER = {wer:.2f}", file=f)
    print(
        f"Errors: {ins_errs} insertions, {del_errs} deletions, "
        f"{sub_errs} substitutions, over {ref_len} units ({num_corr} correct)",
        file=f
    )

    logging.info(f"[{test_set_name}] %WER {wer:.2f}")

    return wer


def evaluate_model(country, model, ref_items, hyp_items, compute_CER, OUT_ROOT):
    """
    对单个 (country, model) 做一次评估，输出到 OUT_ROOT/country/model 下面
    """
    out_dir = Path(OUT_ROOT) / country / model
    out_dir.mkdir(parents=True, exist_ok=True)

    # 用 (audio_name, start) 做 key 对齐 ref / hyp
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

        cut_id = f"{ref['audio_name']}_{ref['start']}"

        ref_words = ref_text.split()
        hyp_words = hyp_text.split()

        results.append((cut_id, ref_words, hyp_words))

    metric_name = "cer" if compute_CER else "wer"

    recogs_path = out_dir / f"recogs-{country}-{model}.txt"
    errs_path = out_dir / f"errs-{country}-{model}.txt"
    summary_path = out_dir / f"{metric_name}-summary-{country}-{model}.txt"

    # 每次都是 "w" 覆盖写，不会保留旧文件内容
    store_transcripts(recogs_path, results)

    with open(errs_path, "w", encoding="utf8") as f:
        wer = write_error_stats(f, f"{country}-{model}", results, compute_CER)

    with open(summary_path, "w", encoding="utf8") as f:
        print("model\tWER/CER", file=f)
        print(f"{model}\t{wer:.2f}", file=f)


def main():
    # 需要参与评估的 batch 列表
    BATCHES = [
        "testbatch",
        "20251212",
        "20251205",
    ]

    ROOT_BASE = (
        "/inspire/hdd/project/multilingualspeechrecognition/"
        "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized"
    )
    # 统一结果目录：results
    OUT_ROOT = (
        "/inspire/hdd/project/multilingualspeechrecognition/"
        "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results"
    )
    os.makedirs(OUT_ROOT, exist_ok=True)

    # -------- total 累积池（跨 batch）---------
    total_ref_pool = defaultdict(list)      # key = country
    total_hyp_pool = defaultdict(list)      # key = (country, model)

    logging.info("====== Stage1: 逐 batch 读取 + 评估，同时累积 total ======")

    for batch in BATCHES:
        logging.info(f"---- Batch: {batch} ----")

        batch_ref_pool = defaultdict(list)
        batch_hyp_pool = defaultdict(list)

        REF_ROOT = f"{ROOT_BASE}/{batch}/ref"
        HYP_ROOT = f"{ROOT_BASE}/{batch}/hyp"

        if not os.path.exists(REF_ROOT):
            logging.warning(f"{batch} no ref dir: {REF_ROOT}")
            continue

        # 找这个 batch 里有哪些国家
        countries = [
            f[:-5] for f in os.listdir(REF_ROOT)
            if f.endswith(".json")
        ]

        for country in countries:
            # 加载 ref
            ref_path = os.path.join(REF_ROOT, f"{country}.json")
            with open(ref_path, "r", encoding="utf8") as fr:
                ref_items = json.load(fr)

            # 写入当前 batch ref 池
            batch_ref_pool[country].extend(ref_items)
            # 同时写入 total ref 池
            total_ref_pool[country].extend(ref_items)

            # 对应 hyp 目录
            hyp_dir = os.path.join(HYP_ROOT, country)
            if not os.path.exists(hyp_dir):
                continue

            models = [
                f[:-5] for f in os.listdir(hyp_dir)
                if f.endswith(".json")
            ]

            for model in models:
                hyp_path = os.path.join(hyp_dir, f"{model}.json")
                with open(hyp_path, "r", encoding="utf8") as fh:
                    hyp_items = json.load(fh)

                # 当前 batch
                batch_hyp_pool[(country, model)].extend(hyp_items)
                # total
                total_hyp_pool[(country, model)].extend(hyp_items)

        # ====== 对当前 batch 做一次完整评估 ======
        batch_out_root = os.path.join(OUT_ROOT, batch)
        os.makedirs(batch_out_root, exist_ok=True)

        logging.info(f"====== Stage2 (batch={batch}): evaluate ======")
        for (country, model), hyp_items in batch_hyp_pool.items():
            compute_CER = country in CER_LANGS
            evaluate_model(
                country,
                model,
                batch_ref_pool[country],
                hyp_items,
                compute_CER=compute_CER,
                OUT_ROOT=batch_out_root,
            )

    # ====== 对 total（全部 batch 合并）做一次评估 ======
    total_out_root = os.path.join(OUT_ROOT, "total")
    os.makedirs(total_out_root, exist_ok=True)

    logging.info("====== Stage3: total evaluate (所有 batch 合并) ======")
    for (country, model), hyp_items in total_hyp_pool.items():
        compute_CER = country in CER_LANGS
        evaluate_model(
            country,
            model,
            total_ref_pool[country],
            hyp_items,
            compute_CER=compute_CER,
            OUT_ROOT=total_out_root,
        )


if __name__ == "__main__":
    main()
