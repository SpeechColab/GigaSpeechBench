import glob
import json
import os
import subprocess
from typing import Dict, Union

import dashscope

REF_ROOT_DIR = "Multilingual-ASR-Benchmark/Low-Resource-Languages/text/ref/"
AUDIO_ROOT_DIR = "Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/"
TMP_WAV = "/tmp/tmp.wav"
API_KEY = os.getenv("DASHSCOPE_API_KEY")

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
# dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"


language_mapping = {
    "ARE": "ar",  # 阿联酋 -> 阿拉伯语
    "DZA": "ar",  # 阿尔及利亚 -> 阿拉伯语
    "EGY": "ar",  # 埃及 -> 阿拉伯语
    "IRQ": "ar",  # 伊拉克 -> 阿拉伯语
    "MAR": "ar",  # 摩洛哥 -> 阿拉伯语
    "SAU": "ar",  # 沙特阿拉伯 -> 阿拉伯语
    "SYR": "ar",  # 叙利亚 -> 阿拉伯语
    "IDN": "id",  # 印度尼西亚 -> 印尼语
    "JPN": "ja",  # 日本 -> 日语
    "KOR": "ko",  # 韩国 -> 韩语
    "THA": "th",  # 泰国 -> 泰语
    "VNM": "vi",  # 越南 -> 越南语
    "ZH": "zh",  # 中国 -> 中文（普通话、四川话、闽南语、吴语）
    "EN": "en",  # 英文
}


def cut_audio(src, start, end, dst):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            src,
            "-ss",
            str(start),
            "-to",
            str(end),
            "-ac",
            "1",
            "-ar",
            "16000",
            dst,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def call_asr(tmp_wav_path: str, language: str):
    messages = [{"role": "user", "content": [{"audio": tmp_wav_path}]}]

    response = dashscope.MultiModalConversation.call(
        api_key=API_KEY,
        model="qwen3-asr-flash",
        messages=messages,
        result_format="message",
        asr_options={
            "enable_itn": True,
            **(
                {"language": language_mapping[language]}
                if language in language_mapping
                else {}
            ),
        },
    )
    return response


def process_one_json(json_path: str, lang: str, skip_uids: set):
    base = os.path.basename(json_path).rsplit(".", 1)[0]
    wav_path = next(
        iter(
            glob.glob(os.path.join(AUDIO_ROOT_DIR, "**", base + ".wav"), recursive=True)
        ),
        None,
    )

    if not os.path.exists(wav_path):
        print(f"[WARN] 找不到对应的 wav: {wav_path}")
        raise

    print(f"\n[INFO] 处理: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])

    for seg in segments:
        if seg.get("status") != "valid":
            continue
        start_sec = float(seg["start"])
        end_sec = float(seg["end"])

        if os.path.basename(wav_path) + str(start_sec) + str(end_sec) in skip_uids:
            continue

        cut_audio(wav_path, start_sec, end_sec, TMP_WAV)

        print(f"  [SEG] {start_sec:.3f}~{end_sec:.3f} 秒，写入 {TMP_WAV}，调用 ASR...")

        try:
            resp = call_asr(TMP_WAV, lang)
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
            save_transcription(
                audio_path=wav_path,
                text="",
                language=lang,
                model="qwen3-asr-flash",
                start_time=start_sec,
                end_time=end_sec,
            )


def save_transcription(
    audio_path: str,
    text: str,
    language: str,
    model: str,
    start_time: float,
    end_time: float,
) -> None:
    """
    Save transcription to ./results/{language}_{model}.json

    Each entry is appended as a dict with a unique `id`.
    """

    # ---------- output path ----------
    results_dir = os.path.join(os.getcwd(), "results")
    os.makedirs(results_dir, exist_ok=True)

    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    # ---------- new entry ----------
    entry: Dict[str, Union[str, float, int]] = {
        "audio_name": os.path.basename(audio_path),
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

    print(f"[INFO] Transcription saved -> {output_path}, path={entry['audio_name']}")


def main():
    for lang in os.listdir(REF_ROOT_DIR):
        lang_dir = os.path.join(REF_ROOT_DIR, lang)
        if not os.path.isdir(lang_dir):
            continue

        skip_uids = set()
        results_dir = os.path.join(os.getcwd(), "results")
        filename = f"{lang}_qwen3-asr-flash.json"

        output_path = os.path.join(results_dir, filename)
        if os.path.exists(output_path):
            print(f"{output_path} already exists, about to load...")
            with open(output_path) as f:
                items = json.load(f)
                for item in items:
                    skip_uids.add(
                        item["audio_name"]
                        + str(item["start_time"])
                        + str(item["end_time"])
                    )

        for fname in os.listdir(lang_dir):
            if not fname.endswith(".json"):
                continue

            json_path = os.path.join(lang_dir, fname)
            process_one_json(json_path, lang, skip_uids)


if __name__ == "__main__":
    main()
