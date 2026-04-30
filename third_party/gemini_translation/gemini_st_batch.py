#!/usr/bin/env python3
"""
Gemini Speech Translation batch runner.
Translates audio segments and saves results for evaluation.
Supports rate limiting and resume from checkpoint.

Usage:
  python3 gemini_st_batch.py --lang ARE --target en --max_segs 450 --output_dir /path/to/output
"""

import argparse
import json
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

from pydub import AudioSegment
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"

AUDIO_ROOTS = [
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/testbatch",
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/batch_1",
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/batch_2",
]
REF_ROOT = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/text/ref"

PROMPT_EN = "Listen to this audio and translate the spoken content into English. Do NOT transcribe, only translate. Output ONLY the translated text, no explanations."
PROMPT_ZH = "Listen to this audio and translate the spoken content into Chinese. Do NOT transcribe, only translate. Output ONLY the translated text, no explanations."


def find_audio_file(audio_name: str, lang: str):
    wav_hash = audio_name + ".wav"
    wav_under = audio_name.replace("#", "_") + ".wav"
    for root in AUDIO_ROOTS:
        for wav in (wav_hash, wav_under):
            candidate = os.path.join(root, lang, wav)
            if os.path.isfile(candidate):
                return candidate
    return None


def cut_segment(audio_path: str, start: float, end: float) -> str:
    audio = AudioSegment.from_wav(audio_path)
    segment = audio[int(start * 1000):int(end * 1000)]
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    segment.export(tmp.name, format="wav")
    return tmp.name


def translate_with_retry(client, audio_path: str, prompt: str, max_retries=5):
    for attempt in range(max_retries):
        try:
            uploaded = client.files.upload(file=audio_path)
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, uploaded],
            )
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = min(30 * (2 ** attempt), 300)
                print(f"    Rate limited, waiting {wait}s (attempt {attempt+1})", flush=True)
                time.sleep(wait)
            else:
                print(f"    Error: {err_str[:100]}", flush=True)
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", type=str, required=True)
    parser.add_argument("--target", type=str, default="en", choices=["en", "zh"])
    parser.add_argument("--max_segs", type=int, default=9999, help="Max segments to translate")
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--sleep", type=float, default=2.0, help="Sleep between API calls")
    parser.add_argument("--time_limit", type=int, default=300, help="Time limit in seconds (default 5 min)")
    args = parser.parse_args()

    client = genai.Client(api_key=API_KEY)
    prompt = PROMPT_EN if args.target == "en" else PROMPT_ZH
    ref_field = "text_en" if args.target == "en" else "text_zh"

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{args.lang}_{args.target}.json")

    # Resume from checkpoint
    done_keys = set()
    results = []
    if os.path.isfile(out_path):
        results = json.load(open(out_path))
        for r in results:
            done_keys.add((r["audio_name"], r["start"], r["end"]))
        print(f"Resuming: {len(results)} already done", flush=True)

    ref_dir = os.path.join(REF_ROOT, args.lang)
    count = 0
    skipped = 0
    errors = 0
    start_time = time.time()

    # Collect all eligible segments
    all_segs = []
    for rf in sorted(os.listdir(ref_dir)):
        if not rf.endswith(".json"):
            continue
        ref_data = json.load(open(os.path.join(ref_dir, rf)))
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

    print(f"Eligible segments: {len(all_segs)}", flush=True)
    print(f"Target: {args.max_segs} segments, sleep={args.sleep}s", flush=True)

    for seg_info in all_segs:
        if count >= args.max_segs:
            break
        if time.time() - start_time >= args.time_limit:
            print(f"  Time limit ({args.time_limit}s) reached", flush=True)
            break

        key = (seg_info["audio_name"], seg_info["start"], seg_info["end"])
        if key in done_keys:
            skipped += 1
            continue

        # Cut and translate
        tmp_path = cut_segment(seg_info["audio_path"], seg_info["start"], seg_info["end"])
        try:
            hyp = translate_with_retry(client, tmp_path, prompt)
        finally:
            os.unlink(tmp_path)

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

        # Save checkpoint every 10 segments
        if count % 10 == 0:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            elapsed = time.time() - start_time
            rate = count / elapsed * 60
            print(f"  [{count}/{args.max_segs}] {elapsed:.0f}s elapsed, {rate:.1f} segs/min, errors={errors}", flush=True)

        time.sleep(args.sleep)

    # Final save
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"\nDone: {count} translated, {skipped} skipped, {errors} errors in {elapsed:.0f}s")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
