#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ASR 评测脚本（CPU-safe Streaming 终态完整版）

✅ batch / total 均生成 recogs + errs + summary
✅ coverage + dur(h)
✅ total 为真正全量统计（非平均）
"""

import os
import json
import logging
from pathlib import Path
from collections import defaultdict
import kaldialign
import gc

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
WER_LANGS = ["IRQ","DZA","ARE","EGY","MAR","SAU",
             "IDN","MYS","PHL","VNM","USA"]
CER_LANGS = ["JPN","KOR","THA","CHN"]

ERR = "*"

COUNTRY_COL_WIDTH = 6
MODEL_COL_WIDTH = 70
INT_COL_WIDTH = 8

# =========================
# 核心 streaming 计算
# =========================

def process_one_ref_hyp(ref_items, hyp_items, compute_CER, recogs_f, stats):
    hyp_index = {
        (h["audio_name"], float(h["start"])): h["text"]
        for h in hyp_items
    }

    valid = 0
    dur_sec = 0.0

    for r in ref_items:
        key = (r["audio_name"], float(r["start"]))
        if key not in hyp_index:
            continue

        # coverage
        valid += 1
        dur_sec += float(r["end"]) - float(r["start"])

        ref_tok = r["text"].strip().split()
        hyp_tok = hyp_index[key].strip().split()

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
        print(
            f"Errors: {stats['I']} insertions, "
            f"{stats['D']} deletions, "
            f"{stats['S']} substitutions, "
            f"over {N} units ({stats['C']} correct)",
            file=f
        )

    metric = "cer" if compute_CER else "wer"
    with open(out_dir / f"{metric}-summary-{country}-{model}.txt",
              "w", encoding="utf8") as f:
        print("model\tWER/CER", file=f)
        print(f"{model}\t{wer:.2f}", file=f)

# =========================
# 主流程
# =========================

def main():
    BATCHES = ["testbatch", "20251212", "20251205", "20251226", "20251219"]

    ROOT_BASE = (
        "/inspire/hdd/project/multilingualspeechrecognition/"
        "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized"
    )
    OUT_ROOT = (
        "/inspire/hdd/project/multilingualspeechrecognition/"
        "chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results"
    )
    os.makedirs(OUT_ROOT, exist_ok=True)

    # =========================
    # Batch 阶段
    # =========================
    for batch in BATCHES:
        logging.info(f"====== Batch {batch} ======")

        REF_ROOT = f"{ROOT_BASE}/{batch}/ref"
        HYP_ROOT = f"{ROOT_BASE}/{batch}/hyp"
        if not os.path.isdir(REF_ROOT):
            continue

        batch_out = Path(OUT_ROOT) / batch
        batch_out.mkdir(parents=True, exist_ok=True)

        country_max = defaultdict(int)
        cache = {}

        for fn in os.listdir(REF_ROOT):
            if not fn.endswith(".json"):
                continue
            country = fn[:-5]

            ref_path = f"{REF_ROOT}/{fn}"
            hyp_country_dir = f"{HYP_ROOT}/{country}"
            if not os.path.isdir(hyp_country_dir):
                continue

            for hfn in os.listdir(hyp_country_dir):
                if not hfn.endswith(".json"):
                    continue
                model = hfn[:-5]

                with open(ref_path, "r", encoding="utf8") as f:
                    ref_items = json.load(f)
                with open(f"{hyp_country_dir}/{hfn}", "r", encoding="utf8") as f:
                    hyp_items = json.load(f)

                stats = defaultdict(int)
                compute_CER = country in CER_LANGS

                out_dir = batch_out / country / model
                out_dir.mkdir(parents=True, exist_ok=True)

                with open(out_dir / f"recogs-{country}-{model}.txt",
                          "w", encoding="utf8") as rec_f:
                    v, d = process_one_ref_hyp(
                        ref_items, hyp_items,
                        compute_CER, rec_f, stats
                    )

                write_errs_and_summary(
                    out_dir, country, model, stats, compute_CER
                )

                cache[(country, model)] = (v, d)
                country_max[country] = max(country_max[country], v)

                del hyp_items
                del ref_items
                gc.collect()

        with open(batch_out / "segment_coverage.txt", "w", encoding="utf8") as f:
            print(
                f"{'country':<{COUNTRY_COL_WIDTH}} "
                f"{'model':<{MODEL_COL_WIDTH}} "
                f"{'valid':>{INT_COL_WIDTH}} "
                f"{'max':>{INT_COL_WIDTH}} "
                f"{'ratio':>8} "
                f"{'dur(h)':>10}",
                file=f
            )
            for (country, model), (v, d) in sorted(cache.items()):
                m = country_max[country]
                r = v / m if m > 0 else 0.0
                print(
                    f"{country:<{COUNTRY_COL_WIDTH}} "
                    f"{model:<{MODEL_COL_WIDTH}} "
                    f"{v:>{INT_COL_WIDTH}d} "
                    f"{m:>{INT_COL_WIDTH}d} "
                    f"{r:>8.4f} "
                    f"{d:>10.3f}",
                    file=f
                )

    # =========================
    # Total 阶段
    # =========================
    logging.info("====== Total ======")

    total_out = Path(OUT_ROOT) / "total"
    total_out.mkdir(parents=True, exist_ok=True)

    total_cache = defaultdict(lambda: [0, 0.0])
    total_country_max = defaultdict(int)
    total_stats = defaultdict(lambda: defaultdict(int))

    for batch in BATCHES:
        REF_ROOT = f"{ROOT_BASE}/{batch}/ref"
        HYP_ROOT = f"{ROOT_BASE}/{batch}/hyp"
        if not os.path.isdir(REF_ROOT):
            continue

        for fn in os.listdir(REF_ROOT):
            if not fn.endswith(".json"):
                continue
            country = fn[:-5]

            ref_path = f"{REF_ROOT}/{fn}"
            hyp_country_dir = f"{HYP_ROOT}/{country}"
            if not os.path.isdir(hyp_country_dir):
                continue

            for hfn in os.listdir(hyp_country_dir):
                if not hfn.endswith(".json"):
                    continue
                model = hfn[:-5]

                with open(ref_path, "r", encoding="utf8") as f:
                    ref_items = json.load(f)
                with open(f"{hyp_country_dir}/{hfn}", "r", encoding="utf8") as f:
                    hyp_items = json.load(f)

                stats = defaultdict(int)
                compute_CER = country in CER_LANGS

                out_dir = total_out / country / model
                out_dir.mkdir(parents=True, exist_ok=True)

                with open(out_dir / f"recogs-{country}-{model}.txt",
                          "a", encoding="utf8") as rec_f:
                    v, d = process_one_ref_hyp(
                        ref_items, hyp_items,
                        compute_CER, rec_f, stats
                    )

                total_cache[(country, model)][0] += v
                total_cache[(country, model)][1] += d
                total_country_max[country] = max(
                    total_country_max[country],
                    total_cache[(country, model)][0]
                )

                for k, vv in stats.items():
                    total_stats[(country, model)][k] += vv

                del hyp_items
                del ref_items
                gc.collect()

    with open(total_out / "segment_coverage.txt", "w", encoding="utf8") as f:
        print(
            f"{'country':<{COUNTRY_COL_WIDTH}} "
            f"{'model':<{MODEL_COL_WIDTH}} "
            f"{'valid':>{INT_COL_WIDTH}} "
            f"{'max':>{INT_COL_WIDTH}} "
            f"{'ratio':>8} "
            f"{'dur(h)':>10}",
            file=f
        )
        for (country, model), (v, d) in sorted(total_cache.items()):
            m = total_country_max[country]
            r = v / m if m > 0 else 0.0
            print(
                f"{country:<{COUNTRY_COL_WIDTH}} "
                f"{model:<{MODEL_COL_WIDTH}} "
                f"{v:>{INT_COL_WIDTH}d} "
                f"{m:>{INT_COL_WIDTH}d} "
                f"{r:>8.4f} "
                f"{d:>10.3f}",
                file=f
            )

    # ===== 写 total errs / summary =====
    for (country, model), stats in sorted(total_stats.items()):
        compute_CER = country in CER_LANGS
        out_dir = total_out / country / model
        out_dir.mkdir(parents=True, exist_ok=True)
        write_errs_and_summary(out_dir, country, model, stats, compute_CER)

    logging.info("✅ 全部完成（Batch + Total 三文件齐全）")


if __name__ == "__main__":
    main()
