#!/usr/bin/env python3
"""
Evaluate Speech Translation results using BLEU and chrF.
Reads JSON files with ref/hyp pairs, computes per-language and overall scores.

Usage:
  python3 eval_st.py --results_dir /path/to/results --output /path/to/report.txt
"""

import argparse
import json
import os
import sys

import sacrebleu


def evaluate_file(path: str):
    """Evaluate a single result file. Returns dict with metrics."""
    data = json.load(open(path, encoding="utf-8"))
    if not data:
        return None

    refs = [item["ref"] for item in data]
    hyps = [item["hyp"] for item in data]

    # BLEU
    bleu = sacrebleu.corpus_bleu(hyps, [refs])

    # chrF
    chrf = sacrebleu.corpus_chrf(hyps, [refs])

    # TER
    ter = sacrebleu.corpus_ter(hyps, [refs])

    return {
        "n_segments": len(data),
        "bleu": round(bleu.score, 2),
        "chrf": round(chrf.score, 2),
        "ter": round(ter.score, 2),
        "bleu_details": str(bleu),
        "chrf_details": str(chrf),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results_dir", type=str, required=True)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    results_dir = args.results_dir
    lines = []

    def log(s):
        lines.append(s)
        print(s)

    log("=" * 70)
    log(f"Speech Translation Evaluation Report")
    log(f"Results dir: {results_dir}")
    log("=" * 70)

    all_refs_en = []
    all_hyps_en = []
    all_refs_zh = []
    all_hyps_zh = []

    for f in sorted(os.listdir(results_dir)):
        if not f.endswith(".json"):
            continue
        path = os.path.join(results_dir, f)
        metrics = evaluate_file(path)
        if metrics is None:
            log(f"\n{f}: empty")
            continue

        lang = f.replace(".json", "")
        log(f"\n--- {lang} ({metrics['n_segments']} segments) ---")
        log(f"  BLEU:  {metrics['bleu']}")
        log(f"  chrF:  {metrics['chrf']}")
        log(f"  TER:   {metrics['ter']}")

        # Accumulate for overall
        data = json.load(open(path))
        if "_en" in f:
            all_refs_en.extend([d["ref"] for d in data])
            all_hyps_en.extend([d["hyp"] for d in data])
        elif "_zh" in f:
            all_refs_zh.extend([d["ref"] for d in data])
            all_hyps_zh.extend([d["hyp"] for d in data])

    # Overall scores
    if all_refs_en:
        bleu = sacrebleu.corpus_bleu(all_hyps_en, [all_refs_en])
        chrf = sacrebleu.corpus_chrf(all_hyps_en, [all_refs_en])
        ter = sacrebleu.corpus_ter(all_hyps_en, [all_refs_en])
        log(f"\n{'='*70}")
        log(f"OVERALL EN ({len(all_refs_en)} segments)")
        log(f"  BLEU:  {bleu.score:.2f}")
        log(f"  chrF:  {chrf.score:.2f}")
        log(f"  TER:   {ter.score:.2f}")

    if all_refs_zh:
        bleu = sacrebleu.corpus_bleu(all_hyps_zh, [all_refs_zh])
        chrf = sacrebleu.corpus_chrf(all_hyps_zh, [all_refs_zh])
        ter = sacrebleu.corpus_ter(all_hyps_zh, [all_refs_zh])
        log(f"\n{'='*70}")
        log(f"OVERALL ZH ({len(all_refs_zh)} segments)")
        log(f"  BLEU:  {bleu.score:.2f}")
        log(f"  chrF:  {chrf.score:.2f}")
        log(f"  TER:   {ter.score:.2f}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
