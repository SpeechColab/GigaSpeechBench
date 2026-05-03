#!/usr/bin/env python3
"""
Run Chirp3 on missing SYR segments only.
Reads ref to find missing segments, cuts audio, calls API, merges into existing hyp.
"""
import io
import json
import os
import time
import logging
from collections import defaultdict

from google.api_core import retry
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = "project-b8b84a33-1939-4f27-bda"
DEFAULT_LOCATION = "eu"
MODEL_NAME = "chirp_3"
LANGUAGE_CODE = "ar-SA"  # SYR = Syrian Arabic; fallback to ar-SA if needed

BASE = "/path/to/dataset"
REF_DIR = os.path.join(BASE, "Low-Resource-Languages/text/ref/SYR")
HYP_PATH = os.path.join(BASE, "Low-Resource-Languages/text/hyp/SYR_chirp3.json")
AUDIO_DIR = "/tmp/SYR_audio/SYR"
TOL = 0.1


def norm(a):
    b = os.path.basename(str(a).replace("\\", "/"))
    while True:
        ch = False
        for e in [".wav", ".mp3", ".mp4", ".webm"]:
            if b.lower().endswith(e): b = b[:-len(e)]; ch = True
        if not ch: break
    if b.endswith("#raw"): b = b[:-4]
    return b


def get_speech_client():
    api_endpoint = f"{DEFAULT_LOCATION}-speech.googleapis.com"
    client_options = ClientOptions(api_endpoint=api_endpoint)
    return SpeechClient(client_options=client_options)


def transcribe_segment(client, audio_path, start, end):
    """Cut segment from audio and transcribe via Chirp3."""
    audio = AudioSegment.from_file(audio_path)
    start_ms = int(start * 1000)
    end_ms = int(end * 1000)
    if end_ms > len(audio):
        end_ms = len(audio)
    segment = audio[start_ms:end_ms]

    with io.BytesIO() as buf:
        segment.export(buf, format="wav")
        content = buf.getvalue()

    recognizer_path = f"projects/{PROJECT_ID}/locations/{DEFAULT_LOCATION}/recognizers/_"
    config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        model=MODEL_NAME,
        features=cloud_speech.RecognitionFeatures(enable_automatic_punctuation=True),
        language_codes=[LANGUAGE_CODE],
    )
    request = cloud_speech.RecognizeRequest(
        recognizer=recognizer_path,
        config=config,
        content=content,
    )
    response = client.recognize(
        request=request,
        retry=retry.Retry(
            predicate=lambda exc: True,
            initial=1.0, maximum=30.0, multiplier=2.0, deadline=300.0,
        ),
    )
    text = " ".join(
        r.alternatives[0].transcript for r in response.results if r.alternatives
    ).strip()
    return text


def main():
    # Load existing hyp
    hyp = json.load(open(HYP_PATH))
    hyp_idx = defaultdict(list)
    for x in hyp:
        a = norm(x.get("audio_name") or x.get("audio_path", ""))
        hyp_idx[a].append((
            float(x.get("start", x.get("start_time", 0))),
            float(x.get("end", x.get("end_time", 0))),
        ))

    # Collect missing segments
    missing = []
    for rf in sorted(os.listdir(REF_DIR)):
        if not rf.endswith(".json"): continue
        d = json.load(open(os.path.join(REF_DIR, rf)))
        aname = d.get("audio_name", "")
        for seg in d.get("segments", []):
            if seg.get("status") == "invalid": continue
            start, end = float(seg["start"]), float(seg["end"])
            a = norm(aname)
            found = any(abs(hs-start) <= TOL and abs(he-end) <= TOL for hs, he in hyp_idx.get(a, []))
            if not found:
                # Find audio file
                wav = aname + ".wav"
                audio_path = os.path.join(AUDIO_DIR, wav)
                if not os.path.isfile(audio_path):
                    wav2 = aname.replace("#", "_") + ".wav"
                    audio_path = os.path.join(AUDIO_DIR, wav2)
                if os.path.isfile(audio_path):
                    missing.append((aname, start, end, audio_path))

    logger.info(f"Missing segments to transcribe: {len(missing)}")

    client = get_speech_client()
    added = 0
    errors = 0

    for i, (aname, start, end, audio_path) in enumerate(missing):
        try:
            text = transcribe_segment(client, audio_path, start, end)
            hyp.append({
                "audio_name": aname,
                "text": text,
                "language": "SYR",
                "model": "chirp3",
                "start_time": start,
                "end_time": end,
            })
            added += 1
            if added % 10 == 0:
                # Checkpoint
                with open(HYP_PATH, "w", encoding="utf-8") as f:
                    json.dump(hyp, f, ensure_ascii=False, indent=2)
                logger.info(f"  [{added}/{len(missing)}] checkpoint saved, errors={errors}")
        except Exception as e:
            errors += 1
            logger.warning(f"  Error seg {aname} {start}-{end}: {str(e)[:100]}")
            if "PERMISSION_DENIED" in str(e) or "NOT_FOUND" in str(e):
                logger.error("Auth/project error, stopping.")
                break
            time.sleep(2)

    # Final save
    with open(HYP_PATH, "w", encoding="utf-8") as f:
        json.dump(hyp, f, ensure_ascii=False, indent=2)
    logger.info(f"Done: {added} added, {errors} errors. Total hyp: {len(hyp)}")


if __name__ == "__main__":
    main()
