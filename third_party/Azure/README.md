# Azure Speech-to-Text

Batch ASR transcription using Microsoft Azure Cognitive Services Speech-to-Text API.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `Azure.py` | Main transcription script / 主转录脚本 |

## Setup / 环境配置

```bash
export AZURE_SPEECH_KEY=your_key
export AZURE_SPEECH_REGION=your_region
```

## Usage / 使用方法

```bash
python Azure.py --input_dir /path/to/audio --output_dir /path/to/results
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

# Azure 语音转文本

使用 Microsoft Azure 认知服务语音转文本 API 进行批量 ASR 转录。

脚本和使用方法见上方英文部分。
