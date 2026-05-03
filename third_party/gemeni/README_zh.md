# Google Gemini ASR

<p align="center"><a href="README.md">🇬🇧 English</a></p>

使用 Google Gemini 多模态模型进行批量音频转录。支持多线程并行处理长音频。

## 脚本

| 文件 | 说明 |
|:-----|:-----|
| `gemini.py` | 主转录脚本 |
| `gemini_MYS.py` | MYS 专用脚本 |
| `run_syr_missing.py` | 补跑缺失的 SYR 段 |

## 环境配置

```bash
export GOOGLE_API_KEY=your_key
```

## 使用方法

```bash
python gemini.py --input_dir /path/to/audio --output_dir /path/to/results
```

## 输出格式

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="转写结果", lang="ARE")
writer.save("results/model_name.json")
```
