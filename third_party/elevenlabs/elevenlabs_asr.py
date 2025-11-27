import os
import sys
import argparse
import json
from collections import defaultdict
from io import BytesIO
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment

from utils import save_transcription

# 支持的 model_id 列表
SUPPORTED_MODEL_IDS = {
    "scribe_v1",
    "scribe_v1_experimental",
    "scribe_v2"
}

LANGUAGE_MAPPING = {
    "ARE": "ara",  # 阿拉伯语-阿联酋
    "IRQ": "ara",  # 阿拉伯语-伊拉克
    "DZA": "ara",  # 阿拉伯语-阿尔及利亚
    "EGY": "ara",  # 阿拉伯语-埃及
    "SAU": "ara",  # 阿拉伯语-沙特
    "MAR": "ara",  # 阿拉伯语-摩洛哥
    "IDN": "ind",  # 印尼语
    "JPN": "jpn",  # 日语
    "KOR": "kor",  # 韩语
    "THA": "tha",  # 泰语
    "VNM": "vie",  # 越南语
    "PHL": "fil",  # 菲律宾语
    "MYS": "msa",  # 马来语
    "USA": "eng",  # 英语
    "CHN": "zho",  # 中文(普通话)
}


def load_transcribed_segments(language: str, model: str) -> set:
    """
    加载已转录的segments，返回一个集合，用于快速检查。

    Args:
        language (str): 语种代码
        model (str): 模型名称

    Returns:
        set: 包含已转录segment的元组集合，每个元组格式为 (path, start_time, end_time)
    """
    results_dir = os.path.join(os.getcwd(), "results")
    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    transcribed_segments = set()

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for entry in data:
                            path = entry.get("path", "")
                            start_time = entry.get("start_time", 0.0)
                            end_time = entry.get("end_time", 0.0)
                            # 路径格式为 {language_code}/{wav_filename}，直接使用
                            transcribed_segments.add((
                                path,
                                float(start_time),
                                float(end_time)
                            ))
        except Exception as e:
            print(f"[WARN] 无法加载已转录结果文件 {output_path}: {e}")

    return transcribed_segments


def is_segment_transcribed(
    audio_path: str,
    start_time: float,
    end_time: float,
    language_code: str,
    transcribed_segments: set
) -> bool:
    """
    检查segment是否已经转录过。

    Args:
        audio_path (str): 音频文件路径
        start_time (float): 开始时间
        end_time (float): 结束时间
        language_code (str): 语种代码
        transcribed_segments (set): 已转录segments的集合

    Returns:
        bool: 如果已转录返回True，否则返回False
    """
    # 构造格式化的路径：{language_code}/{wav_filename}
    wav_filename = os.path.basename(audio_path)
    formatted_path = f"{language_code}/{wav_filename}"
    segment_key = (formatted_path, float(start_time), float(end_time))
    return segment_key in transcribed_segments


def transcribe_audio(
    audio_path: str,
    start_time: float,
    end_time: float,
    language: str,
    model_id: str = "scribe_v1"
) -> str:
    """
    转录音频文件的指定片段。

    Args:
        audio_path (str): 音频文件的绝对路径
        start_time (float): 起始时间（秒）
        end_time (float): 结束时间（秒）
        language (str): 国家代码（如 "ARE", "IRQ"），将自动映射到 ElevenLabs API 支持的语言代码
        model_id (str): ElevenLabs 模型 ID，默认为 "scribe_v1"

    Returns:
        str: 转录文本
    """
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY 环境变量未设置")

    # 验证 model_id
    if model_id not in SUPPORTED_MODEL_IDS:
        raise ValueError(f"不支持的 model_id: {model_id}。支持的 model_id: {', '.join(SUPPORTED_MODEL_IDS)}")

    api_language_code = LANGUAGE_MAPPING.get(language.upper(), None)
    if api_language_code is None:
        print(f"警告：未找到语种 {language} 的映射，将使用自动检测")
        api_language_code = None

    # 初始化客户端
    client = ElevenLabs(api_key=api_key)

    # 加载音频文件
    audio = AudioSegment.from_wav(audio_path)

    # 截取音频片段（pydub 使用毫秒）
    start_ms = int(start_time * 1000)
    end_ms = int(end_time * 1000)
    audio_segment = audio[start_ms:end_ms]

    # 将音频片段导出为字节流
    buffer = BytesIO()
    audio_segment.export(buffer, format="wav")
    buffer.seek(0)

    # 调用 ElevenLabs API 进行转录
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
        print(f"转录失败: {e}")
        raise


