import os
import json
from typing import Dict

def save_transcription(audio_path: str, text: str, language: str, model: str) -> None:
    """
    Save transcription to /results/{language}_{model}.json file.

    Args:
        audio_path (str): Absolute path to the audio file.
        text (str): Transcribed text corresponding to the audio.
        language (str): Language code, e.g., "IRQ".
        model (str): Model name, e.g., "elevenlabs".
    """
    results_dir = os.path.join(os.getcwd(), "results")
    os.makedirs(results_dir, exist_ok=True)

    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    entry: Dict[str, str] = {
        "path": os.path.abspath(audio_path),
        "text": text.strip(),
        "language": language.strip(),
        "model": model.strip()
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

def save_wer_results(
    params: AttributeDict,
    test_set_name: str,
    results_dict: Dict[str, List[Tuple[str, List[str], List[str]]]],
):
    test_set_wers = dict()
    for key, results in results_dict.items():
        errs_filename = params.res_dir / f"errs-{test_set_name}-{params.suffix}.txt"
        with open(errs_filename, "w", encoding="utf8") as fd:
            wer = write_error_stats(
                fd, f"{test_set_name}-{key}", results, enable_log=True
            )
            test_set_wers[key] = wer

        logging.info(f"详细错误统计已写入到 {errs_filename}")

    test_set_wers = sorted(test_set_wers.items(), key=lambda x: x[1])

    wer_filename = params.res_dir / f"wer-summary-{test_set_name}-{params.suffix}.txt"

    with open(wer_filename, "w", encoding="utf8") as fd:
        print("settings\tWER", file=fd)
        for key, val in test_set_wers:
            print(f"{key}\t{val}", file=fd)

    s = f"\n对于 {test_set_name}，不同设置的 WER 如下:\n"
    note = f"\t{test_set_name} 的最佳结果"
    for key, val in test_set_wers:
        s += f"{key}\t{val}{note}\n"
        note = ""
    logging.info(s)



# Test 
if __name__ == "__main__":
    save_transcription(
        audio_path="/root/shared-nvme/data/audio/sample1.wav",
        text="آه حنا نطبعو نهار تكون آه ق قيام دولة فلسطين كاملة واشفا مليح على كلمة كا كاملة خرجو يطاولو علينا",
        language="IRQ",
        model="elevenlabs"
    )

    save_transcription(
        audio_path="/root/shared-nvme/data/audio/sample2.wav",
        text="آه حنا نطبعو نهار تكون آه ق قيام دولة فلسطين كاملة واشفا مليح على كلمة كا كاملة خرجو يطاولو علينا",
        language="IRQ",
        model="elevenlabs"
    )

    print("[DONE] Test completed. Check ./results/IRQ_elevenlabs.json")
