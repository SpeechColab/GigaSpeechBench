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

# 语言映射：将国家代码映射到 (lang_sym, region_sym) 二元组
# lang_sym 和 region_sym 会加上 <> 符号，例如 "<ja>", "<JP>"
LANGUAGE_MAPPING = {
    "ARE": ("ar", "AE"),      # 阿拉伯语-阿联酋
    "IRQ": ("ar", ""),     # 阿拉伯语-伊拉克
    "DZA": ("ar", ""),      # 阿拉伯语-阿尔及利亚
    "EGY": ("ar", "EG"),      # 阿拉伯语-埃及
    "SAU": ("ar", "SA"),      # 阿拉伯语-沙特
    "MAR": ("ar", "MA"),      # 阿拉伯语-摩洛哥
    "IDN": ("id", "ID"),      # 印尼语
    "JPN": ("ja", "JP"),      # 日语
    "KOR": ("ko", "KR"),      # 韩语
    "THA": ("th", "TH"),      # 泰语
    "VNM": ("vi", "VN"),      # 越南语
    "PHL": ("fil", "PH"),     # 菲律宾语
    "MYS": ("ms", "MY"),      # 马来语
    "CMN": ("zh", ""),      # 中文
}


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
    
    # 转换为单声道（如果是立体声）
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
    
    # 转换为 numpy array
    waveform = wav.squeeze().numpy().astype(np.float32)
    
    return waveform


def transcribe_audio_segment(
    audio_path: str,
    model,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    lang_sym: Optional[str] = None,
    region_sym: Optional[str] = None
) -> str:
    """
    对音频文件的指定片段进行语音识别
    
    Args:
        audio_path: 音频文件路径
        model: 已加载的 dolphin 模型
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        lang_sym: 语言代码符号（例如 "ja"），会自动加上 <>
        region_sym: 地区代码符号（例如 "JP"），会自动加上 <>
        如果 lang_sym 为空，则不指定语种使用自动检测
        如果 lang_sym 存在但 region_sym 为空，则只指定语言
    
    Returns:
        text_nospecial: 识别结果文本（不含特殊符号）
    """
    # 加载并截取音频片段
    waveform_segment = load_audio_segment(
        audio_path, 
        start_time=start_time, 
        end_time=end_time
    )
    
    # 处理空字符串的情况（将空字符串视为 None）
    if lang_sym == "":
        lang_sym = None
    if region_sym == "":
        region_sym = None
    # 根据 lang_sym 和 region_sym 的值决定如何调用模型
    if lang_sym is None:
        # 如果 lang 为空，则不指定语种，使用自动检测
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
    
    # 返回不含特殊符号的文本
    return result.text_nospecial


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
    wav_filename = os.path.basename(audio_path)
    formatted_path = f"{language_code}/{wav_filename}"
    segment_key = (formatted_path, float(start_time), float(end_time))
    return segment_key in transcribed_segments


def transcribe_audio(
    audio_path: str,
    start_time: float,
    end_time: float,
    language: str,
    model
) -> str:
    """
    转录音频文件的指定片段。

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
        print(f"警告：未找到语种 {language} 的映射，将使用自动检测")
        lang_sym = None
        region_sym = None
    else:
        lang_sym, region_sym = lang_region

    # 调用转录函数
    try:
        text = transcribe_audio_segment(
            audio_path=audio_path,
            model=model,
            start_time=start_time,
            end_time=end_time,
            lang_sym=lang_sym,
            region_sym=region_sym
        )
        return text
    except Exception as e:
        print(f"转录失败: {e}")
        raise


def main():
    """
    主函数：根据标准格式的JSON文件转录音频文件。
    """
    parser = argparse.ArgumentParser(description="批量转录音频文件并保存结果")
    parser.add_argument(
        "--lang_codes",
        type=str,
        nargs="+",
        required=True,
        help="要处理的语种代码列表（例如：--lang_codes JPN ARE IDN）"
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
        default=None,
        help="模型目录路径"
    )

    args = parser.parse_args()
    
    # 验证并规范化语种代码
    lang_codes = [lang.upper() for lang in args.lang_codes]
    
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
    print(f"处理语种: {', '.join(lang_codes)}")

    # 加载模型
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

    # 遍历指定的语种
    total_languages = len(lang_codes)
    for lang_idx, lang_code in enumerate(lang_codes, 1):
        print(f"\n处理语种 [{lang_idx}/{total_languages}]: {lang_code}")

        # 构建文本文件路径：data/text/ref/{lang_code}.json
        text_file = os.path.join(text_dir, f"{lang_code}.json")
        
        if not os.path.exists(text_file):
            print(f"  警告：文本文件不存在，跳过: {text_file}")
            continue

        # 加载该语种已转录的segments
        model_name = f"dolphin_{args.model_name}"
        transcribed_segments = load_transcribed_segments(lang_code, model_name)
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

            # 构建音频文件路径：data/audio/testbatch/{lang_code}/{audio_name}.wav
            # 尝试多种可能的扩展名
            audio_extensions = ['.wav', '.mp3', '.flac', '.m4a']
            audio_path = None
            
            lang_audio_dir = os.path.join(audio_dir, lang_code)
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

                # 构造格式化的路径：{lang_code}/{audio_filename}
                audio_filename = os.path.basename(audio_path)
                formatted_path = f"{lang_code}/{audio_filename}"

                # 检查该segment是否已经转录过
                if is_segment_transcribed(audio_path, start_time, end_time, lang_code, transcribed_segments):
                    print(f"      该segment已转录，跳过")
                    continue

                # 调用 transcribe_audio 进行转录
                try:
                    transcription_text = transcribe_audio(
                        audio_path=audio_path,
                        start_time=start_time,
                        end_time=end_time,
                        language=lang_code,
                        model=model
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
                        language=lang_code,
                        model=model_name,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    # 修正保存的路径格式，确保使用 Linux 风格的路径分隔符
                    results_dir = os.path.join(os.getcwd(), args.output_dir)
                    os.makedirs(results_dir, exist_ok=True)
                    filename = f"{lang_code}_{model_name}.json"
                    output_path = os.path.join(results_dir, filename)
                    
                    if os.path.exists(output_path):
                        with open(output_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        # 修正最后一个条目的路径格式
                        if data and len(data) > 0:
                            last_entry = data[-1]
                            # 将路径标准化为 Linux 风格：{lang_code}/{audio_filename}
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
