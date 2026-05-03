import os
import sys
import argparse
import json
from collections import defaultdict
from io import BytesIO
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment

from utils import save_transcription

# Supported model_id list
SUPPORTED_MODEL_IDS = {
    "scribe_v1",
    "scribe_v1_experimental",
    "scribe_v2"
}

LANGUAGE_MAPPING = {
    "AR": "ara",  # Arabic
    "ARE": "ara",  # Arabic-阿联酋
    "IRQ": "ara",  # Arabic-Iraq
    "DZA": "ara",  # Arabic-阿尔及利亚
    "EGY": "ara",  # Arabic-埃及
    "SAU": "ara",  # Arabic-Saudi
    "MAR": "ara",  # Arabic-Morocco
    "IDN": "ind",  # Indonesia语
    "JPN": "jpn",  # 日语
    "KOR": "kor",  # 韩语
    "THA": "tha",  # 泰语
    "VNM": "vie",  # Vietnam语
    "PHL": "fil",  # Philippines语
    "MYS": "msa",  # 马来语
    "USA": "eng",  # 英语
    "CHN": "zho",  # 中文(普通话)
    "CHN-EN": "eng",  # Chinese English
    "IDN-EN": "eng",  # 印度口音英语
    "JPN-EN": "eng",  # Japan口音英语
    "PHL-EN": "eng",  # Philippines口音英语
    "SCT-EN": "eng",  # 苏格兰口音英语
    "SGP-EN": "eng",  # 新加坡口音英语
    "XIANG": "zho",  # 湘方言
    "JIN": "zho",  # 晋方言
}


def _segment_key(entry: dict):
    """从条目中提取 (path或audio_name, start, end) 作为唯一键，used for加载与去重。"""
    path_or_name = entry.get("path") or entry.get("audio_name") or ""
    start = entry.get("start_time") if "start_time" in entry else entry.get("start", 0.0)
    end = entry.get("end_time") if "end_time" in entry else entry.get("end", 0.0)
    return (path_or_name, float(start), float(end))


def load_transcribed_segments(language: str, model: str):
    """
    加载已转录的segments。
    以 (path或audio_name, start, end) 为键

    返回:
        - transcribed_segments (set): used for快速检查是否存在某个 (path_or_audio_name, start, end)
        - segment_texts (dict): 以该元组为 key，文本内容为 value

    Args:
        language (str): language代码
        model (str): 模型名称

    Returns:
        (set, dict): 
            set: 已转录 segment 的键集合
            dict: key 同上，value 为该片段的文本内容（字符串）
    """
    results_dir = os.path.join(os.getcwd(), "results")
    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    transcribed_segments = set()
    segment_texts = {}

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for entry in data:
                            key = _segment_key(entry)
                            transcribed_segments.add(key)
                            segment_texts[key] = (entry.get("text") or "").strip()
        except Exception as e:
            print(f"[WARN] 无法加载已转录结果文件 {output_path}: {e}")

    return transcribed_segments, segment_texts


