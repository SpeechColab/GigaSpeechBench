# pip install openai tqdm pydub ffmpeg-python
import os
import json
import threading
import glob
from typing import Dict, Any
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from pydub.utils import mediainfo

# 导入 OpenAI 客户端
from openai import OpenAI

# 从 utils 导入 save_transcription（如果没有，下方会提供替代实现）
try:
    from utils import save_transcription
except ImportError:
    # 占位，实际用自定义保存逻辑
    def save_transcription(audio_path, text, language, model, start_time, end_time):
        pass 

########################################  参数配置  ########################################
# 注意：替换为你的 OpenAI API Key
    

API_KEY      = os.getenv("OPENAI_API_KEY")  # set via environment variable
ROOT_DIR     = r"/Users/wangpeng/Desktop/data4test_v2"  # <--- 修改为您的数据目录
TESTMARK_DIR = r"/Users/wangpeng/Desktop/data4test_v2"  # <--- 修改为您的数据目录
OUTPUT_DIR   = r"/Users/wangpeng/Desktop/data4test_v2/asr_results_output" # <--- 修改为您希望保存结果的目录
MODEL_NAME   = "gpt-4o-transcribe"                         
TEMP_DIR     = r"/Users/wangpeng/Desktop/data4test_v2/temp_segments_openai" # <--- 临时切割音频目录，可选修改
FINAL_OUTPUT_DIR = r"/Users/wangpeng/Desktop/data4test_v2/asr_results_all" # <--- 新增：最终合并结果目录

MAX_WORKERS  = 16                                          
########################################  参数配置  ########################################

# 定义语言映射表：目录名 -> ISO-639-1 语言代码 (供 OpenAI API 使用)
LANG_MAP = {
    "ARE": "ar", "DZA": "ar", "EGY": "ar", "IRQ": "ar", "MAR": "ar", "SAU": "ar",
    "MYS": "ms", "IDN": "id", "PHL": "tl", "THA": "th", "VNM": "vi",
    "JPN": "ja", "KOR": "ko",
}

# 初始化 OpenAI 客户端（线程安全，无需每个线程创建）
client = OpenAI(api_key=API_KEY)

# 创建必要目录
Path(TEMP_DIR).mkdir(exist_ok=True, parents=True)
Path(OUTPUT_DIR).mkdir(exist_ok=True, parents=True)
Path(FINAL_OUTPUT_DIR).mkdir(exist_ok=True, parents=True) # <--- 创建最终输出目录

# 线程锁：避免多线程同时打印导致输出混乱
print_lock = threading.Lock()

def get_audio_segment(wav_path: str, start_sec: float, end_sec: float) -> AudioSegment:
    """按时间切割音频片段（单位：秒）"""
    audio = AudioSegment.from_wav(str(wav_path))
    start_ms = int(start_sec * 1000)
    end_ms = int(end_sec * 1000)
    return audio[start_ms:end_ms]

def transcribe_segment_worker(segment_idx: int, segment_audio: AudioSegment, lang_code: str) -> tuple[int, str]:
    """转录单个音频片段（线程工作函数）：返回 (分段索引, 转录文本)"""
    temp_file = Path(TEMP_DIR) / f"temp_segment_{segment_idx}_{threading.get_ident()}.wav"
    
    segment_audio.export(str(temp_file), format="wav")
    
    transcribed_text = ""
    try:
        with open(str(temp_file), "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=MODEL_NAME,
                file=audio_file,
                language=lang_code 
            )
            transcribed_text = transcript.text.strip() if hasattr(transcript, "text") else ""
        
        temp_file.unlink(missing_ok=True) 
        
        with print_lock:
            print(f"[线程完成] 分段 {segment_idx} 转录成功 (语言: {lang_code})")
        return (segment_idx, transcribed_text)
    
    except Exception as e:
        with print_lock:
            temp_file.unlink(missing_ok=True) 
            print(f"[线程警告] 分段 {segment_idx} 转录失败：{e}")
        return (segment_idx, "")

