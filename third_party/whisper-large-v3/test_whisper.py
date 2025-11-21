#!/usr/bin/env python3
"""
Test script for Whisper ASR wrapper
Demonstrates usage with different language codes
"""

import os
import sys
from whisper_asr import WhisperASR, transcribe_audio
from language_mapping import country_code_to_language, get_supported_country_codes

def test_language_mapping():
    """Test language code conversion"""
    print("=== Testing Language Code Mapping ===")
    test_codes = ["IRQ", "USA", "CHN", "ESP", "FRA", "DEU"]

    for code in test_codes:
        try:
            language = country_code_to_language(code)
            print(f"✓ {code} -> {language}")
        except ValueError as e:
            print(f"✗ {code} -> ERROR: {e}")

def test_whisper_asr():
    """Test Whisper ASR functionality"""
    print("\n=== Testing Whisper ASR ===")

    # Check if we have a test audio file
    test_audio = "test.mp3"
    if not os.path.exists(test_audio):
        print(f"⚠ Test audio file '{test_audio}' not found.")
        print("To test with actual audio:")
        print("1. Place an audio file named 'test.mp3' in this directory")
        print("2. Or modify the test_audio variable to point to your audio file")
        print("3. Then run this script again")
        return

    # Initialize ASR
    try:
        print("Initializing Whisper ASR...")
        asr = WhisperASR()

        # Test with different language codes
        test_cases = [
            ("IRQ", "Arabic"),
            ("USA", "English"),
            ("CHN", "Chinese")
        ]

        for lang_code, lang_name in test_cases:
            print(f"\n--- Testing with {lang_name} ({lang_code}) ---")
            try:
                text = asr.transcribe(test_audio, lang_code)
                print(f"✓ Transcription successful: {text[:100]}...")

                # Test save functionality
                saved_text = asr.transcribe_and_save(test_audio, lang_code)
                print(f"✓ Saved to results/{lang_code}_whisper-large-v3.json")

            except Exception as e:
                print(f"✗ Error with {lang_code}: {e}")

    except Exception as e:
        print(f"✗ Failed to initialize Whisper ASR: {e}")
        print("Make sure:")
        print("1. The whisper model directory exists at './whisper_model'")
        print("2. PyTorch and transformers are installed")
        print("3. You have sufficient GPU/CPU memory")

def show_supported_codes():
    """Show all supported country codes"""
    print("\n=== Supported Country Codes ===")
    codes = get_supported_country_codes()

    # Group by language for better readability
    language_groups = {}
    for code in codes:
        lang = country_code_to_language(code)
        if lang not in language_groups:
            language_groups[lang] = []
        language_groups[lang].append(code)

    for lang, codes_list in sorted(language_groups.items()):
        print(f"{lang.title()}: {', '.join(codes_list)}")

def main():
    """Main test function"""
    print("Whisper ASR Wrapper Test")
    print("=" * 50)

    # Test language mapping
    test_language_mapping()

    # Show supported codes
    show_supported_codes()

    # Test actual ASR (if audio available)
    test_whisper_asr()

    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    main()