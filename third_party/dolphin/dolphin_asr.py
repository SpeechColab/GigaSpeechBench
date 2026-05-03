import os
import sys
import argparse
import json
from collections import defaultdict
from typing import Optional, Tuple

import dolphin
from dolphin.transcribe import load_model
from dolphin.constants import SAMPLE_RATE
import torchaudio
import numpy as np

from utils import save_transcription

# Language映射：将国家代码映射到 (lang_sym, region_sym) 二元组
LANGUAGE_MAPPING = {
    "AR": ("ar", ""),      # Arabic
    "ARE": ("ar", "AE"),      # Arabic-阿联酋
    "IRQ": ("ar", ""),     # Arabic-Iraq
    "DZA": ("ar", ""),      # Arabic-阿尔及利亚
    "EGY": ("ar", "EG"),      # Arabic-埃及
    "SAU": ("ar", "SA"),      # Arabic-Saudi
    "MAR": ("ar", "MA"),      # Arabic-Morocco
    "IDN": ("id", "ID"),      # Indonesia语
    "JPN": ("ja", "JP"),      # 日语
    "KOR": ("ko", "KR"),      # 韩语
    "THA": ("th", "TH"),      # 泰语
    "VNM": ("vi", "VN"),      # Vietnam语
    "PHL": ("fil", "PH"),     # Philippines语
    "MYS": ("ms", "MY"),      # 马来语
    "CHN": ("zh", "CN"),      # 中文(普通话)
    "XIANG": ("zh", "HUNAN"),      # 湘方言
    "JIN": ("zh", "SHANXI"),      # 晋方言
}


def _segment_key(entry: dict):
    """从条目中提取 (path或audio_name, start, end) 作为唯一键，used for加载与去重。"""
    path_or_name = entry.get("path") or entry.get("audio_name") or ""
    start = entry.get("start_time") if "start_time" in entry else entry.get("start", 0.0)
    end = entry.get("end_time") if "end_time" in entry else entry.get("end", 0.0)
    return (path_or_name, float(start), float(end))


def load_transcribed_segments(language: str, model: str, output_dir: str = "results") -> Tuple[set, dict]:
    """
    加载已转录的segments。
    以 (path或audio_name, start, end) 为键

    返回:
        - transcribed_segments (set): used for快速检查是否存在某个 (path_or_audio_name, start, end)
        - segment_texts (dict): 以该元组为 key，文本内容为 value

    Args:
        language (str): language代码
        model (str): 模型名称
        output_dir (str): 结果目录，默认为 "results"

    Returns:
        (set, dict):
            set: 已转录 segment 的键集合
            dict: key 同上，value 为该片段的文本内容（字符串）
    """
    results_dir = os.path.join(os.getcwd(), output_dir)
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


def load_audio_segment(
    audio_path: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> np.ndarray:
    """
    加载音频文件，可选择性地截取指定时间段的片段
    使用 torchaudio 加载，自动处理采样率和重采样
    
    Args:
        audio_path: 音频文件路径
        start_time: 开始时间（秒），如果为 None 则从开头开始
        end_time: 结束时间（秒），如果为 None 则到结尾结束
    
    Returns:
        waveform: 音频波形数据（numpy array，float32），已重采样到 16000 Hz
    """
    # 使用 torchaudio 加载音频，自动获取采样率
    wav, sr = torchaudio.load(audio_path, channels_first=False)
    
    # Convert为单声道（如果是立体声）
    if wav.dim() > 1 and wav.size(1) > 1:
        wav = wav.mean(dim=1, keepdim=True)
    
    # 如果提供了时间范围，先截取片段（在原始采样率下）
    if start_time is not None or end_time is not None:
        start_sample = int(start_time * sr) if start_time is not None else 0
        end_sample = int(end_time * sr) if end_time is not None else wav.size(0)
        start_sample = max(0, start_sample)
        end_sample = min(wav.size(0), end_sample)
        wav = wav[start_sample:end_sample]
    
    # 如果采样率不是 16000，需要重采样
    if sr != SAMPLE_RATE:
        # 使用 torchaudio 重采样
        resampler = torchaudio.transforms.Resample(sr, SAMPLE_RATE)
        # wav 的形状是 (n_samples, n_channels)，需要转置为 (n_channels, n_samples) 进行重采样
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)  # (n_samples,) -> (1, n_samples)
        elif wav.dim() == 2 and wav.size(1) == 1:
            wav = wav.transpose(0, 1)  # (n_samples, 1) -> (1, n_samples)
        wav = resampler(wav)
        # 转回 (n_samples,) 或 (n_samples, 1)
        if wav.size(0) == 1:
            wav = wav.squeeze(0)  # (1, n_samples) -> (n_samples,)
    
    # Convert为 numpy array
    waveform = wav.squeeze().numpy().astype(np.float32)
    
    return waveform




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


