# NVIDIA NeMo ASR

<p align="center"><a href="README.md">🇬🇧 English</a></p>

使用 NVIDIA NeMo 预训练模型进行批量 ASR 转录。包含阿拉伯语、日语、韩语、中文方言和英语方言的专用脚本。

## 脚本

| 文件 | 说明 |
|:-----|:-----|
| `ar_asr.py` | 阿拉伯语 ASR |
| `jpn_asr.py` | 日语 ASR |
| `kor_asr.py` | 韩语 ASR |
| `ZH-Dialects.py` | 中文方言 ASR |
| `EN_Dialects.py` | 英语方言 ASR |
| `download.py` | 模型下载工具 |

## 环境配置

```bash
pip install nemo_toolkit[asr]
```

## 使用方法

```bash
python ar_asr.py --input_dir /path/to/audio --output_dir /path/to/results
```

## 输出格式

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="转写结果", lang="ARE")
writer.save("results/model_name.json")
```
