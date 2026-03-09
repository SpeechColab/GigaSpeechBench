#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ASR 评测脚本（Single-batch · normalized · audio_name 去 .wav）

特性：
- 单 batch
- model 名来自 hyp item["model"]
- audio_name 匹配时统一去掉 .wav
- 输出 ref / hyp / matched 段数一致性检查
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

# =========================
# 路径（normalized）
# =========================
REF_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/common-voice/ref"


HYP_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/common-voice/hyp"

OUT_ROOT = "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/results_common-voice"


os.makedirs(OUT_ROOT, exist_ok=True)

# =========================
# audio_name 归一化（关键）
# =========================

def norm_audio_name(name: str) -> str:
    """
    用于匹配的 audio_name：
    - 取 basename
    - 去掉 .wav
    """
    name = name.replace("\\", "/")
    base = os.path.basename(name)
    if base.lower().endswith(".wav"):
        base = base[:-4]
    return base

# =========================
# 核心 streaming 计算
# =========================

def process_one_ref_hyp(ref_items, hyp_items, compute_CER, recogs_f, stats):
    """
    返回：
      valid_segments, duration_hours
    """

    hyp_index = {
        (norm_audio_name(h["audio_name"]), float(h["start"])): h["text"]
        for h in hyp_items
    }

    valid = 0
    dur_sec = 0.0

    for r in ref_items:
        key = (norm_audio_name(r["audio_name"]), float(r["start"]))
        if key not in hyp_index:
            continue

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
# 主流程（单 batch）
# =========================

def main():
    logging.info("====== Single Batch Evaluation ======")

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

        # 🔑 按 model 聚合（model 来自 item）
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

            with open(out_dir / f"recogs-{country}-{model}.txt",
                      "w", encoding="utf8") as rec_f:
                valid, dur_h = process_one_ref_hyp(
                    ref_items, hyp_items,
                    compute_CER, rec_f, stats
                )

            write_errs_and_summary(out_dir, country, model, stats, compute_CER)

            # ===== 段数一致性检查 =====
            ref_n = len(ref_items)
            hyp_n = len(hyp_items)

            with open(out_dir / "segment_check.txt", "w", encoding="utf8") as f:
                f.write(
                    f"ref_segments={ref_n}\n"
                    f"hyp_segments={hyp_n}\n"
                    f"matched_segments={valid}\n"
                )

            logging.info(
                f"[CHECK] {country}/{model}: "
                f"ref={ref_n} hyp={hyp_n} matched={valid}"
            )

        del ref_items
        gc.collect()

    logging.info("✅ 单 batch 评测完成")


if __name__ == "__main__":
    main()
