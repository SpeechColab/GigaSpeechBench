import os
import sys
import argparse
import json
from collections import defaultdict
from typing import Optional, Tuple

import dolphin
from dolphin.transcribe import load_model
from dolphin.constants import SAMPLE_RATE
import torchaudio
import numpy as np

from utils import save_transcription

# Language mapping: country codes mapped to (lang_sym, region_sym) tuples
LANGUAGE_MAPPING = {
    "AR": ("ar", ""),      # Arabic
    "ARE": ("ar", "AE"),      # Arabic - UAE
    "IRQ": ("ar", ""),     # Arabic - Iraq
    "DZA": ("ar", ""),      # Arabic - Algeria
    "EGY": ("ar", "EG"),      # Arabic - Egypt
    "SAU": ("ar", "SA"),      # Arabic - Saudi Arabia
    "MAR": ("ar", "MA"),      # Arabic - Morocco
    "IDN": ("id", "ID"),      # Indonesian
    "JPN": ("ja", "JP"),      # Japanese
    "KOR": ("ko", "KR"),      # Korean
    "THA": ("th", "TH"),      # Thai
    "VNM": ("vi", "VN"),      # Vietnamese
    "PHL": ("fil", "PH"),     # Filipino
    "MYS": ("ms", "MY"),      # Malay
    "CHN": ("zh", "CN"),      # Chinese (Mandarin)
    "XIANG": ("zh", "HUNAN"),      # Xiang dialect
    "JIN": ("zh", "SHANXI"),      # Jin dialect
}


def _segment_key(entry: dict):
    """Extract (path or audio_name, start, end) as a unique key from an entry, used for loading and deduplication."""
    path_or_name = entry.get("path") or entry.get("audio_name") or ""
    start = entry.get("start_time") if "start_time" in entry else entry.get("start", 0.0)
    end = entry.get("end_time") if "end_time" in entry else entry.get("end", 0.0)
    return (path_or_name, float(start), float(end))


def load_transcribed_segments(language: str, model: str, output_dir: str = "results") -> Tuple[set, dict]:
    """
    Load previously transcribed segments.
    Uses (path or audio_name, start, end) as the key.

    Args:
        language (str): Language code
        model (str): Model name
        output_dir (str): Results directory, defaults to "results"

    Returns:
        (set, dict):
            set: Set of keys for transcribed segments, used for quick lookup of (path_or_audio_name, start, end)
            dict: Mapping from the same key tuple to the text content of that segment
    """
    results_dir = os.path.join(os.getcwd(), output_dir)
    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    transcribed_segments = set()
    segment_texts = {}

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for entry in data:
                            key = _segment_key(entry)
                            transcribed_segments.add(key)
                            segment_texts[key] = (entry.get("text") or "").strip()
        except Exception as e:
            print(f"[WARN] Failed to load transcribed results file {output_path}: {e}")

    return transcribed_segments, segment_texts


