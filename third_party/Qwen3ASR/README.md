# Qwen3 ASR (DashScope API)

Batch ASR transcription using Alibaba Qwen3 ASR models via DashScope API. Supports qwen3-asr-flash, qwen3-asr-1.7b, and qwen3.5-omni-flash.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `qwen3asr.py` | Main transcription script / 主转录脚本 |
| `run_qwen35_cv_threaded.py` | Threaded qwen3.5-omni-flash inference / 多线程 qwen3.5 推理 |
| `run_qwen35_omni_fleurs.py` | qwen3.5-omni-flash on FLEURS / qwen3.5 在 FLEURS 上推理 |

## Setup / 环境配置

```bash
export DASHSCOPE_API_KEY=your_key
```

## Usage / 使用方法

```bash
python qwen3asr.py --input_dir /path/to/audio --output_dir /path/to/results
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

# Qwen3 ASR（DashScope API）

通过 DashScope API 使用阿里 Qwen3 ASR 系列模型进行批量转录。支持 qwen3-asr-flash、qwen3-asr-1.7b 和 qwen3.5-omni-flash。

脚本和使用方法见上方英文部分。
