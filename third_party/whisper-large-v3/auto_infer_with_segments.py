#!/usr/bin/env python3
"""
Segment-based batch inference script for Whisper ASR
Processes audio files based on timestamp segments from JSON files
Uses standard save_transcription format consistent with elevenlabs implementation
"""

import os
import sys
import glob
import argparse
import json
import shutil
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import torch
import torchaudio
import numpy as np
from whisper_asr import WhisperASR
from language_mapping import get_supported_country_codes, COUNTRY_CODE_TO_LANGUAGE

# Configuration
TIMESTAMP_DIR = './timestamp'
AUDIO_DIR = '/path/to/audio_root'
MODEL_DIR = '/path/to/model'
MODEL_NAME = 'whisper-large-v3'

def load_timestamp_json(country_code: str) -> List[Dict]:
    """Load timestamp JSON files for a specific country"""
    country_timestamp_dir = os.path.join(TIMESTAMP_DIR, country_code)
    if not os.path.exists(country_timestamp_dir):
        raise FileNotFoundError(f"Timestamp directory not found: {country_timestamp_dir}")

    json_files = glob.glob(os.path.join(country_timestamp_dir, "*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in: {country_timestamp_dir}")

    all_data = []
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_data.append(data)

    return all_data

def find_audio_file(audio_name: str, country_code: str) -> Optional[str]:
    """Find audio file based on audio_name and country_code"""
    country_audio_dir = os.path.join(AUDIO_DIR, country_code)
    if not os.path.exists(country_audio_dir):
        return None

    # Try different audio extensions
    audio_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']

    for ext in audio_extensions:
        audio_path = os.path.join(country_audio_dir, audio_name + ext)
        if os.path.exists(audio_path):
            return audio_path

    return None

def extract_audio_segment(audio_path: str, start_time: float, end_time: float, sample_rate: int = 16000) -> np.ndarray:
    """Extract audio segment from start_time to end_time using torchaudio"""
    try:
        # Load audio with torchaudio (GPU-accelerated)
        waveform, sr = torchaudio.load(audio_path)

        # Convert to mono if needed
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        # Resample if needed
        if sr != sample_rate:
            resampler = torchaudio.transforms.Resample(sr, sample_rate)
            waveform = resampler(waveform)

        # Convert to numpy array
        audio = waveform.squeeze().numpy()

        # Convert time to sample indices
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate)

        # Boundary check
        start_sample = max(0, start_sample)
        end_sample = min(len(audio), end_sample)

        if start_sample >= end_sample:
            raise ValueError(f"Invalid time range: {start_time} - {end_time}")

        # Extract segment
        segment = audio[start_sample:end_sample]
        return segment

    except Exception as e:
        raise RuntimeError(f"Failed to extract audio segment from {audio_path}: {e}")

