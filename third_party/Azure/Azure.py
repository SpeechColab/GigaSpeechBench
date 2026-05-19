#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import ntpath
import tempfile
import time
import argparse
from tqdm import tqdm
from pydub import AudioSegment
import azure.cognitiveservices.speech as speechsdk

# ===================== 1. Language mapping config =====================
# Language mapping table (can be changed to external JSON config)
LANG_MAP = {
    # --- Original mapping ---
    "ARE": "ar-AE",
    "DZA": "ar-DZ",
    "EGY": "ar-EG",
    "IRQ": "ar-IQ",
    "MAR": "ar-MA",
    "SAU": "ar-SA",
    "MYS": "ms-MY",
    "THA": "th-TH",
    "IDN": "id-ID",
    "PHL": "fil-PH",
    "VNM": "vi-VN",
    "KOR": "ko-KR",
    "JPN": "ja-JP",
    "AR": "ar-SA",

    "PHL-EN": "en-PH",  # Philippine English
    "SGP-EN": "en-SG",  # Singapore English
    "SCT-EN": "en-GB",  # Scottish English

    "CHN-EN": "en-HK",  # Chinese English 
    "IDN-EN": "en-US",  # Indonesian English
    "JPN-EN": "en-US",  # Japanese English
    "JIN": "zh-CN",     # Jin dialect
    "XIANG": "zh-CN",   # Xiang dialect
}


# ===================== 2. Argument parsing =====================
def parse_args():
    parser = argparse.ArgumentParser(description="Azure ASR Evaluation Script")

    # Base path config
    parser.add_argument("--base_dir", type=str, default="/path/to/dataset_root",
                        help="Base dataset directory path")
    
    parser.add_argument("--speech_roots", type=str, nargs="+", default=None,
                        help="Audio directory list. If not specified, defaults to base_dir/audio/testbatch")
    
    parser.add_argument("--ref_roots", type=str, nargs="+", default=None,
                        help="Reference text directory list. If not specified, defaults to base_dir/text/ref")
    
    parser.add_argument("--submission_root", type=str, default=None,
                        help="Output results directory. If not specified, defaults to base_dir/submission_azure")
    
    parser.add_argument("--pre_root", type=str, default=None,
                        help="Previous results (cache) directory. If not specified, defaults to base_dir/submission_azure2")

    # Azure and model configuration
    parser.add_argument("--model_name", type=str, default="azure",
                        help="Model name used for writing JSON results")
    
    parser.add_argument("--speech_key", type=str, default=os.environ.get("SPEECH_KEY"),
                        help="Azure Speech API Key (defaults to environment variable SPEECH_KEY)")
    
    parser.add_argument("--speech_region", type=str, default="eastasia",
                        help="Azure Speech API Region")

    return parser.parse_args()


# ===================== 3. Utility functions =====================

def build_audio_index(roots):
    """
    audio_index[(lang, audio_name_without_ext)] = full_path
    """
    idx = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for lang in os.listdir(root):
            lang_dir = os.path.join(root, lang)
            if not os.path.isdir(lang_dir):
                continue
            for f in os.listdir(lang_dir):
                if f.lower().endswith(".wav") or f.lower().endswith(".mp3"):
                    # Store without extension for direct matching with JSON filenames
                    name_no_ext = os.path.splitext(f)[0]
                    idx[(lang, name_no_ext)] = os.path.join(lang_dir, f)
    
    print(f"[DEBUG] Index sample: {list(idx.keys())[:5]}")
    return idx


def extract_audio_segment(file_path, start_time, end_time, output_path):
    """
    Extract a specified time segment from audio, supports wav/mp3/flac etc.
    Output as wav (most stable for Azure)
    """
    try:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".") 
        if ext == "":
            ext = None 

        audio = AudioSegment.from_file(file_path, format=ext)

        # Prevent out-of-bounds
        start_ms = max(0, int(start_time * 1000))
        end_ms = max(start_ms, int(end_time * 1000))
        if end_ms > len(audio):
            end_ms = len(audio)

        segment = audio[start_ms:end_ms]
        segment.export(output_path, format="wav")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to extract audio segment {file_path}: {e}")
        return False


def recognize_chunk(file_path, lang, speech_key, speech_region):
    """Call Azure API to recognize audio chunk"""
    if not speech_key:
        raise ValueError("Azure SPEECH_KEY not configured. Please provide via environment variable or --speech_key argument.")

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key, region=speech_region
    )
    speech_config.speech_recognition_language = lang
    audio_config = speechsdk.AudioConfig(filename=file_path)

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config
    )

    results = []
    done = False

    def recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            txt = evt.result.text.strip()
            if txt:
                results.append(txt)

    def stop_cb(evt):
        nonlocal done
        done = True

    recognizer.recognized.connect(recognized)
    recognizer.session_stopped.connect(stop_cb)
    recognizer.canceled.connect(stop_cb)

    recognizer.start_continuous_recognition()
    while not done:
        time.sleep(0.1)
    recognizer.stop_continuous_recognition()

    return " ".join(results)


