import os
import sys
import argparse
import json
from collections import defaultdict
from io import BytesIO
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment

from utils import save_transcription

# Supported model_id list
SUPPORTED_MODEL_IDS = {
    "scribe_v1",
    "scribe_v1_experimental",
    "scribe_v2"
}

LANGUAGE_MAPPING = {
    "AR": "ara",  # Arabic
    "ARE": "ara",  # Arabic-UAE
    "IRQ": "ara",  # Arabic-Iraq
    "DZA": "ara",  # Arabic-Algeria
    "EGY": "ara",  # Arabic-Egypt
    "SAU": "ara",  # Arabic-Saudi
    "MAR": "ara",  # Arabic-Morocco
    "IDN": "ind",  # Indonesian
    "JPN": "jpn",  # Japanese
    "KOR": "kor",  # Korean
    "THA": "tha",  # Thai
    "VNM": "vie",  # Vietnamese
    "PHL": "fil",  # Filipino
    "MYS": "msa",  # Malay
    "USA": "eng",  # English
    "CHN": "zho",  # Chinese (Mandarin)
    "CHN-EN": "eng",  # Chinese English
    "IND-EN": "eng",  # Indian-accented English
    "JPN-EN": "eng",  # Japanese-accented English
    "PHL-EN": "eng",  # Filipino-accented English
    "SCT-EN": "eng",  # Scottish-accented English
    "SGP-EN": "eng",  # Singapore-accented English
    "XIANG": "zho",  # Xiang dialect
    "JIN": "zho",  # Jin dialect
}


def _segment_key(entry: dict):
    """Extract (path or audio_name, start, end) as a unique key from the entry, used for loading and deduplication."""
    path_or_name = entry.get("path") or entry.get("audio_name") or ""
    start = entry.get("start_time") if "start_time" in entry else entry.get("start", 0.0)
    end = entry.get("end_time") if "end_time" in entry else entry.get("end", 0.0)
    return (path_or_name, float(start), float(end))


def load_transcribed_segments(language: str, model: str):
    """
    Load previously transcribed segments.
    Keyed by (path or audio_name, start, end)

    Returns:
        - transcribed_segments (set): used for quick check of whether a (path_or_audio_name, start, end) exists
        - segment_texts (dict): keyed by the same tuple, with text content as value

    Args:
        language (str): language code
        model (str): model name

    Returns:
        (set, dict):
            set: set of keys for transcribed segments
            dict: same keys as above, values are text content of each segment (string)
    """
    results_dir = os.path.join(os.getcwd(), "results")
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
            print(f"[WARN] Unable to load transcribed results file {output_path}: {e}")

    return transcribed_segments, segment_texts


