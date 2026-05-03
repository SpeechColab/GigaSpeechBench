# Whisper Large V3（OpenAI）

<p align="center"><a href="README.md">🇬🇧 English</a></p>

使用 OpenAI 的 Whisper Large V3 模型进行批量 ASR 转录。支持全音频和分段推理模式。使用 `uv` 进行环境管理。

## 脚本

| 文件 | 说明 |
|:-----|:-----|
| `whisper_asr.py` | Whisper ASR 封装 |
| `auto_infer.py` | 全音频批量推理 |
| `auto_infer_with_segments.py` | 分段推理 |
| `language_mapping.py` | 语言代码映射 |

## 环境配置

```bash
uv sync
# Or: pip install openai-whisper torch
```

## 使用方法

```bash
python auto_infer.py --input_dir /path/to/audio --output_dir /path/to/results
```

## 输出格式

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="转写结果", lang="ARE")
writer.save("results/model_name.json")
```
