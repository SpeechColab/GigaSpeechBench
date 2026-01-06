#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从多个 batch 读取 ref/hyp，
- 每个 batch 各自算一套 WER/CER，输出到 results/{batch}/
- 同时在每个 results/{batch}/ 下生成【定宽】segment_coverage.txt
- 再按【国家级 streaming】算 total，输出到 results/total/
（功能与原版完全一致，但不会 OOM）
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import logging
import kaldialign

# =========================
# 日志
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# 常量
# =========================

WER_LANGS = ["IRQ", "DZA", "ARE", "EGY", "MAR", "SAU",
             "IDN", "MYS", "PHL", "VNM", "USA"]
CER_LANGS = ["JPN", "KOR", "THA", "CHN"]

ERR = "*"

# === 覆盖最长模型名的定宽设置 ===
COUNTRY_COL_WIDTH = 6
MODEL_COL_WIDTH = 70   # 覆盖 DZA_stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo
INT_COL_WIDTH = 8


# =========================
# 基础工具函数
# =========================

def store_transcripts(filename: Path, texts):
    with open(filename, "w", encoding="utf8") as f:
        for cut_id, ref, hyp in texts:
            print(f"{cut_id}:\tref={' '.join(ref)}", file=f)
            print(f"{cut_id}:\thyp={' '.join(hyp)}", file=f)


def write_error_stats(f, test_set_name, results, compute_CER=False):
    subs = defaultdict(int)
    ins = defaultdict(int)
    dels = defaultdict(int)
    num_corr = 0

    if compute_CER:
        tmp = []
        for cut_id, ref_words, hyp_words in results:
            tmp.append(
                (cut_id, list("".join(ref_words)), list("".join(hyp_words)))
            )
        results = tmp

    for _, ref, hyp in results:
        ali = kaldialign.align(ref, hyp, ERR)
        for r, h in ali:
            if r == ERR:
                ins[h] += 1
            elif h == ERR:
                dels[r] += 1
            elif r != h:
                subs[(r, h)] += 1
            else:
                num_corr += 1

    ref_len = sum(len(r) for _, r, _ in results)
    total_err = sum(subs.values()) + sum(ins.values()) + sum(dels.values())
    wer = 100.0 * total_err / ref_len if ref_len > 0 else 0.0

    print(f"%WER = {wer:.2f}", file=f)
    print(
        f"Errors: {sum(ins.values())} insertions, "
        f"{sum(dels.values())} deletions, "
        f"{sum(subs.values())} substitutions, "
        f"over {ref_len} units ({num_corr} correct)",
        file=f
    )

    logging.info(f"[{test_set_name}] %WER {wer:.2f}")
    return wer


def count_valid_segments(ref_items, hyp_items):
    hyp_keys = {
        (item["audio_name"], float(item["start"]))
        for item in hyp_items
    }

    valid = 0
    for ref in ref_items:
        key = (ref["audio_name"], float(ref["start"]))
        if key in hyp_keys:
            valid += 1

    return valid, len(ref_items)


# =========================
# 单 batch 评估
# =========================

def evaluate_model(country, model, ref_items, hyp_items, compute_CER, OUT_ROOT):
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

        cut_id = f"{ref['audio_name']}_{ref['start']}"
        ref_words = ref["text"].strip().split()
        hyp_words = hyp_index[key].strip().split()
        results.append((cut_id, ref_words, hyp_words))

    metric = "cer" if compute_CER else "wer"

    store_transcripts(out_dir / f"recogs-{country}-{model}.txt", results)

    with open(out_dir / f"errs-{country}-{model}.txt", "w", encoding="utf8") as f:
        wer = write_error_stats(
            f, f"{country}-{model}", results, compute_CER
        )

    with open(out_dir / f"{metric}-summary-{country}-{model}.txt",
              "w", encoding="utf8") as f:
        print("model\tWER/CER", file=f)
        print(f"{model}\t{wer:.2f}", file=f)


# =========================
# total streaming 统计
# =========================

def accumulate_stats(ref_items, hyp_items, compute_CER, stats):
    hyp_index = {
        (item["audio_name"], float(item["start"])): item["text"]
        for item in hyp_items
    }

    for ref in ref_items:
        key = (ref["audio_name"], float(ref["start"]))
        if key not in hyp_index:
            continue

        ref_tokens = ref["text"].strip().split()
        hyp_tokens = hyp_index[key].strip().split()

        if compute_CER:
            ref_tokens = list("".join(ref_tokens))
            hyp_tokens = list("".join(hyp_tokens))

        ali = kaldialign.align(ref_tokens, hyp_tokens, ERR)
        for r, h in ali:
            if r == ERR:
                stats["I"] += 1
            elif h == ERR:
                stats["D"] += 1
                stats["N"] += 1
            elif r != h:
                stats["S"] += 1
                stats["N"] += 1
            else:
                stats["C"] += 1
                stats["N"] += 1


# =========================
# 主流程
# =========================

