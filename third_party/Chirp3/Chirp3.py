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

PROJECT_ID = "steady-fin-478206-g9"
DEFAULT_LOCATION = "eu"
MODEL_NAME = "chirp_3"  # Actual API model name
OUTPUT_MODEL_NAME = "chirp3"  # Display name in outputs
MS_PER_SECOND = 1000.0
MAX_SYNC_DURATION_SEC = 60

TranscriptionSegment = namedtuple("TranscriptionSegment", ["audio_path", "start_time", "end_time", "text", "model", "language"])

ALPHA3_TO_BCP47_MAP = {
    # English accent
    "CHN-EN": "en-US",  # Chinese-accented English, use US English model
    "IDN-EN": "en-US",  # Indonesian-accented English
    "JPN-EN": "en-US",  # Japan口音英语
    "PHL-EN": "en-US",  # Philippines口音英语
    "SCT-EN": "en-GB",  # 苏格兰口音英语用英式英语模型
    "SGP-EN": "en-US",  # 新加坡口音英语
    "JIN": "cmn-Hans-CN",  # Jin dialect(山西话)用普通话模型
    "XIANG": "cmn-Hans-CN",# Xiang dialect(湖南话)用普通话模型

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
}

_speech_client = None


def get_speech_client() -> SpeechClient:
    global _speech_client
    if _speech_client is None:
        api_endpoint = f"{DEFAULT_LOCATION}-speech.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)
        _speech_client = SpeechClient(client_options=client_options)
        logger.info(f"SpeechClient 初始化完成，服务端点: {api_endpoint}")
    return _speech_client


def transcribe_audio_segment(audio_path: str, start: Optional[float] = None, end: Optional[float] = None, language: Optional[str] = None) -> TranscriptionSegment:
    log_context = f"[文件: {audio_path} | 语言: {language} | Start: {start} | End: {end} | 模型: {OUTPUT_MODEL_NAME} | 项目: {PROJECT_ID} | 区域: {DEFAULT_LOCATION}]"

    if not language:
        raise ValueError(f"必须提供语言参数 (language)。{log_context}")

    if language not in ALPHA3_TO_BCP47_MAP:
        msg = f"不支持的语言代码: '{language}'。支持列表: {list(ALPHA3_TO_BCP47_MAP.keys())}。{log_context}"
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
            raise ValueError(f"起始时间 ({start:.2f}s) 超出音频总时长 ({audio_duration_sec:.2f}s)")
        actual_end = end if end is not None else audio_duration_sec
        if start is not None and start > actual_end:
            raise ValueError(f"时间戳无效: 起始时间 ({start:.2f}s) 晚于结束时间 ({actual_end:.2f}s)")
        if end_ms > audio_duration_ms:
            end_ms = audio_duration_ms

        actual_start_sec = start_ms / MS_PER_SECOND
        actual_end_sec = end_ms / MS_PER_SECOND

        segment = audio[start_ms:end_ms]
        segment_duration_sec = len(segment) / MS_PER_SECOND

        if segment_duration_sec > MAX_SYNC_DURATION_SEC:
            raise ValueError(f"音频片段时长 ({segment_duration_sec:.1f}s) 超过同步请求最大限制 ({MAX_SYNC_DURATION_SEC}s)")

        with io.BytesIO() as audio_buffer:
            segment.export(audio_buffer, format="wav")
            audio_content = audio_buffer.getvalue()

    except Exception as e:
        raise Exception(f"音频预处理失败: {str(e)} | {log_context}") from e

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
                predicate=lambda exc: True, initial=1.0, maximum=30.0, multiplier=2.0, deadline=300.0, on_error=lambda exc: logger.warning(f"API 请求失败，正在重试: {exc} | {log_context}")
            ),
        )

        full_transcript = " ".join(res.alternatives[0].transcript for res in response.results if res.alternatives).strip()

        return TranscriptionSegment(audio_path=abs_audio_path, start_time=actual_start_sec, end_time=actual_end_sec, text=full_transcript, model=OUTPUT_MODEL_NAME, language=language)

    except Exception as e:
        raise Exception(f"API 请求最终失败 (语言: {api_language_code}): {str(e)} | {log_context}") from e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Speech-to-Text V2 (Chirp) 推理工具")
    parser.add_argument("--json_dir", required=True, type=Path)
    parser.add_argument("--audio_dir", required=True, type=Path)
    parser.add_argument("--project_id", type=str, default=PROJECT_ID)
    parser.add_argument("--location", type=str, default=DEFAULT_LOCATION)
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="日志级别（默认: INFO）")

    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    PROJECT_ID = args.project_id
    DEFAULT_LOCATION = args.location

    if not args.json_dir.exists():
        logger.error(f"输入目录不存在: {args.json_dir}")
        exit(1)

    languages = [f.name for f in args.json_dir.iterdir()]
    audio_langs = [f.name for f in args.audio_dir.iterdir()]
    if set(languages) != set(audio_langs):
        logger.warning(f"json 和 audio 语言目录不一致: json={languages}, audio={audio_langs}")

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
                    raise FileNotFoundError(f"音频文件不存在：{str(audio_path)}")

                for idx, segment in enumerate(obj["segments"]):
                    try:
                        if segment["status"] == "valid":
                            seg_pred = transcribe_audio_segment(str(audio_path), language=lang, start=segment["start"], end=segment["end"])
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
                        error_context = f"[文件: {json_path}:{idx} | 语言: {lang}]"
                        logger.error(f"片段转写最终失败: {e} | {error_context}")
                        save_transcription(
                            audio_path=audio_path,
                            text="",
                            language=lang,
                            model=OUTPUT_MODEL_NAME,
                            start_time=segment["start"],
                            end_time=segment["end"],
                        )

            except FileNotFoundError as e:
                logger.error(f"音频文件缺失: {e} | [JSON: {json_path}, 语言: {lang}]")
                continue
            except Exception as e:
                logger.error(f"文件处理异常: {e} | [JSON: {json_path}, 语言: {lang}]")
                continue

            logger.info(f"JSON文件 {json_path.name} 处理完成：{success_count}/{total_segments} 个片段成功。")
            if success_count != total_segments:
                logger.error(f"JSON文件 {json_path.name} 成功数不匹配：{success_count}/{total_segments}。")

    if total_processed_seconds > 0:
        total_hours = total_processed_seconds / 3600
        logger.info(f"===== 总处理统计 =====")
        logger.info(f"总处理时长: {total_hours:.2f} 小时 ({total_processed_seconds:.1f} 秒)")
        logger.info(f"配额使用率: {total_hours/480*100:.1f}% (每日限额: 480 小时)")

