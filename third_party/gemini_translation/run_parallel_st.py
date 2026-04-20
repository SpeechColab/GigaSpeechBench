#!/usr/bin/env python3
"""
Parallel Gemini ST runner.
Launches all languages × targets concurrently with individual time limits.
Gemini free tier: 15 RPM shared. With 11 concurrent jobs, each gets ~1.3 RPM.
Use sleep=8s per job to stay under limit (11 jobs × 7.5 RPM_each ≈ 82 RPM > 15 limit).
Actually we need sleep = 11 * 60/15 ≈ 44s per call per job. That's too slow.
Better: run 2-3 batch waves.
"""

import subprocess
import sys
import time
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

PYTHON = "python3"
SCRIPT = "/home/v-yujietu/Multilingual-ASR-Benchmark/third_party/gemini_translation/gemini_st_batch.py"
EVAL_SCRIPT = "/home/v-yujietu/Multilingual-ASR-Benchmark/third_party/gemini_translation/eval_st.py"
OUTPUT_DIR = "/home/v-yujietu/Multilingual-ASR-Benchmark/data/st_results"

LANGS = ["ARE", "DZA", "EGY", "IDN", "IRQ", "MAR", "MYS", "PHL", "SAU", "THA", "VNM"]
TARGETS = ["en", "zh"]

# Gemini free tier: 15 RPM, 1500 RPD
# With concurrent_jobs=3, each job gets 5 RPM → sleep=12s per call
# 5 min × 5 RPM = 25 segs per job per wave
# 22 jobs / 3 concurrent = ~8 waves × 5 min = 40 min total
CONCURRENT = 3
TIME_LIMIT = 300  # 5 min per job
SLEEP = 12  # seconds between calls per job


def run_one(lang, target):
    """Run one language+target batch."""
    cmd = [
        PYTHON, SCRIPT,
        "--lang", lang,
        "--target", target,
        "--output_dir", OUTPUT_DIR,
        "--sleep", str(SLEEP),
        "--time_limit", str(TIME_LIMIT),
    ]
    print(f"  START {lang}_{target}", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIME_LIMIT + 60)
    
    # Count results
    out_file = os.path.join(OUTPUT_DIR, f"{lang}_{target}.json")
    n = 0
    if os.path.isfile(out_file):
        try:
            n = len(json.load(open(out_file)))
        except:
            pass
    
    status = "OK" if result.returncode == 0 else f"ERR({result.returncode})"
    print(f"  DONE {lang}_{target}: {n} segs [{status}]", flush=True)
    if result.returncode != 0 and result.stderr:
        # Print last error line
        err_lines = [l for l in result.stderr.strip().split('\n') if l.strip()]
        if err_lines:
            print(f"    last err: {err_lines[-1][:100]}", flush=True)
    return lang, target, n


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Build task list
    tasks = []
    for target in TARGETS:
        for lang in LANGS:
            tasks.append((lang, target))
    
    print(f"=== Gemini ST Parallel Runner ===")
    print(f"Tasks: {len(tasks)} ({len(LANGS)} langs × {len(TARGETS)} targets)")
    print(f"Concurrent: {CONCURRENT}, time_limit: {TIME_LIMIT}s, sleep: {SLEEP}s")
    print(f"Output: {OUTPUT_DIR}")
    print(f"", flush=True)
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=CONCURRENT) as pool:
        futures = {pool.submit(run_one, lang, target): (lang, target) for lang, target in tasks}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                lang, target = futures[future]
                print(f"  FAIL {lang}_{target}: {e}", flush=True)
    
    elapsed = time.time() - start
    print(f"\n=== All done in {elapsed:.0f}s ===\n", flush=True)
    
    # Summary
    print("=== Results Summary ===")
    for target in TARGETS:
        for lang in LANGS:
            out_file = os.path.join(OUTPUT_DIR, f"{lang}_{target}.json")
            n = 0
            if os.path.isfile(out_file):
                try:
                    n = len(json.load(open(out_file)))
                except:
                    pass
            print(f"  {lang}_{target}: {n} segs")
    
    # Run evaluation
    print(f"\n=== Running Evaluation ===", flush=True)
    subprocess.run([
        PYTHON, EVAL_SCRIPT,
        "--results_dir", OUTPUT_DIR,
        "--output", os.path.join(OUTPUT_DIR, "eval_report.txt"),
    ])


if __name__ == "__main__":
    main()
