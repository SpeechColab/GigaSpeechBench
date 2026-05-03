# ElevenLabs Scribe v2

Batch ASR transcription using ElevenLabs Scribe v2 speech recognition API.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `elevenlabs_asr.py` | Main transcription script / 主转录脚本 |

## Setup / 环境配置

```bash
export ELEVENLABS_API_KEY=your_key
```

## Usage / 使用方法

```bash
python elevenlabs_asr.py --input_dir /path/to/audio --output_dir /path/to/results
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

# ElevenLabs Scribe v2

使用 ElevenLabs Scribe v2 语音识别 API 进行批量转录。

脚本和使用方法见上方英文部分。
