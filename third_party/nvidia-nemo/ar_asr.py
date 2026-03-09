import os
import json
import torch
import librosa
import soundfile as sf
from nemo.collections.asr.models import EncDecHybridRNNTCTCModel
from utils import save_transcription
from pathlib import Path
from tqdm import tqdm
from typing import Dict, Any, Optional

class ArabicASRProcessor:
    def __init__(self, model_path: str):
        """阿拉伯语ASR处理器（自动跳过无效片段）"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("⏳ 加载阿拉伯语模型...")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件未找到: {model_path}")
        
        self.model = EncDecHybridRNNTCTCModel.restore_from(model_path).to(self.device)
        self.model.eval()
        print(f"✅ 模型已加载 ({self.device})")
        
    def _is_silent_segment(self, segment: Dict[str, Any]) -> bool:
        """判断是否为无效片段"""
        return (
            segment.get("status", "") == "invalid" 
        )

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
        temp_dir = "temp_ara_segments"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_{start:.2f}-{end:.2f}.wav")
        y, sr = librosa.load(audio_path, sr=None, offset=start, duration=end-start)
        sf.write(temp_path, y, sr)
        return temp_path

    def _transcribe_segment(self, audio_path: str) -> Optional[str]:
        """转录单个音频片段"""
        try:
            transcription = self.model.transcribe([audio_path], batch_size=1)
            return self._clean_text(transcription)
        except Exception as e:
            print(f"⚠️ 转录异常: {str(e)}")
            return None

    def process_file(self, audio_path: str, label_path: str):
        """处理单个音频文件"""
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                segments = json.load(f).get("segments", [])
        except Exception as e:
            print(f"⚠️ 标签读取失败: {label_path} - {str(e)}")
            return
        
        country_code = Path(audio_path).parent.name.upper()
        silent_count = 0
        processed_count = 0
        
        print(f"\n🔊 处理 {Path(audio_path).name} [{country_code}]")
        
        for seg in tqdm(segments, desc="分段处理"):
            # 跳过静音/无效片段
            if self._is_silent_segment(seg):
                silent_count += 1
                continue
                
            try:
                tmp_audio = self._process_segment(audio_path, seg["start"], seg["end"])
                text = self._transcribe_segment(tmp_audio)
                
                save_transcription(
                    audio_path=audio_path,
                    text=text if text is not None else "",
                    language=country_code,
                    model="stt_ar_fastconformer_hybrid_large",
                    start_time=seg["start"],
                    end_time=seg["end"],
                )
                processed_count += 1
                if os.path.exists(tmp_audio):
                    os.remove(tmp_audio)
            except Exception as e:
                print(f"⚠️ 分段异常 [{seg['start']}-{seg['end']}s]: {str(e)}")
                save_transcription(
                    audio_path=audio_path,
                    text="",
                    language=country_code,
                    model="stt_ar_fastconformer_hybrid_large",
                    start_time=seg["start"],
                    end_time=seg["end"],
                )
                processed_count += 1
        
        print(f"  已跳过 {silent_count} 个静音片段，处理了 {processed_count} 个有效片段")

def process_dataset(audio_dir: str, label_dir: str, model_path: str):
    """处理整个数据集"""
    try:
        asr = ArabicASRProcessor(model_path)
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        return
    
    processed_files = 0
    for root, _, files in os.walk(audio_dir):
        for file in files:
            if not file.lower().endswith('.wav'):
                continue
                
            audio_file = os.path.join(root, file)
            rel_path = os.path.relpath(audio_file, audio_dir)
            label_file = os.path.join(label_dir, rel_path.replace('.wav', '.json'))
            
            if os.path.exists(label_file):
                asr.process_file(audio_file, label_file)
                processed_files += 1
            else:
                print(f"⚠️ 标签文件未找到: {label_file}")
    
    print(f"\n🎉 完成! 共处理 {processed_files} 个文件")

if __name__ == "__main__":
    CONFIG = {
        "model_path": "/root/shared-nvme/haoranwang/nemo_asr/model/stt_ar_fastconformer_hybrid_large_pcd_v1ureau.0.nemo",
        "audio_dir": "/root/shared-nvme/haoranwang/nemo_asr/audio_processed/DZA",
        "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/asr/20251219/DZA"
    }
    
    process_dataset(**CONFIG)

