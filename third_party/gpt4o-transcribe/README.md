# GPT-4o Transcribe (OpenAI)

Batch ASR transcription using OpenAI's GPT-4o audio transcription API.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `chatgpt4o-transcribe.py` | Main transcription script / 主转录脚本 |
| `run_fleurs_missing.py` | Rerun missing FLEURS segments / 补跑缺失的 FLEURS 段 |

## Setup / 环境配置

```bash
export OPENAI_API_KEY=your_key
```

## Usage / 使用方法

```bash
python chatgpt4o-transcribe.py --input_dir /path/to/audio --output_dir /path/to/results
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

# GPT-4o Transcribe（OpenAI）

使用 OpenAI 的 GPT-4o 音频转录 API 进行批量 ASR 转录。

脚本和使用方法见上方英文部分。
