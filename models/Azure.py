import os
import time
import json
import azure.cognitiveservices.speech as speechsdk

SPEECH_KEY = ""
SPEECH_REGION = "westus"

done = False
transcribed_text = ""

def stop_cb(evt):
    print('CLOSING on {}'.format(evt))
    global done
    done = True

def recognized_cb(evt):
    global transcribed_text
    if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
        transcribed_text += evt.result.text + "\n"
        print(f"RECOGNIZED: {evt.result.text}")
    elif evt.result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized")
    elif evt.result.reason == speechsdk.ResultReason.Canceled:
        print("Recognition canceled: {}".format(evt.result.cancellation_details))

def from_file(file_path):
    global done, transcribed_text
    transcribed_text = ""  
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = "ar-DZ"  

    audio_config = speechsdk.AudioConfig(filename=file_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    # 绑定事件
    speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
    speech_recognizer.recognized.connect(recognized_cb)  
    speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
    speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))

    # 结束时的回调
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # 开始连续识别
    speech_recognizer.start_continuous_recognition()

    # 等待直到识别完成
    while not done:
        time.sleep(0.5)

    return transcribed_text.strip()  # 返回识别的文本，去掉多余的空白

def append_result_to_json(result, json_path):
    """将单条转录结果追加写入 JSON 文件"""
    data = []
    
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"[WARN] 文件 {json_path} 内容为空或格式错误，重新创建")

    data.append(result)

    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def process_audio_files(input_dir="/root/shared-nvme/yujietu/Arabic", output_json="/root/shared-nvme/yujietu/ASR-API/API/Azure/results.json"):
    os.makedirs(os.path.dirname(output_json), exist_ok=True)

    
    files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)) and f.lower().endswith((".wav", ".mp3", ".m4a"))]
    total_files = len(files)

    if total_files == 0:
        print("[INFO] 没有找到音频文件.")
        return

    print(f"[INFO] 总共找到 {total_files} 个音频文件，开始处理...")

    for idx, file_name in enumerate(files, 1):
        file_path = os.path.join(input_dir, file_name)

        
        if os.path.exists(output_json):
            with open(output_json, "r", encoding="utf-8") as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
            if any(entry.get("file_name") == file_name for entry in existing_data):
                print(f"[SKIP] 结果已存在，跳过: {file_name}")
                continue

        print(f"[INFO] 正在处理 {file_name} ({idx}/{total_files})")

        global done
        done = False
        text = from_file(file_path)

        if text:
            result_entry = {
                "file_name": file_name,
                "transcription": text
            }
            append_result_to_json(result_entry, output_json)
            print(f"[SUCCESS] 转录写入完成: {file_name}")

        
        progress = (idx / total_files) * 100
        print(f"[PROGRESS] 处理进度: {progress:.2f}%")

if __name__ == '__main__':
    process_audio_files()