def fix_and_clean_results(language: str, model: str, text_file: str, output_dir: str) -> None:
    """
    Fix and clean up results file:
    1. Read the ref file, build a key set of (audio_name, start, end)
    2. Check each entry in the result file: if (path/audio_name, start, end) matches a key in ref (allowing time tolerance of 0.001 seconds), keep it; otherwise, delete it.
    No id supplementation or correction is performed.

    Args:
        language (str): language code
        model (str): model name
        text_file (str): reference file path (ref JSON)
        output_dir (str): output directory
    """
    results_dir = os.path.join(os.getcwd(), output_dir)
    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    if not os.path.exists(output_path):
        return

    # Read reference file, build (audio_name, start, end) -> id mapping
    if not os.path.exists(text_file):
        print(f"  [WARN] Reference file does not exist, cannot fix results file: {text_file}")
        return

    try:
        with open(text_file, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
            if not isinstance(ref_data, list):
                print(f"  [WARN] Reference file format error, should be a list: {text_file}")
                return
    except Exception as e:
        print(f"  [WARN] Unable to read reference file {text_file}: {e}")
        return

    # Build key set from reference file: (audio_name, start, end)
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
        print(f"  [WARN] Unable to read results file {output_path}: {e}")
        return

    original_count = len(result_data)
    print(f"  Results file contains {original_count} entries")

    # Check each entry against ref keys by (path/audio_name, start, end), keep if matched
    fixed_entries = []
    deleted_count = 0

    for entry in result_data:
        path_or_name = entry.get("path") or entry.get("audio_name") or ""
        start_time = entry.get("start_time") if "start_time" in entry else entry.get("start", 0.0)
        end_time = entry.get("end_time") if "end_time" in entry else entry.get("end", 0.0)
        # Path format may be {language}/{audio_filename}, need to get audio_name for comparison with ref
        if path_or_name and "/" in path_or_name:
            audio_name = os.path.basename(path_or_name)
            
        else:
            audio_name = path_or_name
        audio_name = os.path.splitext(audio_name)[0]

        # Whether it matches a key in ref (allowing time tolerance of 0.001 seconds)
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
            print(f"  Results file cleanup complete: originally {original_count} entries, deleted {deleted_count} unmatched, kept {len(fixed_entries)} entries")
        except Exception as e:
            print(f"  [WARN] Unable to write back results file {output_path}: {e}")


def is_quota_exceeded_error(error: Exception) -> bool:
    """
    Check if the exception is a quota exceeded error.

    Args:
        error (Exception): exception object

    Returns:
        bool: True if quota exceeded error, False otherwise
    """
    error_str = str(error).lower()
    error_repr = repr(error).lower()
    
    # Check if error message contains quota_exceeded related keywords
    quota_keywords = ["quota_exceeded", "quota exceeded", "credits remaining", "exceeds your quota"]
    for keyword in quota_keywords:
        if keyword in error_str or keyword in error_repr:
            return True
    
    # Check exception object attributes (some API libraries may store error messages in attributes)
    if hasattr(error, 'body'):
        try:
            if isinstance(error.body, dict):
                body_str = json.dumps(error.body).lower()
                if "quota_exceeded" in body_str:
                    return True
        except:
            pass
    
    if hasattr(error, 'detail'):
        try:
            if isinstance(error.detail, dict):
                detail_str = json.dumps(error.detail).lower()
                if "quota_exceeded" in detail_str:
                    return True
        except:
            pass
    
    return False


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
    When matching, try multiple path formats: {language_code}/{wav_filename}, wav_filename, wav_filename without extension,
    to accommodate different path/audio_name formats that may exist in existing JSON files.

    Args:
        audio_path (str): audio file path
        start_time (float): start time
        end_time (float): end time
        language_code (str): language code
        transcribed_segments (set): set of already transcribed segments
        force (bool): whether to force re-transcription
        segment_texts (dict): text content of already transcribed segments

    Returns:
        bool: True if already transcribed, False otherwise
    """
    wav_filename = os.path.basename(audio_path)
    wav_filename_without_ext = os.path.splitext(wav_filename)[0]
    start_f = float(start_time)
    end_f = float(end_time)

    # Try multiple path formats to match keys in transcribed_segments
    path_variants = [
        f"{language_code}/{wav_filename}",  # standard format
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

    # When force is not enabled, consider it transcribed if a record exists, skip it
    if not force:
        return True

    # In force mode: if no text cache, cannot determine if empty, treat as needing re-run; if cache exists, decide based on whether text is empty
    if segment_texts is None:
        return False
    text = segment_texts.get(matched_key, "")
    if isinstance(text, str) and text.strip() == "":
        return False

    return True


def transcribe_audio(
    audio_path: str,
    start_time: float,
    end_time: float,
    language: str,
    model_id: str = "scribe_v1"
) -> str:
    """
    Transcribe a specified segment of an audio file.

    Args:
        audio_path (str): absolute path to the audio file
        start_time (float): start time (seconds)
        end_time (float): end time (seconds)
        language (str): country code (e.g., "ARE", "IRQ"), will be automatically mapped to an ElevenLabs API-supported language code
        model_id (str): ElevenLabs model ID, default is "scribe_v1"

    Returns:
        str: transcribed text
    """
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set")

    # Validate model_id
    if model_id not in SUPPORTED_MODEL_IDS:
        raise ValueError(f"Unsupported model_id: {model_id}. Supported model_ids: {', '.join(SUPPORTED_MODEL_IDS)}")

    api_language_code = LANGUAGE_MAPPING.get(language.upper(), None)
    if api_language_code is None:
        print(f"Warning: No mapping found for language {language}, will use auto-detection")
        api_language_code = None

    # Initialize client
    client = ElevenLabs(api_key=api_key)

    # Load audio file
    audio = AudioSegment.from_file(audio_path)

    # Extract audio segment (pydub uses milliseconds)
    start_ms = int(start_time * 1000)
    end_ms = int(end_time * 1000)
    audio_segment = audio[start_ms:end_ms]

    # Export audio segment as byte stream
    buffer = BytesIO()
    audio_segment.export(buffer, format="wav")
    buffer.seek(0)

    # Call ElevenLabs API for transcription
    try:
        transcription_result = client.speech_to_text.convert(
            file=buffer,
            model_id=model_id,
            tag_audio_events=False,
            language_code=api_language_code,
            diarize=False,
        )
        return transcription_result.text
    except Exception as e:
        print(f"Transcription failed: {e}")
        raise


def deduplicate_and_sort_results(language: str, model: str, output_dir: str) -> None:
    """
    Deduplicate and sort the results file for the specified language and model:
      1. Use (path or audio_name, start, end) as the unique key, keeping the last occurrence;
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
                print(f"[WARN] Results file format error (not a list), skipping deduplication: {output_path}")
                return
    except Exception as e:
        print(f"[WARN] Unable to read results file for deduplication: {output_path}, reason: {e}")
        return

    original_len = len(data)

    # Use (path or audio_name, start, end) as key, later entries override earlier ones
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
        print(f"[INFO] Results deduplication and sorting complete: {output_path} (originally {original_len} entries, {len(deduped)} after deduplication)")
    except Exception as e:
        print(f"[WARN] Failed to write deduplication results: {output_path}, reason: {e}")


def main():
    """
    Main function: Transcribe audio files based on standard-format JSON files.
    """
    parser = argparse.ArgumentParser(description="Batch transcribe audio files and save results")
    parser.add_argument(
        "--languages",
        type=str,
        nargs="+",
        required=True,
        help="Language codes to process (e.g., --languages JPN ARE IDN)"
    )
    parser.add_argument(
        "--text_dir",
        type=str,
        default="data/text/testbatch/ref",
        help="Text file directory (default: data/text/testbatch/ref)"
    )
    parser.add_argument(
        "--audio_dir",
        type=str,
        default="data/audio/testbatch",
        help="Audio file directory (default: data/audio/testbatch)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="results",
        help="Output directory path (save transcription results)"
    )
    parser.add_argument(
        "--api_key",
        type=str,
        default=None,
        help="ElevenLabs API key (if not provided, reads from ELEVENLABS_API_KEY environment variable)"
    )
    parser.add_argument(
        "--model_id",
        type=str,
        default="scribe_v1",
        choices=list(SUPPORTED_MODEL_IDS),
        help="ElevenLabs model ID (options: scribe_v1, scribe_v1_experimental, scribe_v2)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="If true, re-transcribe segments that already exist but have empty text"
    )

    args = parser.parse_args()
    
    # Validate model_id
    model_id = args.model_id
    if model_id not in SUPPORTED_MODEL_IDS:
        raise ValueError(f"Unsupported model_id: {model_id}. Supported model_ids: {', '.join(SUPPORTED_MODEL_IDS)}")
    
    # Validate and normalize language codes
    languages = [lang.upper() for lang in args.languages]
    
    # Set paths
    text_dir = os.path.abspath(args.text_dir)
    audio_dir = os.path.abspath(args.audio_dir)
    
    print(f"Using model: {model_id}")
    print(f"Text directory: {text_dir}")
    print(f"Audio directory: {audio_dir}")
    print(f"Processing languages: {', '.join(languages)}")

    # Set API key
    if args.api_key:
        os.environ["ELEVENLABS_API_KEY"] = args.api_key
    elif not os.getenv("ELEVENLABS_API_KEY"):
        raise ValueError("Please provide an API key (via --api_key argument or set ELEVENLABS_API_KEY environment variable)")

    # Validate directories exist
    if not os.path.exists(text_dir):
        raise ValueError(f"Text directory does not exist: {text_dir}")
    if not os.path.exists(audio_dir):
        raise ValueError(f"Audio directory does not exist: {audio_dir}")

    # Iterate over specified languages
    total_languages = len(languages)
    for lang_idx, language in enumerate(languages, 1):
        print(f"\nProcessing language [{lang_idx}/{total_languages}]: {language}")

        # Build text file path: data/text/testbatch/ref/{language}.json
        text_file = os.path.join(text_dir, f"{language}.json")
        
        if not os.path.exists(text_file):
            print(f"  Warning: Text file does not exist, skipping: {text_file}")
            continue

        # Load transcribed segments for this language
        model_name = f"elevenlabs_{model_id}"
        transcribed_segments, segment_texts = load_transcribed_segments(language, model_name)
        print(f"  Loaded {len(transcribed_segments)} transcribed segments")

        # Load text JSON file
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                segments_data = json.load(f)
        except Exception as e:
            print(f"  Error: Unable to load text file {text_file}: {e}")
            continue

        if not isinstance(segments_data, list):
            print(f"  Error: Text file format error, expected list format: {text_file}")
            continue

        print(f"  Found {len(segments_data)} segments")

        # Fix and clean up results file (before formal transcription)
        fix_and_clean_results(language, model_name, text_file, args.output_dir)
        
        # Reload transcribed segments after fix (since IDs may have been updated or mismatched entries removed)
        transcribed_segments, segment_texts = load_transcribed_segments(language, model_name)
        print(f"  Reloaded {len(transcribed_segments)} transcribed segments after fix")
        # Group by audio_name for processing
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

            # Build audio file path: data/audio/testbatch/{language}/{audio_name}.wav
            # Try multiple possible extensions
            audio_extensions = ['.wav', '.mp3', '.flac', '.m4a']
            audio_path = None
            
            lang_audio_dir = os.path.join(audio_dir, language)
            
            _, ext = os.path.splitext(audio_name)
            if ext:
                potential_path = os.path.join(lang_audio_dir, audio_name)
                if os.path.exists(potential_path):
                    audio_path = potential_path
            else:
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

                # Construct formatted path: {language}/{audio_filename}
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
                        model_id=model_id
                    )

                    # Save even if the returned text is empty
                    preview = ""
                    if isinstance(transcription_text, str):
                        preview = transcription_text.strip()[:50]
                    print(f"      Transcription successful: {preview}...")
                except Exception as e:
                    # Check if quota exceeded error
                    if is_quota_exceeded_error(e):
                        print(f"      Transcription failed (quota exceeded): {e}")
                        print(f"      Skipping this segment (not saving)")
                        continue
                    else:
                        # Other error: save result as empty string
                        print(f"      Transcription failed (other error): {e}")
                        print(f"      Saving result as empty string")
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
                    
                    # Fix saved path format, ensuring Linux-style path separators
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
                            # Normalize path to Linux style: {language}/{audio_filename}
                            last_entry["path"] = formatted_path
                            # Write back to file
                            with open(output_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=4)
                    
                    # Add newly transcribed segment to the set to avoid duplicate checks
                    transcribed_segments.add((formatted_path, float(start_time), float(end_time)))
                except Exception as e:
                    print(f"      Failed to save results: {e}")

        # After all audio and segments for this language are processed, deduplicate and sort the results file
        deduplicate_and_sort_results(language, model_name, args.output_dir)

    print("\nAll files processed!")


if __name__ == "__main__":
    main()
