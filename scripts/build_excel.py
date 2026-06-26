#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Strict non-batch Excel generation script (with CLI arguments)

- Scans results_root/<COUNTRY>/<MODEL>/
- Strict model whitelist
- Outputs a single Excel (WER / CER)
- Supports specifying RESULTS_ROOT, REF_ROOT, EXCEL_COUNTRIES via command line
"""

import os
import re
import json
import pandas as pd
import argparse

# =========================
# Default model whitelist
# =========================
COVERAGE_MODELS = {
    "AZURE","CHIRP3","CHIRP-3","DOLPHIN_SMALL","DOLPHIN-SMALL","DOLPHIN_BASE","DOLPHIN-BASE",
    "ELEVENLABS_SCRIBE_V2","ELEVENLABS-SCRIBE-V2","FUN-ASR-MLT-NANO","FUNASR-MLT-NANO",
    "GEMINI_3_0_FLASH","GEMINI-3.0-FLASH","GPT4O-TRANSCRIBE","GPT-4O-TRANSCRIBE",
    "OMNIASR_LLM_3B","META-OMNIASR-3B","QWEN3-ASR-FLASH",
    "NVIDIA-NEMO","WHISPER","WHISPER-LARGE-V3",
    "GEMINI","GEMINI-3-FLASH-PREVIEW","QWEN3-ASR-1.7B","FUN-ASR-NANO","SEEDASR",
    "FUN-ASR","QWEN3.5-OMNI-FLASH","QWEN3.5-OMNI-PLUS","FUNASR_V1.5","FUNASR-REALTIME",
    "BIGASR","DEEPGRAM_NOVA3","DEEPGRAM-NOVA-3"
}

# Model display order (display_name, {internal_names...})
MODEL_ORDER = [
    ("Azure",                   {"AZURE"}),
    ("Chirp 3",                 {"CHIRP3", "CHIRP-3"}),
    ("ElevenLabs Scribe v2",    {"ELEVENLABS_SCRIBE_V2", "ELEVENLABS-SCRIBE-V2"}),
    ("Meta OmniASR 3B",         {"OMNIASR_LLM_3B", "META-OMNIASR-3B"}),
    ("Qwen3-ASR-Flash",         {"QWEN3-ASR-FLASH"}),
    ("Qwen3-ASR-1.7B",          {"QWEN3-ASR-1.7B"}),
    ("NVIDIA NeMo",             {"NVIDIA-NEMO"}),
    ("GPT-4o Transcribe",       {"GPT4O-TRANSCRIBE", "GPT-4O-TRANSCRIBE"}),
    ("Gemini 3.0 Flash",        {"GEMINI_3_0_FLASH", "GEMINI-3-FLASH-PREVIEW", "GEMINI", "GEMINI-3.0-FLASH"}),
    ("Whisper Large v3",        {"WHISPER", "WHISPER-LARGE-V3"}),
    ("Dolphin Small",           {"DOLPHIN_SMALL", "DOLPHIN-SMALL"}),
    ("Dolphin Base",            {"DOLPHIN_BASE", "DOLPHIN-BASE"}),
    ("FunASR-MLT-Nano",         {"FUN-ASR-MLT-NANO", "FUN-ASR-NANO", "FUNASR-MLT-NANO"}),
    ("FunASR-Realtime",         {"FUNASR-REALTIME", "FUN-ASR", "FUNASR_V1.5"}),
    ("Qwen3.5-Omni-Plus",       {"QWEN3.5-OMNI-PLUS", "QWEN3.5-OMNI-FLASH"}),
    ("BigASR",                  {"BIGASR"}),
    ("SeedASR",                 {"SEEDASR"}),
    ("Deepgram Nova 3",         {"DEEPGRAM_NOVA3", "DEEPGRAM-NOVA-3"}),
]

def _build_internal_to_display():
    """internal name -> display name"""
    m = {}
    for display, internals in MODEL_ORDER:
        for i in internals:
            m[i] = display
    return m

_INT2DISP = _build_internal_to_display()
_DISP_ORDER = [d for d, _ in MODEL_ORDER]

# =========================
# Utility functions
# =========================
def extract_value(path: str):
    """Extract %WER/CER from err* file"""
    try:
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("%WER"):
                    m = re.search(r"%WER\s*=\s*([0-9]+(?:\.[0-9]+)?)", line)
                    if m:
                        return float(m.group(1))
        return "-"
    except Exception:
        return "-"

def normalize_model_name(model: str):
    # Strip 3-letter country prefix (e.g. ARE_, DZA_) but NOT model names like FUNASR_
    # Only strip if the prefix looks like a country code followed by a known model
    m = re.match(r"^([A-Z]{3})_(.+)$", model)
    if m:
        prefix, rest = m.group(1), m.group(2)
        # Check if rest (after stripping prefix) is a known model
        if rest in COVERAGE_MODELS:
            return rest
    return model

def pick_err_file(m_dir: str):
    if not os.path.isdir(m_dir):
        return None
    names = [n for n in os.listdir(m_dir) if os.path.isfile(os.path.join(m_dir, n))]
    if not names:
        return None
    err = [n for n in names if n.lower().startswith("err")]
    if err:
        txts = [n for n in err if n.lower().endswith(".txt")]
        return os.path.join(m_dir, sorted(txts or err)[0])
    txts = sorted(n for n in names if n.lower().endswith(".txt"))
    return os.path.join(m_dir, txts[0]) if txts else None

# =========================
# Scan results
# =========================
def _is_fully_matched(m_dir: str) -> bool:
    """Check segment_check.txt: return True only if matched == ref."""
    seg_path = os.path.join(m_dir, "segment_check.txt")
    if not os.path.isfile(seg_path):
        return False
    vals = {}
    try:
        with open(seg_path, "r", encoding="utf8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    vals[k] = v
        ref_n = int(vals.get("ref_segments", -1))
        matched_n = int(vals.get("matched_segments", -2))
        return ref_n == matched_n
    except Exception:
        return False

def scan_results(results_root: str, excel_countries, matched_only: bool = False):
    table = {}
    for country in excel_countries:
        c_dir = os.path.join(results_root, country)
        if not os.path.isdir(c_dir):
            continue
        for model in os.listdir(c_dir):
            m_dir = os.path.join(c_dir, model)
            if not os.path.isdir(m_dir):
                continue
            model_clean = normalize_model_name(model)
            if model_clean not in COVERAGE_MODELS:
                continue
            if matched_only and not _is_fully_matched(m_dir):
                continue
            err_path = pick_err_file(m_dir)
            if not err_path:
                continue
            val = extract_value(err_path)
            # Map to display name, merge models with same display name into one row
            display = _INT2DISP.get(model_clean, model_clean)
            table.setdefault(display, {})[country] = val
    df = pd.DataFrame.from_dict(table, orient="index")
    df = df.reindex(columns=excel_countries)
    # Strictly sort by MODEL_ORDER, all models must appear (show "-" if no data)
    df = df.reindex(_DISP_ORDER)
    return df.fillna("-")

# =========================
# REF segment count statistics
# =========================
def load_ref_counts(ref_root: str):
    """Load ref segment counts: total and valid (non-empty text)."""
    ref_count = {}
    ref_valid_count = {}
    for fn in os.listdir(ref_root):
        if not fn.endswith(".json"):
            continue
        country = fn[:-5]
        path = os.path.join(ref_root, fn)
        try:
            with open(path, "r", encoding="utf8") as f:
                data = json.load(f)
            if isinstance(data, list):
                ref_count[country] = len(data)
                ref_valid_count[country] = sum(1 for d in data if d.get("text", "").strip())
        except Exception:
            continue
    return ref_count, ref_valid_count


def scan_matched_counts(results_root: str, excel_countries):
    """Scan segment_check.txt to build matched segment count table."""
    table = {}
    for country in excel_countries:
        c_dir = os.path.join(results_root, country)
        if not os.path.isdir(c_dir):
            continue
        for model in os.listdir(c_dir):
            m_dir = os.path.join(c_dir, model)
            if not os.path.isdir(m_dir):
                continue
            model_clean = normalize_model_name(model)
            if model_clean not in COVERAGE_MODELS:
                continue
            seg_path = os.path.join(m_dir, "segment_check.txt")
            if not os.path.isfile(seg_path):
                continue
            vals = {}
            try:
                with open(seg_path, "r", encoding="utf8") as f:
                    for line in f:
                        if "=" in line:
                            k, v = line.strip().split("=", 1)
                            vals[k] = v
                matched_n = int(vals.get("matched_segments", 0))
            except Exception:
                continue
            display = _INT2DISP.get(model_clean, model_clean)
            table.setdefault(display, {})[country] = matched_n
    df = pd.DataFrame.from_dict(table, orient="index")
    df = df.reindex(columns=excel_countries)
    df = df.reindex(_DISP_ORDER)
    return df.fillna(0).astype(int)


def normalize_excel_countries(raw_countries):
    """Accept both space-separated and comma-separated country lists."""
    out = []
    for item in raw_countries:
        if item is None:
            continue
        for token in str(item).split(","):
            token = token.strip()
            if token:
                out.append(token)
    # Keep stable order while removing duplicates.
    return list(dict.fromkeys(out))

# =========================
# Main entry
# =========================
def main(results_root: str, ref_root: str, excel_countries, skip_existing: bool = False, matched_only: bool = False):
    print(f"📂 Scanning results directory: {results_root}")
    if matched_only:
        print("🔒 matched_only mode: only writing results where ref==matched")
    ref_count, ref_valid_count = load_ref_counts(ref_root)
    df = scan_results(results_root, excel_countries, matched_only=matched_only)

    # Build ref valid segments row
    ref_valid_row = pd.DataFrame(
        {c: [ref_valid_count.get(c, 0)] for c in excel_countries},
        index=["Ref Valid Segments"]
    )

    # WER/CER Excel with ref valid segments row on top
    out_xlsx = os.path.join(results_root, "results.xlsx")
    if skip_existing and os.path.exists(out_xlsx):
        print(f"⏭️ Skip existing Excel: {out_xlsx}")
    else:
        df_wer = pd.concat([ref_valid_row, df])
        df_wer.to_excel(out_xlsx)
        print(f"✔️ WER/CER Excel → {out_xlsx}")

    # Count Excel: matched segments per model per country, with ref valid on top
    out_count_xlsx = os.path.join(results_root, "results_count.xlsx")
    if skip_existing and os.path.exists(out_count_xlsx):
        print(f"⏭️ Skip existing Count Excel: {out_count_xlsx}")
    else:
        df_count = scan_matched_counts(results_root, excel_countries)
        ref_valid_row_int = pd.DataFrame(
            {c: [ref_valid_count.get(c, 0)] for c in excel_countries},
            index=["Ref Valid Segments"]
        )
        df_count_out = pd.concat([ref_valid_row_int, df_count])
        df_count_out.to_excel(out_count_xlsx)
        print(f"✔️ Count Excel → {out_count_xlsx}")

    print("\n📊 Ref segment count statistics:")
    for c, n in sorted(ref_count.items()):
        valid = ref_valid_count.get(c, 0)
        print(f"  {c}: total={n}, valid={valid}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strict non-batch Excel generator")
    parser.add_argument("--results_root", type=str, required=True)
    parser.add_argument("--ref_root", type=str, required=True)
    parser.add_argument("--excel_countries", type=str, nargs="+", required=True,
                        help="List of countries/regions to generate Excel for, e.g. AGR-CH AIT-CH ...")
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=0,
                        help="1: skip existing Excel; 0: overwrite")
    parser.add_argument("--matched_only", type=int, choices=[0, 1], default=0,
                        help="1: only include fully matched (ref==matched) results; 0: include all")
    args = parser.parse_args()
    excel_countries = normalize_excel_countries(args.excel_countries)
    main(args.results_root, args.ref_root, excel_countries, bool(args.skip_existing), bool(args.matched_only))