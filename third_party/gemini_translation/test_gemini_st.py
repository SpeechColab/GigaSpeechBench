#!/usr/bin/env python3
"""
Gemini Speech Translation test script.
Translates audio segments to English and Chinese using Gemini 3.0 Flash.
Tests with 2 segments first to verify correctness before full batch.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path
from pydub import AudioSegment
from google import genai

API_KEY = "REDACTED_GEMINI_KEY"
MODEL_NAME = "gemini-2.0-flash"

# Audio search paths
AUDIO_ROOTS = [
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/testbatch",
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/batch_1",
    "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/batch_2",
]

REF_ROOT = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark/Low-Resource-Languages/text/ref"


def find_audio_file(audio_name: str, lang: str) -> str | None:
    """Find audio file on disk given ref audio_name (e.g. ARE#UC...#vid#raw)."""
    # batch_1 and batch_2 use # separator (same as ref)
    wav_hash = audio_name + ".wav"
    # testbatch uses _ separator
    wav_under = audio_name.replace("#", "_") + ".wav"
    for root in AUDIO_ROOTS:
        for wav in (wav_hash, wav_under):
            candidate = os.path.join(root, lang, wav)
            if os.path.isfile(candidate):
                return candidate
    return None


def cut_segment(audio_path: str, start: float, end: float) -> str:
    """Cut audio segment and return path to temp wav file."""
    audio = AudioSegment.from_wav(audio_path)
    segment = audio[int(start * 1000):int(end * 1000)]
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    segment.export(tmp.name, format="wav")
    return tmp.name


def translate_segment(client, audio_path: str, target_lang: str) -> str:
    """Upload audio and get translation from Gemini."""
    uploaded = client.files.upload(file=audio_path)
    prompt = f"Listen to this audio and translate the spoken content into {target_lang}. Do NOT transcribe, only translate. Output ONLY the translated text, no explanations."
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt, uploaded],
    )
    # Clean up uploaded file
    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass
    return response.text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", type=str, default="ARE", help="Language code")
    parser.add_argument("--n", type=int, default=2, help="Number of segments to test")
    parser.add_argument("--target", type=str, default="both", choices=["en", "zh", "both"])
    args = parser.parse_args()

    client = genai.Client(api_key=API_KEY)

    # Load ref and find segments with existing translations for comparison
    ref_dir = os.path.join(REF_ROOT, args.lang)
    tested = 0

    for rf in sorted(os.listdir(ref_dir)):
        if tested >= args.n:
            break
        if not rf.endswith(".json"):
            continue

        ref_data = json.load(open(os.path.join(ref_dir, rf)))
        audio_name = ref_data.get("audio_name", "")
        audio_path = find_audio_file(audio_name, args.lang)

        if not audio_path:
            continue

        for seg in ref_data.get("segments", []):
            if tested >= args.n:
                break
            if seg.get("status") == "invalid":
                continue
            if not seg.get("text_en"):
                continue  # only test segments that have reference translations

            start = float(seg["start"])
            end = float(seg["end"])
            duration = end - start
            if duration < 2 or duration > 30:
                continue  # skip very short/long segments

            print(f"\n{'='*60}")
            print(f"Audio: {audio_name}")
            print(f"Segment: {start:.2f} - {end:.2f} ({duration:.1f}s)")
            print(f"Original text: {seg['text'][:80]}")

            # Cut segment
            tmp_path = cut_segment(audio_path, start, end)

            try:
                if args.target in ("en", "both"):
                    en_result = translate_segment(client, tmp_path, "English")
                    ref_en = seg.get("text_en", "N/A")
                    print(f"\n[EN] Gemini:    {en_result[:100]}")
                    print(f"[EN] Reference: {ref_en[:100]}")

                if args.target in ("zh", "both"):
                    zh_result = translate_segment(client, tmp_path, "Chinese")
                    ref_zh = seg.get("text_zh", "N/A")
                    print(f"\n[ZH] Gemini:    {zh_result[:100]}")
                    print(f"[ZH] Reference: {ref_zh[:100]}")
            finally:
                os.unlink(tmp_path)

            tested += 1

    print(f"\n{'='*60}")
    print(f"Tested {tested} segments")


if __name__ == "__main__":
    main()
