import os
import json
import torch
import librosa
import soundfile as sf
from nemo.collections.asr.models import EncDecHybridRNNTCTCModel
from utils import save_transcription
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

class CountryASRProcessor:
    def __init__(self, model_path: str):
        """初始化ASR处理器"""
        self.model = EncDecHybridRNNTCTCModel.restore_from(model_path)
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)
        print(f"✅ Model loaded on {self.device}")
        
    def _clean_text(self, text):
        """清理转录文本为纯字符串"""
        if isinstance(text, (list, tuple)):
            if len(text) > 0:
                if isinstance(text[0], (list, tuple)):
                    return str(text[0][0]) if len(text[0]) > 0 else ""
                return str(text[0])
            return ""
        return str(text)

    def _extract_segment(self, audio_path: str, start: float, end: float) -> str:
        """创建临时音频片段"""
        temp_dir = "temp_segments"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_{start:.2f}-{end:.2f}.wav")
        y, sr = librosa.load(audio_path, sr=None, offset=start, duration=end-start)
        sf.write(temp_path, y, sr)
        return temp_path

    def transcribe_segment(self, audio_path: str, segment: dict) -> dict:
        """转录单个片段"""
        result = {
            "path": audio_path,
            "start_time": segment["start"],
            "end_time": segment["end"],
            "language": "",  # 将由主流程填充
            "model": "stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo",
            "text": ""
        }
        
        if segment.get("status") == "valid":
            try:
                temp_path = self._extract_segment(audio_path, segment["start"], segment["end"])
                transcription = self.model.transcribe([temp_path], batch_size=1)
                result["text"] = self._clean_text(transcription)
                os.remove(temp_path)
            except Exception as e:
                print(f"⚠️ Error transcribing {segment['start']:.2f}-{segment['end']:.2f}s: {str(e)}")
                result["error"] = str(e)
        
        return result

    def process_file(self, audio_path: str, label_path: str):
        """处理单个音频文件"""
        with open(label_path, 'r', encoding='utf-8') as f:
            label_data = json.load(f)
        
        country_code = os.path.basename(os.path.dirname(audio_path)).upper()
        segments = label_data.get("segments", [])
        
        print(f"\n🔊 Processing {Path(audio_path).name} [{country_code}]")
        
        for segment in tqdm(segments, desc="Transcribing segments"):
            result = self.transcribe_segment(audio_path, segment)
            result["language"] = country_code
            
            # 使用提供的utils函数保存结果
            save_transcription(
                audio_path=result["path"],
                text=result["text"],
                language=result["language"],
                model="stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo",
                start_time=result["start_time"],
                end_time=result["end_time"]
            )

def process_dataset(audio_dir: str, label_dir: str, model_path: str):
    """处理整个数据集"""
    processor = CountryASRProcessor(model_path)
    
    for root, _, files in os.walk(audio_dir):
        for file in files:
            if file.lower().endswith('.wav'):
                audio_path = os.path.join(root, file)
                
                # 构建标签路径
                rel_path = os.path.relpath(audio_path, audio_dir)
                country_dir = os.path.basename(os.path.dirname(rel_path))
                label_file = os.path.splitext(file)[0] + '.json'
                label_path = os.path.join(label_dir, country_dir, label_file)
                
                if os.path.exists(label_path):
                    processor.process_file(audio_path, label_path)
                else:
                    print(f"⚠️ Label missing: {label_path}")

if __name__ == "__main__":
    CONFIG = {
        "model_path": "/root/shared-nvme/haoranwang/nemo_asr/stt_ar_fastconformer_hybrid_large_pcd_v1.0.nemo",
        "audio_dir": "/root/shared-nvme/data/ASRBench/testbatch_processed/DZA",
        "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/labeled/DZA"
    }
    
    process_dataset(**CONFIG)
    print("\n✅ All files processed!")