def fix_and_clean_results(language: str, model: str, text_file: str, output_dir: str) -> None:
    """
    修复和清理结果文件：
    1. 读取 ref 文件，构建 (audio_name, start, end) 的键集合
    2. 在 result 文件中逐个检查：若 (path/audio_name, start, end) 与 ref 中某键匹配（允许时间误差 0.001 秒）则保留，否则删除。
    不进行 id 的补充或纠正。

    Args:
        language (str): language代码
        model (str): 模型名称
        text_file (str): 参考文件路径（ref JSON）
        output_dir (str): 输出目录
    """
    results_dir = os.path.join(os.getcwd(), output_dir)
    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    if not os.path.exists(output_path):
        return

    # Read参考文件，构建 (audio_name, start, end) -> id 的映射
    if not os.path.exists(text_file):
        print(f"  [WARN] 参考文件不存在，无法修复结果文件: {text_file}")
        return

    try:
        with open(text_file, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
            if not isinstance(ref_data, list):
                print(f"  [WARN] 参考文件格式错误，应为列表格式: {text_file}")
                return
    except Exception as e:
        print(f"  [WARN] 无法读取参考文件 {text_file}: {e}")
        return

    # 构建参考文件的键集合：(audio_name, start, end)
    ref_keys = set()
    for segment in ref_data:
        audio_name = segment.get("audio_name", "")
        start = segment.get("start", 0.0)
        end = segment.get("end", 0.0)
        ref_keys.add((audio_name, float(start), float(end)))

    print(f"  参考文件包含 {len(ref_keys)} 个片段")

    # Read结果文件
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return
            result_data = json.loads(content)
            if not isinstance(result_data, list):
                return
    except Exception as e:
        print(f"  [WARN] 无法读取结果文件 {output_path}: {e}")
        return

    original_count = len(result_data)
    print(f"  结果文件包含 {original_count} 个条目")

    # 按 (path/audio_name, start, end) 与 ref 键匹配检查，通过则保留
    fixed_entries = []
    deleted_count = 0

    for entry in result_data:
        path_or_name = entry.get("path") or entry.get("audio_name") or ""
        start_time = entry.get("start_time") if "start_time" in entry else entry.get("start", 0.0)
        end_time = entry.get("end_time") if "end_time" in entry else entry.get("end", 0.0)
        # path 格式可能为 {language}/{audio_filename}，需得到 audio_name 与 ref 比较
        if path_or_name and "/" in path_or_name:
            audio_name = os.path.basename(path_or_name)
            
        else:
            audio_name = path_or_name
        audio_name = os.path.splitext(audio_name)[0]

        # 是否与 ref 中某键匹配（允许时间误差 0.001 秒）
        matched = False
        for (ref_audio_name, ref_start, ref_end) in ref_keys:
            if (ref_audio_name == audio_name and
                abs(ref_start - float(start_time)) < 0.001 and
                abs(ref_end - float(end_time)) < 0.001):
                matched = True
                break

        if matched:
            fixed_entries.append(entry)
        else:
            deleted_count += 1
    if deleted_count > 0:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(fixed_entries, f, ensure_ascii=False, indent=4)
            print(f"  结果文件清理完成: 原有 {original_count} 条, 删除不匹配 {deleted_count} 条, 保留 {len(fixed_entries)} 条")
        except Exception as e:
            print(f"  [WARN] 无法写回结果文件 {output_path}: {e}")


def is_quota_exceeded_error(error: Exception) -> bool:
    """
    检查异常是否为余额不足错误。

    Args:
        error (Exception): 异常对象

    Returns:
        bool: 如果是余额不足错误返回True，否则返回False
    """
    error_str = str(error).lower()
    error_repr = repr(error).lower()
    
    # Check错误信息中是否包含 quota_exceeded 相关关键词
    quota_keywords = ["quota_exceeded", "quota exceeded", "credits remaining", "exceeds your quota"]
    for keyword in quota_keywords:
        if keyword in error_str or keyword in error_repr:
            return True
    
    # Check异常对象的属性（某些 API 库可能将错误信息存储在属性中）
    if hasattr(error, 'body'):
        try:
            if isinstance(error.body, dict):
                body_str = json.dumps(error.body).lower()
                if "quota_exceeded" in body_str:
                    return True
        except:
            pass
    
    if hasattr(error, 'detail'):
        try:
            if isinstance(error.detail, dict):
                detail_str = json.dumps(error.detail).lower()
                if "quota_exceeded" in detail_str:
                    return True
        except:
            pass
    
    return False


def is_segment_transcribed(
    audio_path: str,
    start_time: float,
    end_time: float,
    language_code: str,
    transcribed_segments: set,
    force: bool = False,
    segment_texts: dict = None,
) -> bool:
    """
    检查segment是否已经转录过。
    匹配时尝试多种 path 格式：{language_code}/{wav_filename}、wav_filename、wav_filename 无扩展名，
    以兼容已有 JSON 中可能存在的不同 path/audio_name 写法。

    Args:
        audio_path (str): 音频文件路径
        start_time (float): 开始时间
        end_time (float): 结束时间
        language_code (str): language代码
        transcribed_segments (set): 已转录segments的集合
        force (bool): 是否强制重新转录
        segment_texts (dict): 已转录segments的文本内容

    Returns:
        bool: 如果已转录返回True，否则返回False
    """
    wav_filename = os.path.basename(audio_path)
    wav_filename_without_ext = os.path.splitext(wav_filename)[0]
    start_f = float(start_time)
    end_f = float(end_time)

    # 尝试多种 path 格式与 transcribed_segments 中的 key 匹配
    path_variants = [
        f"{language_code}/{wav_filename}",  # 标准格式
        wav_filename,
        wav_filename_without_ext,
    ]
    matched_key = None
    for path_variant in path_variants:
        candidate_key = (path_variant, start_f, end_f)
        if candidate_key in transcribed_segments:
            matched_key = candidate_key
            break

    if matched_key is None:
        return False

    # 未开启 force 时，只要存在记录就认为已转录，跳过
    if not force:
        return True

    # force 模式下，没有文本缓存则无法判断是否为空，视为需重跑；有缓存则根据文本是否为空决定
    if segment_texts is None:
        return False
    text = segment_texts.get(matched_key, "")
    if isinstance(text, str) and text.strip() == "":
        return False

    return True


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
        print(f"警告：未找到language {language} 的映射，将使用自动检测")
        api_language_code = None

    # Initialize客户端
    client = ElevenLabs(api_key=api_key)

    # Load音频文件
    audio = AudioSegment.from_file(audio_path)

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


def deduplicate_and_sort_results(language: str, model: str, output_dir: str) -> None:
    """
    对指定语言和模型的结果文件进行去重与排序：
      1. 以 (path或audio_name, start, end) 为唯一键，保留“最后出现”的一条记录；
      2. 按 path/audio_name、start、end 排序后回写。
    """
    results_dir = os.path.join(os.getcwd(), output_dir)
    filename = f"{language}_{model}.json"
    output_path = os.path.join(results_dir, filename)

    if not os.path.exists(output_path):
        return

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return
            data = json.loads(content)
            if not isinstance(data, list):
                print(f"[WARN] 结果文件格式异常（非列表），跳过去重: {output_path}")
                return
    except Exception as e:
        print(f"[WARN] 无法读取结果文件以进行去重: {output_path}, 原因: {e}")
        return

    original_len = len(data)

    # 以 (path或audio_name, start, end) 为 key，后出现的覆盖前面的
    unique_map = {}
    for entry in data:
        key = _segment_key(entry)
        unique_map[key] = entry

    deduped = list(unique_map.values())

    # 按 path/audio_name、start、end 排序
    deduped.sort(key=lambda e: _segment_key(e))

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(deduped, f, ensure_ascii=False, indent=4)
        print(f"[INFO] 结果去重与排序完成: {output_path} (原有 {original_len} 条, 去重后 {len(deduped)} 条)")
    except Exception as e:
        print(f"[WARN] 写回去重结果失败: {output_path}, 原因: {e}")


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
        help="要处理的language代码列表（例如：--languages JPN ARE IDN）"
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="如果为 true，则对于已存在但文本为空的片段重新进行识别"
    )

    args = parser.parse_args()
    
    # 验证 model_id
    model_id = args.model_id
    if model_id not in SUPPORTED_MODEL_IDS:
        raise ValueError(f"不支持的 model_id: {model_id}。支持的 model_id: {', '.join(SUPPORTED_MODEL_IDS)}")
    
    # 验证并normalizationlanguage代码
    languages = [lang.upper() for lang in args.languages]
    
    # 设置路径
    text_dir = os.path.abspath(args.text_dir)
    audio_dir = os.path.abspath(args.audio_dir)
    
    print(f"使用模型: {model_id}")
    print(f"文本目录: {text_dir}")
    print(f"音频目录: {audio_dir}")
    print(f"处理language: {', '.join(languages)}")

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

    # Iterate指定的language
    total_languages = len(languages)
    for lang_idx, language in enumerate(languages, 1):
        print(f"\n处理language [{lang_idx}/{total_languages}]: {language}")

        # 构建文本文件路径：data/text/testbatch/ref/{language}.json
        text_file = os.path.join(text_dir, f"{language}.json")
        
        if not os.path.exists(text_file):
            print(f"  警告：文本文件不存在，跳过: {text_file}")
            continue

        # Load该language已转录的segments
        model_name = f"elevenlabs_{model_id}"
        transcribed_segments, segment_texts = load_transcribed_segments(language, model_name)
        print(f"  已加载 {len(transcribed_segments)} 个已转录的segments")

        # Load文本JSON文件
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

        # 修复和clean up结果文件（在正式转录之前）
        fix_and_clean_results(language, model_name, text_file, args.output_dir)
        
        # 修复后重新加载已转录的segments（因为可能更新了id或删除了不匹配的条目）
        transcribed_segments, segment_texts = load_transcribed_segments(language, model_name)
        print(f"  修复后重新加载 {len(transcribed_segments)} 个已转录的segments")
        # 按 audio_name 分组process
        segments_by_audio = defaultdict(list)
        for segment in segments_data:
            audio_name = segment.get("audio_name", "")
            if audio_name:
                segments_by_audio[audio_name].append(segment)

        print(f"  涉及 {len(segments_by_audio)} 个音频文件")

        # Process每个音频文件
        total_audios = len(segments_by_audio)
        for audio_idx, (audio_name, segments) in enumerate(segments_by_audio.items(), 1):
            print(f"  [{audio_idx}/{total_audios}] 处理音频: {audio_name}")

            # 构建音频文件路径：data/audio/testbatch/{language}/{audio_name}.wav
            # 尝试多种可能的扩展名
            audio_extensions = ['.wav', '.mp3', '.flac', '.m4a']
            audio_path = None
            
            lang_audio_dir = os.path.join(audio_dir, language)
            
            _, ext = os.path.splitext(audio_name)
            if ext:
                potential_path = os.path.join(lang_audio_dir, audio_name)
                if os.path.exists(potential_path):
                    audio_path = potential_path
            else:
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

            # Process该音频的每个片段
            for seg_idx, segment in enumerate(segments, 1):
                start_time = segment.get("start", 0.0)
                end_time = segment.get("end", 0.0)
                segment_id = segment.get("id", seg_idx)

                print(f"    片段 {seg_idx}/{len(segments)} (id={segment_id}): {start_time:.2f}s - {end_time:.2f}s")

                # 构造格式化的路径：{language}/{audio_filename}
                audio_filename = os.path.basename(audio_path)
                formatted_path = f"{language}/{audio_filename}"
                
                # Check该segment是否已经转录过
                if is_segment_transcribed(
                    audio_path,
                    start_time,
                    end_time,
                    language,
                    transcribed_segments,
                    force=args.force,
                    segment_texts=segment_texts,
                ):
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

                    # 即使返回为空文本也进行保存
                    preview = ""
                    if isinstance(transcription_text, str):
                        preview = transcription_text.strip()[:50]
                    print(f"      转录成功: {preview}...")
                except Exception as e:
                    # Check是否为余额不足错误
                    if is_quota_exceeded_error(e):
                        print(f"      转录失败（余额不足）: {e}")
                        print(f"      跳过该片段（不保存）")
                        continue
                    else:
                        # 其他错误情况，保存结果为空字符串
                        print(f"      转录失败（其他错误）: {e}")
                        print(f"      保存结果为空字符串")
                        transcription_text = ""


                # 调用 save_transcription 保存结果
                try:
                    save_transcription(
                        audio_path=formatted_path,
                        text=transcription_text,
                        language=language,
                        model=model_name,
                        start_time=start_time,
                        end_time=end_time,
                        index=segment_id
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

        # 该language所有音频与片段process完毕后，对结果文件进行去重与排序
        deduplicate_and_sort_results(language, model_name, args.output_dir)

    print("\n所有文件处理完毕！")


if __name__ == "__main__":
    main()