def main():
    """
    主函数：根据标准格式的JSON文件转录音频文件。
    """
    parser = argparse.ArgumentParser(description="批量转录音频文件并保存结果")
    parser.add_argument(
        "--languages",
        type=str,
        nargs="+",
        required=True,
        help="要处理的语种代码列表（例如：--languages JPN ARE IDN）"
    )
    parser.add_argument(
        "--text_dir",
        type=str,
        default="data/text/testbatch/ref",
        help="文本文件目录（默认：data/text/testbatch/ref）"
    )
    parser.add_argument(
        "--audio_dir",
        type=str,
        default="data/audio/testbatch",
        help="音频文件目录（默认：data/audio/testbatch）"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="results",
        help="输出目录路径（保存转录结果）"
    )
    parser.add_argument(
        "--api_key",
        type=str,
        default=None,
        help="ElevenLabs API key（如果不提供，将从环境变量 ELEVENLABS_API_KEY 读取）"
    )
    parser.add_argument(
        "--model_id",
        type=str,
        default="scribe_v1",
        choices=list(SUPPORTED_MODEL_IDS),
        help="ElevenLabs 模型 ID（可选值：scribe_v1, scribe_v1_experimental, scribe_v2）"
    )

    args = parser.parse_args()
    
    # 验证 model_id
    model_id = args.model_id
    if model_id not in SUPPORTED_MODEL_IDS:
        raise ValueError(f"不支持的 model_id: {model_id}。支持的 model_id: {', '.join(SUPPORTED_MODEL_IDS)}")
    
    # 验证并规范化语种代码
    languages = [lang.upper() for lang in args.languages]
    
    # 设置路径
    text_dir = os.path.abspath(args.text_dir)
    audio_dir = os.path.abspath(args.audio_dir)
    
    print(f"使用模型: {model_id}")
    print(f"文本目录: {text_dir}")
    print(f"音频目录: {audio_dir}")
    print(f"处理语种: {', '.join(languages)}")

    # 设置 API key
    if args.api_key:
        os.environ["ELEVENLABS_API_KEY"] = args.api_key
    elif not os.getenv("ELEVENLABS_API_KEY"):
        raise ValueError("请提供 API key（通过 --api_key 参数或设置 ELEVENLABS_API_KEY 环境变量）")

    # 验证目录是否存在
    if not os.path.exists(text_dir):
        raise ValueError(f"文本目录不存在: {text_dir}")
    if not os.path.exists(audio_dir):
        raise ValueError(f"音频目录不存在: {audio_dir}")

    # 遍历指定的语种
    total_languages = len(languages)
    for lang_idx, language in enumerate(languages, 1):
        print(f"\n处理语种 [{lang_idx}/{total_languages}]: {language}")

        # 构建文本文件路径：data/text/testbatch/ref/{language}.json
        text_file = os.path.join(text_dir, f"{language}.json")
        
        if not os.path.exists(text_file):
            print(f"  警告：文本文件不存在，跳过: {text_file}")
            continue

        # 加载该语种已转录的segments
        model_name = f"elevenlabs_{model_id}"
        transcribed_segments = load_transcribed_segments(language, model_name)
        print(f"  已加载 {len(transcribed_segments)} 个已转录的segments")

        # 加载文本JSON文件
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                segments_data = json.load(f)
        except Exception as e:
            print(f"  错误：无法加载文本文件 {text_file}: {e}")
            continue

        if not isinstance(segments_data, list):
            print(f"  错误：文本文件格式错误，应为列表格式: {text_file}")
            continue

        print(f"  找到 {len(segments_data)} 个片段")

        # 按 audio_name 分组处理
        segments_by_audio = defaultdict(list)
        for segment in segments_data:
            audio_name = segment.get("audio_name", "")
            if audio_name:
                segments_by_audio[audio_name].append(segment)

        print(f"  涉及 {len(segments_by_audio)} 个音频文件")

        # 处理每个音频文件
        total_audios = len(segments_by_audio)
        for audio_idx, (audio_name, segments) in enumerate(segments_by_audio.items(), 1):
            print(f"  [{audio_idx}/{total_audios}] 处理音频: {audio_name}")

            # 构建音频文件路径：data/audio/testbatch/{language}/{audio_name}.wav
            # 尝试多种可能的扩展名
            audio_extensions = ['.wav', '.mp3', '.flac', '.m4a']
            audio_path = None
            
            lang_audio_dir = os.path.join(audio_dir, language)
            for ext in audio_extensions:
                potential_path = os.path.join(lang_audio_dir, f"{audio_name}{ext}")
                if os.path.exists(potential_path):
                    audio_path = potential_path
                    break
            
            if audio_path is None:
                print(f"    警告：音频文件不存在，跳过。尝试路径: {lang_audio_dir}/{audio_name}[.wav|.mp3|.flac|.m4a]")
                continue

            print(f"    找到音频文件: {audio_path}")
            print(f"    该音频有 {len(segments)} 个片段")

            # 处理该音频的每个片段
            for seg_idx, segment in enumerate(segments, 1):
                start_time = segment.get("start", 0.0)
                end_time = segment.get("end", 0.0)
                segment_id = segment.get("id", seg_idx)

                print(f"    片段 {seg_idx}/{len(segments)} (id={segment_id}): {start_time:.2f}s - {end_time:.2f}s")

                # 构造格式化的路径：{language}/{audio_filename}
                audio_filename = os.path.basename(audio_path)
                formatted_path = f"{language}/{audio_filename}"

                # 检查该segment是否已经转录过
                if is_segment_transcribed(audio_path, start_time, end_time, language, transcribed_segments):
                    print(f"      该segment已转录，跳过")
                    continue

                # 调用 transcribe_audio 进行转录
                try:
                    transcription_text = transcribe_audio(
                        audio_path=audio_path,
                        start_time=start_time,
                        end_time=end_time,
                        language=language,
                        model_id=model_id
                    )
                    print(f"      转录成功: {transcription_text[:50]}...")
                except Exception as e:
                    print(f"      转录失败: {e}")
                    transcription_text = ""

                # 调用 save_transcription 保存结果
                try:
                    save_transcription(
                        audio_path=formatted_path,
                        text=transcription_text,
                        language=language,
                        model=model_name,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    # 修正保存的路径格式，确保使用 Linux 风格的路径分隔符
                    results_dir = os.path.join(os.getcwd(), args.output_dir)
                    os.makedirs(results_dir, exist_ok=True)
                    filename = f"{language}_{model_name}.json"
                    output_path = os.path.join(results_dir, filename)
                    
                    if os.path.exists(output_path):
                        with open(output_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        # 修正最后一个条目的路径格式
                        if data and len(data) > 0:
                            last_entry = data[-1]
                            # 将路径标准化为 Linux 风格：{language}/{audio_filename}
                            last_entry["path"] = formatted_path
                            # 写回文件
                            with open(output_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=4)
                    
                    # 将新转录的segment添加到集合中，避免重复检查
                    transcribed_segments.add((formatted_path, float(start_time), float(end_time)))
                except Exception as e:
                    print(f"      保存结果失败: {e}")

    print("\n所有文件处理完毕！")


if __name__ == "__main__":
    main()
