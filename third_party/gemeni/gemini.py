# pip install google-genai tqdm pydub ffmpeg-python
import os
import json
import threading
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from pydub.utils import mediainfo

from google import genai

# Import from utils save_transcription (if not available, fallback implementation below)
try:
    from utils import save_transcription
except ImportError:
    def save_transcription(audio_path, text, language, model, start_time, end_time):
        pass  # placeholder, use custom save logic

########################################  Parameter config  ########################################
API_KEY      = os.getenv("GEMINI_API_KEY")  # set via environment variable
ROOT_DIR     = "/path/to/audio_root"    # Root directory for audio to transcribe
TESTMARK_DIR = "/path/to/testmark"       # Root directory for reference format
OUTPUT_DIR   = "/path/to/results_root"   # Root directory for output results
MODEL_NAME   = "gemini-2.0-flash"        # Stable model version
TEMP_DIR     = "/path/to/temp_segments"  # Temporary directory for cut audio segments
MAX_WORKERS  = 16                         # Max thread count (adjust based on API concurrency limits, recommended 5-10)
########################################  Parameter config  ########################################

# Initialize Gemini client (thread-safe, no need to create per thread)
client = genai.Client(api_key=API_KEY)

# Create necessary directories
Path(TEMP_DIR).mkdir(exist_ok=True, parents=True)
Path(OUTPUT_DIR).mkdir(exist_ok=True, parents=True)

# Thread lock: prevent concurrent printing from mixing output
print_lock = threading.Lock()

def get_audio_segment(wav_path: str, start_sec: float, end_sec: float) -> AudioSegment:
    """Cut audio segment by time (unit: seconds)"""
    audio = AudioSegment.from_wav(str(wav_path))
    start_ms = int(start_sec * 1000)
    end_ms = int(end_sec * 1000)
    return audio[start_ms:end_ms]

def transcribe_segment_worker(segment_idx: int, segment_audio: AudioSegment) -> tuple[int, str]:
    """Transcribe a single audio segment (thread worker function): returns (segment index, transcribed text)"""
    temp_file = Path(TEMP_DIR) / f"temp_segment_{segment_idx}_{id(segment_audio)}.wav"
    segment_audio.export(str(temp_file), format="wav")
    
    try:
        uploaded = client.files.upload(file=str(temp_file))
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                "Transcribe the speech accurately.",
                uploaded
            ]
        )
        # Clean up resources
        client.files.delete(name=uploaded.name)
        temp_file.unlink(missing_ok=True)
        transcribed_text = response.text.strip() if response.text else ""
        
        with print_lock:
            print(f"[Thread Done] Segment {segment_idx} transcribed successfully")
        return (segment_idx, transcribed_text)
    
    except Exception as e:
        with print_lock:
            print(f"[Thread Warning] Segment {segment_idx} transcription failed: {e}")
        temp_file.unlink(missing_ok=True)
        return (segment_idx, "")

def main():
    wav_list = list(Path(ROOT_DIR).rglob("*.wav"))
    if not wav_list:
        print("No wav files found, please check directory settings!")
        return

    # Process each long audio file sequentially
    for wav_path in tqdm(wav_list, desc="Gemini-ASR main process"):
        wav_path = wav_path.resolve()
        audio_name = wav_path.stem
        lang_code = wav_path.parent.name.upper()
        
        # Find reference JSON file
        ref_json_path = Path(TESTMARK_DIR) / lang_code / f"{audio_name}.json"
        if not ref_json_path.exists():
            with print_lock:
                print(f"\n[ERROR] Reference file not found: {ref_json_path}, skipping this audio")
            continue
        
        # Read reference segment info
        with open(ref_json_path, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
        ref_segments = ref_data.get("segments", [])
        if not ref_segments:
            with print_lock:
                print(f"\n[WARNING] No segment info in reference file: {ref_json_path}, skipping this audio")
            continue
        
        # Pre-process: filter valid segments (need transcription), record original indices
        valid_tasks = []  # Store (original segment index, audio segment, reference segment data)
        for seg_idx, seg in enumerate(ref_segments):
            start_sec = seg["start"]
            end_sec = seg["end"]
            # Skip invalid segments or overly short segments
            if seg["status"] == "invalid" or (end_sec - start_sec) < 0.1:
                continue
            # Cut audio segment
            segment_audio = get_audio_segment(wav_path, start_sec, end_sec)
            valid_tasks.append((seg_idx, segment_audio, seg))
        
        if not valid_tasks:
            with print_lock:
                print(f"\n[INFO] Audio {audio_name} has no valid segments, directly copying reference file")
            # Directly copy reference file (text field is empty)
            output_dir = Path(OUTPUT_DIR) / lang_code
            output_dir.mkdir(exist_ok=True, parents=True)
            output_json_path = output_dir / f"{audio_name}.json"
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(ref_data, f, ensure_ascii=False, indent=2)
            continue
        
        # Multi-thread parallel transcription of valid segments
        with print_lock:
            print(f"\n[INFO] Processing audio {audio_name}, {len(valid_tasks)} valid segments, using {MAX_WORKERS} threads")
        
        # Store transcription results: key=original segment index, value=transcribed text
        transcribed_results = {}
        
        # Use thread pool to execute tasks
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_seg = {
                executor.submit(transcribe_segment_worker, seg_idx, seg_audio): (seg_idx, seg_data)
                for seg_idx, seg_audio, seg_data in valid_tasks
            }
            
            # Monitor task completion
            for future in tqdm(as_completed(future_to_seg), total=len(future_to_seg), desc=f"{audio_name} segment transcription"):
                seg_idx, _ = future_to_seg[future]
                try:
                    result_idx, result_text = future.result()
                    transcribed_results[result_idx] = result_text
                except Exception as e:
                    with print_lock:
                        print(f"[ERROR] Segment {seg_idx} result retrieval failed: {e}")
                    transcribed_results[seg_idx] = ""
        
        # Build final output segments (replace text field)
        output_segments = []
        for seg_idx, seg in enumerate(ref_segments):
            if seg_idx in transcribed_results:
                # Replace transcribed text
                output_seg = seg.copy()
                output_seg["text"] = transcribed_results[seg_idx]
                output_segments.append(output_seg)
            else:
                # Invalid segments: keep original data
                output_segments.append(seg)
        
        # Save output file
        output_dir = Path(OUTPUT_DIR) / lang_code
        output_dir.mkdir(exist_ok=True, parents=True)
        output_json_path = output_dir / f"{audio_name}.json"
        
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "audio_name": audio_name,
                "segments": output_segments
            }, f, ensure_ascii=False, indent=2)
        
        with print_lock:
            print(f"\n[SUCCESS] Audio {audio_name} processed, results saved to: {output_json_path}")

    print(f"\n===== All audio processing complete! Results in {OUTPUT_DIR} =====")

if __name__ == "__main__":
    main()