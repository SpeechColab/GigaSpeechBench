import os
import json
from typing import Dict, Union


def save_transcription(
    audio_path: str,
    text: str,
    language: str,
    model: str,
    start_time: float,
    end_time: float,
    index: int,
) -> None:
    """
    Save transcription to ./results/{language}_{model}.json

    Each entry is appended as a dict with a unique `id`.

    Args:
        audio_path (str): Absolute or relative path to the audio file.
        text (str): Transcribed text.
        language (str): Language code, e.g. "IRQ".
        model (str): Model name, e.g. "elevenlabs".
        start_time (float): Start time in seconds.
        end_time (float): End time in seconds.
        index (int): Sample index, will be saved as `id`.
    """

    # ---------- output path ----------
    results_dir = os.path.join(os.getcwd(), "results")
    os.makedirs(results_dir, exist_ok=True)

    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    # ---------- new entry ----------
    entry: Dict[str, Union[str, float, int]] = {
        "id": int(index),
        "path": os.path.abspath(audio_path),
        "text": text.strip(),
        "language": language.strip(),
        "model": model.strip(),
        "start_time": float(start_time),
        "end_time": float(end_time),
    }

    # ---------- load existing ----------
    data = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if not isinstance(data, list):
                        raise ValueError("JSON root is not a list")
        except Exception as e:
            print(f"[WARN] Failed to read {output_path}, recreating. Reason: {e}")
            data = []

    # ---------- append ----------
    data.append(entry)

    # ---------- write back ----------
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[INFO] Transcription saved -> {output_path}")
    print(f"       + id={index}, path={entry['path']}")


# ==========================================================
# Test / Example usage
# ==========================================================
if __name__ == "__main__":
    save_transcription(
        audio_path="/root/shared-nvme/data/audio/sample1.wav",
        text="آه حنا نطبعو نهار تكون آه ق قيام دولة فلسطين كاملة واشفا مليح على كلمة كا كاملة خرجو يطاولو علينا",
        language="IRQ",
        model="elevenlabs",
        start_time=0.00,
        end_time=3.52,
        index=0,
    )

    save_transcription(
        audio_path="/root/shared-nvme/data/audio/sample2.wav",
        text="آه حنا نطبعو نهار تكون آه ق قيام دولة فلسطين كاملة واشفا مليح على كلمة كا كاملة خرجو يطاولو علينا",
        language="IRQ",
        model="elevenlabs",
        start_time=0.00,
        end_time=3.52,
        index=1,
    )

    print("[DONE] Test completed. Check ./results/IRQ_elevenlabs.json")
