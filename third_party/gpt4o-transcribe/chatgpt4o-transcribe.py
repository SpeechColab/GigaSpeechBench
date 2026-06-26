# pip install openai tqdm pydub ffmpeg-python
import os
import json
import threading
import glob
from typing import Dict, Any
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from pydub.utils import mediainfo

# Import OpenAI client
from openai import OpenAI

# Import from utils save_transcription (if not available, fallback implementation below)
try:
    from utils import save_transcription
except ImportError:
    # placeholder, use custom save logic
    def save_transcription(audio_path, text, language, model, start_time, end_time):
        pass 

########################################  Parameter config  ########################################
# Note: Set your OpenAI API Key via environment variable OPENAI_API_KEY

API_KEY      = os.getenv("OPENAI_API_KEY")  # set via environment variable
ROOT_DIR     = "/path/to/dataset_root"                      # <--- Modify to your dataset directory
TESTMARK_DIR = "/path/to/dataset_root"                      # <--- Modify to your dataset directory
OUTPUT_DIR   = "/path/to/results_root"                      # <--- Modify to your desired output directory
MODEL_NAME   = "gpt-4o-transcribe"                         
TEMP_DIR     = "/path/to/temp_segments"                     # <--- Temporary audio segment directory, optional to modify
FINAL_OUTPUT_DIR = "/path/to/results_all"                   # <--- Final merged results directory

MAX_WORKERS  = 16                                          
########################################  Parameter config  ########################################

# Language mapping table: directory name -> ISO-639-1 language code (for OpenAI API usage)
LANG_MAP = {
    "ARE": "ar", "DZA": "ar", "EGY": "ar", "IRQ": "ar", "MAR": "ar", "SAU": "ar",
    "MYS": "ms", "IDN": "id", "PHL": "tl", "THA": "th", "VNM": "vi",
    "JPN": "ja", "KOR": "ko",
}

# Initialize OpenAI client (thread-safe, no need to create per thread)
client = OpenAI(api_key=API_KEY)

# Create necessary directories
Path(TEMP_DIR).mkdir(exist_ok=True, parents=True)
Path(OUTPUT_DIR).mkdir(exist_ok=True, parents=True)
Path(FINAL_OUTPUT_DIR).mkdir(exist_ok=True, parents=True) # <--- Create final output directory

# Thread lock: prevents interleaved output from concurrent threads
print_lock = threading.Lock()

def get_audio_segment(wav_path: str, start_sec: float, end_sec: float) -> AudioSegment:
    """Cut an audio segment by time (unit: seconds)"""
    audio = AudioSegment.from_wav(str(wav_path))
    start_ms = int(start_sec * 1000)
    end_ms = int(end_sec * 1000)
    return audio[start_ms:end_ms]

def transcribe_segment_worker(segment_idx: int, segment_audio: AudioSegment, lang_code: str) -> tuple[int, str]:
    """Transcribe a single audio segment (thread worker function): returns (segment index, transcription text)"""
    temp_file = Path(TEMP_DIR) / f"temp_segment_{segment_idx}_{threading.get_ident()}.wav"
    
    segment_audio.export(str(temp_file), format="wav")
    
    transcribed_text = ""
    try:
        with open(str(temp_file), "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=MODEL_NAME,
                file=audio_file,
                language=lang_code 
            )
            transcribed_text = transcript.text.strip() if hasattr(transcript, "text") else ""
        
        temp_file.unlink(missing_ok=True) 
        
        with print_lock:
            print(f"[Thread Done] Segment {segment_idx} transcribed successfully (language: {lang_code})")
        return (segment_idx, transcribed_text)
    
    except Exception as e:
        with print_lock:
            temp_file.unlink(missing_ok=True) 
            print(f"[Thread Warning] Segment {segment_idx} transcription failed: {e}")
        return (segment_idx, "")

# ==============================================================================
# Additional features: aggregation and format conversion
# ==============================================================================

# ==============================================================================
# Additional features: aggregation by language and format conversion
# ==============================================================================

def aggregate_results(output_dir: Path, root_dir: Path, lang_map: Dict[str, str], model_name: str, final_output_dir_path: Path):
    """
    Iterate through all JSON files under OUTPUT_DIR, group by language, and convert their contents
    to a unified list format. Then generate a separate JSON file for each language,
    named {language}_{model_name}.json.
    
    Args:
        output_dir (Path): Root directory containing per-audio JSON results.
        root_dir (Path): Root directory for audio files, used to construct full WAV paths.
        lang_map (Dict[str, str]): Mapping from language directory names to ISO codes
            (though this function primarily uses directory names).
        model_name (str): Model name used for result file naming.
        final_output_dir_path (Path): Output directory for the final aggregated results.
    """
    # Store transcription data grouped by language: { "JPN": [ {entry1}, {entry2}, ... ], "MYS": [ ... ] }
    results_by_language: Dict[str, list[Dict[str, str | float]]] = {}
    
    # Find all generated JSON files
    result_files = list(output_dir.rglob("*.json"))
    
    if not result_files:
        print("\n[INFO] No JSON result files found, skipping aggregation.")
        return

    print(f"\n===== Starting grouped aggregation of {len(result_files)} JSON files =====")

    for json_path in tqdm(result_files, desc="Grouping JSON files"):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 1. Extract information
            audio_name = data.get("audio_name")
            segments = data.get("segments", [])
            
            # 2. Determine the language directory name (e.g., JPN, MYS) - this is the grouping key
            lang_dir_name = json_path.parent.name # e.g., JPN
            
            # Initialize the list for this language
            if lang_dir_name not in results_by_language:
                results_by_language[lang_dir_name] = []
            
            # 3. Determine the full path to the original WAV file
            original_wav_path = root_dir / lang_dir_name / f"{audio_name}.wav"
            
            # 4. Convert segment format and add to the corresponding language group
            for seg in segments:
                transcribed_text = seg.get("text", "").strip()
                if not transcribed_text:
                    continue
                    
                entry: Dict[str, str | float] = {
                    "path": str(original_wav_path.resolve()),
                    "text": transcribed_text,
                    "language": lang_dir_name, # Use directory name like JPN/MYS
                    "model": model_name,
                    "start_time": seg.get("start", 0.0),
                    "end_time": seg.get("end", 0.0)
                }
                results_by_language[lang_dir_name].append(entry)

        except Exception as e:
            print(f"\n[WARNING] Error processing file {json_path}: {e}")
            continue

    # 5. Write the final aggregated files (loop by language)
    final_output_dir = final_output_dir_path
    final_output_dir.mkdir(exist_ok=True, parents=True)
    
    print("\n===== Writing language-grouped aggregated files =====")

    for lang_dir_name, data_list in results_by_language.items():
        if not data_list:
            continue
            
        # File name format: {language}_{model_name}.json (e.g., JPN_gpt4o-transcribe.json)
        final_filename = f"{lang_dir_name}_{model_name}.json" 
        final_output_path = final_output_dir / final_filename

        with open(final_output_path, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)

        print(f"[SUCCESS] Language {lang_dir_name} aggregated file saved to: {final_output_path} ({len(data_list)} records)")

