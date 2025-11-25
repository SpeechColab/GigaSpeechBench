import os
import io
import json
import logging
from pathlib import Path
from collections import namedtuple
from typing import Optional

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions
from pydub import AudioSegment
from tqdm import tqdm

from utils import save_transcription


# 日志
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# 全局配置
YOUR_PROJECT_ID = "steady-fin-478206-g9"
DEFAULT_LOCATION = "us"
MODEL_NAME = "chirp_3"
MAX_SYNC_DURATION_SEC = 60  # Speech-to-Text V2 同步识别的时长限制 (60s)
MS_PER_SECOND = 1000.0


# 用 namedtuple 存结果，方便后续处理
TranscriptionSegment = namedtuple("TranscriptionSegment", ["audio_path", "start_time", "end_time", "text", "model", "language"])


# 3 字母国家代码 (alpha-3) 转 BCP-47
# 仅包含本项目需要的语言
ALPHA3_TO_BCP47_MAP = {
    "ARE": "ar-AE",  # 阿拉伯语 (阿联酋)
    "DZA": "ar-DZ",  # 阿拉伯语 (阿尔及利亚)
    "EGY": "ar-EG",  # 阿拉伯语 (埃及)
    "IDN": "id-ID",  # 印度尼西亚语
    "IRQ": "ar-IQ",  # 阿拉伯语 (伊拉克)
    "JPN": "ja-JP",  # 日语
    "KOR": "ko-KR",  # 韩语
    "MAR": "ar-MA",  # 阿拉伯语 (摩洛哥)
    "MYS": "ms-MY",  # 马来语
    "PHL": "fil-PH",  # 菲律宾语
    "SAU": "ar-SA",  # 阿拉伯语 (沙特阿拉伯)
    "THA": "th-TH",  # 泰语
    "VNM": "vi-VN",  # 越南语
}


# SpeechClient (单例)
_speech_client = None


def get_speech_client() -> SpeechClient:
    """全局复用 SpeechClient，避免重复初始化。"""
    global _speech_client
    if _speech_client is None:
        # 必须指定 us 区域端点才能用 chirp
        api_endpoint = f"{DEFAULT_LOCATION}-speech.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)
        _speech_client = SpeechClient(client_options=client_options)
        logger.info(f"初始化 SpeechClient: {api_endpoint}")
    return _speech_client


