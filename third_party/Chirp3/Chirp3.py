import io
import logging
import os
import argparse
from collections import namedtuple
from pathlib import Path
from typing import Optional

from google.api_core import retry
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from pydub import AudioSegment
from tqdm import tqdm

# 初始化日志记录器
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- 全局默认配置 ---
# 注意：以下为默认值，建议通过命令行参数进行覆盖
PROJECT_ID = "steady-fin-478206-g9"
DEFAULT_LOCATION = "eu"
MODEL_NAME = "chirp_3"
MS_PER_SECOND = 1000.0

# Google Speech-to-Text V2 同步请求限制：音频时长不得超过 60 秒
# 参考文档：https://docs.cloud.google.com/speech-to-text/quotas
MAX_SYNC_DURATION_SEC = 60

TranscriptionSegment = namedtuple("TranscriptionSegment", ["audio_path", "start_time", "end_time", "text", "model", "language"])

# 语言代码映射表：将 ISO 639-3 (三字母代码) 映射为 Google API 所需的 BCP-47 格式
ALPHA3_TO_BCP47_MAP = {
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
    """
    获取或延迟初始化全局 SpeechClient 实例。
    """
    global _speech_client
    if _speech_client is None:
        # Chirp 模型需要指定区域端点 (Regional Endpoint)
        api_endpoint = f"{DEFAULT_LOCATION}-speech.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)
        _speech_client = SpeechClient(client_options=client_options)
        logger.info(f"SpeechClient 初始化完成，服务端点: {api_endpoint}")
    return _speech_client


def transcribe_audio_segment(audio_path: str, start: Optional[float] = None, end: Optional[float] = None, language: Optional[str] = None) -> TranscriptionSegment:
    """
    调用 Google Speech-to-Text V2 API 对音频片段进行转写。

    处理流程：读取音频文件 -> 截取片段 -> 转换为 WAV 字节流 -> 发送 API 请求。

    Args:
        audio_path: 音频文件路径。
        start: 片段起始时间（秒）。
        end: 片段结束时间（秒）。
        language: ISO 639-3 语言代码 (如 "JPN")。

    Returns:
        TranscriptionSegment: 包含转写文本及元数据的对象。
    """

    # 构造通用的日志上下文，包含所有处理时的参数，方便排查
    log_context = f"[文件: {audio_path} | 语言: {language} | Start: {start} | End: {end} | 模型: {MODEL_NAME} | 项目: {PROJECT_ID} | 区域: {DEFAULT_LOCATION}]"

    if not language:
        raise ValueError(f"必须提供语言参数 (language)。{log_context}")

    if language not in ALPHA3_TO_BCP47_MAP:
        msg = f"不支持的语言代码: '{language}'。支持列表: {list(ALPHA3_TO_BCP47_MAP.keys())}。{log_context}"
        logger.error(msg)
        raise ValueError(msg)

    try:
        abs_audio_path = os.path.abspath(audio_path)
        # 使用 pydub 读取音频，支持自动探测多种格式 (wav, mp3, flac 等)
        audio = AudioSegment.from_file(audio_path)

        # 转换时间戳为毫秒
        start_ms = int(start * MS_PER_SECOND) if start is not None and start > 0 else 0
        end_ms = int(end * MS_PER_SECOND) if end is not None and end > 0 else len(audio)

        # 时间戳边界检查
        if start_ms >= len(audio):
            logger.warning(f"起始时间超出音频总时长，跳过处理。{log_context} | 音频总长: {len(audio)/MS_PER_SECOND:.2f}s")
        if end_ms > len(audio):
            end_ms = len(audio)
        if start_ms > end_ms:
            logger.warning(f"时间戳逻辑错误: 起始时间晚于结束时间。{log_context} | StartMs: {start_ms} | EndMs: {end_ms}")

        actual_start_sec = start_ms / MS_PER_SECOND
        actual_end_sec = end_ms / MS_PER_SECOND

        segment = audio[start_ms:end_ms]
        segment_duration_sec = len(segment) / MS_PER_SECOND

        # API 限制检查：同步请求不支持超过 60 秒的音频
        if segment_duration_sec > MAX_SYNC_DURATION_SEC:
            logger.warning(f"音频片段时长超过 API 限制 (60s)，跳过处理。{log_context} | 片段时长: {segment_duration_sec:.1f}s")
            return TranscriptionSegment(audio_path=abs_audio_path, start_time=actual_start_sec, end_time=actual_end_sec, text=None, model=MODEL_NAME, language=language)

        # 导出为 WAV 格式字节流，确保 API 兼容性
        with io.BytesIO() as audio_buffer:
            segment.export(audio_buffer, format="wav")
            audio_content = audio_buffer.getvalue()

    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"音频预处理失败: {str(e)} | {log_context}") from e

    try:
        api_language_code = ALPHA3_TO_BCP47_MAP[language]
        # 构造识别器路径，使用默认识别器标识符 '_'
        recognizer_path = f"projects/{PROJECT_ID}/locations/{DEFAULT_LOCATION}/recognizers/_"

        client = get_speech_client()

        # 启用自动标点功能
        recognition_features = cloud_speech.RecognitionFeatures(
            enable_automatic_punctuation=True,
        )

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

        # 发送请求，配置重试策略以应对网络波动
        response = client.recognize(
            request=request,
            retry=retry.Retry(
                predicate=lambda exc: True, initial=1.0, maximum=30.0, multiplier=2.0, deadline=300.0, on_error=lambda exc: logger.warning(f"API 请求失败，正在重试: {str(exc)} | {log_context}")
            ),
        )

        # 拼接结果中的所有候选项
        full_transcript = " ".join(res.alternatives[0].transcript for res in response.results if res.alternatives).strip()

        return TranscriptionSegment(audio_path=abs_audio_path, start_time=actual_start_sec, end_time=actual_end_sec, text=full_transcript, model=MODEL_NAME, language=language)

    except Exception as e:
        logger.error(f"API 请求异常: {str(e)} | {log_context}")
        raise Exception(f"API 请求异常 (语言: {api_language_code}): {str(e)}") from e


