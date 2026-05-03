# SeedASR（字节跳动火山引擎）

<p align="center"><a href="README.md">🇬🇧 English</a></p>

使用字节跳动火山引擎的豆包录音文件识别模型 2.0 API 进行批量转录。支持断点续传和失败记录。

## 脚本

| 文件 | 说明 |
|:-----|:-----|
| `seed_asr_infer_list.py` | 主转录脚本 |

## 环境配置

```bash
# See https://console.volcengine.com/speech/service/10012
```

## 使用方法

```bash
python seed_asr_infer_list.py
```

## 输出格式

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="转写结果", lang="ARE")
writer.save("results/model_name.json")
```