def deduplicate_and_sort_results(language: str, model: str, output_dir: str) -> None:
    """
    对指定语言和模型的结果文件进行去重与排序：
      1. 以 (path或audio_name, start, end) 为唯一键，保留"最后出现"的一条记录；
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


def transcribe_audio(
    audio_path: str,
    start_time: float,
    end_time: float,
    language: str,
    model
) -> str:
    """
    转录音频文件的指定片段。
    
    该函数支持转录单一音频片段，会自动处理Language mapping、音频加载和模型调用。

    Args:
        audio_path (str): 音频文件的绝对路径
        start_time (float): 起始时间（秒）
        end_time (float): 结束时间（秒）
        language (str): 国家代码（如 "ARE", "IRQ"），将自动映射到 dolphin 支持的语言代码
        model: 已加载的 dolphin 模型

    Returns:
        str: 转录文本（不含特殊符号）
    """
    # 获取语言和地区代码
    lang_region = LANGUAGE_MAPPING.get(language.upper(), None)
    if lang_region is None:
        print(f"警告：未找到language {language} 的映射，将使用自动检测")
        lang_sym = None
        region_sym = None
    else:
        lang_sym, region_sym = lang_region

    # Process空字符串的情况（将空字符串视为 None）
    if lang_sym == "":
        lang_sym = None
    if region_sym == "":
        region_sym = None

    # Load并截取音频片段
    waveform_segment = load_audio_segment(
        audio_path, 
        start_time=start_time, 
        end_time=end_time
    )
    
    # 根据 lang_sym 和 region_sym 的值决定如何调用模型
    try:
        if lang_sym is None:
            # 如果 lang 为空，则不指定language，使用自动检测
            result = model(speech=waveform_segment)
        elif region_sym is None:
            # 如果 lang 存在但 region 为空，则只指定语言
            result = model(speech=waveform_segment, lang_sym=lang_sym)
        else:
            # 如果两者都存在，则同时指定语言和地区
            result = model(
                waveform_segment,
                lang_sym=lang_sym,
                region_sym=region_sym
            )
        
        # Return不含特殊符号的文本
        return result.text_nospecial
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
        "--model_name",
        type=str,
        default="small",
        choices=["base", "small"],
        help="模型名称（base 或 small）"
    )
    parser.add_argument(
        "--model_dir",
        type=str,
        required=True,
        help="模型目录路径"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="如果为 true，则对于已存在但文本为空的片段重新进行识别"
    )

    args = parser.parse_args()
    
    # 验证并normalizationlanguage代码
    languages = [lang.upper() for lang in args.languages]
    
    # 设置默认路径
    if args.text_dir is None:
        text_dir = os.path.join(os.getcwd(), "data", "text", "ref")
    else:
        text_dir = os.path.abspath(args.text_dir)
    
    if args.audio_dir is None:
        audio_dir = os.path.join(os.getcwd(), "data", "audio", "testbatch")
    else:
        audio_dir = os.path.abspath(args.audio_dir)
    
    print(f"使用模型: {args.model_name}")
    print(f"模型目录: {args.model_dir}")
    print(f"文本目录: {text_dir}")
    print(f"音频目录: {audio_dir}")
    print(f"处理language: {', '.join(languages)}")

    # Load模型
    print("\n正在加载模型...")
    try:
        model = load_model(
            model_name=args.model_name,
            model_dir=args.model_dir
        )
        print("模型加载成功")
    except Exception as e:
        print(f"模型加载失败: {e}")
        raise

    # 验证目录是否存在
    if not os.path.exists(text_dir):
        raise ValueError(f"文本目录不存在: {text_dir}")
    if not os.path.exists(audio_dir):
        raise ValueError(f"音频目录不存在: {audio_dir}")

    # Iterate指定的language
    total_languages = len(languages)
    for lang_idx, language in enumerate(languages, 1):
        print(f"\n处理language [{lang_idx}/{total_languages}]: {language}")

        # 构建文本文件路径：data/text/ref/{language}.json
        text_file = os.path.join(text_dir, f"{language}.json")
        
        if not os.path.exists(text_file):
            print(f"  警告：文本文件不存在，跳过: {text_file}")
            continue

        # Load该language已转录的segments
        model_name = f"dolphin_{args.model_name}"
        transcribed_segments, segment_texts = load_transcribed_segments(language, model_name, args.output_dir)
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
        transcribed_segments, segment_texts = load_transcribed_segments(language, model_name, args.output_dir)
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
            # 构建音频文件路径：若 audio_name 已带扩展名则直接使用，否则尝试多种扩展名
            audio_extensions = ['.wav', '.mp3', '.flac', '.m4a']
            audio_path = None
            lang_audio_dir = os.path.join(audio_dir, language)

            # 若已有扩展名则直接使用该路径，不再尝试追加扩展名
            _, ext = os.path.splitext(audio_name)
            if ext:
                direct_path = os.path.join(lang_audio_dir, audio_name)
                if os.path.exists(direct_path):
                    audio_path = direct_path
            else:
                # 无扩展名时，尝试可能的扩展名
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
                        model=model
                    )
                    # 即使返回为空文本也进行保存
                    preview = ""
                    if isinstance(transcription_text, str):
                        preview = transcription_text.strip()[:50]
                    print(f"      转录成功: {preview}...")
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
