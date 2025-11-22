#!/usr/bin/env python3
"""
Batch inference script for Whisper ASR
Processes audio files from multiple countries and saves results in unified format
"""

import os
import sys
import glob
import argparse
import shutil
from pathlib import Path
from typing import List, Dict, Set
from whisper_asr import WhisperASR
from language_mapping import get_supported_country_codes, COUNTRY_CODE_TO_LANGUAGE

# Configuration
DATA_DIR = '/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yanqiaozhu/Multilingual-ASR-Benchmark/examples/whisper-large-v3/data/testbatch_processed/testbatch_processed'
RESULTS_DIR = './results'
MODEL_DIR = '/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yanqiaozhu/Multilingual-ASR-Benchmark/examples/whisper-large-v3/whisper_model'
MODEL_NAME = 'whisper-large-v3'

def get_country_directories() -> List[str]:
    """Get list of country code directories in the data folder"""
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    countries = []
    for item in os.listdir(DATA_DIR):
        country_path = os.path.join(DATA_DIR, item)
        if os.path.isdir(country_path) and len(item) == 3:  # 3-letter country codes
            countries.append(item)

    return sorted(countries)

def check_language_mapping(countries: List[str]) -> None:
    """Check if all countries have language mapping, raise error if not"""
    unsupported_countries = []
    for country in countries:
        if country not in COUNTRY_CODE_TO_LANGUAGE:
            unsupported_countries.append(country)

    if unsupported_countries:
        error_msg = f"Unsupported country codes found: {', '.join(unsupported_countries)}\n"
        error_msg += "Please check and add these countries to COUNTRY_CODE_TO_LANGUAGE in language_mapping.py\n"
        error_msg += f"Currently supported countries: {', '.join(sorted(COUNTRY_CODE_TO_LANGUAGE.keys()))}"
        raise ValueError(error_msg)

def get_existing_results() -> Set[str]:
    """Get set of country codes that already have results files"""
    existing = set()
    if not os.path.exists(RESULTS_DIR):
        return existing

    pattern = os.path.join(RESULTS_DIR, f"*_{MODEL_NAME}.json")
    for filepath in glob.glob(pattern):
        filename = os.path.basename(filepath)
        # Extract country code from filename like "IRQ_whisper-large-v3.json"
        parts = filename.split('_')
        if len(parts) >= 2:
            country_code = parts[0]
            existing.add(country_code)

    return existing

def clear_existing_results(countries: List[str]) -> None:
    """Clear existing result files for specified countries"""
    if not os.path.exists(RESULTS_DIR):
        return

    for country in countries:
        filename = f"{country}_{MODEL_NAME}.json"
        filepath = os.path.join(RESULTS_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"  ✓ Removed existing result: {filename}")

def get_audio_files(country_code: str) -> List[str]:
    """Get all audio files for a specific country"""
    country_path = os.path.join(DATA_DIR, country_code)
    audio_files = []

    # Support common audio formats
    audio_extensions = ['*.wav', '*.mp3', '*.flac', '*.m4a', '*.ogg']

    for ext in audio_extensions:
        pattern = os.path.join(country_path, ext)
        audio_files.extend(glob.glob(pattern))

    return sorted(audio_files)

