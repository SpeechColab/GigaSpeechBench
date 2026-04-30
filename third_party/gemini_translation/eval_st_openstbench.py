#!/usr/bin/env python3
"""
Evaluate Speech Translation results using OpenSTBench TranslationEvaluator.
Supports sacreBLEU, chrF++, COMET (neural metric), and optionally BLEURT.

Reads the same JSON format as eval_st.py:
  [ { "ref": "...", "hyp": "...", "original": "..." }, ... ]

Usage:
  # sacreBLEU + chrF++ only (no model download needed)
  python3 eval_st_openstbench.py --results_dir ../../data/st_results

  # sacreBLEU + chrF++ + COMET (downloads ~1.5GB model on first run)
  python3 eval_st_openstbench.py --results_dir ../../data/st_results --use_comet

  # All metrics including BLEURT
  python3 eval_st_openstbench.py --results_dir ../../data/st_results --use_comet --use_bleurt
"""

import argparse
import json
import os
import sys

from openstbench import TranslationEvaluator
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

LANGS = ["ARE", "DZA", "EGY", "IDN", "IRQ", "MAR", "MYS", "PHL", "SAU", "THA", "VNM"]


def load_st_data(path: str):
    """Load a ST result JSON file. Returns (refs, hyps, originals)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        return [], [], []
    refs = [item["ref"] for item in data]
    hyps = [item["hyp"] for item in data]
    originals = [item.get("original", "") for item in data]
    return refs, hyps, originals


def evaluate_file(evaluator: TranslationEvaluator, path: str, target_lang: str):
    """Evaluate a single ST result file. Returns dict with metrics + n_segments."""
    refs, hyps, originals = load_st_data(path)
    if not refs:
        return None

    results = evaluator.evaluate_all(
        reference=refs,
        target_text=hyps,
        source=originals if any(originals) else None,
        target_lang=target_lang,
    )

    results["n_segments"] = len(refs)
    return results


def evaluate_overall(evaluator: TranslationEvaluator, results_dir: str,
                     target: str, target_lang: str):
    """Compute overall metrics across all languages for a given target."""
    all_refs, all_hyps, all_originals = [], [], []
    for lang in LANGS:
        path = os.path.join(results_dir, f"{lang}_{target}.json")
        if not os.path.isfile(path):
            continue
        refs, hyps, originals = load_st_data(path)
        all_refs.extend(refs)
        all_hyps.extend(hyps)
        all_originals.extend(originals)

    if not all_refs:
        return None

    results = evaluator.evaluate_all(
        reference=all_refs,
        target_text=all_hyps,
        source=all_originals if any(all_originals) else None,
        target_lang=target_lang,
    )
    results["n_segments"] = len(all_refs)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate ST results with OpenSTBench (sacreBLEU, chrF++, COMET, BLEURT)")
    parser.add_argument("--results_dir", type=str, required=True,
                        help="Directory containing {LANG}_{en|zh}.json files")
    parser.add_argument("--use_comet", action="store_true",
                        help="Enable COMET metric (downloads ~1.5GB model on first run)")
    parser.add_argument("--use_bleurt", action="store_true",
                        help="Enable BLEURT metric (requires bleurt-pytorch)")
    parser.add_argument("--device", type=str, default="cpu",
                        choices=["cpu", "cuda"],
                        help="Device for neural metrics (default: cpu)")
    parser.add_argument("--output_xlsx", type=str, default=None)
    parser.add_argument("--output_txt", type=str, default=None)
    args = parser.parse_args()

    results_dir = args.results_dir
    if args.output_xlsx is None:
        args.output_xlsx = os.path.join(results_dir, "openstbench_eval_results.xlsx")
    if args.output_txt is None:
        args.output_txt = os.path.join(results_dir, "openstbench_eval_report.txt")

    # Initialize evaluator
    evaluator = TranslationEvaluator(
        use_bleu=True,
        use_chrf=True,
        use_comet=args.use_comet,
        use_bleurt=args.use_bleurt,
        device=args.device,
    )

    # Determine which metric keys to display
    metric_keys = ["sacreBLEU", "chrF++"]
    if args.use_comet:
        metric_keys.append("COMET")
    if args.use_bleurt:
        metric_keys.append("BLEURT")

    # Evaluate per language × target
    all_metrics = {}  # (lang, target) -> dict
    for lang in LANGS:
        for target, target_lang in [("en", "en"), ("zh", "zh")]:
            path = os.path.join(results_dir, f"{lang}_{target}.json")
            if not os.path.isfile(path):
                continue
            m = evaluate_file(evaluator, path, target_lang)
            if m:
                all_metrics[(lang, target)] = m

    # Evaluate overall
    overall = {}
    for target, target_lang in [("en", "en"), ("zh", "zh")]:
        m = evaluate_overall(evaluator, results_dir, target, target_lang)
        if m:
            overall[target] = m

    # ---- Text report ----
    lines = []

    def log(s):
        lines.append(s)
        print(s)

    log("=" * 80)
    log("OpenSTBench - Speech Translation Evaluation")
    log(f"Metrics: {', '.join(metric_keys)}")
    log(f"Device: {args.device}")
    log("=" * 80)

    for target, label in [("en", "-> English"), ("zh", "-> Chinese")]:
        metric_header = "".join(f"{k:>12}" for k in metric_keys)
        log(f"\n{label}")
        log(f"{'Lang':<8} {'Segs':>6}{metric_header}")
        log("-" * (14 + 12 * len(metric_keys)))

        for lang in LANGS:
            m = all_metrics.get((lang, target))
            if m:
                vals = "".join(f"{m.get(k, -1):>12.4f}" for k in metric_keys)
                log(f"{lang:<8} {m['n_segments']:>6}{vals}")

        if target in overall:
            m = overall[target]
            vals = "".join(f"{m.get(k, -1):>12.4f}" for k in metric_keys)
            log("-" * (14 + 12 * len(metric_keys)))
            log(f"{'OVERALL':<8} {m['n_segments']:>6}{vals}")

    with open(args.output_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nText report: {args.output_txt}")

    # ---- Excel ----
    wb = Workbook()
    ws = wb.active
    ws.title = "OpenSTBench ST Results"

    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    # Build headers: Language | EN segs | EN sacreBLEU | EN chrF++ | [EN COMET] | ... | ZH segs | ...
    headers = ["Language"]
    for prefix in ["EN", "ZH"]:
        headers.append(f"{prefix} segs")
        for k in metric_keys:
            headers.append(f"{prefix} {k}")

    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center

    n_metric_cols = 1 + len(metric_keys)  # segs + metrics per target

    for ri, lang in enumerate(LANGS, 2):
        ws.cell(row=ri, column=1, value=lang).font = bold
        ws.cell(row=ri, column=1).alignment = center

        for target_idx, target in enumerate(["en", "zh"]):
            col_offset = 2 + target_idx * n_metric_cols
            m = all_metrics.get((lang, target))
            if m:
                ws.cell(row=ri, column=col_offset, value=m["n_segments"]).alignment = center
                for j, k in enumerate(metric_keys, 1):
                    cell = ws.cell(row=ri, column=col_offset + j, value=m.get(k, -1))
                    cell.number_format = "0.0000"
                    cell.alignment = center
            else:
                for j in range(n_metric_cols):
                    ws.cell(row=ri, column=col_offset + j, value="-").alignment = center

    # Overall row
    orow = len(LANGS) + 2
    ws.cell(row=orow, column=1, value="OVERALL").font = Font(bold=True, size=12)
    ws.cell(row=orow, column=1).alignment = center

    for target_idx, target in enumerate(["en", "zh"]):
        col_offset = 2 + target_idx * n_metric_cols
        m = overall.get(target)
        if m:
            ws.cell(row=orow, column=col_offset, value=m["n_segments"]).alignment = center
            for j, k in enumerate(metric_keys, 1):
                cell = ws.cell(row=orow, column=col_offset + j, value=m.get(k, -1))
                cell.number_format = "0.0000"
                cell.alignment = center
                cell.font = bold

    ws.column_dimensions["A"].width = 12
    for ci in range(2, len(headers) + 1):
        ws.column_dimensions[get_column_letter(ci)].width = 14

    wb.save(args.output_xlsx)
    print(f"Excel report: {args.output_xlsx}")

    # Cleanup
    evaluator.cleanup()


if __name__ == "__main__":
    main()