if __name__ == "__main__":
    from scripts.utils import save_transcription

    parser = argparse.ArgumentParser(description="Google Speech-to-Text V2 (Chirp) 推理工具")

    # 必选参数
    parser.add_argument("--input_dir", required=True, type=str, help="音频文件目录路径 (支持 wav, mp3, flac 等格式)")
    parser.add_argument("--lang", required=True, type=str, help="目标语言的三字母代码 (例如: JPN, CHN, USA)")

    # 可选参数
    parser.add_argument("--project_id", type=str, default=PROJECT_ID, help="Google Cloud 项目 ID")
    parser.add_argument("--location", type=str, default=DEFAULT_LOCATION, help="Google Cloud 区域 (如 eu, us)")

    args = parser.parse_args()

    # 更新全局配置
    PROJECT_ID = args.project_id
    DEFAULT_LOCATION = args.location

    input_path = Path(args.input_dir)
    if not input_path.exists():
        logger.error(f"输入目录不存在: {args.input_dir}")
        exit(1)

    # 递归查找目录下所有文件
    audio_files = [f for f in input_path.rglob("*") if f.is_file()]

    logger.info(f"在 {args.input_dir} 中发现 {len(audio_files)} 个文件")
    logger.info(f"任务配置 -> 语言: {args.lang} | 项目 ID: {PROJECT_ID} | 区域: {DEFAULT_LOCATION}")

    success_count = 0

    for file_path in tqdm(audio_files, desc="正在处理"):
        try:
            # 执行转写
            seg = transcribe_audio_segment(str(file_path), language=args.lang)

            if seg.text is not None:
                # 调用工具函数保存结果
                save_transcription(audio_path=seg.audio_path, text=seg.text, language=seg.model, model=seg.language, start_time=seg.start_time, end_time=seg.end_time)
                success_count += 1

        except Exception as e:
            # 捕获单个文件的处理异常，避免中断整个批次任务
            # 这里也补充完整的配置信息，防止上述函数外出现异常
            error_context = f"[文件: {file_path} | 语言: {args.lang} | 项目: {PROJECT_ID} | 区域: {DEFAULT_LOCATION}]"
            logger.error(f"文件处理失败: {e} | {error_context}")

    logger.info(f"任务完成。成功转写 {success_count}/{len(audio_files)} 个文件。")
