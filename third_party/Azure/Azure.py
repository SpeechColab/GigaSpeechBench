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

# ===================== 1. 语种映射配置 =====================
# 语种映射表通常作为常量保留，若需要也可以将其改为外部 JSON 配置文件读取
LANG_MAP = {
    # --- 原有映射 ---
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

    "PHL-EN": "en-PH",  # 菲律宾英语
    "SGP-EN": "en-SG",  # 新加坡英语
    "SCT-EN": "en-GB",  # 苏格兰英语

    "CHN-EN": "en-HK",  # 中式英语 
    "IDN-EN": "en-US",  # 印尼英语
    "JPN-EN": "en-US",  # 日式英语
    "JIN": "zh-CN",     # 晋语
    "XIANG": "zh-CN",   # 湘语
}


# ===================== 2. 参数解析 =====================
def parse_args():
    parser = argparse.ArgumentParser(description="Azure ASR Evaluation Script")

    # 基础路径配置
    parser.add_argument("--base_dir", type=str, default="/workdir/Multilingual-ASR-Benchmark/CH-EN-Dialects",
                        help="基础数据集目录路径")
    
    parser.add_argument("--speech_roots", type=str, nargs="+", default=None,
                        help="音频目录列表。若不指定，默认使用 base_dir/audio/testbatch")
    
    parser.add_argument("--ref_roots", type=str, nargs="+", default=None,
                        help="参考文本目录列表。若不指定，默认使用 base_dir/text/ref")
    
    parser.add_argument("--submission_root", type=str, default=None,
                        help="输出结果的保存目录。若不指定，默认使用 base_dir/submission_azure")
    
    parser.add_argument("--pre_root", type=str, default=None,
                        help="先前结果(缓存)的目录。若不指定，默认使用 base_dir/submission_azure2")

    # Azure 与模型配置
    parser.add_argument("--model_name", type=str, default="azure",
                        help="用于写入 JSON 结果的模型名称")
    
    parser.add_argument("--speech_key", type=str, default=os.environ.get("SPEECH_KEY"),
                        help="Azure Speech API Key (默认从环境变量 SPEECH_KEY 中读取)")
    
    parser.add_argument("--speech_region", type=str, default="eastasia",
                        help="Azure Speech API Region")

    return parser.parse_args()


# ===================== 3. 工具函数 =====================

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
                    # 存入时不带后缀，方便和 json 文件名直接匹配
                    name_no_ext = os.path.splitext(f)[0]
                    idx[(lang, name_no_ext)] = os.path.join(lang_dir, f)
    
    print(f"[DEBUG] 索引采样: {list(idx.keys())[:5]}")
    return idx


def extract_audio_segment(file_path, start_time, end_time, output_path):
    """
    从音频中截取指定时间段，支持 wav/mp3/flac 等
    输出为 wav（给 Azure 用最稳）
    """
    try:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".") 
        if ext == "":
            ext = None 

        audio = AudioSegment.from_file(file_path, format=ext)

        # 防止越界
        start_ms = max(0, int(start_time * 1000))
        end_ms = max(start_ms, int(end_time * 1000))
        if end_ms > len(audio):
            end_ms = len(audio)

        segment = audio[start_ms:end_ms]
        segment.export(output_path, format="wav")
        return True
    except Exception as e:
        print(f"[ERROR] 提取音频失败 {file_path}: {e}")
        return False


def recognize_chunk(file_path, lang, speech_key, speech_region):
    """调用 Azure API 识别切片音频"""
    if not speech_key:
        raise ValueError("Azure SPEECH_KEY 未配置，请通过环境变量或 --speech_key 参数提供。")

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

    print(f"[INFO] PRE_ROOT 缓存已加载条目数: {len(cache)}")
    return cache


def build_tasks(ref_roots, audio_index):
    """
    从所有 ref_root 构建待识别任务
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
                    print(f"[MISS AUDIO] 在 audio 中找不到 {lang}/{audio_name}.wav")
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


# ===================== 4. 主逻辑 =====================

if __name__ == "__main__":
    args = parse_args()

    # 动态构建路径变量
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

    print("[INFO] 构建音频索引...")
    audio_index = build_audio_index(SPEECH_ROOTS)
    print(f"[INFO] 音频索引总数: {len(audio_index)}")

    print("[INFO] 加载 PRE_ROOT 缓存...")
    pre_cache = load_pre_root_results(PRE_ROOT)

    print("[INFO] 构建待识别任务...")
    tasks = build_tasks(REF_ROOTS, audio_index)
    print(f"[INFO] 待处理文件数: {len(tasks)}")

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
            print(f"[WARNING] 未在 LANG_MAP 中找到 {lang} 的映射，跳过此文件。")
            continue

        # 遍历该音频文件下的所有切片
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

            # 如果命中缓存，直接取值
            if key in pre_cache:
                item["text"] = pre_cache[key]
                total_found += 1
                per_lang_results[lang].append(item)
            else:
                # 截取音频并调用 API
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    tmp_wav = tf.name

                try:
                    ok = extract_audio_segment(audio_path, start, end, tmp_wav)
                    if not ok:
                        continue

                    # 传入外部配置的 speech_key 和 region
                    hyp = recognize_chunk(tmp_wav, lang_code, args.speech_key, args.speech_region)
                    print(f"\n{audio_path}:{start}-{end} | EST: {hyp} | REF: {ref_text}")
                    item["text"] = hyp
                    total_found += 1
                    per_lang_results[lang].append(item)
                except Exception as e:
                    print(f"[ERROR] Azure API 调用或音频截取错误 {audio_path}:{start}-{end} | {e}")
                    continue
                finally:
                    if os.path.exists(tmp_wav):
                        os.unlink(tmp_wav)

    # ===================== 5. 输出结果 =====================
    for lang, results in per_lang_results.items():
        if not results:
            continue
        out_file = os.path.join(SUBMISSION_ROOT, f"{lang}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"[OK] 写出 {out_file} | {len(results)} 条")

    print("\n============== Overall Statistics ==============")
    print(f"Valid total : {total_valid}")
    print(f"Found total : {total_found}")
    print(f"Missing     : {total_valid - total_found}")
    if total_valid > 0:
        print(f"Coverage    : {(total_found / total_valid * 100):.2f}%")
    print("==============================================")

    print(f"\n[完成] 结果保存在：{SUBMISSION_ROOT}")