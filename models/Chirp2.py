import os
import json
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions

PROJECT_ID = "asr-chirp"
OUTPUT_JSON_PATH = "/root/shared-nvme/yujietu/ASR-API/API/Chirp/results.json"

def transcribe_sync_chirp2(audio_file: str) -> cloud_speech.RecognizeResponse:
    """使用 Google Cloud Speech-to-Text V2 API 的 Chirp 2 模型转录音频文件。"""
    client = SpeechClient(
        client_options=ClientOptions(api_endpoint="us-central1-speech.googleapis.com")
    )

    with open(audio_file, "rb") as f:
        audio_content = f.read()

    config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        language_codes=["ar-EG"],
        model="chirp_2",
    )

    request = cloud_speech.RecognizeRequest(
        recognizer=f"projects/{PROJECT_ID}/locations/us-central1/recognizers/_",
        config=config,
        content=audio_content,
    )

    response = client.recognize(request=request)
    return response

def process_audio_files(input_folder: str):
    """
    处理给定文件夹中的所有 .wav 文件，并将文件名和转录结果实时保存到单个 JSON 文件中。
    """
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)

    results = []
    if os.path.exists(OUTPUT_JSON_PATH):
        try:
            with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
                results = json.load(f)
            print(f"已从 {OUTPUT_JSON_PATH} 加载现有数据。")
        except json.JSONDecodeError:
            print(f"警告：{OUTPUT_JSON_PATH} 不是有效的 JSON 文件。将从空列表开始。")
            results = []
    
    processed_files = {item['file_name'] for item in results}

    try:
        wav_files = [f for f in os.listdir(input_folder) if f.endswith(".wav")]
        total_files = len(wav_files)
        if total_files == 0:
            print("文件夹中没有找到 .wav 文件。")
            return

        for idx, wav_file in enumerate(wav_files, 1):
            if wav_file in processed_files:
                print(f"跳过已存在的文件 {idx}/{total_files}：{wav_file} (已在 JSON 中)。")
                continue

            input_path = os.path.join(input_folder, wav_file)

            print(f"正在处理文件 {idx}/{total_files}：{wav_file}...")
            try:
                response = transcribe_sync_chirp2(input_path)
                transcription = "\n".join(result.alternatives[0].transcript for result in response.results)
                
                results.append({
                    "file_name": wav_file,
                    "transcription": transcription
                })
                print(f"已处理 {wav_file}。")

                with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as output_json_file:
                    json.dump(results, output_json_file, ensure_ascii=False, indent=4)
                print(f"已将当前结果保存到 {OUTPUT_JSON_PATH}。")

            except Exception as e:
                print(f"未能处理 {wav_file}：{e}")
                continue
    except Exception as e:
        print(f"处理文件时出错：{e}")

# 设置输入文件夹路径
input_folder = "/root/shared-nvme/yujietu/Arabic"

# 调用函数开始处理
process_audio_files(input_folder)