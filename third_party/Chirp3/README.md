# Google Chirp 3 (Cloud Speech-to-Text V2)

Batch ASR transcription using Google Cloud Speech-to-Text V2 API with the Chirp 3 model. Designed for short audio (<60s) synchronous inference.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `Chirp3.py` | Main transcription script / 主转录脚本 |
| `run_syr_missing.py` | Rerun missing SYR segments / 补跑缺失的 SYR 段 |

## Setup / 环境配置

```bash
# Set up Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

## Usage / 使用方法

```bash
python Chirp3.py --input_dir /path/to/audio --output_dir /path/to/results
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

# Google Chirp 3（Cloud Speech-to-Text V2）

使用 Google Cloud Speech-to-Text V2 API 和 Chirp 3 模型进行批量 ASR 转录。适用于短音频（<60s）的同步推理。

脚本和使用方法见上方英文部分。
