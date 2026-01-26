#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path
from collections import defaultdict

# =========================
# 官方固定配置
# =========================

COUNTRY_LIST = {
    "IRQ", "DZA", "ARE", "EGY", "MAR", "SAU",
    "IDN", "MYS", "PHL", "VNM", "THA", "JPN", "KOR"
}

MODEL_WHITELIST = {
    "azure",
    "chirp3",
    "elevenlabs_scribe_v2",
    "omniASR_LLM_3B",
    "qwen3-asr-flash",
    "nvidia-nemo",
    "gpt4o-transcribe",
    "gemini_3_0_flash",
    "whisper",
    "dolphin_small",
    "dolphin_base",
    "fun-asr-mlt-nano",
}

EXPECTED_SEGMENTS = {
    "ARE": 18313,
    "DZA": 20060,
    "EGY": 18248,
    "IDN": 24178,
    "IRQ": 16408,
    "JPN": 14272,
    "KOR": 12166,
    "MAR": 15963,
    "MYS": 26519,
    "PHL": 17937,
    "SAU": 13286,
    "THA": 20122,
    "VNM": 15996,
}

REQUIRED_KEYS = {
    "audio_name",
    "text",
    "language",
    "model",
    "start_time",
    "end_time",
}


# =========================
# 校验单个 JSON
# =========================

def check_json(json_path: Path):
    problems = set()

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {f"JSON 解析失败: {e}"}

    if not isinstance(data, list):
        return {"JSON 顶层必须是 list"}

    # language → segment 数校验
    langs = {seg.get("language") for seg in data if isinstance(seg, dict)}
    langs = {l for l in langs if isinstance(l, str)}

    if len(langs) != 1:
        problems.add("language 不唯一或缺失（一个 JSON 只能包含一个国家）")
    else:
        lang = next(iter(langs))
        if lang not in COUNTRY_LIST:
            problems.add(f"language 不在国家列表中: {lang}")
        else:
            expected = EXPECTED_SEGMENTS[lang]
            if len(data) != expected:
                problems.add(f"segment 数量不一致（期望 {expected}，实际 {len(data)}）")

    for seg in data:
        if not isinstance(seg, dict):
            problems.add("存在非 dict 的 segment")
            break

        missing = REQUIRED_KEYS - seg.keys()
        if missing:
            problems.add("存在缺失字段的 segment")
            break

        if not isinstance(seg["audio_name"], str) or not seg["audio_name"].endswith(".wav"):
            problems.add("存在 audio_name 非 .wav 的 segment")

        if not isinstance(seg["text"], str):
            problems.add("存在 text 非字符串的 segment")

        if not isinstance(seg["model"], str) or seg["model"] not in MODEL_WHITELIST:
            problems.add("存在 model 不在白名单的 segment")

        try:
            st = float(seg["start_time"])
            et = float(seg["end_time"])
            if et <= st or st < 0:
                problems.add("存在非法时间区间（start_time / end_time）")
        except Exception:
            problems.add("存在 start_time / end_time 非数值的 segment")

    return problems


# =========================
# 主入口
# =========================

def main():
    if len(sys.argv) != 2:
        print("用法：python check.py <submission_dir>")
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"[❌ ERROR] {root} 不是目录")
        sys.exit(1)

    json_files = sorted(root.glob("*.json"))
    if not json_files:
        print("[❌ ERROR] 目录下没有任何 json 文件")
        sys.exit(1)

    all_errors = {}

    for p in json_files:
        probs = check_json(p)
        if probs:
            all_errors[p.name] = sorted(probs)

    if not all_errors:
        print("🎉 [PASS] 全部 JSON 校验通过，可以提交。")
        sys.exit(0)

    print(f"\n❌ 校验失败，共 {len(all_errors)} 个文件存在问题\n")

    for fname, probs in all_errors.items():
        print(f"{fname}:")
        for msg in probs:
            print(f"  - {msg}")
        print()

    sys.exit(2)


if __name__ == "__main__":
    main()