# ==============================================================================
# 新增功能：汇总和格式转换
# ==============================================================================

# ==============================================================================
# 新增功能：按语言汇总和格式转换
# ==============================================================================

def aggregate_results(output_dir: Path, root_dir: Path, lang_map: Dict[str, str], model_name: str, final_output_dir_path: Path):
    """
    遍历 OUTPUT_DIR 下的所有 JSON 文件，按语言分组，并将它们的内容转换为统一的列表格式，
    然后为每种语言生成一个独立的 JSON 文件，命名为 {language}_{model_name}.json。
    
    Args:
        output_dir (Path): 存放每个长音频 JSON 结果的根目录。
        root_dir (Path): 长音频文件 ROOT_DIR，用于获取完整的 WAV 路径。
        lang_map (Dict[str, str]): 语言目录名到 ISO 代码的映射（虽然在此函数中主要使用目录名）。
        model_name (str): 用于结果文件命名的模型名。
        final_output_dir_path (Path): 最终汇总结果的输出目录。
    """
    # 存储按语言分组的转录数据：{ "JPN": [ {entry1}, {entry2}, ... ], "MYS": [ ... ] }
    results_by_language: Dict[str, list[Dict[str, str | float]]] = {}
    
    # 找到所有生成的 JSON 文件
    result_files = list(output_dir.rglob("*.json"))
    
    if not result_files:
        print("\n[INFO] 未找到任何 JSON 结果文件，跳过汇总。")
        return

    print(f"\n===== 开始分组汇总 {len(result_files)} 个 JSON 文件 =====")

    for json_path in tqdm(result_files, desc="分组汇总 JSON"):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 1. 提取信息
            audio_name = data.get("audio_name")
            segments = data.get("segments", [])
            
            # 2. 确定语言目录名 (例如 JPN, MYS) - 这是分组的关键
            lang_dir_name = json_path.parent.name # 例如 JPN
            
            # 初始化该语言的列表
            if lang_dir_name not in results_by_language:
                results_by_language[lang_dir_name] = []
            
            # 3. 确定原始 WAV 文件的完整路径
            original_wav_path = root_dir / lang_dir_name / f"{audio_name}.wav"
            
            # 4. 转换分段格式并添加到对应语言组
            for seg in segments:
                transcribed_text = seg.get("text", "").strip()
                if not transcribed_text:
                    continue
                    
                entry: Dict[str, str | float] = {
                    "path": str(original_wav_path.resolve()),
                    "text": transcribed_text,
                    "language": lang_dir_name, # 使用 JPN/MYS 这种目录名
                    "model": model_name,
                    "start_time": seg.get("start", 0.0),
                    "end_time": seg.get("end", 0.0)
                }
                results_by_language[lang_dir_name].append(entry)

        except Exception as e:
            print(f"\n[WARNING] 处理文件 {json_path} 时出错: {e}")
            continue

    # 5. 写入最终的汇总文件 (按语言循环)
    final_output_dir = final_output_dir_path
    final_output_dir.mkdir(exist_ok=True, parents=True)
    
    print("\n===== 开始写入按语言分组的汇总文件 =====")

    for lang_dir_name, data_list in results_by_language.items():
        if not data_list:
            continue
            
        # 文件名格式: {language}_{model_name}.json (例如: JPN_gpt4o-transcribe.json)
        final_filename = f"{lang_dir_name}_{model_name}.json" 
        final_output_path = final_output_dir / final_filename

        with open(final_output_path, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)

        print(f"[SUCCESS] 语言 {lang_dir_name} 汇总文件保存至：{final_output_path} (共 {len(data_list)} 条记录)")

# ... (main 函数保持不变，只需确保调用 aggregate_results 即可)