def process_country_segments(asr: WhisperASR, country_code: str, direct: bool = False, skip_invalid: bool = True) -> int:
    """Process all segments for a specific country using standard save_transcription"""
    print(f"\n--- Processing {country_code} segments ---")

    # Import utils for save_transcription
    import sys
    sys.path.append('/path/to/project_root')
    from scripts.utils import save_transcription

    try:
        # Load timestamp data
        timestamp_data = load_timestamp_json(country_code)
        print(f"  Loaded {len(timestamp_data)} timestamp files")

        total_segments = 0
        processed_segments = 0
        failed_segments = 0

        for audio_data in timestamp_data:
            audio_name = audio_data.get('audio_name', '')
            original_segments = audio_data.get('segments', [])

            # Find corresponding audio file
            audio_path = find_audio_file(audio_name, country_code)
            if not audio_path:
                print(f"  ⚠ Audio file not found: {audio_name}")
                # Save empty transcriptions for all segments
                for segment in original_segments:
                    total_segments += 1

                    # Format audio path as {country_code}/{filename}
                    audio_filename = f"{audio_name}.wav"  # Assuming .wav extension
                    formatted_path = f"{country_code}/{audio_filename}"

                    try:
                        save_transcription(
                            audio_path=formatted_path,
                            text="",
                            language=country_code,
                            model=MODEL_NAME,
                            start_time=segment.get('start', 0.0),
                            end_time=segment.get('end', 0.0)
                        )
                        failed_segments += 1
                    except Exception as save_error:
                        print(f"    ✗ Failed to save transcription: {save_error}")
                        failed_segments += 1
                continue

            print(f"  Processing {audio_name}: {len(original_segments)} segments")

            # Process each segment
            for i, segment in enumerate(original_segments, 1):
                total_segments += 1
                start_time = segment.get('start', 0.0)
                end_time = segment.get('end', 0.0)

                print(f"    [{i}/{len(original_segments)}] Segment {segment.get('index', i)}: {start_time:.2f}s - {end_time:.2f}s")

                # Format audio path as {country_code}/{filename}
                audio_filename = os.path.basename(audio_path)
                formatted_path = f"{country_code}/{audio_filename}"

                try:
                    # Handle invalid segments - save empty string
                    if segment.get('status') == 'invalid':
                        save_transcription(
                            audio_path=formatted_path,
                            text="",  # Empty string for invalid segments
                            language=country_code,
                            model=MODEL_NAME,
                            start_time=start_time,
                            end_time=end_time
                        )
                        print(f"      ✓ Saved invalid segment (empty transcription)")
                    else:
                        # Extract audio segment and transcribe
                        audio_segment = extract_audio_segment(audio_path, start_time, end_time)

                        # Transcribe the segment
                        if direct:
                            # Use auto-detection mode
                            text = asr.transcribe_audio_array(audio_segment, language_code=None)
                        else:
                            # Use country-specific language - pass country code directly
                            text = asr.transcribe_audio_array(audio_segment, language_code=country_code)

                        # Save transcription using standard format
                        save_transcription(
                            audio_path=formatted_path,
                            text=text,
                            language=country_code,
                            model=MODEL_NAME,
                            start_time=start_time,
                            end_time=end_time
                        )
                        print(f"      ✓ Transcribed: {text[:50]}...")
                        processed_segments += 1

                except Exception as e:
                    # Save empty transcription on error
                    try:
                        save_transcription(
                            audio_path=formatted_path,
                            text="",
                            language=country_code,
                            model=MODEL_NAME,
                            start_time=start_time,
                            end_time=end_time
                        )
                    except Exception as save_error:
                        print(f"    ✗ Failed to save error transcription: {save_error}")

                    print(f"      ✗ Error: {e}")
                    failed_segments += 1

        print(f"  Summary: {processed_segments}/{total_segments} segments processed successfully, {failed_segments} failed")
        return total_segments

    except Exception as e:
        print(f"  ✗ Error processing {country_code}: {e}")
        return 0

def get_country_directories() -> List[str]:
    """Get list of country code directories in the timestamp folder"""
    if not os.path.exists(TIMESTAMP_DIR):
        raise FileNotFoundError(f"Timestamp directory not found: {TIMESTAMP_DIR}")

    countries = []
    for item in os.listdir(TIMESTAMP_DIR):
        country_path = os.path.join(TIMESTAMP_DIR, item)
        if os.path.isdir(country_path) and len(item) == 3:  # 3-letter country codes
            countries.append(item)

    return sorted(countries)

def get_existing_results() -> Set[str]:
    """Get set of country codes that already have results files in standard format"""
    existing = set()
    results_dir = './results'

    if not os.path.exists(results_dir):
        return existing

    pattern = os.path.join(results_dir, f"*_{MODEL_NAME}.json")
    for filepath in glob.glob(pattern):
        filename = os.path.basename(filepath)
        # Extract country code from filename like "IRQ_whisper-large-v3.json"
        parts = filename.split('_')
        if len(parts) >= 2:
            country_code = parts[0]
            existing.add(country_code)

    return existing

def clear_existing_results(countries: List[str]):
    """Clear existing result files for specified countries"""
    results_dir = './results'
    if not os.path.exists(results_dir):
        return

    for country in countries:
        filename = f"{country}_{MODEL_NAME}.json"
        filepath = os.path.join(results_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"  ✓ Removed existing result: {filename}")