def load_pre_root_results(pre_root):
    """
    cache[(lang, audio_name, start_time_str)] = text
    """
    cache = {}
    if not os.path.isdir(pre_root):
        return cache

    for root, _, files in os.walk(pre_root):
        for f in files:
            if not f.endswith(".json"):
                continue
            try:
                with open(os.path.join(root, f), "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                if not isinstance(data, list):
                    continue
                for item in data:
                    lang = item.get("language")
                    audio_name = item.get("audio_name")
                    start = item.get("start_time")
                    text = item.get("text", "")
                    if lang and audio_name and start is not None and text.strip():
                        key = (lang, audio_name, f"{float(start):.4f}")
                        cache[key] = text.strip()
            except Exception as e:
                print(f"[PRE_ROOT LOAD FAIL] {f} | {e}")

    print(f"[INFO] PRE_ROOT cache loaded entries: {len(cache)}")
    return cache


def build_tasks(ref_roots, audio_index):
    """
    Build recognition tasks from all ref_roots
    """
    tasks = []
    for ref_root in ref_roots:
        if not os.path.isdir(ref_root):
            continue

        for lang in os.listdir(ref_root):
            lang_dir = os.path.join(ref_root, lang)
            if not os.path.isdir(lang_dir):
                continue

            for ref_file in os.listdir(lang_dir):
                if not ref_file.endswith(".json"):
                    continue

                audio_name = ref_file.replace(".json", "")
                audio_path = audio_index.get((lang, audio_name))

                if audio_path is None:
                    print(f"[MISS AUDIO] Cannot find {lang}/{audio_name}.wav in audio directory")
                    continue

                with open(os.path.join(lang_dir, ref_file), "r", encoding="utf-8") as f:
                    ref_data = json.load(f)
                
                segments = ref_data.get("segments", [])
                
                tasks.append(
                    {
                        "language": lang,
                        "audio_name": audio_name,
                        "audio_path": audio_path,
                        "segments": segments,
                    }
                )

    return tasks


# ===================== 4. Main logic =====================

if __name__ == "__main__":
    args = parse_args()

    # Dynamically build path variables
    SPEECH_ROOTS = args.speech_roots if args.speech_roots else [os.path.join(args.base_dir, "audio", "testbatch")]
    REF_ROOTS = args.ref_roots if args.ref_roots else [os.path.join(args.base_dir, "text", "ref")]
    SUBMISSION_ROOT = args.submission_root if args.submission_root else os.path.join(args.base_dir, "submission_azure")
    PRE_ROOT = args.pre_root if args.pre_root else os.path.join(args.base_dir, "submission_azure2")
    
    os.makedirs(SUBMISSION_ROOT, exist_ok=True)

    print("=================== Configuration ===================")
    print(f"Base Directory   : {args.base_dir}")
    print(f"Speech Roots     : {SPEECH_ROOTS}")
    print(f"Ref Roots        : {REF_ROOTS}")
    print(f"Submission Root  : {SUBMISSION_ROOT}")
    print(f"Pre Root (Cache) : {PRE_ROOT}")
    print(f"Model Name       : {args.model_name}")
    print(f"Azure Region     : {args.speech_region}")
    print("=====================================================\n")

    print("[INFO] Building audio index...")
    audio_index = build_audio_index(SPEECH_ROOTS)
    print(f"[INFO] Audio index total: {len(audio_index)}")

    print("[INFO] Loading PRE_ROOT cache...")
    pre_cache = load_pre_root_results(PRE_ROOT)

    print("[INFO] Building recognition tasks...")
    tasks = build_tasks(REF_ROOTS, audio_index)
    print(f"[INFO] Files to process: {len(tasks)}")

    total_valid = 0
    total_found = 0

    per_lang_results = {}

    for task in tasks:
        lang = task["language"]
        audio_name = task["audio_name"]
        audio_path = task["audio_path"]

        if lang not in per_lang_results:
            per_lang_results[lang] = []

        lang_code = LANG_MAP.get(lang)
        if not lang_code:
            print(f"[WARNING] No LANG_MAP mapping found for {lang}, skipping this file.")
            continue

        # Iterate all segments for this audio file
        for seg in tqdm(task["segments"], desc=f"{lang}/{audio_name}"):
            if seg.get("status") == "invalid":
                continue

            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", 0.0))
            key = (lang, audio_name, f"{start:.4f}")

            item = {
                "audio_name": audio_name,
                "text": "",
                "language": lang,
                "model": args.model_name,
                "start_time": start,
                "end_time": end,
            }
            ref_text = seg.get("text", "")

            total_valid += 1

            # If cache hit, use cached value directly
            if key in pre_cache:
                item["text"] = pre_cache[key]
                total_found += 1
                per_lang_results[lang].append(item)
            else:
                # Extract audio segment and call API
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    tmp_wav = tf.name

                try:
                    ok = extract_audio_segment(audio_path, start, end, tmp_wav)
                    if not ok:
                        continue

                    # Pass externally configured speech_key and region
                    hyp = recognize_chunk(tmp_wav, lang_code, args.speech_key, args.speech_region)
                    print(f"\n{audio_path}:{start}-{end} | EST: {hyp} | REF: {ref_text}")
                    item["text"] = hyp
                    total_found += 1
                    per_lang_results[lang].append(item)
                except Exception as e:
                    print(f"[ERROR] Azure API call or audio extraction error {audio_path}:{start}-{end} | {e}")
                    continue
                finally:
                    if os.path.exists(tmp_wav):
                        os.unlink(tmp_wav)

    # ===================== 5. Output results =====================
    for lang, results in per_lang_results.items():
        if not results:
            continue
        out_file = os.path.join(SUBMISSION_ROOT, f"{lang}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"[OK] Written {out_file} | {len(results)} entries")

    print("\n============== Overall Statistics ==============")
    print(f"Valid total : {total_valid}")
    print(f"Found total : {total_found}")
    print(f"Missing     : {total_valid - total_found}")
    if total_valid > 0:
        print(f"Coverage    : {(total_found / total_valid * 100):.2f}%")
    print("==============================================")

    print(f"\n[DONE] Results saved to: {SUBMISSION_ROOT}")