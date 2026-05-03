# Google Chirp 3（Cloud Speech-to-Text V2）

<p align="center"><a href="README.md">🇬🇧 English</a></p>

使用 Google Cloud Speech-to-Text V2 API 和 Chirp 3 模型进行批量 ASR 转录。适用于短音频（<60s）的同步推理。

## 脚本

| 文件 | 说明 |
|:-----|:-----|
| `Chirp3.py` | 主转录脚本 |
| `run_syr_missing.py` | 补跑缺失的 SYR 段 |

## 环境配置

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

## 使用方法

```bash
python Chirp3.py --input_dir /path/to/audio --output_dir /path/to/results
```

## 输出格式

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="转写结果", lang="ARE")
writer.save("results/model_name.json")
```