def fix_and_clean_results(language: str, model: str, text_file: str, output_dir: str) -> None:
    """
    Fix and clean up the results file:
    1. Read the reference file and build a (audio_name, start, end) key set
    2. Check each entry in the result file: if (path/audio_name, start, end) matches a key in the reference (allowing a time tolerance of 0.001 seconds), keep it; otherwise, remove it.
    Does not supplement or correct IDs.

    Args:
        language (str): Language code
        model (str): Model name
        text_file (str): Reference file path (ref JSON)
        output_dir (str): Output directory
    """
    results_dir = os.path.join(os.getcwd(), output_dir)
    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    if not os.path.exists(output_path):
        return

    # Read reference file and build (audio_name, start, end) -> id mapping
    if not os.path.exists(text_file):
        print(f"  [WARN] Reference file does not exist, cannot fix results file: {text_file}")
        return

    try:
        with open(text_file, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
            if not isinstance(ref_data, list):
                print(f"  [WARN] Reference file format error, expected list format: {text_file}")
                return
    except Exception as e:
        print(f"  [WARN] Failed to read reference file {text_file}: {e}")
        return

    # Build reference file key set: (audio_name, start, end)
    ref_keys = set()
    for segment in ref_data:
        audio_name = segment.get("audio_name", "")
        start = segment.get("start", 0.0)
        end = segment.get("end", 0.0)
        ref_keys.add((audio_name, float(start), float(end)))

    print(f"  Reference file contains {len(ref_keys)} segments")

    # Read results file
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return
            result_data = json.loads(content)
            if not isinstance(result_data, list):
                return
    except Exception as e:
        print(f"  [WARN] Failed to read results file {output_path}: {e}")
        return

    original_count = len(result_data)
    print(f"  Results file contains {original_count} entries")

    # Check each entry against reference keys by (path/audio_name, start, end), keep matching ones
    fixed_entries = []
    deleted_count = 0

    for entry in result_data:
        path_or_name = entry.get("path") or entry.get("audio_name") or ""
        start_time = entry.get("start_time") if "start_time" in entry else entry.get("start", 0.0)
        end_time = entry.get("end_time") if "end_time" in entry else entry.get("end", 0.0)
        # path format may be {language}/{audio_filename}, need to get audio_name for comparison with ref
        if path_or_name and "/" in path_or_name:
            audio_name = os.path.basename(path_or_name)
        else:
            audio_name = path_or_name
        audio_name = os.path.splitext(audio_name)[0]

        # Check if it matches a reference key (allowing a time tolerance of 0.001 seconds)
        matched = False
        for (ref_audio_name, ref_start, ref_end) in ref_keys:
            if (ref_audio_name == audio_name and
                abs(ref_start - float(start_time)) < 0.001 and
                abs(ref_end - float(end_time)) < 0.001):
                matched = True
                break

        if matched:
            fixed_entries.append(entry)
        else:
            deleted_count += 1
    if deleted_count > 0:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(fixed_entries, f, ensure_ascii=False, indent=4)
            print(f"  Results file cleanup completed: originally {original_count} entries, removed {deleted_count} unmatched, kept {len(fixed_entries)} entries")
        except Exception as e:
            print(f"  [WARN] Failed to write back results file {output_path}: {e}")


def load_audio_segment(
    audio_path: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> np.ndarray:
    """
    Load an audio file, optionally extracting a segment by time range.
    Uses torchaudio for loading, automatically handling sample rate and resampling.

    Args:
        audio_path: Audio file path
        start_time: Start time (seconds), if None then start from the beginning
        end_time: End time (seconds), if None then go to the end

    Returns:
        waveform: Audio waveform data (numpy array, float32), resampled to 16000 Hz
    """
    # Use torchaudio to load audio, automatically get sample rate
    wav, sr = torchaudio.load(audio_path, channels_first=False)
    
    # Convert to mono (if stereo)
    if wav.dim() > 1 and wav.size(1) > 1:
        wav = wav.mean(dim=1, keepdim=True)
    
    # If a time range is provided, extract the segment first (at original sample rate)
    if start_time is not None or end_time is not None:
        start_sample = int(start_time * sr) if start_time is not None else 0
        end_sample = int(end_time * sr) if end_time is not None else wav.size(0)
        start_sample = max(0, start_sample)
        end_sample = min(wav.size(0), end_sample)
        wav = wav[start_sample:end_sample]
    
    # If sample rate is not 16000, resample is needed
    if sr != SAMPLE_RATE:
        # Use torchaudio for resampling
        resampler = torchaudio.transforms.Resample(sr, SAMPLE_RATE)
        # wav shape is (n_samples, n_channels), need to transpose to (n_channels, n_samples) for resampling
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)  # (n_samples,) -> (1, n_samples)
        elif wav.dim() == 2 and wav.size(1) == 1:
            wav = wav.transpose(0, 1)  # (n_samples, 1) -> (1, n_samples)
        wav = resampler(wav)
        # Convert back to (n_samples,) or (n_samples, 1)
        if wav.size(0) == 1:
            wav = wav.squeeze(0)  # (1, n_samples) -> (n_samples,)
    
    # Convert to numpy array
    waveform = wav.squeeze().numpy().astype(np.float32)
    
    return waveform




def is_segment_transcribed(
    audio_path: str,
    start_time: float,
    end_time: float,
    language_code: str,
    transcribed_segments: set,
    force: bool = False,
    segment_texts: dict = None,
) -> bool:
    """
    Check if a segment has already been transcribed.
    When matching, tries multiple path format variants: {language_code}/{wav_filename}, wav_filename, wav_filename without extension,
    to accommodate different path/audio_name formats that may exist in previous JSON files.

    Args:
        audio_path (str): Audio file path
        start_time (float): Start time
        end_time (float): End time
        language_code (str): Language code
        transcribed_segments (set): Set of already transcribed segments
        force (bool): Whether to force re-transcription
        segment_texts (dict): Text content of already transcribed segments

    Returns:
        bool: True if already transcribed, False otherwise
    """
    wav_filename = os.path.basename(audio_path)
    wav_filename_without_ext = os.path.splitext(wav_filename)[0]
    start_f = float(start_time)
    end_f = float(end_time)

    # Try multiple path format variants to match keys in transcribed_segments
    path_variants = [
        f"{language_code}/{wav_filename}",  # Standard format
        wav_filename,
        wav_filename_without_ext,
    ]
    matched_key = None
    for path_variant in path_variants:
        candidate_key = (path_variant, start_f, end_f)
        if candidate_key in transcribed_segments:
            matched_key = candidate_key
            break

    if matched_key is None:
        return False

    # When force is off, any existing record means already transcribed, skip
    if not force:
        return True

    # In force mode, if no text cache exists then we cannot determine if it is empty, treat as needing re-run; with cache, decide based on whether text is empty
    if segment_texts is None:
        return False
    text = segment_texts.get(matched_key, "")
    if isinstance(text, str) and text.strip() == "":
        return False

    return True


def deduplicate_and_sort_results(language: str, model: str, output_dir: str) -> None:
    """
    Deduplicate and sort the results file for the specified language and model:
      1. Use (path or audio_name, start, end) as a unique key, keeping the "last occurrence" record;
      2. Sort by path/audio_name, start, end and write back.
    """
    results_dir = os.path.join(os.getcwd(), output_dir)
    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    if not os.path.exists(output_path):
        return

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return
            data = json.loads(content)
            if not isinstance(data, list):
                print(f"[WARN] Results file format is abnormal (not a list), skipping deduplication: {output_path}")
                return
    except Exception as e:
        print(f"[WARN] Failed to read results file for deduplication: {output_path}, reason: {e}")
        return

    original_len = len(data)

    # Use (path or audio_name, start, end) as key, later entries overwrite earlier ones
    unique_map = {}
    for entry in data:
        key = _segment_key(entry)
        unique_map[key] = entry

    deduped = list(unique_map.values())

    # Sort by path/audio_name, start, end
    deduped.sort(key=lambda e: _segment_key(e))

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(deduped, f, ensure_ascii=False, indent=4)
        print(f"[INFO] Results deduplication and sorting completed: {output_path} (originally {original_len} entries, after dedup {len(deduped)} entries)")
    except Exception as e:
        print(f"[WARN] Failed to write deduplicated results: {output_path}, reason: {e}")


def transcribe_audio(
    audio_path: str,
    start_time: float,
    end_time: float,
    language: str,
    model
) -> str:
    """
    Transcribe a specified segment of an audio file.

    This function supports transcribing a single audio segment, automatically handling language mapping, audio loading, and model invocation.

    Args:
        audio_path (str): Absolute path of the audio file
        start_time (float): Start time (seconds)
        end_time (float): End time (seconds)
        language (str): Country code (e.g., "ARE", "IRQ"), automatically mapped to dolphin-supported language codes
        model: Loaded dolphin model

    Returns:
        str: Transcribed text (without special symbols)
    """
    # Get language and region codes
    lang_region = LANGUAGE_MAPPING.get(language.upper(), None)
    if lang_region is None:
        print(f"Warning: No mapping found for language {language}, will use auto-detection")
        lang_sym = None
        region_sym = None
    else:
        lang_sym, region_sym = lang_region

    # Handle empty strings (treat empty string as None)
    if lang_sym == "":
        lang_sym = None
    if region_sym == "":
        region_sym = None

    # Load and extract audio segment
    waveform_segment = load_audio_segment(
        audio_path, 
        start_time=start_time, 
        end_time=end_time
    )
    
    # Determine how to call the model based on lang_sym and region_sym values
    try:
        if lang_sym is None:
            # If lang is empty, do not specify language, use auto-detection
            result = model(speech=waveform_segment)
        elif region_sym is None:
            # If lang exists but region is empty, only specify language
            result = model(speech=waveform_segment, lang_sym=lang_sym)
        else:
            # If both exist, specify both language and region
            result = model(
                waveform_segment,
                lang_sym=lang_sym,
                region_sym=region_sym
            )
        
        # Return text without special symbols
        return result.text_nospecial
    except Exception as e:
        print(f"Transcription failed: {e}")
        raise


def main():
    """
    Main function: transcribe audio files based on standard-format JSON files.
    """
    parser = argparse.ArgumentParser(description="Batch transcribe audio files and save results")
    parser.add_argument(
        "--languages",
        type=str,
        nargs="+",
        required=True,
        help="List of language codes to process (e.g., --languages JPN ARE IDN)"
    )
    parser.add_argument(
        "--text_dir",
        type=str,
        default="data/text/testbatch/ref",
        help="Text files directory (default: data/text/testbatch/ref)"
    )
    parser.add_argument(
        "--audio_dir",
        type=str,
        default="data/audio/testbatch",
        help="Audio files directory (default: data/audio/testbatch)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="results",
        help="Output directory path (saves transcription results)"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="small",
        choices=["base", "small"],
        help="Model name (base or small)"
    )
    parser.add_argument(
        "--model_dir",
        type=str,
        required=True,
        help="Model directory path"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="If true, re-transcribe segments that exist but have empty text"
    )

    args = parser.parse_args()
    
    # Validate and normalize language codes
    languages = [lang.upper() for lang in args.languages]
    
    # Set default paths
    if args.text_dir is None:
        text_dir = os.path.join(os.getcwd(), "data", "text", "ref")
    else:
        text_dir = os.path.abspath(args.text_dir)
    
    if args.audio_dir is None:
        audio_dir = os.path.join(os.getcwd(), "data", "audio", "testbatch")
    else:
        audio_dir = os.path.abspath(args.audio_dir)
    
    print(f"Using model: {args.model_name}")
    print(f"Model directory: {args.model_dir}")
    print(f"Text directory: {text_dir}")
    print(f"Audio directory: {audio_dir}")
    print(f"Processing languages: {', '.join(languages)}")

    # Load model
    print("\nLoading model...")
    try:
        model = load_model(
            model_name=args.model_name,
            model_dir=args.model_dir
        )
        print("Model loaded successfully")
    except Exception as e:
        print(f"Model loading failed: {e}")
        raise

    # Verify directories exist
    if not os.path.exists(text_dir):
        raise ValueError(f"Text directory does not exist: {text_dir}")
    if not os.path.exists(audio_dir):
        raise ValueError(f"Audio directory does not exist: {audio_dir}")

    # Iterate over specified languages
    total_languages = len(languages)
    for lang_idx, language in enumerate(languages, 1):
        print(f"\nProcessing language [{lang_idx}/{total_languages}]: {language}")

        # Build text file path: data/text/ref/{language}.json
        text_file = os.path.join(text_dir, f"{language}.json")
        
        if not os.path.exists(text_file):
            print(f"  Warning: Text file does not exist, skipping: {text_file}")
            continue

        # Load previously transcribed segments for this language
        model_name = f"dolphin_{args.model_name}"
        transcribed_segments, segment_texts = load_transcribed_segments(language, model_name, args.output_dir)
        print(f"  Loaded {len(transcribed_segments)} previously transcribed segments")

        # Load text JSON file
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                segments_data = json.load(f)
        except Exception as e:
            print(f"  Error: Failed to load text file {text_file}: {e}")
            continue

        if not isinstance(segments_data, list):
            print(f"  Error: Text file format is incorrect, expected list format: {text_file}")
            continue

        print(f"  Found {len(segments_data)} segments")

        # Fix and clean up results file (before formal transcription)
        fix_and_clean_results(language, model_name, text_file, args.output_dir)
        # After fixing, reload previously transcribed segments (since IDs may have been updated or mismatched entries removed)
        transcribed_segments, segment_texts = load_transcribed_segments(language, model_name, args.output_dir)
        print(f"  After fix, reloaded {len(transcribed_segments)} previously transcribed segments")

        # Group segments by audio_name for processing
        segments_by_audio = defaultdict(list)
        for segment in segments_data:
            audio_name = segment.get("audio_name", "")
            if audio_name:
                segments_by_audio[audio_name].append(segment)

        print(f"  Involving {len(segments_by_audio)} audio files")

        # Process each audio file
        total_audios = len(segments_by_audio)
        for audio_idx, (audio_name, segments) in enumerate(segments_by_audio.items(), 1):
            print(f"  [{audio_idx}/{total_audios}] Processing audio: {audio_name}")
            # Build audio file path: if audio_name already has an extension, use it directly; otherwise try multiple extensions
            audio_extensions = ['.wav', '.mp3', '.flac', '.m4a']
            audio_path = None
            lang_audio_dir = os.path.join(audio_dir, language)

            # If it already has an extension, use that path directly without trying to append extensions
            _, ext = os.path.splitext(audio_name)
            if ext:
                direct_path = os.path.join(lang_audio_dir, audio_name)
                if os.path.exists(direct_path):
                    audio_path = direct_path
            else:
                # When no extension, try possible extensions
                for ext in audio_extensions:
                    potential_path = os.path.join(lang_audio_dir, f"{audio_name}{ext}")
                    if os.path.exists(potential_path):
                        audio_path = potential_path
                        break

            if audio_path is None:
                print(f"    Warning: Audio file does not exist, skipping. Tried path: {lang_audio_dir}/{audio_name}[.wav|.mp3|.flac|.m4a]")
                continue

            print(f"    Found audio file: {audio_path}")
            print(f"    This audio has {len(segments)} segments")

            # Process each segment of this audio
            for seg_idx, segment in enumerate(segments, 1):
                start_time = segment.get("start", 0.0)
                end_time = segment.get("end", 0.0)
                segment_id = segment.get("id", seg_idx)

                print(f"    Segment {seg_idx}/{len(segments)} (id={segment_id}): {start_time:.2f}s - {end_time:.2f}s")

                # Build formatted path: {language}/{audio_filename}
                audio_filename = os.path.basename(audio_path)
                formatted_path = f"{language}/{audio_filename}"

                # Check if this segment has already been transcribed
                if is_segment_transcribed(
                    audio_path,
                    start_time,
                    end_time,
                    language,
                    transcribed_segments,
                    force=args.force,
                    segment_texts=segment_texts,
                ):
                    print(f"      Segment already transcribed, skipping")
                    continue

                # Call transcribe_audio for transcription
                try:
                    transcription_text = transcribe_audio(
                        audio_path=audio_path,
                        start_time=start_time,
                        end_time=end_time,
                        language=language,
                        model=model
                    )
                    # Save even if the returned text is empty
                    preview = ""
                    if isinstance(transcription_text, str):
                        preview = transcription_text.strip()[:50]
                    print(f"      Transcription successful: {preview}...")
                except Exception as e:
                    print(f"      Transcription failed: {e}")
                    transcription_text = ""

                # Call save_transcription to save results
                try:
                    save_transcription(
                        audio_path=formatted_path,
                        text=transcription_text,
                        language=language,
                        model=model_name,
                        start_time=start_time,
                        end_time=end_time,
                        index=segment_id
                    )
                    
                    # Fix the saved path format to ensure Linux-style path separators
                    results_dir = os.path.join(os.getcwd(), args.output_dir)
                    os.makedirs(results_dir, exist_ok=True)
                    filename = f"{language}_{model_name}.json"
                    output_path = os.path.join(results_dir, filename)
                    
                    if os.path.exists(output_path):
                        with open(output_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        # Fix the path format of the last entry
                        if data and len(data) > 0:
                            last_entry = data[-1]
                            # Normalize the path to Linux style: {language}/{audio_filename}
                            last_entry["path"] = formatted_path
                            # Write back to file
                            with open(output_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=4)
                    
                    # Add newly transcribed segment to the set to avoid duplicate checking
                    transcribed_segments.add((formatted_path, float(start_time), float(end_time)))
                except Exception as e:
                    print(f"      Failed to save results: {e}")

        # After all audio files and segments for this language are processed, deduplicate and sort the results file
        deduplicate_and_sort_results(language, model_name, args.output_dir)

    print("\nAll files processed!")


if __name__ == "__main__":
    main()
