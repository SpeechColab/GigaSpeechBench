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
        """Japanese ASR processor (auto-skip invalid segments)"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("⏳ Loading Japanese model...")
        
        self.model_path = os.path.expanduser(model_path)
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        self.model = nemo_asr.models.ASRModel.restore_from(self.model_path).to(self.device)
        print(f"✅ Model loaded ({self.device})")

    def _process_segment(self, audio_path: str, start: float, end: float) -> str:
        """Process audio segment"""
        temp_dir = "temp_jpn_segments"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{Path(audio_path).stem}_{start:.2f}-{end:.2f}.wav")
        
        y, sr = librosa.load(audio_path, sr=16000, offset=start, duration=end-start, mono=True)
        sf.write(temp_path, y, sr)
        return temp_path

    def _transcribe(self, audio_path: str) -> str:
        """Transcribe a Japanese segment"""
        try:
            results: List[List[str]] = self.model.transcribe([audio_path])
            return results[0][0].strip()
        except Exception as e:
            print(f"⚠️ Transcription error: {str(e)}")
            return ""

    def _is_silent_segment(self, segment: Dict[str, Any]) -> bool:
        """Check whether a segment is silent/invalid"""
        # Condition 1: explicitly marked as invalid status
        return (
            segment.get("status", "") == "invalid" 
        )

    def process_file(self, audio_path: str, label_path: str):
        """Process audio file (auto-skip invalid segments)"""
        lang = Path(audio_path).parent.name.upper() if Path(audio_path).parent.name.isalpha() else "JPN"
        
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                segments = json.load(f).get("segments", [])
        except Exception as e:
            print(f"⚠️ Label read failed: {label_path} - {str(e)}")
            return
        
        print(f"\n🔊 Processing {Path(audio_path).name} [{lang}]")
        
        silent_count = 0
        processed_count = 0
        
        for seg in tqdm(segments, desc="Processing segments"):
            # Skip silent/invalid segments
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
                print(f"⚠️ Segment error [{seg['start']}-{seg['end']}s]: {str(e)}")
                # Save failed transcription (empty text)
                save_transcription(
                    audio_path=audio_path,
                    text="",
                    language=lang,
                    model="nvidia-nemo",
                    start_time=seg["start"],
                    end_time=seg["end"],
                )
                processed_count += 1
        
        print(f"  Skipped {silent_count} silent segments, processed {processed_count} valid segments")

def main():
    CONFIG = {
        "audio_dir": "/path/to/nemo_asr/audio_processed/JPN",
        "label_dir": "/path/to/nemo_asr/asr/JPN",
        "model_path": "/path/to/nemo_asr/model/parakeet-tdt_ctc-0.6b-ja.nemo"
    }
    
    try:
        asr = ParakeetASRProcessor(CONFIG["model_path"])
    except Exception as e:
        print(f"❌ Initialization failed: {str(e)}")
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
    
    print(f"\n🎉 Completed! Processed {processed_files} files")

if __name__ == "__main__":
    main()