# ... (main function remains unchanged, just make sure to call aggregate_results)



def main():
    # ... (previous code remains unchanged, process audio and transcribe)
    wav_list = list(Path(ROOT_DIR).rglob("*.wav"))
    if not wav_list:
        print("No WAV files found, please check your directory settings!")
        return

    all_results = {}  # (lang, aid) -> [seg_dict, ...]

    # Process each long audio file (serial)
    for wav_path in tqdm(wav_list, desc="ChatGPT-4o ASR main process"):
        wav_path = wav_path.resolve()
        audio_name = wav_path.stem
        lang_dir = wav_path.parent.name.upper()
        
        lang_code = LANG_MAP.get(lang_dir)
        if not lang_code:
            with print_lock:
                print(f"\n[ERROR] Unrecognized language directory: {lang_dir}, skipping audio {audio_name}. Please check LANG_MAP configuration!")
            continue

        ref_json_path = Path(TESTMARK_DIR) / lang_dir / f"{audio_name}.json"
        if not ref_json_path.exists():
            with print_lock:
                print(f"\n[ERROR] Reference file not found: {ref_json_path}, skipping this audio")
            continue
        
        with open(ref_json_path, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
        ref_segments = ref_data.get("segments", [])
        
        valid_tasks = []  
        for seg_idx, seg in enumerate(ref_segments):
            start_sec = float(seg.get("start", seg.get("begin_time", 0)))
            end_sec = float(seg.get("end", seg.get("end_time", 0)))
            if seg.get("status") == "invalid" or (end_sec - start_sec) < 0.1:
                continue
            
            try:
                segment_audio = get_audio_segment(wav_path, start_sec, end_sec)
                valid_tasks.append((seg_idx, segment_audio, seg))
            except Exception as e:
                 with print_lock:
                     print(f"[WARNING] Audio {audio_name} segment {seg_idx} cut failed: {e}. Skipping.")


        if not valid_tasks:
            with print_lock:
                print(f"\n[INFO] Audio {audio_name} has no valid segments, skipping")
            continue
        
        with print_lock:
            print(f"\n[INFO] Processing audio {audio_name} (language: {lang_code}), {len(valid_tasks)} valid segments, using {MAX_WORKERS} threads")
        
        transcribed_results = {}
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_seg = {
                executor.submit(transcribe_segment_worker, seg_idx, seg_audio, lang_code): (seg_idx, seg_data)
                for seg_idx, seg_audio, seg_data in valid_tasks
            }
            
            for future in tqdm(as_completed(future_to_seg), total=len(future_to_seg), desc=f"{audio_name} segment transcription"):
                seg_idx, _ = future_to_seg[future]
                try:
                    result_idx, result_text = future.result()
                    transcribed_results[result_idx] = result_text
                except Exception as e:
                    with print_lock:
                        print(f"[ERROR] Segment {seg_idx} result retrieval failed: {e}")
                    transcribed_results[seg_idx] = ""
        
        # Collect results in release format
        for seg_idx, seg in enumerate(ref_segments):
            if seg_idx in transcribed_results:
                bt = seg.get("begin_time", str(seg.get("start", "")))
                et = seg.get("end_time", str(seg.get("end", "")))
                sid = seg.get("sid", f"{audio_name}#{bt}#{et}")
                all_results.setdefault((lang_dir, audio_name), []).append({
                    "sid": sid,
                    "begin_time": bt,
                    "end_time": et,
                    "text": transcribed_results[seg_idx],
                    "lang": lang_dir,
                })
        
        with print_lock:
            print(f"\n[SUCCESS] Audio {audio_name} processed")

    # Save all results in release format
    audios = []
    for (lang, aid) in sorted(all_results.keys()):
        audios.append({"aid": aid, "segments": all_results[(lang, aid)], "language": lang})
    out_path = Path(FINAL_OUTPUT_DIR) / f"{MODEL_NAME}.json"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"audios": audios}, f, ensure_ascii=False, indent=2)
    print(f"\n===== Done! Saved {sum(len(a['segments']) for a in audios)} segments -> {out_path} =====")


if __name__ == "__main__":
    main()