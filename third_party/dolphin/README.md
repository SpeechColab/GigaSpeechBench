# Dolphin ASR

Batch ASR transcription using the Dolphin multilingual speech recognition model.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `dolphin_asr.py` | Main transcription script / 主转录脚本 |

## Setup / 环境配置

```bash
# Install dolphin model dependencies
```

## Usage / 使用方法

```bash
python dolphin_asr.py --input_dir /path/to/audio --output_dir /path/to/results
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

# Dolphin ASR

使用 Dolphin 多语言语音识别模型进行批量转录。

脚本和使用方法见上方英文部分。
