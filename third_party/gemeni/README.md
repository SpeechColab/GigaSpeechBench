# Google Gemini ASR

Batch audio transcription using Google Gemini multimodal models. Supports multi-threaded parallel processing for long audio.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `gemini.py` | Main transcription script / 主转录脚本 |
| `gemini_MYS.py` | MYS-specific script / MYS 专用脚本 |
| `run_syr_missing.py` | Rerun missing SYR segments / 补跑缺失的 SYR 段 |

## Setup / 环境配置

```bash
export GOOGLE_API_KEY=your_key
```

## Usage / 使用方法

```bash
python gemini.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format / 输出格式

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```

---

# Google Gemini ASR

使用 Google Gemini 多模态模型进行批量音频转录。支持多线程并行处理长音频。

脚本和使用方法见上方英文部分。
