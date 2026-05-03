# NVIDIA NeMo ASR

Batch ASR transcription using NVIDIA NeMo pre-trained models. Includes language-specific scripts for Arabic, Japanese, Korean, Chinese dialects, and English dialects.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `ar_asr.py` | Arabic ASR / 阿拉伯语 ASR |
| `jpn_asr.py` | Japanese ASR / 日语 ASR |
| `kor_asr.py` | Korean ASR / 韩语 ASR |
| `ZH-Dialects.py` | Chinese dialects ASR / 中文方言 ASR |
| `EN_Dialects.py` | English dialects ASR / 英语方言 ASR |
| `download.py` | Model download helper / 模型下载工具 |

## Setup / 环境配置

```bash
pip install nemo_toolkit[asr]
```

## Usage / 使用方法

```bash
python ar_asr.py --input_dir /path/to/audio --output_dir /path/to/results
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

# NVIDIA NeMo ASR

使用 NVIDIA NeMo 预训练模型进行批量 ASR 转录。包含阿拉伯语、日语、韩语、中文方言和英语方言的专用脚本。

脚本和使用方法见上方英文部分。
