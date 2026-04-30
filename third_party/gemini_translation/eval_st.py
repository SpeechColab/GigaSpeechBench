#!/usr/bin/env python3
"""
Evaluate Speech Translation results using BLEU, chrF, TER.
Chinese uses jieba tokenization for BLEU.
Outputs a single Excel sheet with all languages × targets.

Usage:
  python3 eval_st.py --results_dir /path/to/results
"""

import argparse
import json
import os

import jieba
import sacrebleu
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter


def tokenize_zh(text: str) -> str:
    """Segment Chinese text with jieba, return space-separated string."""
    return " ".join(jieba.cut(text))


def evaluate_file(path: str, is_zh: bool = False):
    """Evaluate a single result file. Returns dict with metrics."""
    data = json.load(open(path, encoding="utf-8"))
    if not data:
        return None

    refs = [item["ref"] for item in data]
    hyps = [item["hyp"] for item in data]

    if is_zh:
        refs_tok = [tokenize_zh(r) for r in refs]
        hyps_tok = [tokenize_zh(h) for h in hyps]
        bleu = sacrebleu.corpus_bleu(hyps_tok, [refs_tok], tokenize="none")
    else:
        bleu = sacrebleu.corpus_bleu(hyps, [refs])

    chrf = sacrebleu.corpus_chrf(hyps, [refs])
    ter = sacrebleu.corpus_ter(hyps, [refs])

    return {
        "n_segments": len(data),
        "bleu": round(bleu.score, 2),
        "chrf": round(chrf.score, 2),
        "ter": round(ter.score, 2),
    }


LANGS = ["ARE", "DZA", "EGY", "IDN", "IRQ", "MAR", "MYS", "PHL", "SAU", "THA", "VNM"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results_dir", type=str, required=True)
    parser.add_argument("--output_xlsx", type=str, default=None)
    parser.add_argument("--output_txt", type=str, default=None)
    args = parser.parse_args()

    results_dir = args.results_dir
    if args.output_xlsx is None:
        args.output_xlsx = os.path.join(results_dir, "st_eval_results.xlsx")
    if args.output_txt is None:
        args.output_txt = os.path.join(results_dir, "eval_report.txt")

    # Collect metrics
    metrics = {}
    for lang in LANGS:
        for target in ("en", "zh"):
            path = os.path.join(results_dir, f"{lang}_{target}.json")
            if not os.path.isfile(path):
                continue
            m = evaluate_file(path, is_zh=(target == "zh"))
            if m:
                metrics[(lang, target)] = m

    # ---- Text report ----
    lines = []
    def log(s):
        lines.append(s)
        print(s)

    log("=" * 70)
    log("Gemini 2.0 Flash - Speech Translation Evaluation")
    log("=" * 70)

    for target, label in [("en", "-> English"), ("zh", "-> Chinese (jieba BLEU)")]:
        log(f"\n{label}")
        log(f"{'Lang':<8} {'Segs':>6} {'BLEU':>8} {'chrF':>8} {'TER':>8}")
        log("-" * 42)

        all_refs, all_hyps = [], []
        for lang in LANGS:
            m = metrics.get((lang, target))
            if m:
                log(f"{lang:<8} {m['n_segments']:>6} {m['bleu']:>8.2f} {m['chrf']:>8.2f} {m['ter']:>8.2f}")
                path = os.path.join(results_dir, f"{lang}_{target}.json")
                data = json.load(open(path))
                all_refs.extend([d["ref"] for d in data])
                all_hyps.extend([d["hyp"] for d in data])

        if all_refs:
            if target == "zh":
                bleu = sacrebleu.corpus_bleu([tokenize_zh(h) for h in all_hyps], [[tokenize_zh(r) for r in all_refs]], tokenize="none")
            else:
                bleu = sacrebleu.corpus_bleu(all_hyps, [all_refs])
            chrf = sacrebleu.corpus_chrf(all_hyps, [all_refs])
            ter = sacrebleu.corpus_ter(all_hyps, [all_refs])
            log("-" * 42)
            log(f"{'OVERALL':<8} {len(all_refs):>6} {bleu.score:>8.2f} {chrf.score:>8.2f} {ter.score:>8.2f}")

    with open(args.output_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nText report: {args.output_txt}")

    # ---- Excel ----
    wb = Workbook()
    ws = wb.active
    ws.title = "ST Results"

    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    headers = ["Language", "EN segs", "EN BLEU", "EN chrF", "EN TER", "ZH segs", "ZH BLEU", "ZH chrF", "ZH TER"]
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center

    for ri, lang in enumerate(LANGS, 2):
        ws.cell(row=ri, column=1, value=lang).font = bold
        ws.cell(row=ri, column=1).alignment = center
        for target, col_offset in [("en", 2), ("zh", 6)]:
            m = metrics.get((lang, target))
            if m:
                ws.cell(row=ri, column=col_offset, value=m["n_segments"]).alignment = center
                for j, key in enumerate(["bleu", "chrf", "ter"], 1):
                    cell = ws.cell(row=ri, column=col_offset + j, value=m[key])
                    cell.number_format = "0.00"
                    cell.alignment = center
            else:
                for j in range(4):
                    ws.cell(row=ri, column=col_offset + j, value="-").alignment = center

    # Overall
    orow = len(LANGS) + 2
    ws.cell(row=orow, column=1, value="OVERALL").font = Font(bold=True, size=12)
    ws.cell(row=orow, column=1).alignment = center
    for target, col_offset in [("en", 2), ("zh", 6)]:
        all_refs, all_hyps = [], []
        for lang in LANGS:
            path = os.path.join(results_dir, f"{lang}_{target}.json")
            if os.path.isfile(path):
                data = json.load(open(path))
                all_refs.extend([d["ref"] for d in data])
                all_hyps.extend([d["hyp"] for d in data])
        if all_refs:
            if target == "zh":
                bleu = sacrebleu.corpus_bleu([tokenize_zh(h) for h in all_hyps], [[tokenize_zh(r) for r in all_refs]], tokenize="none")
            else:
                bleu = sacrebleu.corpus_bleu(all_hyps, [all_refs])
            chrf = sacrebleu.corpus_chrf(all_hyps, [all_refs])
            ter = sacrebleu.corpus_ter(all_hyps, [all_refs])
            ws.cell(row=orow, column=col_offset, value=len(all_refs)).alignment = center
            for j, val in enumerate([bleu.score, chrf.score, ter.score], 1):
                cell = ws.cell(row=orow, column=col_offset + j, value=round(val, 2))
                cell.number_format = "0.00"
                cell.alignment = center
                cell.font = bold

    ws.column_dimensions["A"].width = 12
    for ci in range(2, 10):
        ws.column_dimensions[get_column_letter(ci)].width = 12

    wb.save(args.output_xlsx)
    print(f"Excel report: {args.output_xlsx}")


if __name__ == "__main__":
    main()
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