def batch_infer_segments(countries: List[str] = None, force: bool = False, direct: bool = False, skip_invalid: bool = True):
    """Batch process audio segments from specified countries"""
    print("=== Whisper ASR Segment-based Batch Inference ===")
    print(f"Timestamp directory: {TIMESTAMP_DIR}")
    print(f"Audio directory: {AUDIO_DIR}")
    print(f"Results directory: ./results")  # Changed to standard results directory
    print(f"Model directory: {MODEL_DIR}")
    print(f"Force mode: {force}")
    print(f"Direct auto-detection mode: {direct}")
    print(f"Skip invalid segments: {skip_invalid}")

    # Get country directories
    if countries:
        # Use specified countries
        available_countries = get_country_directories()
        invalid_countries = [c for c in countries if c not in available_countries]
        if invalid_countries:
            print(f"✗ Invalid countries: {', '.join(invalid_countries)}")
            print(f"Available countries: {', '.join(available_countries)}")
            return
        countries_to_check = countries
    else:
        # Get all available countries
        countries_to_check = get_country_directories()

    print(f"\nFound {len(countries_to_check)} countries: {', '.join(countries_to_check)}")

    # Check language mapping for all countries (skip in direct mode)
    if not direct:
        print("\nChecking language mapping...")
        unsupported_countries = []
        for country in countries_to_check:
            if country not in COUNTRY_CODE_TO_LANGUAGE:
                unsupported_countries.append(country)

        if unsupported_countries:
            print(f"✗ Unsupported country codes: {', '.join(unsupported_countries)}")
            print("These countries will be processed in auto-detection mode")
        else:
            print("✓ All countries have language mapping")
    else:
        print("\nSkipping language mapping check (direct auto-detection mode enabled)")

    # Handle existing results
    existing_results = get_existing_results()
    if existing_results and force:
        print(f"\nFound existing results for: {', '.join(sorted(existing_results))}")
        print("Force mode enabled - clearing existing results...")
        clear_existing_results(list(existing_results))
    elif existing_results:
        print(f"\nFound existing results for: {', '.join(sorted(existing_results))}")
        print("Skipping countries with existing results (use --force to reprocess)")

    print(f"\nCountries to process: {countries_to_check}")

    # Initialize Whisper ASR
    print("\nInitializing Whisper ASR model...")
    try:
        asr = WhisperASR(model_dir=MODEL_DIR)
        print("✓ Model initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize model: {e}")
        return

    # Process each country
    total_countries = len(countries_to_check)
    processed_countries = 0
    total_segments_processed = 0

    for country_code in countries_to_check:
        try:
            # Process segments for this country
            segments_processed = process_country_segments(asr, country_code, direct, skip_invalid)

            if segments_processed > 0:
                processed_countries += 1
                total_segments_processed += segments_processed

        except Exception as e:
            print(f"  ✗ Error processing {country_code}: {e}")
            continue

    # Summary
    print(f"\n=== Processing Complete ===")
    print(f"Countries processed: {processed_countries}/{total_countries}")
    print(f"Total segments processed: {total_segments_processed}")
    print(f"Results saved in: ./results/")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Segment-based batch inference script for Whisper ASR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 auto_infer_with_segments.py                    # Process all countries
  python3 auto_infer_with_segments.py --countries KOR JPN  # Process specific countries
  python3 auto_infer_with_segments.py --force            # Reprocess all countries
  python3 auto_infer_with_segments.py --direct           # Use auto-detection mode
  python3 auto_infer_with_segments.py --no-skip-invalid  # Process all segments including invalid

The script will:
1. Load timestamp JSON files from timestamp/ directory
2. Find corresponding audio files in the audio directory
3. Extract audio segments based on timestamps
4. Transcribe each segment using Whisper
5. Save results in standard project format using save_transcription()

Output format:
- Uses standard save_transcription() format consistent with elevenlabs
- Saves each segment as a separate entry with start/end times
- Invalid segments are saved with empty transcriptions
- Results are saved as {country_code}_{MODEL_NAME}.json
        """
    )

    parser.add_argument(
        '--countries',
        nargs='+',
        help='Specific countries to process (3-letter codes). If not specified, process all available countries.'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing of all countries, clearing existing results'
    )

    parser.add_argument(
        '--direct',
        action='store_true',
        help='Use Whisper auto-detection mode (skip language mapping, let model detect language automatically)'
    )

    parser.add_argument(
        '--no-skip-invalid',
        action='store_true',
        help='Process invalid segments as well (by default, invalid segments are saved with empty transcriptions)'
    )

    parser.add_argument(
        '--timestamp-dir',
        default=TIMESTAMP_DIR,
        help=f'Timestamp directory path (default: {TIMESTAMP_DIR})'
    )

    parser.add_argument(
        '--audio-dir',
        default=AUDIO_DIR,
        help=f'Audio files directory path (default: {AUDIO_DIR})'
    )

    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()

    # Update global configuration
    global TIMESTAMP_DIR, AUDIO_DIR
    TIMESTAMP_DIR = args.timestamp_dir
    AUDIO_DIR = args.audio_dir

    try:
        batch_infer_segments(
            countries=args.countries,
            force=args.force,
            direct=args.direct,
            skip_invalid=not args.no_skip_invalid
        )
    except KeyboardInterrupt:
        print("\n⚠ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()