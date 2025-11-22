import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import torchaudio
import os
import numpy as np
from typing import Optional, Union
from language_mapping import country_code_to_language

class WhisperASR:
    """
    Whisper ASR wrapper that follows the project interface:
    Input: audio_path (str) - absolute path to audio file
    Output: text (str) - transcribed text
    """

    def __init__(self, model_dir: str = "./whisper_model", device: Optional[str] = None):
        """
        Initialize Whisper ASR model

        Args:
            model_dir (str): Path to the whisper model directory
            device (str): Device to use ('cuda', 'cpu', or None for auto-detection)
        """
        self.model_dir = model_dir
        self.device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        self.torch_dtype = torch.float16 if "cuda" in self.device else torch.float32

        # Load model and processor
        self._load_model()

    def _load_model(self):
        """Load the Whisper model and processor"""
        print(f"[INFO] Loading Whisper model from {self.model_dir}")
        print(f"[INFO] Using device: {self.device}")

        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.model_dir,
            torch_dtype=self.torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True
        )
        self.model.to(self.device)

        self.processor = AutoProcessor.from_pretrained(self.model_dir)

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            torch_dtype=self.torch_dtype,
            device=self.device,
        )

        print("[INFO] Whisper model loaded successfully")

    def transcribe(self, audio_path: str, language_code: Optional[str] = None) -> str:
        """
        Transcribe audio file to text

        Args:
            audio_path (str): Absolute path to the audio file
            language_code (str, optional): 3-letter country code (e.g., "IRQ", "USA")

        Returns:
            str: Transcribed text
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"[INFO] Transcribing: {audio_path}")

        # Convert country code to Whisper language name if provided
        whisper_language = None
        if language_code:
            try:
                whisper_language = country_code_to_language(language_code)
                print(f"[INFO] Using language: {whisper_language} (from country code: {language_code})")
            except ValueError as e:
                print(f"[WARN] {e}. Using auto-detection.")

        try:
            # Use the pipeline to transcribe with language if specified
            kwargs = {"return_timestamps": True}
            if whisper_language:
                kwargs["generate_kwargs"] = {"language": whisper_language}

            result = self.pipe(audio_path, **kwargs)
            text = result["text"].strip()

            print(f"[INFO] Transcription completed")
            return text

        except Exception as e:
            print(f"[ERROR] Transcription failed: {e}")
            raise

    def transcribe_and_save(self, audio_path: str, language_code: str) -> str:
        """
        Transcribe audio and save result using utils.py format

        Args:
            audio_path (str): Absolute path to the audio file
            language_code (str): 3-letter country code (e.g., "IRQ", "ENG")

        Returns:
            str: Transcribed text
        """
        # Import here to avoid circular imports
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from utils import save_transcription

        # Transcribe the audio with language specification
        text = self.transcribe(audio_path, language_code)

        # Save using the project's standard format
        save_transcription(audio_path, text, language_code, "whisper-large-v3")

        return text

    def transcribe_audio_array(self, audio_array: np.ndarray, language_code: Optional[str] = None, sample_rate: int = 16000) -> str:
        """
        Transcribe audio array to text

        Args:
            audio_array (np.ndarray): Audio data as numpy array
            language_code (str, optional): 3-letter country code (e.g., "IRQ", "USA")
            sample_rate (int): Sample rate of the audio array (default: 16000)

        Returns:
            str: Transcribed text
        """
        if not isinstance(audio_array, np.ndarray):
            raise ValueError("Audio input must be a numpy array")

        if len(audio_array) == 0:
            return ""

        print(f"[INFO] Transcribing audio array: {len(audio_array)} samples at {sample_rate}Hz")

        # Convert country code to Whisper language name if provided
        whisper_language = None
        if language_code:
            try:
                whisper_language = country_code_to_language(language_code)
                print(f"[INFO] Using language: {whisper_language} (from country code: {language_code})")
            except ValueError as e:
                print(f"[WARN] {e}. Using auto-detection.")

        try:
            # Convert numpy array to the format expected by the pipeline
            # The pipeline expects either a file path or raw audio data
            # For raw audio, we need to ensure it's in the right format

            # Use the pipeline to transcribe with language if specified
            kwargs = {
                "return_timestamps": True
            }

            if whisper_language:
                kwargs["generate_kwargs"] = {"language": whisper_language}

            # Process the audio array directly
            result = self.pipe(audio_array, **kwargs)
            text = result["text"].strip()

            print(f"[INFO] Array transcription completed")
            return text

        except Exception as e:
            print(f"[ERROR] Audio array transcription failed: {e}")
            raise

    def transcribe_audio_array_and_save(self, audio_array: np.ndarray, audio_path: str, language_code: str, sample_rate: int = 16000) -> str:
        """
        Transcribe audio array and save result using utils.py format

        Args:
            audio_array (np.ndarray): Audio data as numpy array
            audio_path (str): Original audio file path for saving metadata
            language_code (str): 3-letter country code (e.g., "IRQ", "ENG")
            sample_rate (int): Sample rate of the audio array (default: 16000)

        Returns:
            str: Transcribed text
        """
        # Transcribe the audio array
        text = self.transcribe_audio_array(audio_array, language_code, sample_rate)

        # Import here to avoid circular imports
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from utils import save_transcription

        # Save using the project's standard format
        save_transcription(audio_path, text, language_code, "whisper-large-v3")

        return text


# Convenience function for direct usage
def transcribe_audio(audio_path: str, language: str = "ENG", model_dir: str = "./whisper_model") -> str:
    """
    Convenience function to transcribe audio and save results

    Args:
        audio_path (str): Absolute path to audio file
        language (str): Language code (default: "ENG")
        model_dir (str): Path to whisper model (default: "./whisper_model")

    Returns:
        str: Transcribed text
    """
    asr = WhisperASR(model_dir)
    return asr.transcribe_and_save(audio_path, language)


# Test usage
if __name__ == "__main__":
    # Example usage
    audio_file = "test.mp3"  # Replace with actual audio path
    breakpoint()
    language_code = "ENG"     # Replace with appropriate language code

    try:
        # Initialize ASR
        whisper_asr = WhisperASR()

        # Transcribe and save
        transcribed_text = whisper_asr.transcribe_and_save(audio_file, language_code)

        print(f"Transcription: {transcribed_text}")

    except Exception as e:
        print(f"Error: {e}")