# pip install google-genai tqdm pydub ffmpeg-python
import os
import json
import threading
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from pydub.utils import mediainfo

from google import genai

# 从 utils 导入 save_transcription（如果没有，下方会提供替代实现）
try:
    from utils import save_transcription
except ImportError:
    def save_transcription(audio_path, text, language, model, start_time, end_time):
        pass  # 占位，实际用自定义保存逻辑

########################################  参数配置  ########################################
API_KEY      = "AIzaSyDkQMeqc8hAMignNtgoxkHxjsqgWphyzf8"  # 你的 API Key
ROOT_DIR     = r"E:\workspace\SH-ASR\testbatch_processed"  # 待转录音频根目录
TESTMARK_DIR = r"E:\workspace\SH-ASR\testmark"             # 参考格式根目录
OUTPUT_DIR   = r"E:\workspace\SH-ASR\results"              # 输出结果根目录
MODEL_NAME   = "gemini-2.0-flash"                          # 稳定版模型
TEMP_DIR     = r"E:\workspace\SH-ASR\temp_segments"         # 临时切割音频目录
MAX_WORKERS  = 16                                           # 最大线程数（根据 API 并发限制调整）
TARGET_LANG  = "MYS"                                       # 仅处理 MYS 语种
########################################  参数配置  ########################################

# 初始化 Gemini 客户端（线程安全）
client = genai.Client(api_key=API_KEY)

# 创建必要目录
Path(TEMP_DIR).mkdir(exist_ok=True, parents=True)
Path(OUTPUT_DIR).mkdir(exist_ok=True, parents=True)

# 线程锁：避免多线程同时打印导致输出混乱
print_lock = threading.Lock()

def get_audio_segment(wav_path: str, start_sec: float, end_sec: float) -> AudioSegment:
    """按时间切割音频片段（单位：秒）"""
    audio = AudioSegment.from_wav(str(wav_path))
    start_ms = int(start_sec * 1000)
    end_ms = int(end_sec * 1000)
    return audio[start_ms:end_ms]

def transcribe_segment_worker(segment_idx: int, segment_audio: AudioSegment) -> tuple[int, str]:
    """转录单个音频片段（线程工作函数）：返回 (分段索引, 转录文本)"""
    temp_file = Path(TEMP_DIR) / f"temp_segment_{segment_idx}_{id(segment_audio)}.wav"
    segment_audio.export(str(temp_file), format="wav")
    
    try:
        uploaded = client.files.upload(file=str(temp_file))
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                # 优化指令：明确 MYS（马来语）转录，提升准确率
                "Transcribe the speech accurately.",
                uploaded
            ]
        )
        # 清理资源
        client.files.delete(name=uploaded.name)
        temp_file.unlink(missing_ok=True)
        transcribed_text = response.text.strip() if response.text else ""
        
        with print_lock:
            print(f"[线程完成] 分段 {segment_idx} 转录成功")
        return (segment_idx, transcribed_text)
    
    except Exception as e:
        with print_lock:
            print(f"[线程警告] 分段 {segment_idx} 转录失败：{e}")
        temp_file.unlink(missing_ok=True)
        return (segment_idx, "")