def transcribe_audio_segment(audio_path: str, start: Optional[float] = None, end: Optional[float] = None, language: Optional[str] = None) -> TranscriptionSegment:
    """
    核心转录函数：调用 Google Speech-to-Text V2 (Chirp 3)。

    处理单个音频片段 (必须 < 60s)，使用 pydub 截取。

    Args:
        audio_path: 文件路径
        start: 开始时间 (秒)
        end: 结束时间 (秒)
        language: 3 字母国家代码 (如 "VNM")

    Returns:
        TranscriptionSegment (namedtuple)
    """

    # --- 1. 参数校验 ---
    if not language:
        raise ValueError("必须提供 language 参数")

    if language not in ALPHA3_TO_BCP47_MAP:
        msg = f"语言代码 '{language}' 不支持。可用: {list(ALPHA3_TO_BCP47_MAP.keys())}"
        logger.error(msg)
        raise ValueError(msg)

    # --- 2. pydub 音频截取 ---
    try:
        abs_audio_path = os.path.abspath(audio_path)
        audio = AudioSegment.from_file(audio_path)

        # 处理时间戳，None 则默认
        start_ms = int(start * MS_PER_SECOND) if start is not None and start > 0 else 0
        end_ms = int(end * MS_PER_SECOND) if end is not None and end > 0 else len(audio)

        # 边界检查
        if start_ms >= len(audio):
            raise ValueError("开始时间在音频结束之后")
        if end_ms > len(audio):
            end_ms = len(audio)
        if start_ms > end_ms:
            raise ValueError(f"开始时间 ({start_ms}ms) 不能晚于结束时间 ({end_ms}ms)")

        actual_start_sec = start_ms / MS_PER_SECOND
        actual_end_sec = end_ms / MS_PER_SECOND

        segment = audio[start_ms:end_ms]
        segment_duration_sec = len(segment) / MS_PER_SECOND

        # V2 同步 API 有时长限制
        if segment_duration_sec > MAX_SYNC_DURATION_SEC:
            raise ValueError(f"片段超长 ({segment_duration_sec:.3f}s > {MAX_SYNC_DURATION_SEC}s)，跳过。")

        # 将音频片段导出到内存
        with io.BytesIO() as audio_buffer:
            segment.export(audio_buffer, format="wav")
            audio_content = audio_buffer.getvalue()

    except ValueError:
        raise  # 重新抛出 ValueError
    except Exception as e:
        raise Exception(f"pydub 处理失败: {str(e)}") from e

    # --- 3. 调用 Google API ---
    try:
        # 语言代码转换
        api_language_code = ALPHA3_TO_BCP47_MAP[language]
        recognizer_path = f"projects/{YOUR_PROJECT_ID}/locations/{DEFAULT_LOCATION}/recognizers/_"

        client = get_speech_client()

        recognition_features = cloud_speech.RecognitionFeatures(
            enable_automatic_punctuation=True,  # 自动标点
        )

        config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            model=MODEL_NAME,  # chirp_3
            features=recognition_features,
            language_codes=[api_language_code],
        )

        request = cloud_speech.RecognizeRequest(
            recognizer=recognizer_path,
            config=config,
            content=audio_content,
        )

        # 发起同步请求
        response = client.recognize(request=request)

        full_transcript = " ".join(res.alternatives[0].transcript for res in response.results if res.alternatives).strip()

        # 返回结果
        return TranscriptionSegment(
            audio_path=abs_audio_path,
            start_time=actual_start_sec,
            end_time=actual_end_sec,
            text=full_transcript,
            model=MODEL_NAME,
            language=language  # 统一用 3 字母
        )

    except Exception as e:
        # API 错误
        logger.error(f"API 调用失败 (Lang: {api_language_code}): {str(e)}")
        raise Exception(f"API 调用失败 (Lang: {api_language_code}): {str(e)}") from e


# 批处理脚本入口
if __name__ == "__main__":
    BATCH_ROOT_DIR = Path("data/audio")
    logger.info(f"根目录: {BATCH_ROOT_DIR.resolve()}")
    logger.info("--- 开始批处理转录 ---")
    logger.info("=" * 40)

    # 遍历 data/audio/ 下所有语言文件夹
    language_dirs = [d for d in BATCH_ROOT_DIR.iterdir() if d.is_dir()]

    for language_dir in tqdm(language_dirs, desc="处理语言", unit="语言"):
        language_code = language_dir.name

        # 遍历 .wav，并从对应的 notation/{lang_code}/{json_file} 读取时间戳
        all_segments = []
        for wavpath in language_dir.glob("*.wav"):
            
            # 路径替换，从 data/audio/VNM/file.wav -> data/notation/VNM/file.json
            notation_path = Path(str(wavpath).replace("audio", "notation").replace(".wav", ".json"))
            
            if not notation_path.exists():
                logger.warning(f"找不到对应的 notation 文件: {notation_path}")
                continue
                
            with open(notation_path) as f:
                obj = json.load(f)
            
            # 按开始时间排序
            for segment in sorted(obj["segments"], key=lambda s: s["start"]):
                all_segments.append((wavpath, segment["start"], segment["end"], segment["status"]))

        # 内层 tqdm (leave=False 处理完一行就消失)
        for wavpath, start, end, status in tqdm(all_segments, desc=f"  {language_code}", unit="seg", leave=False):
            if status == "invalid":  # 跳过 "invalid" 标记的
                continue
            try:
                segment_data = transcribe_audio_segment(
                    audio_path=str(wavpath),
                    start=start,
                    end=end,
                    language=language_code
                )
                
                save_transcription(
                    audio_path=segment_data.audio_path,
                    text=segment_data.text,
                    language=segment_data.language,
                    model=segment_data.model,
                    start_time=segment_data.start_time,
                    end_time=segment_data.end_time,
                )

            except ValueError as ve:
                # 捕获校验错误 (如 > 60s)
                logger.warning(f"  [SKIPPED] {wavpath.name}:[{start}:{end}]s - {ve}")
            except Exception as e:
                # 捕获 API 或 pydub 错误
                logger.error(f"  [ERROR] {wavpath.name}:[{start}:{end}]s - {e}")

    logger.info("\n" + "=" * 40)
    logger.info("--- 批处理完成 ---")
    logger.info("结果已保存到: ./results/ 目录")


