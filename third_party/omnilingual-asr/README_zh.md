# Omnilingual ASR（Meta）

<p align="center"><a href="README.md">🇬🇧 English</a></p>

使用 Meta 的 omnilingual-asr 模型（基于 fairseq2）进行 ASR 转录。LLM 系列解码需要 lang_id，CTC 系列不需要。

## 脚本

| 文件 | 说明 |
|:-----|:-----|
| `omniasr.py` | 主转录脚本 |
| `test_label_decode.py` | 标签解码测试 |

## 环境配置

```bash
# See: https://github.com/facebookresearch/omnilingual-asr
conda install libsndfile
pip install fairseq2
```

## 使用方法

```bash
python omniasr.py --input_dir /path/to/audio --output_dir /path/to/results
```

## 输出格式

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="转写结果", lang="ARE")
writer.save("results/model_name.json")
```
