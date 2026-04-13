#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotword WER evaluation script.
Computes overall WER, U-WER (unbiased, non-hotword tokens),
and B-WER (biased, hotword tokens), plus hotword recall (TP/TN/FP/FN).

Data format:
  - result_dir: entity-annotated reference JSON files, e.g.
      result_dir/AGR-CH/AGR-CH#bilibili#BV17ae1zZEaU.json
      Each file: {"audio_name": ..., "segments": [{..., "entities": [...], "start": ..., "end": ..., "text": ...}]}
  - hyp_dir: model hypothesis JSON files, e.g.
      hyp_dir/AGR-CH_Gemini.json  or  hyp_dir/AGR-CH.json  (model=azure)
      Each file: list of {"audio_name": "...wav", "text": ..., "start_time": ..., "end_time": ..., "language": ..., "model": ...}

Segment matching: by (audio_name_without_wav, start_time, end_time).
"""

import argparse
import json
import os
import sys
import unicodedata
from enum import Enum
from collections import defaultdict


# ---------------------------------------------------------------------------
# Tokenisation helpers (from wer.py)
# ---------------------------------------------------------------------------

PUNCTS = set("!,?、。！，；？：「」︰『』《》")
SPACELIST = set(" \t\r\n")


class Code(Enum):
    match = 1
    substitution = 2
    insertion = 3
    deletion = 4


def characterize(string: str):
    """Tokenise a string character-by-character (for CJK / mixed text)."""
    res = []
    i = 0
    while i < len(string):
        char = string[i]
        if char in PUNCTS:
            i += 1
            continue
        cat1 = unicodedata.category(char)
        if cat1 == "Zs" or cat1 == "Cn" or char in SPACELIST:
            i += 1
            continue
        if cat1 == "Lo":  # Letter-Other (CJK etc.)
            res.append(char)
            i += 1
        else:
            sep = ">"  if char == "<" else " "
            j = i + 1
            while j < len(string):
                c = string[j]
                if ord(c) >= 128 or c in SPACELIST or c == sep:
                    break
                j += 1
            if j < len(string) and string[j] == ">":
                j += 1
            res.append(string[i:j])
            i = j
    return res


def tokenize(text: str, tochar: bool):
    """Tokenise text; returns list of upper-cased tokens."""
    if tochar:
        tokens = characterize(text)
    else:
        tokens = text.strip().split()
    return [t.upper() for t in tokens]


def entity_tokens(entities, tochar: bool):
    """Return a flat set of tokens from all entity strings."""
    tokens = set()
    for e in entities:
        tokens.update(tokenize(e, tochar))
    return tokens


# ---------------------------------------------------------------------------
# Edit-distance calculator (from wer.py, simplified)
# ---------------------------------------------------------------------------

class Calculator:
    def __init__(self):
        self.data = {}
        self.space = []
        self.cost = {"cor": 0, "sub": 1, "del": 1, "ins": 1}

    def calculate(self, lab, rec):
        lab = [""] + lab
        rec = [""] + rec
        while len(self.space) < len(lab):
            self.space.append([])
        for row in self.space:
            for element in row:
                element["dist"] = 0
                element["error"] = "non"
            while len(row) < len(rec):
                row.append({"dist": 0, "error": "non"})
        for i in range(len(lab)):
            self.space[i][0]["dist"] = i
            self.space[i][0]["error"] = "del"
        for j in range(len(rec)):
            self.space[0][j]["dist"] = j
            self.space[0][j]["error"] = "ins"
        self.space[0][0]["error"] = "non"

        for token in lab + rec:
            if token and token not in self.data:
                self.data[token] = {"all": 0, "cor": 0, "sub": 0, "ins": 0, "del": 0}

        for i, lab_token in enumerate(lab):
            for j, rec_token in enumerate(rec):
                if i == 0 or j == 0:
                    continue
                min_dist = sys.maxsize
                min_error = "none"
                for dist, error in [
                    (self.space[i-1][j]["dist"] + self.cost["del"], "del"),
                    (self.space[i][j-1]["dist"] + self.cost["ins"], "ins"),
                ]:
                    if dist < min_dist:
                        min_dist, min_error = dist, error
                if lab_token == rec_token.replace("<BIAS>", ""):
                    dist = self.space[i-1][j-1]["dist"] + self.cost["cor"]
                    error = "cor"
                else:
                    dist = self.space[i-1][j-1]["dist"] + self.cost["sub"]
                    error = "sub"
                if dist < min_dist:
                    min_dist, min_error = dist, error
                self.space[i][j]["dist"] = min_dist
                self.space[i][j]["error"] = min_error

        result = {"lab": [], "rec": [], "code": [],
                  "all": 0, "cor": 0, "sub": 0, "ins": 0, "del": 0}
        i, j = len(lab) - 1, len(rec) - 1
        while True:
            err = self.space[i][j]["error"]
            if err == "cor":
                if lab[i]:
                    self._update(lab[i], "cor")
                    result["all"] += 1; result["cor"] += 1
                result["lab"].insert(0, lab[i])
                result["rec"].insert(0, rec[j])
                result["code"].insert(0, Code.match)
                i -= 1; j -= 1
            elif err == "sub":
                if lab[i]:
                    self._update(lab[i], "sub")
                    result["all"] += 1; result["sub"] += 1
                result["lab"].insert(0, lab[i])
                result["rec"].insert(0, rec[j])
                result["code"].insert(0, Code.substitution)
                i -= 1; j -= 1
            elif err == "del":
                if lab[i]:
                    self._update(lab[i], "del")
                    result["all"] += 1; result["del"] += 1
                result["lab"].insert(0, lab[i])
                result["rec"].insert(0, "")
                result["code"].insert(0, Code.deletion)
                i -= 1
            elif err == "ins":
                if rec[j]:
                    self.data.setdefault(rec[j], {"all": 0, "cor": 0, "sub": 0, "ins": 0, "del": 0})
                    self.data[rec[j]]["ins"] += 1
                    result["ins"] += 1
                result["lab"].insert(0, "")
                result["rec"].insert(0, rec[j])
                result["code"].insert(0, Code.insertion)
                j -= 1
            elif err == "non":
                break
        return result

    def _update(self, token, err_type):
        if token not in self.data:
            self.data[token] = {"all": 0, "cor": 0, "sub": 0, "ins": 0, "del": 0}
        self.data[token]["all"] += 1
        self.data[token][err_type] += 1

    def overall(self):
        result = {"all": 0, "cor": 0, "sub": 0, "ins": 0, "del": 0}
        for token in self.data:
            for k in result:
                result[k] += self.data[token].get(k, 0)
        return result


# ---------------------------------------------------------------------------
# WER accumulator
# ---------------------------------------------------------------------------

class WordError:
    def __init__(self):
        self.errors = {Code.substitution: 0, Code.insertion: 0, Code.deletion: 0}
        self.ref_words = 0

    def get_wer(self):
        if self.ref_words == 0:
            return 0.0
        errs = sum(self.errors.values())
        return 100.0 * errs / self.ref_words

    def __str__(self):
        return (
            f"WER={self.get_wer():.4f}%, "
            f"ref={self.ref_words}, "
            f"sub={self.errors[Code.substitution]}, "
            f"ins={self.errors[Code.insertion]}, "
            f"del={self.errors[Code.deletion]}"
        )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_ref(result_dir: str, domain: str):
    """
    Load entity-annotated reference for a domain.
    Returns: dict {(audio_name, start, end): {"text": str, "entities": list}}
    """
    domain_dir = os.path.join(result_dir, domain)
    if not os.path.isdir(domain_dir):
        return {}
    ref = {}
    for fname in os.listdir(domain_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(domain_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        audio_name = data["audio_name"]
        for seg in data.get("segments", []):
            if seg.get("status") != "valid":
                continue
            key = (audio_name, seg["start"], seg["end"])
            ref[key] = {
                "text": seg.get("text", ""),
                "entities": seg.get("entities", []),
            }
    return ref


def extract_audio_name(item: dict) -> str:
    """
    Extract the bare audio name (no extension, no directory) from a hyp item.
    Handles several field naming conventions used by different models:
      - item["audio_name"]: may be "AGR-CH#foo#bar.wav" or a full path
      - item["audio_path"]: full Windows/Linux path
    """
    raw = item.get("audio_name") or item.get("audio_path") or ""
    # strip directory components (handles both '/' and '\\')
    raw = raw.replace("\\", "/")
    raw = raw.split("/")[-1]
    # strip extension
    if "." in raw:
        raw = raw.rsplit(".", 1)[0]
    return raw


def load_hyp(hyp_dir: str, domain: str, model: str):
    """
    Load hypothesis for a domain+model combination.
    model='azure' corresponds to file {domain}.json; others: {domain}_{model}.json
    Returns: dict {(audio_name, start, end): str}, or None if file not found.
    """
    if model == "azure":
        fname = f"{domain}.json"
    else:
        fname = f"{domain}_{model}.json"
    fpath = os.path.join(hyp_dir, fname)
    if not os.path.isfile(fpath):
        return None
    hyp = {}
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        audio_name = extract_audio_name(item)
        # handle both start_time/end_time and start/end field names
        start = item.get("start_time") if "start_time" in item else item.get("start")
        end = item.get("end_time") if "end_time" in item else item.get("end")
        if start is None or end is None:
            continue
        key = (audio_name, start, end)
        hyp[key] = item.get("text", "")
    return hyp


def detect_language(domain: str) -> bool:
    """Return True (tochar=True) for Chinese domains, False for English."""
    return domain.upper().endswith("-CH")


# ---------------------------------------------------------------------------
# Per-domain evaluation
# ---------------------------------------------------------------------------

def evaluate_domain(ref: dict, hyp: dict, tochar: bool, verbose: bool = False):
    """
    Evaluate one domain's ref vs hyp.
    Returns stats dict.
    """
    calc = Calculator()
    wer_acc = WordError()
    u_wer_acc = WordError()
    b_wer_acc = WordError()
    hotword = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    n_matched_segs = 0
    n_skipped_segs = 0

    for key, ref_info in ref.items():
        if key not in hyp:
            n_skipped_segs += 1
            continue
        n_matched_segs += 1
        audio_name, start, end = key

        lab = tokenize(ref_info["text"], tochar)
        rec = tokenize(hyp[key], tochar)

        # build hotword token set from entities
        hot_set = entity_tokens(ref_info["entities"], tochar)
        # only keep hotword tokens that actually appear in label
        hot_true_list = {t for t in hot_set if t in set(lab)}
        # bad hotwords: in entity list but NOT in label
        hot_bad_list = hot_set - hot_true_list

        # compute edit distance
        result = calc.calculate(lab.copy(), rec.copy())

        if verbose:
            seg_id = f"{audio_name}[{start:.2f},{end:.2f}]"
            if result["all"] != 0:
                seg_wer = (result["ins"] + result["sub"] + result["del"]) * 100.0 / result["all"]
            else:
                seg_wer = 0.0
            print(f"\n{seg_id}  WER={seg_wer:.2f}%")
            print(f"  ref: {' '.join(lab)}")
            print(f"  hyp: {' '.join(rec)}")
            print(f"  entities: {ref_info['entities']}")

        # accumulate U-WER / B-WER
        rec_tokens = [w.replace("<BIAS>", "") for w in rec]
        for code, rec_word, lab_word in zip(result["code"], result["rec"], result["lab"]):
            if code == Code.match:
                wer_acc.ref_words += 1
                if lab_word in hot_true_list:
                    b_wer_acc.ref_words += 1
                else:
                    u_wer_acc.ref_words += 1
            elif code == Code.substitution:
                wer_acc.ref_words += 1
                wer_acc.errors[Code.substitution] += 1
                if lab_word in hot_true_list:
                    b_wer_acc.ref_words += 1
                    b_wer_acc.errors[Code.substitution] += 1
                else:
                    u_wer_acc.ref_words += 1
                    u_wer_acc.errors[Code.substitution] += 1
            elif code == Code.deletion:
                wer_acc.ref_words += 1
                wer_acc.errors[Code.deletion] += 1
                if lab_word in hot_true_list:
                    b_wer_acc.ref_words += 1
                    b_wer_acc.errors[Code.deletion] += 1
                else:
                    u_wer_acc.ref_words += 1
                    u_wer_acc.errors[Code.deletion] += 1
            elif code == Code.insertion:
                wer_acc.errors[Code.insertion] += 1
                if rec_word in hot_true_list:
                    b_wer_acc.errors[Code.insertion] += 1
                else:
                    u_wer_acc.errors[Code.insertion] += 1

        # accumulate hotword recall stats
        for bad_hw in hot_bad_list:
            count = rec_tokens.count(bad_hw)
            if count == 0:
                hotword["tn"] += 1
            else:
                hotword["fp"] += count

        for hw in hot_true_list:
            true_cnt = lab.count(hw)
            rec_cnt = rec_tokens.count(hw)
            if rec_cnt >= true_cnt:
                hotword["tp"] += true_cnt
                hotword["fp"] += rec_cnt - true_cnt
            else:
                hotword["tp"] += rec_cnt
                hotword["fn"] += true_cnt - rec_cnt

    overall = calc.overall()
    recall = (hotword["tp"] / (hotword["tp"] + hotword["fn"]) * 100
              if hotword["tp"] + hotword["fn"] > 0 else 0.0)

    return {
        "n_matched": n_matched_segs,
        "n_skipped": n_skipped_segs,
        "wer": wer_acc,
        "u_wer": u_wer_acc,
        "b_wer": b_wer_acc,
        "hotword": hotword,
        "recall": recall,
        "overall": overall,
    }


def print_domain_result(domain: str, model: str, stats: dict):
    o = stats["overall"]
    wer_val = (o["ins"] + o["sub"] + o["del"]) * 100.0 / o["all"] if o["all"] else 0.0
    hw = stats["hotword"]
    print(f"\n{'='*70}")
    print(f"Domain: {domain}  Model: {model}")
    print(f"  Segments matched: {stats['n_matched']}  skipped: {stats['n_skipped']}")
    print(f"  WER:   {wer_val:.4f}%  "
          f"N={o['all']} C={o['cor']} S={o['sub']} D={o['del']} I={o['ins']}")
    print(f"  WER:   {stats['wer']}")
    print(f"  U-WER: {stats['u_wer']}")
    print(f"  B-WER: {stats['b_wer']}")
    print(f"  Hotword: tp={hw['tp']} tn={hw['tn']} fp={hw['fp']} fn={hw['fn']}  "
          f"recall={stats['recall']:.2f}%")
    print(f"  >> {stats['wer'].get_wer():.3f}; "
          f"{stats['u_wer'].get_wer():.3f}; "
          f"{stats['b_wer'].get_wer():.3f}; "
          f"{stats['recall']:.2f}%")


# ---------------------------------------------------------------------------
# Aggregate across domains
# ---------------------------------------------------------------------------

def aggregate(stats_list):
    """Sum up stats across multiple domain results."""
    agg_wer = WordError()
    agg_u_wer = WordError()
    agg_b_wer = WordError()
    agg_hw = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}

    for s in stats_list:
        for code in [Code.substitution, Code.insertion, Code.deletion]:
            agg_wer.errors[code] += s["wer"].errors[code]
            agg_u_wer.errors[code] += s["u_wer"].errors[code]
            agg_b_wer.errors[code] += s["b_wer"].errors[code]
        agg_wer.ref_words += s["wer"].ref_words
        agg_u_wer.ref_words += s["u_wer"].ref_words
        agg_b_wer.ref_words += s["b_wer"].ref_words
        for k in agg_hw:
            agg_hw[k] += s["hotword"][k]

    recall = (agg_hw["tp"] / (agg_hw["tp"] + agg_hw["fn"]) * 100
              if agg_hw["tp"] + agg_hw["fn"] > 0 else 0.0)
    return {
        "wer": agg_wer, "u_wer": agg_u_wer, "b_wer": agg_b_wer,
        "hotword": agg_hw, "recall": recall,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def get_args():
    parser = argparse.ArgumentParser(description="Hotword WER evaluation")
    parser.add_argument(
        "--result_dir",
        default=None,
        help="Directory with entity-annotated reference JSONs (one subdir per domain)",
    )
    parser.add_argument(
        "--hyp_dir",
        default=None,
        help="Directory with hypothesis JSON files",
    )
    parser.add_argument(
        "--out_dir",
        default=None,
        help="Output directory for hotword results (default: <base>/data/results_hotword)",
    )
    parser.add_argument(
        "--domain",
        nargs="*",
        default=None,
        help="Domain(s) to evaluate, e.g. AGR-CH AGR-EN. Default: all available.",
    )
    parser.add_argument(
        "--model",
        nargs="*",
        default=None,
        help="Model(s) to evaluate, e.g. azure Gemini. Default: all available.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-segment details",
    )
    return parser.parse_args()


def discover_domains(result_dir: str, hyp_dir: str):
    """Return sorted list of domains present in both result_dir and hyp_dir."""
    result_domains = set(os.listdir(result_dir)) if os.path.isdir(result_dir) else set()
    hyp_domains = set()
    for fname in os.listdir(hyp_dir):
        if fname.endswith(".json"):
            domain = fname.replace(".json", "").split("_")[0]
            hyp_domains.add(domain)
    return sorted(result_domains & hyp_domains)


def discover_models(hyp_dir: str, domain: str):
    """Return list of models available for a domain."""
    models = []
    for fname in os.listdir(hyp_dir):
        if not fname.endswith(".json"):
            continue
        base = fname.replace(".json", "")
        if base == domain:
            models.append("azure")
        elif base.startswith(domain + "_"):
            models.append(base[len(domain) + 1:])
    return sorted(models)


def main():
    args = get_args()

    # resolve defaults relative to script location
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_root = os.environ.get("DATA_ROOT",
        "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark")

    result_dir = args.result_dir or os.path.join(data_root, "Vertical-Domain", "text", "entity_ref")
    hyp_dir = args.hyp_dir or os.path.join(data_root, "Vertical-Domain", "text", "hyp")
    out_dir = args.out_dir or os.path.join(base_dir, "data", "results_hotword")
    os.makedirs(out_dir, exist_ok=True)

    # determine domains to evaluate
    if args.domain:
        domains = args.domain
    else:
        domains = discover_domains(result_dir, hyp_dir)
    if not domains:
        print("No matching domains found.", file=sys.stderr)
        sys.exit(1)

    # collect per-model aggregated stats
    model_agg = defaultdict(list)
    # table for Excel: {model: {domain: {"wer":..., "u_wer":..., "b_wer":..., "recall":...}}}
    excel_data = defaultdict(dict)

    for domain in domains:
        tochar = detect_language(domain)
        ref = load_ref(result_dir, domain)
        if not ref:
            print(f"[WARN] No ref data for domain {domain}, skipping.", file=sys.stderr)
            continue

        models = args.model if args.model else discover_models(hyp_dir, domain)
        for model in models:
            hyp = load_hyp(hyp_dir, domain, model)
            if hyp is None:
                continue
            stats = evaluate_domain(ref, hyp, tochar, verbose=args.verbose)
            print_domain_result(domain, model, stats)
            model_agg[model].append(stats)

            # Save per-domain per-model results
            m_dir = os.path.join(out_dir, domain, model.upper())
            os.makedirs(m_dir, exist_ok=True)
            hw = stats["hotword"]
            with open(os.path.join(m_dir, "hotword_result.txt"), "w", encoding="utf8") as f:
                f.write(f"wer={stats['wer'].get_wer():.4f}\n")
                f.write(f"u_wer={stats['u_wer'].get_wer():.4f}\n")
                f.write(f"b_wer={stats['b_wer'].get_wer():.4f}\n")
                f.write(f"recall={stats['recall']:.4f}\n")
                f.write(f"tp={hw['tp']}\n")
                f.write(f"tn={hw['tn']}\n")
                f.write(f"fp={hw['fp']}\n")
                f.write(f"fn={hw['fn']}\n")
                f.write(f"matched_segments={stats['n_matched']}\n")
                f.write(f"skipped_segments={stats['n_skipped']}\n")

            excel_data[model][domain] = {
                "wer": stats["wer"].get_wer(),
                "u_wer": stats["u_wer"].get_wer(),
                "b_wer": stats["b_wer"].get_wer(),
                "recall": stats["recall"],
            }

    # print per-model aggregate
    if len(domains) > 1:
        print(f"\n{'='*70}")
        print("AGGREGATE (all domains)")
        for model, stats_list in sorted(model_agg.items()):
            agg = aggregate(stats_list)
            hw = agg["hotword"]
            print(f"\n  Model: {model}  ({len(stats_list)} domains)")
            print(f"  WER:   {agg['wer']}")
            print(f"  U-WER: {agg['u_wer']}")
            print(f"  B-WER: {agg['b_wer']}")
            print(f"  Hotword: tp={hw['tp']} tn={hw['tn']} fp={hw['fp']} fn={hw['fn']}  "
                  f"recall={agg['recall']:.2f}%")
            print(f"  >> {agg['wer'].get_wer():.3f}; "
                  f"{agg['u_wer'].get_wer():.3f}; "
                  f"{agg['b_wer'].get_wer():.3f}; "
                  f"{agg['recall']:.2f}%")

    # Write Excel with 4 sheets: WER, U-WER, B-WER, Recall
    write_hotword_excel(out_dir, excel_data, domains)


def write_hotword_excel(out_dir, excel_data, domains):
    """Write hotword results to Excel with 4 sheets."""
    try:
        import pandas as pd
        from openpyxl.styles import Font, Alignment
    except ImportError:
        print("[WARN] pandas/openpyxl not available, skipping Excel output.")
        return

    metrics = ["wer", "u_wer", "b_wer", "recall"]
    sheet_names = {"wer": "WER", "u_wer": "U-WER", "b_wer": "B-WER", "recall": "Recall"}

    out_xlsx = os.path.join(out_dir, "hotword_results.xlsx")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        for metric in metrics:
            table = {}
            for model, domain_stats in excel_data.items():
                row = {}
                for domain in domains:
                    if domain in domain_stats:
                        row[domain] = round(domain_stats[domain][metric], 2)
                    else:
                        row[domain] = "-"
                table[model] = row
            df = pd.DataFrame.from_dict(table, orient="index")
            if not df.empty:
                df = df.reindex(columns=[d for d in domains if d in df.columns])
                # Add MIN row
                min_vals = {}
                for col in df.columns:
                    numeric = pd.to_numeric(df[col], errors="coerce")
                    if numeric.notna().any():
                        min_vals[col] = numeric.min()
                    else:
                        min_vals[col] = "-"
                df = pd.concat([df, pd.DataFrame(min_vals, index=["MIN"])])
            df.to_excel(writer, sheet_name=sheet_names[metric])

            # Style
            ws = writer.sheets[sheet_names[metric]]
            bold_font = Font(bold=True)
            center = Alignment(horizontal="center", vertical="center")
            for cell in ws[1]:
                cell.font = bold_font
                cell.alignment = center
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
                for cell in row:
                    cell.alignment = center
            for cell in ws[ws.max_row]:
                cell.font = bold_font
            for col_cells in ws.columns:
                max_len = max(len(str(c.value or "")) for c in col_cells)
                ws.column_dimensions[col_cells[0].column_letter].width = max_len + 3

    print(f"\n✅ Hotword Excel -> {out_xlsx}")


if __name__ == "__main__":
    main()
