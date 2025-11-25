import os
import json
import torch
import librosa
import soundfile as sf
import nemo.collections.asr as nemo_asr
from pathlib import Path
from tqdm import tqdm
from utils import save_transcription
from typing import List

class ParakeetASRProcessor:
    def __init__(self, model_path: str):
        """初始化包含静音片段处理的ASR处理器"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("⏳ Loading Parakeet-TDT model with silence preservation...")
        
        self.model_path = os.path.expanduser(model_path)
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found at: {self.model_path}")
        
        self.model = nemo_asr.models.ASRModel.restore_from(self.model_path).to(self.device)
        print(f"✅ Model loaded on {self.device}")

    def _process_segment(self, audio_path: str, start: float, end: float) -> str:
        """处理音频片段（包含静音检测）"""
        temp_dir = "temp_silence_segments"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_{start:.2f}-{end:.2f}.wav")
        
        y, _ = librosa.load(audio_path, sr=16000, offset=start, duration=end-start, mono=True)
        sf.write(temp_path, y, 16000)
        return temp_path

    def _transcribe(self, audio_path: str) -> str:
        """总是返回文本（静音片段返回空字符串）"""
        try:
            results: List[List[str]] = self.model.transcribe([audio_path])
            return results[0][0].strip() if results[0][0].strip() else ""
        except Exception as e:
            print(f"⚠️ Transcription error (treated as silence): {str(e)}")
            return ""

    def process_file(self, audio_path: str, label_path: str):
        """处理文件（强制处理所有片段）"""
        lang = Path(audio_path).parent.name.upper() if Path(audio_path).parent.name.isalpha() else "JPN"
        
        try:
            with open(label_path, 'r',encoding='utf-8') as f:
                segments = json.load(f).get("segments", [])
        except Exception as e:
            print(f"⚠️ Label load failed: {label_path} - {str(e)}")
            return
        
        print(f"\n🔊 Processing {Path(audio_path).name} [{lang}] (including silence)")
        
        for seg in tqdm(segments, desc="Processing ALL segments"):
            try:
                tmp_audio = self._process_segment(audio_path, seg["start"], seg["end"])
                text = self._transcribe(tmp_audio)
                
                save_transcription(
                    audio_path=audio_path,
                    text=text,  # 静音片段会自动保存为 ""
                    language=lang,
                    model="parakeet-tdt_ctc-0.6b-ja",
                    start_time=seg["start"],
                    end_time=seg["end"]
                )
                os.remove(tmp_audio)
            except Exception as e:
                print(f"⚠️ Segment failed {seg}: {str(e)}")
                # 即使失败也保存空记录
                save_transcription(
                    audio_path=audio_path,
                    text="",
                    language=lang,
                    model="parakeet-tdt_ctc-0.6b-ja",
                    start_time=seg["start"],
                    end_time=seg["end"]
                )

def main():
    CONFIG = {
        "audio_dir": "/root/shared-nvme/data/ASRBench/testbatch_processed/JPN",
        "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/labeled/JPN",
        "model_path": "~/.cache/huggingface/hub/models--nvidia--parakeet-tdt_ctc-0.6b-ja/snapshots/44edb27eea9317daf89333e75eb830db4b1cc298/parakeet-tdt_ctc-0.6b-ja.nemo"
    }
    
    try:
        asr = ParakeetASRProcessor(CONFIG["model_path"])
    except Exception as e:
        print(f"❌ Init failed: {str(e)}")
        return
    
    success = 0
    for root, _, files in os.walk(CONFIG["audio_dir"]):
        for f in files:
            if not f.lower().endswith('.wav'):
                continue
                
            audio = os.path.join(root, f)
            rel_path = os.path.relpath(audio, CONFIG["audio_dir"])
            label = os.path.join(CONFIG["label_dir"], rel_path.replace('.wav', '.json'))
            
            if os.path.exists(label):
                asr.process_file(audio, label)
                success += 1
    
    print(f"\n🎉 Completed! Processed {success} files (silence preserved)")

if __name__ == "__main__":
    main()