"""
/root/shared-nvme/yunchongxiao/Multilingual-ASR-Benchmark/data
|-- audio
|   |-- ARE
|   |   `-- ARE_UCpTncbkcIjS0v51sJz2jhsg__N1S84dzeYU_raw.wav
|   |-- DZA
|   |   |-- DZA_UC57OCoLoU6zAtBdJOmwg2vA_T7cGFKzKKaQ_raw.wav
|   |   |-- DZA_UC57OCoLoU6zAtBdJOmwg2vA_gBvqK28oBgo_raw.wav
|   |   `-- DZA_UC57OCoLoU6zAtBdJOmwg2vA_mDOnrxRs6Ow_raw.wav
|   |-- EGY
|   |   |-- EGY_UCMDqMSSFLDDot6JVTq4Fj2g_A9EcGjHIviU_raw.wav
|   |   `-- EGY_UCMDqMSSFLDDot6JVTq4Fj2g_NDp9aHbM5vw_raw.wav
|   |-- IDN
|   |   |-- IDN_UCEYUCOmWOEG_ESkL3xwBMNw_1r8Ntk_DekM_raw.wav
|   |   `-- IDN_UCEYUCOmWOEG_ESkL3xwBMNw_AZaOr8Igw8k_raw.wav
|   |-- IRQ
|   |   `-- IRQ_UCZ8zJO04KF6RD2VqZaWFkxg_lQvR95t-SIg_raw.wav
|   |-- JPN
|   |   |-- JPN_UCuTAXTexrhetbOe3zgskJBQ_4F-qUKtHj9M_raw.wav
|   |   |-- JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw.wav
|   |   |-- JPN_UCuTAXTexrhetbOe3zgskJBQ_gXb_Y243WF0_raw.wav
|   |   |-- JPN_UCuTAXTexrhetbOe3zgskJBQ_jO0kVdJ6qAM_raw.wav
|   |   `-- JPN_UCuTAXTexrhetbOe3zgskJBQ_m7V-KzysAZA_raw.wav
|   |-- KOR
|   |   |-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_4IhvQA7h6uI_raw.wav
|   |   |-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_bn7ccOETti8_raw.wav
|   |   |-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_qb3R_NxqJ-s_raw.wav
|   |   |-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_sdS3RvlpJyE_raw.wav
|   |   `-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_zP092Igcl2c_raw.wav
|   |-- MAR
|   |   |-- MAR_UC4uXxIk2qt0sSQuio1F0G1w_3MPdIL_ZXQs_raw.wav
|   |   |-- MAR_UC4uXxIk2qt0sSQuio1F0G1w_6YulIKifp7A_raw.wav
|   |   `-- MAR_UC4uXxIk2qt0sSQuio1F0G1w_wSkUdqE90Rk_raw.wav
|   |-- MYS
|   |   |-- MYS_UCfztuMBrL9F-KqLZk_SY9TA_PByniemQfp8_raw.wav
|   |   |-- MYS_UCfztuMBrL9F-KqLZk_SY9TA_zGSNMYwYXcs_raw.wav
|   |   `-- MYS_UCkmwGg4oN_Ik4QBx8SqCYJA_D6Ob68k7VVY_raw.wav
|   |-- PHL
|   |   |-- PHL_UC39p6707suIKTZiw0BTGapw_lWFFBK5Bb20_raw.wav
|   |   `-- PHL_UCj5RwDivLksanrNvkW0FB4w_p0fkd1sXunw_raw.wav
|   |-- SAU
|   |   `-- SAU_UCprydOtbOm6h5fsGiZFFwaw_YnfGyUP4TCA_raw.wav
|   |-- THA
|   |   `-- THA_UCMSLmwkXFhkxKFv2gS4NBww_Qif3_Fa2yLo_raw.wav
|   `-- VNM
|       `-- VNM_UCqL0-EknCK4m5pHrH79fOcw_BnQxIL_dTvc_raw.wav
`-- notation
    |-- ARE
    |   `-- ARE_UCpTncbkcIjS0v51sJz2jhsg__N1S84dzeYU_raw.json
    |-- DZA
    |   |-- DZA_UC57OCoLoU6zAtBdJOmwg2vA_T7cGFKzKKaQ_raw.json
    |   |-- DZA_UC57OCoLoU6zAtBdJOmwg2vA_gBvqK28oBgo_raw.json
    |   `-- DZA_UC57OCoLoU6zAtBdJOmwg2vA_mDOnrxRs6Ow_raw.json
    |-- EGY
    |   |-- EGY_UCMDqMSSFLDDot6JVTq4Fj2g_A9EcGjHIviU_raw.json
    |   `-- EGY_UCMDqMSSFLDDot6JVTq4Fj2g_NDp9aHbM5vw_raw.json
    |-- IDN
    |   |-- IDN_UCEYUCOmWOEG_ESkL3xwBMNw_1r8Ntk_DekM_raw.json
    |   `-- IDN_UCEYUCOmWOEG_ESkL3xwBMNw_AZaOr8Igw8k_raw.json
    |-- IRQ
    |   `-- IRQ_UCZ8zJO04KF6RD2VqZaWFkxg_lQvR95t-SIg_raw.json
    |-- JPN
    |   |-- JPN_UCuTAXTexrhetbOe3zgskJBQ_4F-qUKtHj9M_raw.json
    |   |-- JPN_UCuTAXTexrhetbOe3zgskJBQ_eIIeZquJWFQ_raw.json
    |   |-- JPN_UCuTAXTexrhetbOe3zgskJBQ_gXb_Y243WF0_raw.json
    |   |-- JPN_UCuTAXTexrhetbOe3zgskJBQ_jO0kVdJ6qAM_raw.json
    |   `-- JPN_UCuTAXTexrhetbOe3zgskJBQ_m7V-KzysAZA_raw.json
    |-- KOR
    |   |-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_4IhvQA7h6uI_raw.json
    |   |-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_bn7ccOETti8_raw.json
    |   |-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_qb3R_NxqJ-s_raw.json
    |   |-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_sdS3RvlpJyE_raw.json
    |   `-- KOR_UCkinYTS9IHqOEwR1Sze2JTw_zP092Igcl2c_raw.json
    |-- MAR
    |   |-- MAR_UC4uXxIk2qt0sSQuio1F0G1w_3MPdIL_ZXQs_raw.json
    |   |-- MAR_UC4uXxIk2qt0sSQuio1F0G1w_6YulIKifp7A_raw.json
    |   `-- MAR_UC4uXxIk2qt0sSQuio1F0G1w_wSkUdqE90Rk_raw.json
    |-- MYS
    |   |-- MYS_UCfztuMBrL9F-KqLZk_SY9TA_PByniemQfp8_raw.json
    |   |-- MYS_UCfztuMBrL9F-KqLZk_SY9TA_zGSNMYwYXcs_raw.json
    |   `-- MYS_UCkmwGg4oN_Ik4QBx8SqCYJA_D6Ob68k7VVY_raw.json
    |-- PHL
    |   |-- PHL_UC39p6707suIKTZiw0BTGapw_lWFFBK5Bb20_raw.json
    |   `-- PHL_UCj5RwDivLksanrNvkW0FB4w_p0fkd1sXunw_raw.json
    |-- SAU
    |   `-- SAU_UCprydOtbOm6h5fsGiZFFwaw_YnfGyUP4TCA_raw.json
    |-- THA
    |   `-- THA_UCMSLmwkXFhkxKFv2gS4NBww_Qif3_Fa2yLo_raw.json
    `-- VNM
        `-- VNM_UCqL0-EknCK4m5pHrH79fOcw_BnQxIL_dTvc_raw.json
29 directories, 60 files
"""