# Whisper Large V3 (OpenAI)

Batch ASR transcription using OpenAI's Whisper Large V3 model. Supports full-audio and segment-based inference modes. Uses `uv` for environment management.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `whisper_asr.py` | Whisper ASR wrapper / Whisper ASR 封装 |
| `auto_infer.py` | Full-audio batch inference / 全音频批量推理 |
| `auto_infer_with_segments.py` | Segment-based inference / 基于时间戳的分段推理 |
| `language_mapping.py` | Language code mapping / 语言代码映射 |

## Setup / 环境配置

```bash
# Using uv for environment management
uv sync
# Or: pip install openai-whisper torch
```

## Usage / 使用方法

```bash
python auto_infer.py --input_dir /path/to/audio --output_dir /path/to/results
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

# Whisper Large V3（OpenAI）

使用 OpenAI 的 Whisper Large V3 模型进行批量 ASR 转录。支持全音频和分段推理模式。使用 `uv` 进行环境管理。

脚本和使用方法见上方英文部分。
