import os
import time
import json
import subprocess
import tempfile
import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment
import utils

# ===== 全局配置 =====
SPEECH_KEY = "EWGsOgJxZ6FKG73BTYmYJJ5ohFz8FR0kykIGEkRywJxavPS39XwGJQQJ99BKAC3pKaRXJ3w3AAAAACOG4AFu"
SPEECH_REGION = "eastasia"
CHUNK_SECONDS = 30           # 每段最大时长（秒）
SILENCE_THRESH = -40         # 静音检测阈值 (dBFS)
MIN_SILENCE_LEN = 500        # 静音最短持续时间 (ms)


def extract_audio_segment(file_path, start_time, end_time, output_path):
    """
    从音频文件中提取指定时间段的片段
    """
    try:
        audio = AudioSegment.from_wav(file_path)
        # 转换为毫秒
        start_ms = start_time * 1000
        end_ms = end_time * 1000
        segment = audio[start_ms:end_ms]
        segment.export(output_path, format="wav")
        return True
    except Exception as e:
        print(f"[ERROR] 提取音频片段失败: {e}")
        return False

def recognize_chunk(file_path, lang="en-US"):
    """
    调用 Azure Speech SDK 识别单个音频片段
    """
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = lang
    audio_config = speechsdk.AudioConfig(filename=file_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = recognizer.recognize_once_async().get()
    print(f"{file_path}: {result}")
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text.strip()
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print(f"[WARN] No speech recognized in {os.path.basename(file_path)}")
        return ""
    elif result.reason == speechsdk.ResultReason.Canceled:
        print(f"[ERROR] Recognition canceled: {result.cancellation_details.reason}")
        print(f"Details: {result.cancellation_details.error_details}")
        return ""
    return ""

def segment_already_processed(audio_path, start, end):
    """检查该段音频是否已识别过"""
    for entry in existing_entries:
        if os.path.abspath(entry.get("path", "")) == os.path.abspath(audio_path):
            if abs(entry.get("start_time", -1) - start) < 1e-3 and \
            abs(entry.get("end_time", -1) - end) < 1e-3:
                return True
    return False

if __name__ == '__main__':
    model_name = "Azure"
    speech_root = r"E:\\MLASR\\testbatch_processed\\testbatch_processed"
    prelabel_root = r"E:\MLASR\试标注汇总"
    output_root = r"E:\MLASR\Multilingual-ASR-Benchmark\results"
    
    lang_map = {
        "ARE": "ar-AE", "DZA": "ar-DZ", "EGY": "ar-EG", "IRQ": "ar-IQ", "MAR": "ar-MA",
        "SAU": "ar-SA", "MYS": "ms-MY", "THA": "th-TH", "IDN": "id-ID", "PHL": "fil-PH",
        "VNM": "vi-VN", "KOR": "ko-KR", "JPN": "ja-JP",
    }

    os.makedirs(output_root, exist_ok=True)

    for lang_folder in sorted(os.listdir(speech_root)):
        lang_path = os.path.join(speech_root, lang_folder)
        if not os.path.isdir(lang_path):
            continue

        lang_code = lang_map.get(lang_folder)
        if not lang_code:
            print(f"[SKIP] 未配置语种代码：{lang_folder}")
            continue

        output_json = os.path.join(output_root, f"{lang_folder}_Azure.json")
        print(f"\n=== 🌍 处理语种: {lang_folder} ({lang_code}) ===")

        # 收集所有音频或视频文件
        file_list = []
        for root, _, files in os.walk(lang_path):
            for f in files:
                if f.lower().endswith(".wav"):
                    if f.lower().find("chunk_") != -1:
                        continue
                    file_list.append(os.path.join(root, f))
        print(f"[INFO] 共发现 {len(file_list)} 个文件。")

        for idx, file_path in enumerate(file_list, 1):
            
            file_name = os.path.basename(file_path)
            print(f"\n[INFO] ({idx}/{len(file_list)}) 正在处理 {file_name}")

            # 读取已有结果（如果存在）
            existing_entries = []
            output_json = os.path.join(output_root, f"{lang_folder}_{model_name}.json")

            if os.path.exists(output_json):
                try:
                    with open(output_json, "r", encoding="utf-8") as f:
                        existing_entries = json.load(f)
                except Exception:
                    existing_entries = []
            
            

            # 视频转音频（保存在同目录）
            json_path = os.path.join(prelabel_root, os.path.relpath(file_path, speech_root).replace(".wav", ".json"))
            with open(json_path, "r", encoding="utf-8") as rf:
                prelabel_json = json.load(rf)
            # 处理每个片段
            for segment_idx, prelabel_item in enumerate(prelabel_json.get("segments", [])):
                start, end = prelabel_item["start"], prelabel_item["end"]
                prelabel = prelabel_item["text"]
                print(f"[INFO] 处理片段 {segment_idx + 1}: {start:.2f}s - {end:.2f}s")
                
                if segment_already_processed(file_path, start, end):
                    print(f"[SKIP] 片段已识别，跳过 {start:.2f}-{end:.2f}s")
                    continue

                # 创建临时文件用于存储音频片段
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_path = temp_file.name

                try:
                    # 提取音频片段
                    if extract_audio_segment(file_path, start, end, temp_path):
                        # 识别音频片段
                        recognized_text = recognize_chunk(temp_path, lang_code)
                        
                        # 将片段识别结果添加到完整文本中
                        utils.save_transcription(
                            audio_path=file_path,
                            text=recognized_text,
                            language=lang_folder,
                            model=model_name,
                            start_time=start,
                            end_time=end
                        )
                        print(f"[SUCCESS] 片段 {segment_idx + 1} 识别完成: {recognized_text} 参考：{prelabel}")
                    else:
                        print(f"[ERROR] 提取音频片段失败: {start:.2f}s - {end:.2f}s")
                        
                except Exception as e:
                    print(f"[ERROR] 处理片段失败: {e}")
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)

            # 保存整个文件的识别结果
            print(f"[SUCCESS] 完成: {file_name}")