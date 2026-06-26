#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Single-batch ASR evaluation script (with CLI arguments)

- Supports specifying REF/HYP/OUT root directories via command line
- Single batch
- Model name from hyp item["model"]
- audio_name strips .wav
- Outputs ref/hyp/matched segment count consistency check
- Supports automatic WER/CER detection
"""

import os
import json
import logging
from pathlib import Path
from collections import defaultdict
import kaldialign
import gc
import argparse
from multiprocessing import Pool, cpu_count

# =========================
# Logging
# =========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# =========================
# Constants
# =========================
WER_LANGS = ["IRQ","DZA","ARE","EGY","MAR","SAU","IDN","MYS","PHL","PHL_EN","PHL_noEN","VNM","SYR","USA",
             "CHN-EN","IDN-EN","JPN-EN","PHL-EN","SCT-EN","SGP-EN","AGR-EN","AIT-EN",
             "ART-EN","BIO-EN","ECM-EN","EDU-EN","ENG-EN","ENT-EN","FIN-EN","HUM-EN",
             "LAW-EN","MED-EN","MIL-EN"]
CER_LANGS = ["JPN","JPN_hard","KOR","KOR_hard","THA","CHN","GAN","JIN","XIANG","YUE","WU",
             "MIN","AGR-CH","AIT-CH","ART-CH","BIO-CH","ECM-CH","EDU-CH","ENG-CH","ENT-CH",
             "FIN-CH","HUM-CH","LAW-CH","MED-CH","MIL-CH","CHILD-CH","OLD-CH"]

def is_cer_lang(country):
    """Check if country should use CER. Matches exact or prefix (e.g. JPN_0502 -> JPN)."""
    if country in CER_LANGS:
        return True
    for cl in CER_LANGS:
        if country.startswith(cl + "_") and cl + "_" != country[:len(cl)+1] + "hard":
            return True
    # Simple prefix check for base lang
    base = country.split("_")[0]
    if base in CER_LANGS:
        return True
    return False

ERR = "*"
MATCH_TOL = 0.1

# =========================
# Utility functions
# =========================
def norm_audio_name(name: str) -> str:
    """Normalize audio ids for robust ref/hyp matching."""
    name = name.replace("\\", "/")
    base = os.path.basename(name)
    changed = True
    while changed:
        changed = False
        for ext in [".wav", ".mp3", ".mp4", ".webm"]:
            if base.lower().endswith(ext):
                base = base[:-len(ext)]
                changed = True
                break
    # Normalize legacy suffix in some refs/hyps (e.g. "...#raw") so keys align.
    if base.endswith("#raw"):
        base = base[:-4]

    # Normalize underscore-style ids to hash-style:
    # ARE_UCxxxx_yyyy_raw -> ARE#UCxxxx#yyyy
    # ARE_UCxxxx__N1S84_raw -> ARE#UCxxxx#_N1S84 (double _ means video starts with _)
    if "#" not in base:
        # Strip _raw suffix for legacy format
        if base.endswith("_raw"):
            base = base[:-4]
        parts = base.split("_")
        if len(parts) >= 3 and len(parts[0]) == 3 and parts[0].isalpha():
            lang = parts[0]
            channel = parts[1]
            video = "_".join(parts[2:])
            base = f"{lang}#{channel}#{video}"
    return base.lower()


def fmt_seg(seg):
    if not seg:
        return ""
    audio = str(seg.get("audio_name", "")).replace("\t", " ").replace("\n", " ")
    start = seg.get("start", "")
    end = seg.get("end", "")
    text = str(seg.get("text", "")).replace("\t", " ").replace("\n", " ").strip()
    return f"audio_name={audio}; start={start}; end={end}; text={text}"

def make_seg_key(audio_name, start):
    """Unique key for a segment: (normalized_audio_name, start_time)."""
    return f"{norm_audio_name(audio_name)}|{float(start):.3f}"


def load_seg_cache(cache_path):
    """Load per-segment alignment cache from JSON. Returns dict keyed by seg_key."""
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        return {it["key"]: it for it in items}
    except Exception:
        return {}


def save_seg_cache(cache_path, cache_list):
    """Save per-segment alignment results as JSON list."""
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_list, f, ensure_ascii=False)


def process_one_ref_hyp(ref_items, hyp_items, compute_CER, recogs_f, stats, seg_cache=None):
    """Match ref/hyp and compute alignment. Uses seg_cache to skip unchanged segments."""
    if seg_cache is None:
        seg_cache = {}

    hyp_index = defaultdict(list)
    hyp_records = []
    for i, h in enumerate(hyp_items):
        name = norm_audio_name(h.get("audio_name", ""))
        start = float(h.get("start", 0) or 0)
        end = float(h.get("end", 0) or 0)
        rec = {
            "idx": i,
            "audio_name": h.get("audio_name", ""),
            "start": start,
            "end": end,
            "text": h.get("text", ""),
            "matched": False,
        }
        hyp_records.append(rec)
        hyp_index[name].append(rec)

    valid = 0
    dur_sec = 0.0
    first_unmatched_ref = None
    new_cache_list = []
    cache_hits = 0
    # Dye mechanism: record original identifiers of matched ref/hyp segments.
    matched_pairs = []

    for r in ref_items:
        # Skip segments whose normalized ref text is empty (e.g. pure filler
        # words like "# Uh." that become "" after normalization). Such empty
        # refs would otherwise count every hyp token as an insertion error.
        if not str(r.get("text", "")).strip():
            continue

        name = norm_audio_name(r["audio_name"])
        start_ref = float(r["start"])
        end_ref = float(r["end"])

        if name not in hyp_index:
            if first_unmatched_ref is None:
                first_unmatched_ref = {
                    "audio_name": r.get("audio_name", ""),
                    "start": r.get("start", ""),
                    "end": r.get("end", ""),
                    "text": r.get("text", ""),
                }
            continue

        hyp_match = None
        best_score = None
        for cand in hyp_index[name]:
            start_hyp = float(cand["start"])
            end_hyp = float(cand["end"])
            if abs(start_ref - start_hyp) <= MATCH_TOL and abs(end_ref - end_hyp) <= MATCH_TOL:
                score = abs(start_ref - start_hyp) + abs(end_ref - end_hyp)
                if best_score is None or score < best_score:
                    best_score = score
                    hyp_match = cand

        if hyp_match is None:
            if first_unmatched_ref is None:
                first_unmatched_ref = {
                    "audio_name": r.get("audio_name", ""),
                    "start": r.get("start", ""),
                    "end": r.get("end", ""),
                    "text": r.get("text", ""),
                }
            continue
        hyp_match["matched"] = True
        hyp_index[name].remove(hyp_match)
        matched_pairs.append({
            "ref_audio_name": r.get("audio_name", ""),
            "ref_start": float(r["start"]),
            "hyp_audio_name": hyp_match.get("audio_name", ""),
            "hyp_start": float(hyp_match.get("start", 0) or 0),
        })

        valid += 1
        dur_sec += float(r["end"]) - float(r["start"])

        ref_text = r["text"].strip()
        hyp_val = str(hyp_match.get("text", "")).strip()

        ref_tok = ref_text.split()
        hyp_tok = hyp_val.split() if hyp_val else []
        if compute_CER:
            ref_tok = list("".join(ref_tok))
            hyp_tok = list("".join(hyp_tok))

        cut_id = f"{r['audio_name']}_{r['start']}"
        print(f"{cut_id}:\tref={' '.join(ref_tok)}", file=recogs_f)
        print(f"{cut_id}:\thyp={' '.join(hyp_tok)}", file=recogs_f)

        seg_key = make_seg_key(r["audio_name"], r["start"])

        # Check segment cache: reuse if ref_text and hyp_text unchanged
        cached = seg_cache.get(seg_key)
        if cached and cached.get("ref_text") == ref_text and cached.get("hyp_text") == hyp_val:
            seg_stats = cached["stats"]
            cache_hits += 1
        else:
            # Compute alignment
            ali = kaldialign.align(ref_tok, hyp_tok, ERR)
            seg_stats = {"I": 0, "D": 0, "S": 0, "C": 0, "N": 0}
            for a, b in ali:
                if a == ERR:
                    seg_stats["I"] += 1
                elif b == ERR:
                    seg_stats["D"] += 1
                    seg_stats["N"] += 1
                elif a != b:
                    seg_stats["S"] += 1
                    seg_stats["N"] += 1
                else:
                    seg_stats["C"] += 1
                    seg_stats["N"] += 1

        # Accumulate into global stats
        for k in ("I", "D", "S", "C", "N"):
            stats[k] += seg_stats[k]

        # Save to new cache (include duration for filtered computation)
        seg_dur = float(r["end"]) - float(r["start"])
        new_cache_list.append({
            "key": seg_key,
            "ref_text": ref_text,
            "hyp_text": hyp_val,
            "stats": seg_stats,
            "duration": seg_dur,
        })

    first_unmatched_hyp = None
    for rec in hyp_records:
        if not rec["matched"]:
            first_unmatched_hyp = {
                "audio_name": rec.get("audio_name", ""),
                "start": rec.get("start", ""),
                "end": rec.get("end", ""),
                "text": rec.get("text", ""),
            }
            break

    return valid, dur_sec / 3600.0, first_unmatched_ref, first_unmatched_hyp, new_cache_list, cache_hits, matched_pairs

def write_errs_and_summary(out_dir, country, model, stats, compute_CER, suffix=""):
    N = stats["N"]
    err = stats["S"] + stats["D"] + stats["I"]
    wer = 100.0 * err / N if N > 0 else 0.0
    with open(out_dir / f"errs-{country}-{model}{suffix}.txt", "w", encoding="utf8") as f:
        print(f"%WER = {wer:.2f}", file=f)
        print(f"Errors: {stats['I']} insertions, {stats['D']} deletions, {stats['S']} substitutions, over {N} units ({stats['C']} correct)", file=f)
    metric = "cer" if compute_CER else "wer"
    with open(out_dir / f"{metric}-summary-{country}-{model}{suffix}.txt", "w", encoding="utf8") as f:
        print("model\tWER/CER", file=f)
        print(f"{model}\t{wer:.2f}", file=f)


def compute_filtered_stats(cache_list, min_duration):
    """Compute aggregated stats from cache entries where duration > min_duration."""
    stats = defaultdict(int)
    count = 0
    for entry in cache_list:
        dur = entry.get("duration", 0)
        if dur > min_duration:
            for k in ("I", "D", "S", "C", "N"):
                stats[k] += entry["stats"][k]
            count += 1
    return stats, count

def process_country_model(args_tuple):
    """Process a single (country, model) pair. Designed for multiprocessing."""
    country, model, ref_items, hyp_items, OUT_ROOT, compute_CER, min_duration = args_tuple

    stats = defaultdict(int)
    out_dir = Path(OUT_ROOT) / country / model
    seg_path = out_dir / "segment_check.txt"
    cache_path = out_dir / "seg_cache.json"

    # Load existing segment-level cache
    seg_cache = load_seg_cache(cache_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"recogs-{country}-{model}.txt", "w", encoding="utf8") as rec_f:
        valid, dur_h, first_unmatched_ref, first_unmatched_hyp, new_cache_list, cache_hits, matched_pairs = process_one_ref_hyp(
            ref_items, hyp_items, compute_CER, rec_f, stats, seg_cache
        )
    write_errs_and_summary(out_dir, country, model, stats, compute_CER)

    # Dye mechanism: dump matched ref/hyp identifiers when DYE_OUT_DIR is set.
    # Skip the duration-filtered (_mindur) pass so we capture the FULL matched set.
    dye_dir = os.environ.get("DYE_OUT_DIR")
    if dye_dir and "_mindur" not in str(OUT_ROOT):
        os.makedirs(dye_dir, exist_ok=True)
        safe = lambda s: str(s).replace(os.sep, "_")
        dye_path = os.path.join(dye_dir, f"{safe(country)}__{safe(model)}.json")
        with open(dye_path, "w", encoding="utf-8") as df:
            json.dump({"country": country, "model": model, "matched": matched_pairs}, df, ensure_ascii=False)

    # Save segment cache
    save_seg_cache(cache_path, new_cache_list)

    # Compute duration-filtered WER/CER (segments with duration > min_duration)
    filtered_stats, filtered_count = compute_filtered_stats(new_cache_list, min_duration)
    write_errs_and_summary(out_dir, country, model, filtered_stats, compute_CER, suffix="-mindur")

    # Count only non-empty refs as the total: empty-normalized refs are skipped
    # during scoring (see filter in process_one_ref_hyp), so excluding them here
    # keeps ref_segments aligned with matched_segments (avoids spurious red cells).
    ref_n = sum(1 for r in ref_items if str(r.get("text", "")).strip())
    hyp_n = len(hyp_items)
    with open(seg_path, "w", encoding="utf8") as f:
        f.write(f"ref_segments={ref_n}\n")
        f.write(f"hyp_segments={hyp_n}\n")
        f.write(f"matched_segments={valid}\n")
        f.write(f"first_unmatched_in_hyp={fmt_seg(first_unmatched_ref)}\n")
        f.write(f"first_unmatched_in_ref={fmt_seg(first_unmatched_hyp)}\n")
    recomputed = valid - cache_hits
    return f"[CHECK] {country}/{model}: ref={ref_n} hyp={hyp_n} matched={valid} (cached={cache_hits}, recomputed={recomputed})"


# =========================
# Main entry (single batch, with CLI arguments)
# =========================
def main(REF_ROOT, HYP_ROOT, OUT_ROOT, skip_existing=False, min_duration=0.5, workers=None):
    logging.info("====== Single Batch Evaluation ======")
    # 🔹 Print directory paths
    print(f"🔹 REF root: {REF_ROOT}")
    print(f"🔹 HYP root: {HYP_ROOT}")

    if workers is None:
        workers = min(cpu_count(), 16)
    print(f"🔹 Workers: {workers}")

    # Collect all tasks
    tasks = []
    for fn in os.listdir(REF_ROOT):
        if not fn.endswith(".json"):
            continue
        country = fn[:-5]
        compute_CER = is_cer_lang(country)
        with open(os.path.join(REF_ROOT, fn), "r", encoding="utf8") as f:
            ref_items = json.load(f)

        hyp_country_dir = os.path.join(HYP_ROOT, country)
        if not os.path.isdir(hyp_country_dir):
            continue

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
            tasks.append((country, model, ref_items, hyp_items, OUT_ROOT, compute_CER, min_duration))

    logging.info(f"Total tasks: {len(tasks)}, using {workers} workers")

    if workers > 1:
        with Pool(workers) as pool:
            results = pool.map(process_country_model, tasks)
    else:
        results = [process_country_model(t) for t in tasks]

    for msg in results:
        logging.info(msg)

    logging.info("✅ Single batch evaluation completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Single-batch ASR evaluation")
    parser.add_argument("--ref_root", type=str, required=True)
    parser.add_argument("--hyp_root", type=str, required=True)
    parser.add_argument("--out_root", type=str, required=True)
    parser.add_argument("--skip_existing", type=int, choices=[0, 1], default=0,
                        help="1: skip existing model-level outputs; 0: overwrite")
    parser.add_argument("--min_duration", type=float, default=0.5,
                        help="Duration threshold (seconds) for the filtered table (default: 0.5)")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of parallel workers (default: min(cpu_count, 16))")
    args = parser.parse_args()
    main(
        REF_ROOT=args.ref_root,
        HYP_ROOT=args.hyp_root,
        OUT_ROOT=args.out_root,
        skip_existing=bool(args.skip_existing),
        min_duration=args.min_duration,
        workers=args.workers,
    )