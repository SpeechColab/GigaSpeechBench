#!/usr/bin/env python3
"""
Qwen3-LiveTranslate Speech Translation batch runner.
Translates audio segments and saves results for evaluation.
Uses the same dashscope MultiModalConversation API as qwen3-asr-flash.

Output format matches Gemini ST results:
  [ { "audio_name", "start", "end", "ref", "hyp", "original" }, ... ]

Usage:
  python3 qwen3_st_batch.py --lang ARE --target en --output_dir ../../data/st_results_qwen3lt
  python3 qwen3_st_batch.py --lang ARE --target zh --output_dir ../../data/st_results_qwen3lt --max_segs 40
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback

import dashscope

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
API_KEY = os.getenv("DASHSCOPE_API_KEY")
MODEL_NAME = "qwen3-livetranslate-flash"

AUDIO_ROOTS = [
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/testbatch",
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/batch_1",
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/batch_2",
]
REF_ROOT = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/text/ref"

# Supported source languages: ar, id, th, vi, ja, ko, en, zh
# MYS (ms) and PHL (tl/fil) are NOT supported by qwen3-livetranslate-flash
LANG_MAP = {
    "ARE": "ar", "DZA": "ar", "EGY": "ar", "IRQ": "ar", "MAR": "ar", "SAU": "ar",
    "IDN": "id", "THA": "th", "VNM": "vi",
}

TARGET_LANG_MAP = {"en": "en", "zh": "zh"}


def find_audio_file(audio_name: str, lang: str):
    """Find audio file across multiple root directories."""
    wav_hash = audio_name + ".wav"
    wav_under = audio_name.replace("#", "_") + ".wav"
    for root in AUDIO_ROOTS:
        for wav in (wav_hash, wav_under):
            candidate = os.path.join(root, lang, wav)
            if os.path.isfile(candidate):
                return candidate
    return None


def cut_segment(audio_path: str, start: float, end: float) -> str:
    """Cut audio segment using ffmpeg, return temp file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path, "-ss", str(start), "-to", str(end),
         "-ac", "1", "-ar", "16000", tmp.name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return tmp.name


def translate_with_retry(audio_path: str, source_lang: str, target_lang: str,
                         max_retries=5):
    """Call qwen3-livetranslate-flash via dashscope API with retry logic."""
    for attempt in range(max_retries):
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"audio": audio_path},
                    ],
                }
            ]
            response = dashscope.MultiModalConversation.call(
                api_key=API_KEY,
                model=MODEL_NAME,
                messages=messages,
                result_format="message",
                translation_options={
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                },
            )

            if response.get("status_code") and response["status_code"] != 200:
                code = response.get("status_code", "")
                msg = response.get("message", "")
                if code == 429 or "throttl" in str(msg).lower():
                    wait = min(30 * (2 ** attempt), 300)
                    print(f"    Rate limited, waiting {wait}s (attempt {attempt+1})",
                          flush=True)
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"API error {code}: {msg}")

            text = response["output"]["choices"][0]["message"]["content"][0]["text"]
            return text.strip()

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Throttl" in err_str or "rate" in err_str.lower():
                wait = min(30 * (2 ** attempt), 300)
                print(f"    Rate limited, waiting {wait}s (attempt {attempt+1})",
                      flush=True)
                time.sleep(wait)
            else:
                print(f"    Error (attempt {attempt+1}): {err_str[:150]}", flush=True)
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", type=str, required=True)
    parser.add_argument("--target", type=str, default="en", choices=["en", "zh"])
    parser.add_argument("--max_segs", type=int, default=9999)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--sleep", type=float, default=1.0,
                        help="Sleep between API calls (seconds)")
    parser.add_argument("--time_limit", type=int, default=600,
                        help="Time limit in seconds")
    args = parser.parse_args()

    ref_field = "text_en" if args.target == "en" else "text_zh"
    source_lang = LANG_MAP.get(args.lang, "ar")
    target_lang = TARGET_LANG_MAP[args.target]

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{args.lang}_{args.target}.json")

    # Resume from checkpoint
    done_keys = set()
    results = []
    if os.path.isfile(out_path):
        results = json.load(open(out_path, encoding="utf-8"))
        for r in results:
            done_keys.add((r["audio_name"], r["start"], r["end"]))
        print(f"Resuming: {len(results)} already done", flush=True)

    ref_dir = os.path.join(REF_ROOT, args.lang)
    if not os.path.isdir(ref_dir):
        print(f"Ref dir not found: {ref_dir}", flush=True)
        sys.exit(1)

    # Collect all eligible segments
    all_segs = []
    for rf in sorted(os.listdir(ref_dir)):
        if not rf.endswith(".json"):
            continue
        ref_data = json.load(open(os.path.join(ref_dir, rf), encoding="utf-8"))
        audio_name = ref_data.get("audio_name", "")
        audio_path = find_audio_file(audio_name, args.lang)
        if not audio_path:
            continue
        for seg in ref_data.get("segments", []):
            if seg.get("status") == "invalid":
                continue
            if not seg.get(ref_field):
                continue
            start = float(seg["start"])
            end = float(seg["end"])
            dur = end - start
            if dur < 1 or dur > 60:
                continue
            all_segs.append({
                "audio_name": audio_name,
                "audio_path": audio_path,
                "start": start,
                "end": end,
                "ref_text": seg.get(ref_field, ""),
                "original_text": seg.get("text", ""),
            })

    print(f"[{args.lang}_{args.target}] Eligible: {len(all_segs)}, "
          f"target: {args.max_segs}, sleep={args.sleep}s", flush=True)

    count = 0
    errors = 0
    start_time = time.time()

    for seg_info in all_segs:
        if count >= args.max_segs:
            break
        if time.time() - start_time >= args.time_limit:
            print(f"  Time limit ({args.time_limit}s) reached", flush=True)
            break

        key = (seg_info["audio_name"], seg_info["start"], seg_info["end"])
        if key in done_keys:
            continue

        # Cut segment and translate
        tmp_path = cut_segment(seg_info["audio_path"], seg_info["start"],
                               seg_info["end"])
        try:
            hyp = translate_with_retry(tmp_path, source_lang, target_lang)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if hyp is None:
            errors += 1
            continue

        results.append({
            "audio_name": seg_info["audio_name"],
            "start": seg_info["start"],
            "end": seg_info["end"],
            "ref": seg_info["ref_text"],
            "hyp": hyp,
            "original": seg_info["original_text"],
        })
        done_keys.add(key)
        count += 1

        # Checkpoint every 10 segments
        if count % 10 == 0:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            elapsed = time.time() - start_time
            rate = count / elapsed * 60 if elapsed > 0 else 0
            print(f"  [{count}/{args.max_segs}] {elapsed:.0f}s, "
                  f"{rate:.1f} segs/min, errors={errors}", flush=True)

        time.sleep(args.sleep)

    # Final save
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"\nDone [{args.lang}_{args.target}]: {count} translated, "
          f"{errors} errors in {elapsed:.0f}s", flush=True)
    print(f"Output: {out_path}", flush=True)


if __name__ == "__main__":
    main()
