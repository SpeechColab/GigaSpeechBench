import argparse
import io
import json
import logging
import os
from collections import namedtuple
from pathlib import Path
from typing import Optional

from google.api_core import retry
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from pydub import AudioSegment
from tqdm import tqdm

from scripts.utils import save_transcription

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

TranscriptionSegment = namedtuple("TranscriptionSegment", ["audio_path", "start_time", "end_time", "text", "model", "language"])

ALPHA3_TO_BCP47_MAP = {
    # English accent
    "CHN-EN": "en-US",  
    "IDN-EN": "en-US",  
    "JPN-EN": "en-US", 
    "PHL-EN": "en-US", 
    "SCT-EN": "en-GB",  
    "SGP-EN": "en-US",  
    "JIN": "cmn-Hans-CN",  
    "XIANG": "cmn-Hans-CN",  
    "ARE": "ar-AE",
    "DZA": "ar-DZ",
    "EGY": "ar-EG",
    "IDN": "id-ID",
    "IRQ": "ar-IQ",
    "JPN": "ja-JP",
    "KOR": "ko-KR",
    "MAR": "ar-MA",
    "MYS": "ms-MY",
    "PHL": "fil-PH",
    "SAU": "ar-SA",
    "THA": "th-TH",
    "VNM": "vi-VN",
    "USA": "en-US",
    "CHN": "cmn-Hans-CN",
    "MED-CH": "cmn-Hans-CN",  
    "LAW-CH": "cmn-Hans-CN", 
    "FIN-CH": "cmn-Hans-CN", 
    "EDU-CH": "cmn-Hans-CN",  
    "ART-CH": "cmn-Hans-CN",  
    "MIL-CH": "cmn-Hans-CN",  
    "HUM-CH": "cmn-Hans-CN", 
    "AIT-CH": "cmn-Hans-CN",
    "BIO-CH": "cmn-Hans-CN",
    "ECM-CH": "cmn-Hans-CN",
	"ENT-CH": "cmn-Hans-CN",
	"AGR-CH": "cmn-Hans-CN",
    "ENG-CH": "cmn-Hans-CN",
    "MED-EN": "en-US",  
    "LAW-EN": "en-US", 
    "FIN-EN": "en-US", 
    "EDU-EN": "en-US",  
    "ART-EN": "en-US",  
    "MIL-EN": "en-US",  
    "HUM-EN": "en-US", 
    "AIT-EN": "en-US",
    "BIO-EN": "en-US",
    "ECM-EN": "en-US",
	"ENT-EN": "en-US",
	"AGR-EN": "en-US",
    "ENG-EN": "en-US",
}

_speech_client = None


def get_speech_client() -> SpeechClient:
    global _speech_client
    if _speech_client is None:
        api_endpoint = f"{DEFAULT_LOCATION}-speech.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)
        _speech_client = SpeechClient(client_options=client_options)
        logger.info(f"SpeechClient initialized, endpoint: {api_endpoint}")
    return _speech_client


