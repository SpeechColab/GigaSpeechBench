import json
import os

import dashscope
from pydub import AudioSegment

ROOT_DIR = "testbatch_processed"
TMP_WAV = "/tmp/tmp.wav"
API_KEY = os.getenv("DASHSCOPE_API_KEY")

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
# dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"


def call_asr(tmp_wav_path: str):
    messages = [{"role": "user", "content": [{"audio": TMP_WAV}]}]

    response = dashscope.MultiModalConversation.call(
        api_key=API_KEY,
        model="qwen3-asr-flash",
        messages=messages,
        result_format="message",
        asr_options={
            # "language": "zh",  # 需要的话自己打开
            "enable_itn": True
        },
    )
    return response


def process_one_json(json_path: str, lang: str):
    base = os.path.splitext(json_path)[0]
    wav_path = base + ".wav"

    if not os.path.exists(wav_path):
        print(f"[WARN] 找不到对应的 wav: {wav_path}，跳过。")
        return

    print(f"\n[INFO] 处理: {json_path}")
    audio = AudioSegment.from_wav(wav_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])

    for seg in segments:
        if seg.get("status") != "valid":
            continue
        if not seg.get("text"):
            continue

        start_sec = float(seg["start"])
        end_sec = float(seg["end"])
        seg_idx = seg.get("index")

        start_ms = int(start_sec * 1000)
        end_ms = int(end_sec * 1000)

        clip = audio[start_ms:end_ms]

        clip.export(TMP_WAV, format="wav")

        print(
            f"  [SEG] index={seg_idx}, {start_sec:.3f}~{end_sec:.3f} 秒，写入 {TMP_WAV}，调用 ASR..."
        )

        try:
            resp = call_asr(TMP_WAV)
            save_transcription(
                audio_path=wav_path,
                text=resp["output"]["choices"][0]["message"]["content"][0]["text"],
                language=lang,
                model="qwen3-asr-flash",
                start_time=start_sec,
                end_time=end_sec,
            )
        except Exception as e:
            print(f"    [ERROR] 调用 ASR 失败: {e}")


def save_transcription(
    audio_path: str,
    text: str,
    language: str,
    model: str,
    start_time: float,
    end_time: float,
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
        "end_time": float(end_time),
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
            print(
                f"[WARN] Failed to read existing JSON ({output_path}), recreating. Reason: {e}"
            )

    data.append(entry)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[INFO] Transcription saved -> {output_path}")
    print(f"       + Added entry for: {entry['path']}")


def main():
    for lang in os.listdir(ROOT_DIR):
        lang_dir = os.path.join(ROOT_DIR, lang)
        if not os.path.isdir(lang_dir):
            continue

        for fname in os.listdir(lang_dir):
            if not fname.endswith("_raw.json"):
                continue

            json_path = os.path.join(lang_dir, fname)
            process_one_json(json_path, lang)


if __name__ == "__main__":
    main()
