import os
import json
from typing import Dict, Union


def save_transcription(
    audio_path: str,
    text: str,
    language: str,
    model: str,
    start_time: float = 0.0,
    end_time: float = 0.0,
    index: int = 0,
) -> None:
    """
    Save transcription to ./results/{model}.json in release audios[] format.

    Args:
        audio_path (str): Absolute or relative path to the audio file.
        text (str): Transcribed text.
        language (str): Language code, e.g. "IRQ".
        model (str): Model name, e.g. "elevenlabs".
        start_time (float): Start time in seconds.
        end_time (float): End time in seconds.
        index (int): Sample index (unused, kept for compatibility).
    """

    # ---------- output path ----------
    results_dir = os.path.join(os.getcwd(), "results")
    os.makedirs(results_dir, exist_ok=True)

    filename = f"{model}.json"
    output_path = os.path.join(results_dir, filename)

    # ---------- derive aid and sid ----------
    basename = os.path.basename(audio_path)
    aid = os.path.splitext(basename)[0] if basename.endswith(".wav") else basename
    begin_time_str = str(start_time)
    end_time_str = str(end_time)
    sid = f"{aid}#{begin_time_str}#{end_time_str}"

    seg_entry = {
        "sid": sid,
        "begin_time": begin_time_str,
        "end_time": end_time_str,
        "text": text.strip(),
        "lang": language.strip(),
    }

    # ---------- load existing ----------
    data = {"audios": []}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if not isinstance(data, dict) or "audios" not in data:
                        data = {"audios": []}
        except Exception as e:
            print(f"[WARN] Failed to read {output_path}, recreating. Reason: {e}")
            data = {"audios": []}

    # ---------- append to correct audio ----------
    found = False
    for audio in data["audios"]:
        if audio["aid"] == aid:
            audio["segments"].append(seg_entry)
            found = True
            break
    if not found:
        data["audios"].append({
            "aid": aid,
            "segments": [seg_entry],
            "language": language.strip(),
        })

    # ---------- write back ----------
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[INFO] Transcription saved -> {output_path}, aid={aid}")
