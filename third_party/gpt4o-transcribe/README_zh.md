# GPT-4o Transcribe（OpenAI）

<p align="center"><a href="README.md">🇬🇧 English</a></p>

使用 OpenAI 的 GPT-4o 音频转录 API 进行批量 ASR 转录。

## 脚本

| 文件 | 说明 |
|:-----|:-----|
| `chatgpt4o-transcribe.py` | 主转录脚本 |
| `run_fleurs_missing.py` | 补跑缺失的 FLEURS 段 |

## 环境配置

```bash
export OPENAI_API_KEY=your_key
```

## 使用方法

```bash
python chatgpt4o-transcribe.py --input_dir /path/to/audio --output_dir /path/to/results
```

## 输出格式

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="转写结果", lang="ARE")
writer.save("results/model_name.json")
```