def main():
    # 🌟 关键修改：仅获取 TESTMARK_DIR/MYS 下的参考 JSON 文件
    mys_ref_json_dir = Path(TESTMARK_DIR) / TARGET_LANG
    if not mys_ref_json_dir.exists():
        print(f"[ERROR] 未找到 MYS 参考目录：{mys_ref_json_dir}")
        return
    
    # 获取 MYS 所有参考 JSON 文件（按文件名匹配音频）
    mys_ref_json_list = list(mys_ref_json_dir.rglob("*.json"))
    if not mys_ref_json_list:
        print(f"[ERROR] MYS 参考目录下未找到任何 JSON 文件：{mys_ref_json_dir}")
        return
    
    print(f"[INFO] 找到 {len(mys_ref_json_list)} 个 MYS 语种参考文件，开始处理...")

    # 逐个处理 MYS 音频（按参考 JSON 匹配）
    for ref_json_path in tqdm(mys_ref_json_list, desc="Gemini-ASR (MYS 专属)"):
        audio_name = ref_json_path.stem  # 音频/JSON 文件名（不含后缀）
        lang_code = TARGET_LANG  # 固定为 MYS
        
        # 🌟 关键修改：匹配 ROOT_DIR/MYS 下的对应 WAV 音频文件
        wav_path = Path(ROOT_DIR) / TARGET_LANG / f"{audio_name}.wav"
        if not wav_path.exists():
            with print_lock:
                print(f"\n[ERROR] 未找到对应音频文件：{wav_path}，跳过该 JSON")
            continue
        
        # 读取参考分段信息
        with open(ref_json_path, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
        ref_segments = ref_data.get("segments", [])
        if not ref_segments:
            with print_lock:
                print(f"\n[WARNING] 参考文件无分段信息：{ref_json_path}，跳过")
            continue
        
        # 预处理：筛选有效分段（需转录的）
        valid_tasks = []  # 存储 (分段原始索引, 音频片段, 参考分段数据)
        for seg_idx, seg in enumerate(ref_segments):
            start_sec = seg["start"]
            end_sec = seg["end"]
            # 跳过无效分段或过短片段
            if seg["status"] == "invalid" or (end_sec - start_sec) < 0.1:
                continue
            # 切割音频片段
            segment_audio = get_audio_segment(str(wav_path), start_sec, end_sec)
            valid_tasks.append((seg_idx, segment_audio, seg))
        
        if not valid_tasks:
            with print_lock:
                print(f"\n[INFO] 音频 {audio_name} 无有效分段，直接生成空文本结果")
            # 直接生成格式一致的文件（text 为空）
            output_dir = Path(OUTPUT_DIR) / TARGET_LANG
            output_dir.mkdir(exist_ok=True, parents=True)
            output_json_path = output_dir / f"{audio_name}.json"
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(ref_data, f, ensure_ascii=False, indent=2)
            continue
        
        # 多线程并行转录有效分段
        with print_lock:
            print(f"\n[INFO] 开始处理音频 {audio_name}，共 {len(valid_tasks)} 个有效分段，使用 {MAX_WORKERS} 线程")
        
        # 存储转录结果：key=分段原始索引，value=转录文本
        transcribed_results = {}
        
        # 使用线程池执行任务
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 提交所有任务
            future_to_seg = {
                executor.submit(transcribe_segment_worker, seg_idx, seg_audio): (seg_idx, seg_data)
                for seg_idx, seg_audio, seg_data in valid_tasks
            }
            
            # 监听任务完成情况
            for future in tqdm(as_completed(future_to_seg), total=len(future_to_seg), desc=f"{audio_name} 分段转录"):
                seg_idx, _ = future_to_seg[future]
                try:
                    result_idx, result_text = future.result()
                    transcribed_results[result_idx] = result_text
                except Exception as e:
                    with print_lock:
                        print(f"[ERROR] 分段 {seg_idx} 结果获取失败：{e}")
                    transcribed_results[seg_idx] = ""
        
        # 构建最终输出分段（替换 text 字段）
        output_segments = []
        for seg_idx, seg in enumerate(ref_segments):
            if seg_idx in transcribed_results:
                # 替换转录文本
                output_seg = seg.copy()
                output_seg["text"] = transcribed_results[seg_idx]
                output_segments.append(output_seg)
            else:
                # 无效分段直接保留原数据
                output_segments.append(seg)
        
        # 保存输出文件（固定保存到 MYS 目录）
        output_dir = Path(OUTPUT_DIR) / TARGET_LANG
        output_dir.mkdir(exist_ok=True, parents=True)
        output_json_path = output_dir / f"{audio_name}.json"
        
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "audio_name": audio_name,
                "segments": output_segments
            }, f, ensure_ascii=False, indent=2)
        
        with print_lock:
            print(f"\n[SUCCESS] 音频 {audio_name} 处理完成，结果保存至：{output_json_path}")

    print(f"\n===== MYS 语种全部处理完成！结果在 {Path(OUTPUT_DIR)/TARGET_LANG} =====")

if __name__ == "__main__":
    main()