def batch_infer_countries(force: bool = False, direct: bool = False):
    """Batch process audio files from all countries"""
    print("=== Whisper ASR Batch Inference ===")
    print(f"Data directory: {DATA_DIR}")
    print(f"Results directory: {RESULTS_DIR}")
    print(f"Model directory: {MODEL_DIR}")
    print(f"Force mode: {force}")
    print(f"Direct auto-detection mode: {direct}")

    # Create results directory
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Get all country directories
    countries = get_country_directories()
    print(f"Found {len(countries)} countries: {', '.join(countries)}")

    # Check language mapping for all countries (skip in direct mode)
    if not direct:
        print("\nChecking language mapping...")
        try:
            check_language_mapping(countries)
            print("✓ All countries have language mapping")
        except ValueError as e:
            print(f"✗ Language mapping error: {e}")
            return
    else:
        print("\nSkipping language mapping check (direct auto-detection mode enabled)")

    # Handle existing results
    existing_results = get_existing_results()
    if existing_results:
        print(f"\nFound existing results for: {', '.join(sorted(existing_results))}")

        if force:
            print("Force mode enabled - clearing existing results...")
            clear_existing_results(list(existing_results))
            countries_to_process = countries
        else:
            print("Skipping countries with existing results (use --force to reprocess)")
            countries_to_process = [c for c in countries if c not in existing_results]

            if not countries_to_process:
                print("✓ All countries already processed. Use --force to reprocess.")
                return
    else:
        countries_to_process = countries

    print(f"\nCountries to process: {', '.join(countries_to_process)}")

    # Initialize Whisper ASR (reuse same model for all countries)
    print("\nInitializing Whisper ASR model...")
    try:
        asr = WhisperASR(model_dir=MODEL_DIR)
        print("✓ Model initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize model: {e}")
        return

    # Process each country
    total_files = 0
    processed_files = 0

    for country_code in countries_to_process:
        print(f"\n--- Processing {country_code} ---")

        # Get audio files for this country
        audio_files = get_audio_files(country_code)
        if not audio_files:
            print(f"⚠ No audio files found for {country_code}")
            continue

        total_files += len(audio_files)
        print(f"Found {len(audio_files)} audio files")

        # Process each audio file
        for i, audio_path in enumerate(audio_files, 1):
            try:
                print(f"  [{i}/{len(audio_files)}] Processing: {os.path.basename(audio_path)}")

                # Get audio duration for proper time stamps
                import torchaudio
                try:
                    waveform, sr = torchaudio.load(audio_path)
                    duration = waveform.shape[1] / sr
                except:
                    duration = 0.0

                # Format audio path as {country_code}/{filename}
                audio_filename = os.path.basename(audio_path)
                formatted_path = f"{country_code}/{audio_filename}"

                if direct:
                    # Use auto-detection mode
                    text = asr.transcribe(audio_path, language_code=None)
                    # Save with proper timestamps
                    import sys
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    from utils import save_transcription
                    save_transcription(formatted_path, text, country_code, MODEL_NAME, 0.0, duration)
                    print(f"    ✓ Auto-detected language: {text[:50]}...")
                else:
                    # Use country-specific language
                    text = asr.transcribe(audio_path, country_code)
                    # Save with proper timestamps
                    import sys
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    from utils import save_transcription
                    save_transcription(formatted_path, text, country_code, MODEL_NAME, 0.0, duration)
                    print(f"    ✓ Transcribed: {text[:50]}...")

                processed_files += 1

            except Exception as e:
                print(f"    ✗ Error processing {audio_path}: {e}")
                continue

    # Summary
    print(f"\n=== Processing Complete ===")
    print(f"Total files found: {total_files}")
    print(f"Successfully processed: {processed_files}")
    print(f"Failed: {total_files - processed_files}")
    print(f"Results saved in: {RESULTS_DIR}/")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Batch inference script for Whisper ASR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 auto_infer.py                    # Process new countries only
  python3 auto_infer.py --force            # Reprocess all countries
  python3 auto_infer.py --direct           # Use auto-detection mode
  python3 auto_infer.py --force --direct   # Force reprocess with auto-detection
  python3 auto_infer.py --no-force         # Default behavior (same as above)

The script will:
1. Check language mapping for all detected countries (skipped with --direct)
2. Skip countries that already have results (unless --force is used)
3. Process audio files and save results in utils.py format
4. Results are saved as {country_code}_whisper-large-v3.json

Modes:
- Normal mode: Uses country-specific language from language_mapping.py
- Direct mode (--direct): Uses Whisper auto-detection for each audio file

If a country is not found in COUNTRY_CODE_TO_LANGUAGE mapping,
the script will raise an error directing you to update language_mapping.py
(unless --direct mode is used).
        """
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing of all countries, clearing existing results'
    )

    parser.add_argument(
        '--no-force',
        action='store_true',
        help='Skip countries that already have results (default behavior)'
    )

    parser.add_argument(
        '--direct',
        action='store_true',
        help='Use Whisper auto-detection mode (skip language mapping, let model detect language automatically)'
    )

    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()

    # Default behavior is no-force
    force_mode = args.force and not args.no_force
    direct_mode = args.direct

    try:
        batch_infer_countries(force=force_mode, direct=direct_mode)
    except KeyboardInterrupt:
        print("\n⚠ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()