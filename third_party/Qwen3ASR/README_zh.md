# Qwen3 ASR（DashScope API）

<p align="center"><a href="README.md">🇬🇧 English</a></p>

通过 DashScope API 使用阿里 Qwen3 ASR 系列模型进行批量转录。支持 qwen3-asr-flash、qwen3-asr-1.7b 和 qwen3.5-omni-flash。

## 脚本

| 文件 | 说明 |
|:-----|:-----|
| `qwen3asr.py` | 主转录脚本 |
| `run_qwen35_cv_threaded.py` | 多线程 qwen3.5 推理 |
| `run_qwen35_omni_fleurs.py` | qwen3.5 在 FLEURS 上推理 |

## 环境配置

```bash
export DASHSCOPE_API_KEY=your_key
```

## 使用方法

```bash
python qwen3asr.py --input_dir /path/to/audio --output_dir /path/to/results
```

## 输出格式

结果应使用 `scripts/save_results.py` 保存为 GigaSpeech 风格 JSON 格式：

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="转写结果", lang="ARE")
writer.save("results/model_name.json")
```
