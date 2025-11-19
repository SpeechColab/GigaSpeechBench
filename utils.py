import os
import json
from typing import Dict

def save_transcription(
    audio_path: str,
    text: str,
    language: str,
    model: str,
    start_time: float,
    end_time: float
) -> None:
    """
    Save transcription to /results/{language}_{model}.json file.

    Args:
        audio_path (str): Absolute path to the audio file.
        text (str): Transcribed text.
        language (str): Language code, e.g., "IRQ".
        model (str): Model name, e.g., "elevenlabs".
        start_time (float): Start time in seconds.
        end_time (float): End time in seconds.
    """
    results_dir = os.path.join(os.getcwd(), "results")
    os.makedirs(results_dir, exist_ok=True)

    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    entry: Dict[str, str | float] = {
        "path": os.path.abspath(audio_path),
        "text": text.strip(),
        "language": language.strip(),
        "model": model.strip(),
        "start_time": float(start_time),
        "end_time": float(end_time)
    }

    data = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if not isinstance(data, list):
                        raise ValueError("Invalid JSON structure: root must be a list.")
        except Exception as e:
            print(f"[WARN] Failed to read existing JSON ({output_path}), recreating. Reason: {e}")

    data.append(entry)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[INFO] Transcription saved -> {output_path}")
    print(f"       + Added entry for: {entry['path']}")


# Test 
if __name__ == "__main__":
    save_transcription(
        audio_path="/root/shared-nvme/data/audio/sample1.wav",
        text="آه حنا نطبعو نهار تكون آه ق قيام دولة فلسطين كاملة واشفا مليح على كلمة كا كاملة خرجو يطاولو علينا",
        language="IRQ",
        model="elevenlabs",
        start_time=0.00,
        end_time=3.52
    )

    save_transcription(
        audio_path="/root/shared-nvme/data/audio/sample2.wav",
        text="آه حنا نطبعو نهار تكون آه ق قيام دولة فلسطين كاملة واشفا مليح على كلمة كا كاملة خرجو يطاولو علينا",
        language="IRQ",
        model="elevenlabs",
        start_time=0.00,
        end_time=3.52
    )

    print("[DONE] Test completed. Check ./results/IRQ_elevenlabs.json")
