#!/usr/bin/env python3
import os
import json
import glob
import argparse
import librosa
import torch
import soundfile as sf
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List
from nemo.collections.asr.models import ASRModel

def save_transcription(
    audio_path: str,
    text: str,
    language: str,
    model: str,
    start_time: float,
    end_time: float
) -> None:
    """
    保存转录结果到/results/{language}_{model}.json文件
    字段调整为audio_name格式，其他保持不变
    """
    results_dir = os.path.join(os.getcwd(), "results")
    os.makedirs(results_dir, exist_ok=True)

    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    # 生成audio_name格式：ARE#UC_p5qypAZQAUkgtjoJk5_Bg#fLqRbOYZsHY#raw.wav
    audio_name = f"{Path(audio_path).stem}#raw.wav"

    entry = {
        "audio_name": audio_name,  # 使用简化音频名格式
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
                        raise ValueError("Invalid JSON structure")
        except Exception as e:
            print(f"[WARN] Failed to read existing JSON ({output_path}), recreating. Reason: {e}")

    data.append(entry)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class DialectChineseASRProcessor:
    def __init__(self, model_path: str):
        """中文方言ASR处理器（仅处理valid片段，纯ASR结果）"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("⏳ 加载中文方言ASR模型...")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型未找到: {model_path}")
        
        self.model = ASRModel.restore_from(model_path).to(self.device)
        self.model.eval()
        print(f"✅ 模型加载完成 ({self.device})")

    def _clean_text(self, text) -> str:
        """清理转录文本为纯字符串"""
        if isinstance(text, (list, tuple)):
            if len(text) > 0:
                if isinstance(text[0], (list, tuple)):
                    return str(text[0][0]) if len(text[0]) > 0 else ""
                return str(text[0])
            return ""
        return str(text)

    def _process_segment(self, audio_path: str, start: float, end: float) -> str:
        """创建临时音频片段"""
        temp_dir = "temp_chinese_segments"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_{start:.2f}-{end:.2f}.wav")
        y, sr = librosa.load(audio_path, sr=16000, offset=start, duration=end-start)
        sf.write(temp_path, y, sr)
        return temp_path

    def _transcribe_segment(self, audio_path: str) -> str:
        """转录单个音频片段，只返回ASR结果"""
        try:
            transcription = self.model.transcribe([audio_path], batch_size=1)
            return self._clean_text(transcription)
        except Exception as e:
            print(f"⚠️ 转录错误: {str(e)}")
            return ""

    def process_file(self, audio_path: str, label_path: str):
        """处理单个音频文件（仅处理status=valid的片段）"""
        # 从路径提取方言标识
        dialect = Path(audio_path).parent.name.upper()
        valid_dialects = {"JIN", "XIANG"}
        
        if dialect not in valid_dialects:
            dialect = "ZH"  # 默认标记为中文
            
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                label_data = json.load(f)
                segments = label_data.get("segments", [])
        except Exception as e:
            print(f"⚠️ 标签加载失败: {label_path} - {str(e)}")
            return
        
        print(f"\n🔊 处理文件: {Path(audio_path).name} [{dialect}]")
        
        valid_count = 0
        processed_count = 0
        
        for seg in tqdm(segments, desc="处理有效片段"):
            if seg.get("status") != "valid":
                continue
                
            valid_count += 1
            try:
                tmp_audio = self._process_segment(audio_path, seg["start"], seg["end"])
                asr_text = self._transcribe_segment(tmp_audio)
                
                save_transcription(
                    audio_path=audio_path,
                    text=asr_text,
                    language=dialect,
                    model="nvidia-nemo",
                    start_time=seg["start"],
                    end_time=seg["end"]
                )
                processed_count += 1
                os.remove(tmp_audio) if os.path.exists(tmp_audio) else None
            except Exception as e:
                print(f"⚠️ 片段处理错误 [{seg['start']}-{seg['end']}s]: {str(e)}")
                save_transcription(
                    audio_path=audio_path,
                    text="",
                    language=dialect,
                    model="nvidia-nemo",
                    start_time=seg["start"],
                    end_time=seg["end"]
                )
                processed_count += 1
        
        print(f"  有效片段: {valid_count}, 成功处理: {processed_count}")

def main():
    parser = argparse.ArgumentParser(description='中文方言语音识别')
    parser.add_argument("--audio_dir", type=str, required=True,
                      help="包含WAV文件的输入目录")
    parser.add_argument("--label_dir", type=str, required=True,
                      help="包含JSON标签的目录")
    args = parser.parse_args()

    # 中文ASR模型路径
    MODEL_PATH = "/root/shared-nvme/haoranwang/nemo_asr/model/stt_zh_conformer_transducer_large.nemo"

    try:
        processor = DialectChineseASRProcessor(MODEL_PATH)
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        return

    wav_files = glob.glob(os.path.join(args.audio_dir, "**/*.wav"), recursive=True)
    print(f"找到 {len(wav_files)} 个音频文件")

    success_count = 0
    for wav_path in wav_files:
        rel_path = os.path.relpath(wav_path, args.audio_dir)
        label_path = os.path.join(args.label_dir, rel_path.replace('.wav', '.json'))
        
        if not os.path.exists(label_path):
            print(f"⚠️ 标签缺失: {label_path}")
            continue
            
        try:
            processor.process_file(wav_path, label_path)
            success_count += 1
        except Exception as e:
            print(f"⚠️ 处理失败 {wav_path}: {str(e)}")

    print(f"\n🎉 处理完成. 成功处理 {success_count}/{len(wav_files)} 个文件.")
    print("结果已保存到 ./results/ 目录")

if __name__ == "__main__":
    main()