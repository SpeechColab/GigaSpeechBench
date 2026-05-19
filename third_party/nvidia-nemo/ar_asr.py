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
        """Arabic ASR processor (auto-skip invalid segments)"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("⏳ Loading Arabic model...")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        self.model = EncDecHybridRNNTCTCModel.restore_from(model_path).to(self.device)
        self.model.eval()
        print(f"✅ Model loaded ({self.device})")
        
    def _is_silent_segment(self, segment: Dict[str, Any]) -> bool:
        """Check whether a segment is invalid"""
        return (
            segment.get("status", "") == "invalid" 
        )

    def _clean_text(self, text) -> str:
        """Clean up transcription text to a pure string"""
        if isinstance(text, (list, tuple)):
            if len(text) > 0:
                if isinstance(text[0], (list, tuple)):
                    return str(text[0][0]) if len(text[0]) > 0 else ""
                return str(text[0])
            return ""
        return str(text)

    def _process_segment(self, audio_path: str, start: float, end: float) -> str:
        """Create a temporary audio segment"""
        temp_dir = "temp_ara_segments"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_{start:.2f}-{end:.2f}.wav")
        y, sr = librosa.load(audio_path, sr=None, offset=start, duration=end-start)
        sf.write(temp_path, y, sr)
        return temp_path

    def _transcribe_segment(self, audio_path: str) -> Optional[str]:
        """Transcribe a single audio segment"""
        try:
            transcription = self.model.transcribe([audio_path], batch_size=1)
            return self._clean_text(transcription)
        except Exception as e:
            print(f"⚠️ Transcription error: {str(e)}")
            return None

    def process_file(self, audio_path: str, label_path: str):
        """Process a single audio file"""
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                segments = json.load(f).get("segments", [])
        except Exception as e:
            print(f"⚠️ Label read failed: {label_path} - {str(e)}")
            return
        
        country_code = Path(audio_path).parent.name.upper()
        silent_count = 0
        processed_count = 0
        
        print(f"\n🔊 Processing {Path(audio_path).name} [{country_code}]")
        
        for seg in tqdm(segments, desc="Processing segments"):
            # Skip silent/invalid segments
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
                print(f"⚠️ Segment error [{seg['start']}-{seg['end']}s]: {str(e)}")
                save_transcription(
                    audio_path=audio_path,
                    text="",
                    language=country_code,
                    model="stt_ar_fastconformer_hybrid_large",
                    start_time=seg["start"],
                    end_time=seg["end"],
                )
                processed_count += 1
        
        print(f"  Skipped {silent_count} silent segments, processed {processed_count} valid segments")

def process_dataset(audio_dir: str, label_dir: str, model_path: str):
    """Process entire dataset"""
    try:
        asr = ArabicASRProcessor(model_path)
    except Exception as e:
        print(f"❌ Initialization failed: {str(e)}")
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
                print(f"⚠️ Label file not found: {label_file}")
    
    print(f"\n🎉 Completed! Processed {processed_files} files in total")

if __name__ == "__main__":
    CONFIG = {
        "model_path": "/path/to/nemo_asr/model/stt_ar_fastconformer_hybrid_large_pcd_v1ureau.0.nemo",
        "audio_dir": "/path/to/nemo_asr/audio_processed/DZA",
        "label_dir": "/path/to/nemo_asr/asr/20251219/DZA"
    }
    
    process_dataset(**CONFIG)

