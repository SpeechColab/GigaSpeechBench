import os
import json
import torch
import librosa
import soundfile as sf
import nemo.collections.asr as nemo_asr
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict, Any
from utils import save_transcription

class ParakeetASRProcessor:
    def __init__(self, model_path: str):
        """日语ASR处理器（自动跳过无效片段）"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("⏳ 加载日语模型...")
        
        self.model_path = os.path.expanduser(model_path)
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"模型文件未找到: {self.model_path}")
        
        self.model = nemo_asr.models.ASRModel.restore_from(self.model_path).to(self.device)
        print(f"✅ 模型已加载 ({self.device})")

    def _process_segment(self, audio_path: str, start: float, end: float) -> str:
        """处理音频片段"""
        temp_dir = "temp_jpn_segments"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_{start:.2f}-{end:.2f}.wav")
        
        y, sr = librosa.load(audio_path, sr=16000, offset=start, duration=end-start, mono=True)
        sf.write(temp_path, y, sr)
        return temp_path

    def _transcribe(self, audio_path: str) -> str:
        """转录日语片段"""
        try:
            results: List[List[str]] = self.model.transcribe([audio_path])
            return results[0][0].strip()
        except Exception as e:
            print(f"⚠️ 转录异常: {str(e)}")
            return ""

    def _is_silent_segment(self, segment: Dict[str, Any]) -> bool:
        """判断是否为静音/无效片段"""
        # 条件1: 明确标记为invalid状态
        return (
            segment.get("status", "") == "invalid" 
        )

    def process_file(self, audio_path: str, label_path: str):
        """处理音频文件（自动跳过无效片段）"""
        lang = Path(audio_path).parent.name.upper() if Path(audio_path).parent.name.isalpha() else "JPN"
        
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                segments = json.load(f).get("segments", [])
        except Exception as e:
            print(f"⚠️ 标签读取失败: {label_path} - {str(e)}")
            return
        
        print(f"\n🔊 处理 {Path(audio_path).name} [{lang}]")
        
        silent_count = 0
        processed_count = 0
        
        for seg in tqdm(segments, desc="分段处理"):
            # 跳过静音/无效片段
            if self._is_silent_segment(seg):
                silent_count += 1
                continue
                
            try:
                tmp_audio = self._process_segment(audio_path, seg["start"], seg["end"])
                text = self._transcribe(tmp_audio)
                
                save_transcription(
                    audio_path=audio_path,
                    text=text,
                    language=lang,
                    model="nvidia-nemo",
                    start_time=seg["start"],
                    end_time=seg["end"],
                )
                processed_count += 1
                if os.path.exists(tmp_audio):
                    os.remove(tmp_audio)
            except Exception as e:
                print(f"⚠️ 分段异常 [{seg['start']}-{seg['end']}s]: {str(e)}")
                # 保存失败的转录（空文本）
                save_transcription(
                    audio_path=audio_path,
                    text="",
                    language=lang,
                    model="nvidia-nemo",
                    start_time=seg["start"],
                    end_time=seg["end"],
                )
                processed_count += 1
        
        print(f"  已跳过 {silent_count} 个静音片段，处理了 {processed_count} 个有效片段")

def main():
    CONFIG = {
        "audio_dir": "/root/shared-nvme/haoranwang/nemo_asr/audio_processed/JPN",
        "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/asr/JPN",
        "model_path": "/root/shared-nvme/haoranwang/nemo_asr/model/parakeet-tdt_ctc-0.6b-ja.nemo"
    }
    
    try:
        asr = ParakeetASRProcessor(CONFIG["model_path"])
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        return
    
    processed_files = 0
    for root, _, files in os.walk(CONFIG["audio_dir"]):
        for file in files:
            if not file.lower().endswith('.wav'):
                continue
                
            audio_file = os.path.join(root, file)
            rel_path = os.path.relpath(audio_file, CONFIG["audio_dir"])
            label_file = os.path.join(CONFIG["label_dir"], rel_path.replace('.wav', '.json'))
            
            if os.path.exists(label_file):
                asr.process_file(audio_file, label_file)
                processed_files += 1
    
    print(f"\n🎉 完成! 共处理 {processed_files} 个文件")

if __name__ == "__main__":
    main()

