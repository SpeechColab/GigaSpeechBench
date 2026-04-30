#!/usr/bin/env python3
"""
Run Qwen3-LiveTranslate ST on all languages in parallel.
Matches the same segments as Gemini ST results for fair comparison.

Usage:
  python3 run_parallel_st.py
  python3 run_parallel_st.py --max_segs 40 --concurrent 5
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# MYS and PHL excluded: qwen3-livetranslate-flash does not support ms/tl
LANGS = ["ARE", "DZA", "EGY", "IDN", "IRQ", "MAR", "SAU", "THA", "VNM"]
TARGETS = ["en", "zh"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_SCRIPT = os.path.join(SCRIPT_DIR, "qwen3_st_batch.py")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "../../data/st_results_qwen3lt")
EVAL_SCRIPT = os.path.join(SCRIPT_DIR, "../gemini_translation/eval_st.py")


def run_one(lang: str, target: str, output_dir: str, max_segs: int,
            sleep: float, time_limit: int) -> dict:
    """Run translation for one (lang, target) pair."""
    cmd = [
        sys.executable, BATCH_SCRIPT,
        "--lang", lang,
        "--target", target,
        "--output_dir", output_dir,
        "--max_segs", str(max_segs),
        "--sleep", str(sleep),
        "--time_limit", str(time_limit),
    ]
    t0 = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=time_limit + 60)
        elapsed = time.time() - t0

        # Count results
        out_path = os.path.join(output_dir, f"{lang}_{target}.json")
        n = 0
        if os.path.isfile(out_path):
            n = len(json.load(open(out_path)))

        return {
            "lang": lang, "target": target, "count": n,
            "elapsed": elapsed, "ok": result.returncode == 0,
            "stderr": result.stderr[-200:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "lang": lang, "target": target, "count": 0,
            "elapsed": time.time() - t0, "ok": False,
            "stderr": "TIMEOUT",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, default=DEFAULT_OUTPUT)
    parser.add_argument("--max_segs", type=int, default=40,
                        help="Max segments per lang×target (default 40, matches Gemini)")
    parser.add_argument("--concurrent", type=int, default=5,
                        help="Number of concurrent jobs")
    parser.add_argument("--sleep", type=float, default=1.0,
                        help="Sleep between API calls per job")
    parser.add_argument("--time_limit", type=int, default=600,
                        help="Time limit per job (seconds)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    tasks = [(lang, target) for lang in LANGS for target in TARGETS]
    total = len(tasks)

    print(f"=" * 60)
    print(f"Qwen3-LiveTranslate Speech Translation")
    print(f"Tasks: {total} ({len(LANGS)} langs × {len(TARGETS)} targets)")
    print(f"Max segs: {args.max_segs}, Concurrent: {args.concurrent}")
    print(f"Output: {args.output_dir}")
    print(f"=" * 60)

    t0 = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=args.concurrent) as pool:
        futures = {
            pool.submit(run_one, lang, target, args.output_dir,
                        args.max_segs, args.sleep, args.time_limit): (lang, target)
            for lang, target in tasks
        }

        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            status = "OK" if r["ok"] else "FAIL"
            print(f"  [{len(results)}/{total}] {r['lang']}_{r['target']}: "
                  f"{r['count']} segs, {r['elapsed']:.0f}s [{status}]", flush=True)
            if not r["ok"] and r["stderr"]:
                print(f"    stderr: {r['stderr']}", flush=True)

    elapsed = time.time() - t0
    total_segs = sum(r["count"] for r in results)
    failed = sum(1 for r in results if not r["ok"])

    print(f"\n{'=' * 60}")
    print(f"Completed in {elapsed:.0f}s: {total_segs} segments total, "
          f"{failed} failed jobs")
    print(f"{'=' * 60}")

    # Run evaluation
    print(f"\nRunning evaluation...")
    subprocess.run([sys.executable, EVAL_SCRIPT,
                    "--results_dir", args.output_dir], check=False)


if __name__ == "__main__":
    main()