def main():
    BATCHES = ["testbatch", "20251212", "20251205", "20251226"]

    ROOT_BASE = (
        "/inspire/hdd/project/multilingualspeechrecognition/"
        "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized"
    )
    OUT_ROOT = (
        "/inspire/hdd/project/multilingualspeechrecognition/"
        "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results"
    )
    os.makedirs(OUT_ROOT, exist_ok=True)

    logging.info("====== Stage1: per-batch evaluate + coverage ======")

    # -------- batch 阶段 --------
    for batch in BATCHES:
        logging.info(f"---- Batch: {batch} ----")

        REF_ROOT = f"{ROOT_BASE}/{batch}/ref"
        HYP_ROOT = f"{ROOT_BASE}/{batch}/hyp"
        if not os.path.exists(REF_ROOT):
            continue

        countries = [f[:-5] for f in os.listdir(REF_ROOT) if f.endswith(".json")]

        batch_ref_pool = {}
        batch_hyp_pool = defaultdict(list)

        for country in countries:
            with open(f"{REF_ROOT}/{country}.json", "r", encoding="utf8") as f:
                batch_ref_pool[country] = json.load(f)

            hyp_dir = f"{HYP_ROOT}/{country}"
            if not os.path.exists(hyp_dir):
                continue

            for fn in os.listdir(hyp_dir):
                if fn.endswith(".json"):
                    model = fn[:-5]
                    with open(f"{hyp_dir}/{fn}", "r", encoding="utf8") as f:
                        batch_hyp_pool[(country, model)] = json.load(f)

        batch_out_root = f"{OUT_ROOT}/{batch}"
        os.makedirs(batch_out_root, exist_ok=True)

        coverage_path = Path(batch_out_root) / "segment_coverage.txt"
        with open(coverage_path, "w", encoding="utf8") as cov_f:
            header = (
                f"{'country':<{COUNTRY_COL_WIDTH}} "
                f"{'model':<{MODEL_COL_WIDTH}} "
                f"{'valid':>{INT_COL_WIDTH}} "
                f"{'ref':>{INT_COL_WIDTH}} "
                f"{'ratio':>8}"
            )
            print(header, file=cov_f)

            for (country, model), hyp_items in batch_hyp_pool.items():
                ref_items = batch_ref_pool[country]

                valid, ref_cnt = count_valid_segments(ref_items, hyp_items)
                ratio = valid / ref_cnt if ref_cnt > 0 else 0.0

                line = (
                    f"{country:<{COUNTRY_COL_WIDTH}} "
                    f"{model:<{MODEL_COL_WIDTH}} "
                    f"{valid:>{INT_COL_WIDTH}d} "
                    f"{ref_cnt:>{INT_COL_WIDTH}d} "
                    f"{ratio:>8.4f}"
                )
                print(line, file=cov_f)

                evaluate_model(
                    country,
                    model,
                    ref_items,
                    hyp_items,
                    compute_CER=country in CER_LANGS,
                    OUT_ROOT=batch_out_root,
                )

    # -------- total 阶段（保持原逻辑）--------
    logging.info("====== Stage2: total evaluate (country-level streaming) ======")

    total_out_root = f"{OUT_ROOT}/total"
    os.makedirs(total_out_root, exist_ok=True)

    all_pairs = set()
    for batch in BATCHES:
        hyp_root = f"{ROOT_BASE}/{batch}/hyp"
        if not os.path.exists(hyp_root):
            continue
        for country in os.listdir(hyp_root):
            for fn in os.listdir(f"{hyp_root}/{country}"):
                if fn.endswith(".json"):
                    all_pairs.add((country, fn[:-5]))

    for country, model in sorted(all_pairs):
        stats = defaultdict(int)
        compute_CER = country in CER_LANGS

        for batch in BATCHES:
            ref_path = f"{ROOT_BASE}/{batch}/ref/{country}.json"
            hyp_path = f"{ROOT_BASE}/{batch}/hyp/{country}/{model}.json"

            if not (os.path.exists(ref_path) and os.path.exists(hyp_path)):
                continue

            with open(ref_path, "r", encoding="utf8") as f:
                ref_items = json.load(f)
            with open(hyp_path, "r", encoding="utf8") as f:
                hyp_items = json.load(f)

            accumulate_stats(ref_items, hyp_items, compute_CER, stats)

        N = stats["N"]
        total_err = stats["S"] + stats["D"] + stats["I"]
        wer = 100.0 * total_err / N if N > 0 else 0.0

        out_dir = Path(total_out_root) / country / model
        out_dir.mkdir(parents=True, exist_ok=True)

        metric = "cer" if compute_CER else "wer"
        with open(out_dir / f"{metric}-summary-{country}-{model}.txt",
                  "w", encoding="utf8") as f:
            print("model\tWER/CER", file=f)
            print(f"{model}\t{wer:.2f}", file=f)

        logging.info(f"[{country}-{model}] %WER {wer:.2f}")


if __name__ == "__main__":
    main()
