# Omnilingual ASR (Meta)

ASR transcription using Meta's omnilingual-asr model built on fairseq2. LLM-series decoding requires lang_id; CTC-series does not.

---

## Scripts / 脚本

| File | Description |
|:-----|:------------|
| `omniasr.py` | Main transcription script / 主转录脚本 |
| `test_label_decode.py` | Label decode test / 标签解码测试 |

## Setup / 环境配置

```bash
# See original repo: https://github.com/facebookresearch/omnilingual-asr
conda install libsndfile
pip install fairseq2
```

## Usage / 使用方法

```bash
python omniasr.py --input_dir /path/to/audio --output_dir /path/to/results
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

# Omnilingual ASR（Meta）

使用 Meta 的 omnilingual-asr 模型（基于 fairseq2）进行 ASR 转录。LLM 系列解码需要 lang_id，CTC 系列不需要。

脚本和使用方法见上方英文部分。