def transcribe_audio_segment(audio_path: str, start: Optional[float] = None, end: Optional[float] = None, language: Optional[str] = None) -> TranscriptionSegment:
    log_context = f"[File: {audio_path} | Language: {language} | Start: {start} | End: {end} | Model: {OUTPUT_MODEL_NAME} | Project: {PROJECT_ID} | Region: {DEFAULT_LOCATION}]"

    if not language:
        raise ValueError(f"Language parameter (language) must be provided. {log_context}")

    if language not in ALPHA3_TO_BCP47_MAP:
        msg = f"Unsupported language code: '{language}'. Supported: {list(ALPHA3_TO_BCP47_MAP.keys())}. {log_context}"
        logger.error(msg)
        raise ValueError(msg)

    try:
        abs_audio_path = os.path.abspath(audio_path)
        audio = AudioSegment.from_file(audio_path)
        audio_duration_ms = len(audio)
        audio_duration_sec = audio_duration_ms / MS_PER_SECOND

        start_ms = int(start * MS_PER_SECOND) if start is not None and start > 0 else 0
        end_ms = int(end * MS_PER_SECOND) if end is not None and end > 0 else audio_duration_ms

        if start is not None and start >= audio_duration_sec:
            raise ValueError(f"Start time ({start:.2f}s) exceeds audio duration ({audio_duration_sec:.2f}s)")
        actual_end = end if end is not None else audio_duration_sec
        if start is not None and start > actual_end:
            raise ValueError(f"Invalid timestamps: start time ({start:.2f}s) is later than end time ({actual_end:.2f}s)")
        if end_ms > audio_duration_ms:
            end_ms = audio_duration_ms

        actual_start_sec = start_ms / MS_PER_SECOND
        actual_end_sec = end_ms / MS_PER_SECOND

        segment = audio[start_ms:end_ms]
        segment_duration_sec = len(segment) / MS_PER_SECOND

        if segment_duration_sec > MAX_SYNC_DURATION_SEC:
            raise ValueError(f"Audio segment duration ({segment_duration_sec:.1f}s) exceeds sync request limit ({MAX_SYNC_DURATION_SEC}s)")

        with io.BytesIO() as audio_buffer:
            segment.export(audio_buffer, format="wav")
            audio_content = audio_buffer.getvalue()

    except Exception as e:
        raise Exception(f"Audio preprocessing failed: {str(e)} | {log_context}") from e

    try:
        api_language_code = ALPHA3_TO_BCP47_MAP[language]
        recognizer_path = f"projects/{PROJECT_ID}/locations/{DEFAULT_LOCATION}/recognizers/_"

        client = get_speech_client()

        recognition_features = cloud_speech.RecognitionFeatures(enable_automatic_punctuation=True)
        config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            model=MODEL_NAME,
            features=recognition_features,
            language_codes=[api_language_code],
        )

        request = cloud_speech.RecognizeRequest(
            recognizer=recognizer_path,
            config=config,
            content=audio_content,
        )

        response = client.recognize(
            request=request,
            retry=retry.Retry(
                predicate=lambda exc: True, initial=1.0, maximum=30.0, multiplier=2.0, deadline=300.0, on_error=lambda exc: logger.warning(f"API request failed, retrying: {exc} | {log_context}")
            ),
        )

        full_transcript = " ".join(res.alternatives[0].transcript for res in response.results if res.alternatives).strip()

        return TranscriptionSegment(audio_path=abs_audio_path, start_time=actual_start_sec, end_time=actual_end_sec, text=full_transcript, model=OUTPUT_MODEL_NAME, language=language)

    except Exception as e:
        raise Exception(f"API request ultimately failed (language: {api_language_code}): {str(e)} | {log_context}") from e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Speech-to-Text V2 (Chirp) inference tool")
    parser.add_argument("--json_dir", required=True, type=Path)
    parser.add_argument("--audio_dir", required=True, type=Path)
    parser.add_argument("--project_id", type=str, default="YOUR_PROJECT_ID",
                        help="Google Cloud project ID")
    parser.add_argument("--location", type=str, default="us-central1",
                        help="Google Cloud region (e.g. us-central1, eu)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Log level (default: INFO)")

    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    PROJECT_ID = args.project_id
    DEFAULT_LOCATION = args.location

    if not args.json_dir.exists():
        logger.error(f"Input directory does not exist: {args.json_dir}")
        exit(1)

    languages = [f.name for f in args.json_dir.iterdir()]
    audio_langs = [f.name for f in args.audio_dir.iterdir()]
    if set(languages) != set(audio_langs):
        logger.warning(f"JSON and audio language directories are inconsistent: json={languages}, audio={audio_langs}")

    total_processed_seconds = 0.0

    for lang in tqdm(languages, desc="language", disable=numeric_level > logging.INFO):
        lang_json_dir = args.json_dir / lang
        for json_path in tqdm(list(lang_json_dir.glob("*.json")), desc="json", disable=numeric_level > logging.INFO):
            with open(json_path) as f:
                obj = json.load(f)
            audio_path = (args.audio_dir / lang / obj["audio_name"]).with_suffix(".wav")
            total_segments = len(obj.get("segments", []))
            success_count = 0

            try:
                if not audio_path.exists():
                    raise FileNotFoundError(f"Audio file does not exist: {str(audio_path)}")

                for idx, segment in enumerate(obj["segments"]):
                    try:
                        if segment.get("status") == "valid":
                            seg_start = float(segment.get("start", segment.get("begin_time", 0)))
                            seg_end = float(segment.get("end", segment.get("end_time", 0)))
                            seg_pred = transcribe_audio_segment(str(audio_path), language=lang, start=seg_start, end=seg_end)
                            save_transcription(
                                audio_path=audio_path,
                                text=seg_pred.text,
                                language=seg_pred.language,
                                model=OUTPUT_MODEL_NAME,
                                start_time=seg_pred.start_time,
                                end_time=seg_pred.end_time,
                            )
                            total_processed_seconds += seg_pred.end_time - seg_pred.start_time
                        else:
                            continue
                        success_count += 1

                    except Exception as e:
                        error_context = f"[File: {json_path}:{idx} | Language: {lang}]"
                        logger.error(f"Segment transcription ultimately failed: {e} | {error_context}")
                        save_transcription(
                            audio_path=audio_path,
                            text="",
                            language=lang,
                            model=OUTPUT_MODEL_NAME,
                            start_time=float(segment.get("start", segment.get("begin_time", 0))),
                            end_time=float(segment.get("end", segment.get("end_time", 0))),
                        )

            except FileNotFoundError as e:
                logger.error(f"Audio file missing: {e} | [JSON: {json_path}, Language: {lang}]")
                continue
            except Exception as e:
                logger.error(f"File processing error: {e} | [JSON: {json_path}, Language: {lang}]")
                continue

            logger.info(f"JSON file {json_path.name} processing complete: {success_count}/{total_segments} segments successful.")
            if success_count != total_segments:
                logger.error(f"JSON file {json_path.name} success count mismatch: {success_count}/{total_segments}.")

    if total_processed_seconds > 0:
        total_hours = total_processed_seconds / 3600
        logger.info(f"===== Total Processing Statistics =====")
        logger.info(f"Total processing duration: {total_hours:.2f} hours ({total_processed_seconds:.1f} seconds)")
        logger.info(f"Quota usage: {total_hours/480*100:.1f}% (daily limit: 480 hours)")

