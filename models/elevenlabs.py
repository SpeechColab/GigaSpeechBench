import os
import sys
import argparse
import json
from io import BytesIO
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment

# 添加父目录到路径，以便导入 utils 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
                            # 路径格式为 {lang_code}/{wav_filename}，直接使用
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
    # 构造格式化的路径：{lang_code}/{wav_filename}
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
    主函数：处理 testbatch_processed 目录下的音频和文本文件。
    """
    parser = argparse.ArgumentParser(description="批量转录音频文件并保存结果")
    parser.add_argument(
        "--input_dir",
        type=str,
        default="testbatch_processed",
        help="输入目录路径（包含 wav 和 text 子文件夹）"
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
    parser.add_argument(
        "--languages",
        type=str,
        nargs="+",
        required=True,
        help="要处理的语种代码列表（例如：--languages JPN ARE IDN）"
    )

    args = parser.parse_args()
    
    # 验证 model_id
    model_id = args.model_id
    if model_id not in SUPPORTED_MODEL_IDS:
        raise ValueError(f"不支持的 model_id: {model_id}。支持的 model_id: {', '.join(SUPPORTED_MODEL_IDS)}")
    
    # 验证并规范化语种代码
    languages = [lang.upper() for lang in args.languages]
    
    print(f"使用模型: {model_id}")
    print(f"处理语种: {', '.join(languages)}")

    # 设置 API key
    if args.api_key:
        os.environ["ELEVENLABS_API_KEY"] = args.api_key
    elif not os.getenv("ELEVENLABS_API_KEY"):
        raise ValueError("请提供 API key（通过 --api_key 参数或设置 ELEVENLABS_API_KEY 环境变量）")

    input_dir = os.path.abspath(args.input_dir)
    wav_dir = os.path.join(input_dir, "wav")
    text_dir = os.path.join(input_dir, "text")

    if not os.path.exists(wav_dir):
        raise ValueError(f"音频目录不存在: {wav_dir}")
    if not os.path.exists(text_dir):
        raise ValueError(f"文本目录不存在: {text_dir}")

    # 验证指定的语种文件夹是否存在
    available_folders = [
        f for f in os.listdir(wav_dir)
        if os.path.isdir(os.path.join(wav_dir, f))
    ]
    
    # 检查指定的语种是否都存在
    missing_languages = [lang for lang in languages if lang not in available_folders]
    if missing_languages:
        raise ValueError(f"指定的语种文件夹不存在: {', '.join(missing_languages)}。可用的语种: {', '.join(sorted(available_folders))}")

    # 只处理指定的语种文件夹
    language_folders = [lang for lang in languages if lang in available_folders]
    
    print(f"将处理 {len(language_folders)} 个语种文件夹: {language_folders}")

    # 遍历指定的语种文件夹
    for language_code in language_folders:
        print(f"\n处理语种: {language_code}")

        lang_wav_dir = os.path.join(wav_dir, language_code)
        lang_text_dir = os.path.join(text_dir, language_code)

        if not os.path.exists(lang_text_dir):
            print(f"警告：文本目录不存在，跳过: {lang_text_dir}")
            continue

        # 加载该语种已转录的segments
        model_name = "elevenlabs"
        transcribed_segments = load_transcribed_segments(language_code, model_name)
        print(f"  已加载 {len(transcribed_segments)} 个已转录的segments")

        # 获取该语种下的所有 JSON 文件
        json_files = [
            f for f in os.listdir(lang_text_dir)
            if f.endswith(".json")
        ]

        print(f"  找到 {len(json_files)} 个标注文件")

        # 处理每个标注文件
        for json_file in json_files:
            json_path = os.path.join(lang_text_dir, json_file)
            audio_name = os.path.splitext(json_file)[0]

            # 查找对应的音频文件
            wav_file = f"{audio_name}.wav"
            wav_path = os.path.join(lang_wav_dir, wav_file)

            if not os.path.exists(wav_path):
                print(f"  警告：音频文件不存在，跳过: {wav_path}")
                continue

            print(f"  处理: {audio_name}")

            # 加载标注 JSON 文件
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    annotation_data = json.load(f)
            except Exception as e:
                print(f"  错误：无法加载标注文件 {json_path}: {e}")
                continue

            # 获取 segments 列表
            segments = annotation_data.get("segments", [])
            if not segments:
                print(f"  警告：{audio_name} 没有 segments，跳过")
                continue

            print(f"    找到 {len(segments)} 个片段")

            # 处理每个 segment
            for idx, segment in enumerate(segments, start=1):
                start_time = segment.get("start", 0.0)
                end_time = segment.get("end", 0.0)
                status = segment.get("status", "valid")

                print(f"    片段 {idx}/{len(segments)}: {start_time:.2f}s - {end_time:.2f}s, status={status}")

                # 构造格式化的路径：{lang_code}/{wav_filename}，使用 Linux 风格的路径分隔符
                wav_filename = os.path.basename(wav_path)
                formatted_path = f"{language_code}/{wav_filename}"

                # 检查该segment是否已经转录过
                if is_segment_transcribed(wav_path, start_time, end_time, language_code, transcribed_segments):
                    print(f"      该segment已转录，跳过")
                    continue

                # 如果 status 为 invalid，转录文本为空
                if status == "invalid":
                    transcription_text = ""
                    print(f"      状态为 invalid，跳过转录")
                else:
                    # 调用 transcribe_audio 进行转录
                    try:
                        transcription_text = transcribe_audio(
                            audio_path=wav_path,
                            start_time=start_time,
                            end_time=end_time,
                            language=language_code,
                            model_id=model_id
                        )
                        print(f"      转录成功: {transcription_text[:50]}...")
                    except Exception as e:
                        print(f"      转录失败: {e}")
                        transcription_text = ""

                # 调用 save_transcription 保存结果
                # 由于 utils.py 中的 os.path.abspath() 可能会将路径转换为 Windows 风格，
                # 我们需要传入一个已经是绝对路径且使用 Linux 风格分隔符的路径
                # 或者传入相对路径，然后在保存后手动修正
                # 这里我们传入格式化的相对路径，然后在保存后通过修改结果文件来确保路径格式正确
                try:
                    # 先保存（可能会被转换为绝对路径）
                    save_transcription(
                        audio_path=formatted_path,
                        text=transcription_text,
                        language=language_code,
                        model="elevenlabs",
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    # 修正保存的路径格式，确保使用 Linux 风格的路径分隔符
                    results_dir = os.path.join(os.getcwd(), "results")
                    filename = f"{language_code}_elevenlabs.json"
                    output_path = os.path.join(results_dir, filename)
                    
                    if os.path.exists(output_path):
                        with open(output_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        # 修正最后一个条目的路径格式
                        if data and len(data) > 0:
                            last_entry = data[-1]
                            # 将路径标准化为 Linux 风格：{lang_code}/{wav_filename}
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