def main():
    # ... (前面的代码保持不变，处理音频和转录)
    wav_list = list(Path(ROOT_DIR).rglob("*.wav"))
    if not wav_list:
        print("未找到任何 wav 文件，请检查目录设置！")
        return

    # 逐个处理长音频（串行）
    for wav_path in tqdm(wav_list, desc="ChatGPT-4o ASR 主进程"):
        wav_path = wav_path.resolve()
        audio_name = wav_path.stem
        lang_dir = wav_path.parent.name.upper()
        
        lang_code = LANG_MAP.get(lang_dir)
        if not lang_code:
            with print_lock:
                print(f"\n[ERROR] 无法识别的语言目录：{lang_dir}，跳过该音频 {audio_name}。请检查 LANG_MAP 配置！")
            continue

        ref_json_path = Path(TESTMARK_DIR) / lang_dir / f"{audio_name}.json"
        if not ref_json_path.exists():
            with print_lock:
                print(f"\n[ERROR] 未找到参考文件：{ref_json_path}，跳过该音频")
            continue
        
        with open(ref_json_path, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
        ref_segments = ref_data.get("segments", [])
        
        valid_tasks = []  
        for seg_idx, seg in enumerate(ref_segments):
            start_sec = seg["start"]
            end_sec = seg["end"]
            if seg.get("status") == "invalid" or (end_sec - start_sec) < 0.1:
                continue
            
            try:
                segment_audio = get_audio_segment(wav_path, start_sec, end_sec)
                valid_tasks.append((seg_idx, segment_audio, seg))
            except Exception as e:
                 with print_lock:
                     print(f"[WARNING] 音频 {audio_name} 分段 {seg_idx} 切割失败：{e}。跳过。")


        if not valid_tasks:
            with print_lock:
                print(f"\n[INFO] 音频 {audio_name} 无有效分段，直接复制参考文件")
            output_dir = Path(OUTPUT_DIR) / lang_dir
            output_dir.mkdir(exist_ok=True, parents=True)
            output_json_path = output_dir / f"{audio_name}.json"
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(ref_data, f, ensure_ascii=False, indent=2)
            continue
        
        with print_lock:
            print(f"\n[INFO] 开始处理音频 {audio_name} (语言: {lang_code})，共 {len(valid_tasks)} 个有效分段，使用 {MAX_WORKERS} 线程")
        
        transcribed_results = {}
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_seg = {
                executor.submit(transcribe_segment_worker, seg_idx, seg_audio, lang_code): (seg_idx, seg_data)
                for seg_idx, seg_audio, seg_data in valid_tasks
            }
            
            for future in tqdm(as_completed(future_to_seg), total=len(future_to_seg), desc=f"{audio_name} 分段转录"):
                seg_idx, _ = future_to_seg[future]
                try:
                    result_idx, result_text = future.result()
                    transcribed_results[result_idx] = result_text
                except Exception as e:
                    with print_lock:
                        print(f"[ERROR] 分段 {seg_idx} 结果获取失败：{e}")
                    transcribed_results[seg_idx] = ""
        
        output_segments = []
        for seg_idx, seg in enumerate(ref_segments):
            if seg_idx in transcribed_results:
                output_seg = seg.copy()
                output_seg["text"] = transcribed_results[seg_idx]
                output_segments.append(output_seg)
            else:
                output_segments.append(seg)
        
        output_dir = Path(OUTPUT_DIR) / lang_dir 
        output_dir.mkdir(exist_ok=True, parents=True)
        output_json_path = output_dir / f"{audio_name}.json"
        
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "audio_name": audio_name,
                "segments": output_segments
            }, f, ensure_ascii=False, indent=2)
        
        with print_lock:
            print(f"\n[SUCCESS] 音频 {audio_name} 处理完成，结果保存至：{output_json_path}")

    print(f"\n===== 所有长音频处理完成！分文件结果在 {OUTPUT_DIR} =====")
    
    # <--- 新增：调用 JSON 合并功能 --->
    aggregate_results(Path(OUTPUT_DIR), Path(ROOT_DIR), LANG_MAP, MODEL_NAME, Path(FINAL_OUTPUT_DIR))


if __name__ == "__main__":
    main()