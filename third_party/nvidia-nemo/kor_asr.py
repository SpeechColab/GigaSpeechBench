import os
import json
import torch
import librosa
import soundfile as sf
import nemo.collections.asr as nemo_asr
from pathlib import Path
from tqdm import tqdm
from typing import List, Optional
from utils import save_transcription

class KoreanASRProcessor:
    def __init__(self, model_path: str):
        """保留静音片段的韩语ASR处理器"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("⏳ 加载韩语模型...")
        
        self.model_path = os.path.expanduser(model_path)
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"模型文件未找到，请检查路径: {self.model_path}")
        
        self.model = nemo_asr.models.ASRModel.restore_from(self.model_path).to(self.device)
        print(f"✅ 模型已加载 ({self.device})")

    def _process_audio_segment(self, audio_path: str, start: float, end: float) -> Optional[str]:
        """生成临时音频片段，若静音则返回None"""
        temp_dir = "temp_kor_segments"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_{start:.2f}-{end:.2f}.wav")
        
        # 读取时直接检测静音
        y, sr = librosa.load(audio_path, sr=16000, offset=start, duration=end-start, mono=True)
        if librosa.effects.split(y, top_db=30)[0].size == 0:  # 静音检测阈值
            return None
        sf.write(temp_path, y, sr)
        return temp_path

    def _transcribe_korean(self, audio_path: Optional[str]) -> str:
        """处理静音/非静音片段"""
        if audio_path is None:  # 静音片段
            return ""
        try:
            with torch.inference_mode():
                results: List[List[str]] = self.model.transcribe([audio_path])
            return results[0][0].strip()
        except Exception as e:
            print(f"⚠️ 转录异常: {str(e)}")
            return ""

    def process_file(self,audio_path: str, label_path: str):
        """处理文件（强制保留所有分段）"""
        lang = Path(audio_path).parent.name.upper()[:3] if Path(audio_path).parent.name.isalpha() else "KOR"
        
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                segments = json.load(f).get("segments", [])
        except Exception as e:
            print(f"⚠️ 标签读取失败: {label_path} - {str(e)}")
            return
        
        print(f"\n🔊 处理 {Path(audio_path).name} [{lang}]")
        
        for seg in tqdm(segments, desc="分段处理"):
            # 不再过滤无效片段！
            try:
                tmp_audio = self._process_audio_segment(audio_path, seg["start"], seg["end"])
                text = self._transcribe_korean(tmp_audio)
                
                save_transcription(
                    audio_path=audio_path,
                    text=text,  # 静音片段会自动存为 ""
                    language=lang,
                    model="stt_kr_conformer_transducer_large",
                    start_time=seg["start"],
                    end_time=seg["end"]
                )
                if tmp_audio and os.path.exists(tmp_audio):
                    os.remove(tmp_audio)
            except Exception as e:
                print(f"⚠️ 分段异常 [{seg['start']}-{seg['end']}s]: {str(e)}")

def main():
    CONFIG = {
        "audio_dir": "/root/shared-nvme/data/ASRBench/testbatch_processed/KOR",
        "label_dir": "/root/shared-nvme/haoranwang/nemo_asr/labeled/KOR",
        "model_path": "/root/.cache/huggingface/hub/models--eesungkim--stt_kr_conformer_transducer_large/snapshots/fdc8412fe0d089913524767b20ff244ff1007ed0/stt_kr_conformer_transducer_large.nemo"
    }
    
    try:
        asr = KoreanASRProcessor(CONFIG["model_path"])
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        return
    
    processed_files = 0
    for root, _, files in os.walk(CONFIG["audio_dir"]):
        for file in files:
            if not file.lower().endswith(('.wav', '.flac')):
                continue
                
            audio_file = os.path.join(root, file)
            rel_path = os.path.relpath(audio_file, CONFIG["audio_dir"])
            label_file = os.path.join(CONFIG["label_dir"], rel_path.replace('.wav', '.json').replace('.flac', '.json'))
            
            if os.path.exists(label_file):
                asr.process_file(audio_file, label_file)
                processed_files += 1
    
    print(f"\n🎉 完成! 共处理 {processed_files} 个文件（包含静音片段）")

if __name__ == "__main__":
    main()
