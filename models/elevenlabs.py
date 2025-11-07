import os
import argparse
import json
from io import BytesIO
from elevenlabs.client import ElevenLabs

def transcribe_audio(input_folder, output_json_path):
    client = ElevenLabs(api_key="")

    output_dir = os.path.dirname(output_json_path)
    os.makedirs(output_dir, exist_ok=True)

    all_transcriptions = []

    wav_files = [f for f in os.listdir(input_folder) if f.endswith(".wav")]
    total_files = len(wav_files)

    if total_files == 0:
        print("没有找到 .wav 文件。")
        return

    if os.path.exists(output_json_path):
        try:
            with open(output_json_path, 'r', encoding='utf-8') as f:
                all_transcriptions = json.load(f)
            print(f"已从 {output_json_path} 加载现有转录。")
        except json.JSONDecodeError:
            print(f"警告：无法解析 {output_json_path}。将从头开始创建。")
            all_transcriptions = []
    
    transcribed_ids = {item['id'] for item in all_transcriptions}

    for index, wav_file in enumerate(wav_files, start=1):
        file_id = os.path.splitext(wav_file)[0] 
        input_path = os.path.join(input_folder, wav_file)

        if file_id in transcribed_ids:
            print(f"文件 {wav_file} (ID: {file_id}) 已经转录，跳过。")
            continue

        print(f"处理进度: {index}/{total_files} - {wav_file}") 

        try:
            with open(input_path, "rb") as audio_file:
                audio_data = audio_file.read()

            transcription_result = client.speech_to_text.convert(
                file=BytesIO(audio_data),
                model_id="scribe_v1",
                tag_audio_events=False,
                language_code="ara",
                diarize=False,
            )

            all_transcriptions.append({
                "id": file_id,
                "text": transcription_result.text
            })
            transcribed_ids.add(file_id) 

            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(all_transcriptions, f, ensure_ascii=False, indent=4)
            print(f"已将 {wav_file} 的转录添加到 {output_json_path}。")

        except Exception as e:
            print(f"处理 {wav_file} 时出错: {e}")
            
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(all_transcriptions, f, ensure_ascii=False, indent=4)
    print(f"所有文件处理完毕。最终结果保存在 {output_json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量转录 WAV 文件并保存到 JSON 文件")
    parser.add_argument("--input", type=str, default="/root/shared-nvme/yujietu/Arabic", help="输入文件夹路径")
    parser.add_argument("--output_json", type=str, default="/root/shared-nvme/yujietu/ASR-API/API/elevenlabs/results.json", help="输出 JSON 文件路径")

    args = parser.parse_args()
    transcribe_audio(args.input, args.output_json)