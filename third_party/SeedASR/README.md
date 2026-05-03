# SeedASR (ByteDance Volcengine)

Batch ASR transcription using ByteDance Volcengine's Doubao recording recognition model 2.0 API. Supports resume and failure logging.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `seed_asr_infer_list.py` | Main transcription script / 主转录脚本 |

## Setup / 环境配置

```bash
# See https://console.volcengine.com/speech/service/10012
```

## Usage / 使用方法

```bash
python seed_asr_infer_list.py
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

# SeedASR（字节跳动火山引擎）

使用字节跳动火山引擎的豆包录音文件识别模型 2.0 API 进行批量转录。支持断点续传和失败记录。

脚本和使用方法见上方英文部分。
