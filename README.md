# Multilingual ASR Benchmark

<p align="center">
  <b>A Large-Scale Multilingual Speech Recognition Benchmark for Low-Resource Languages</b><br>
  <b>面向低资源语言的大规模多语种语音识别基准</b>
</p>

<p align="center">
  <a href="#leaderboard">Leaderboard</a> •
  <a href="#dataset">Dataset</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#evaluation">Evaluation</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## Participating Institutions / 参与机构

- **Shanghai Jiao Tong University (SJTU)** 上海交通大学
- **Microsoft** 微软

---

## Leaderboard

> **Low-Resource Languages ASR — WER/CER (%) ↓**
>
> 低资源语言 ASR — 词/字错误率 (%) ↓
>
> 14 languages/dialects • ~308 hours • 260K+ segments

| Model | IRQ | DZA | ARE | EGY | MAR | SAU | SYR | IDN | MYS | PHL | PHL\_EN | PHL\_noEN | VNM | THA | JPN | JPN\_hard | KOR | KOR\_hard | AVG |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Duration | 20.4h | 20.0h | 19.3h | 20.2h | 20.0h | 20.3h | 20.2h | 21.2h | 18.9h | 21.5h | 12.1h | 9.4h | 21.3h | 20.9h | 20.1h | 1.1h | 20.3h | 1.6h | |
| Azure | 34.74 | 51.37 | 42.87 | 47.70 | 56.69 | 20.18 | 17.77 | 25.72 | 35.47 | 26.19 | 25.08 | 27.76 | 11.00 | 15.77 | 11.01 | 35.22 | 7.04 | 22.93 | **28.58** |
| Chirp3 | 35.78 | 53.20 | 42.92 | 42.79 | 52.34 | 16.81 | 24.14 | 20.27 | 29.31 | 28.29 | 26.15 | 31.33 | 9.68 | 17.55 | 11.17 | 31.98 | 6.96 | 19.68 | **27.80** |
| ElevenLabs Scribe v2 | 38.86 | 50.62 | 46.21 | 44.54 | 60.11 | 33.46 | 14.76 | 23.39 | 38.95 | 27.34 | 24.22 | 31.76 | 10.62 | 14.02 | 11.84 | 33.46 | 5.91 | 18.69 | **29.38** |
| Gemini 3.0 Flash | 38.68 | 44.49 | 45.81 | 41.87 | 52.07 | 21.43 | 14.66 | 28.18 | 45.21 | 30.32 | 27.13 | 34.87 | 12.61 | 28.62 | 17.05 | 42.89 | 10.00 | 22.56 | **31.03** |
| GPT-4o Transcribe | 54.60 | 63.34 | 26.28 | 64.29 | 71.29 | 42.46 | 31.68 | 38.27 | 52.55 | 38.70 | 39.91 | 36.99 | 29.30 | 48.79 | 24.46 | 45.36 | 31.37 | 38.23 | **43.22** |
| Qwen3-ASR-Flash | 33.29 | 57.28 | 44.28 | 48.86 | 68.53 | 19.30 | 14.42 | 20.75 | 60.57 | 47.98 | 42.99 | 55.07 | 11.36 | 17.11 | 9.95 | 32.46 | 10.83 | 18.96 | **34.11** |
| Qwen3-ASR-1.7B | 41.47 | 63.54 | 53.32 | 59.30 | 76.68 | 25.99 | 18.52 | 22.80 | 51.04 | 51.70 | 47.04 | 58.33 | 12.00 | 15.30 | 11.30 | 44.52 | 7.13 | 20.36 | **37.80** |
| NVIDIA NeMo | 43.39 | 62.78 | 56.08 | 54.91 | 73.68 | 29.40 | 20.15 | - | - | - | - | - | - | - | 15.31 | 33.91 | 14.55 | 40.65 | **40.44** |
| Whisper Large v3 | 51.14 | 72.15 | 68.46 | 69.86 | 91.91 | 32.89 | 19.14 | 27.84 | 46.58 | 31.00 | 28.42 | 34.68 | 18.37 | 27.06 | 15.13 | 42.43 | 11.14 | 31.59 | **39.99** |
| FunASR v1.5 | 53.52 | 66.41 | 66.74 | 63.37 | 74.13 | 37.72 | 24.26 | 21.42 | 33.98 | 28.08 | 25.78 | 31.40 | 12.19 | 17.67 | 10.55 | - | 6.89 | - | **35.88** |
| FunASR-MLT-Nano | - | - | - | - | - | - | 33.67 | 27.90 | 43.35 | 36.59 | 35.05 | 38.78 | 14.09 | 20.87 | 10.14 | 33.01 | 9.75 | 24.32 | **27.29** |
| Meta OmniASR 3B | 39.06 | 62.47 | 56.34 | 52.46 | 68.48 | 25.48 | 17.89 | 38.48 | 69.16 | 45.20 | 42.53 | 49.00 | 19.71 | 30.93 | 32.88 | 71.34 | 15.38 | 55.81 | **44.03** |
| Dolphin Small | 62.24 | 72.69 | 75.71 | 74.80 | 76.02 | 51.09 | 30.06 | 33.50 | 53.13 | 61.28 | 63.99 | 57.42 | 21.82 | 24.63 | 22.35 | 45.57 | 29.48 | 43.25 | **49.95** |
| Dolphin Base | 65.64 | 78.56 | 83.06 | 85.48 | 89.83 | 52.60 | 38.16 | 32.43 | 55.30 | 68.60 | 69.85 | 66.81 | 21.76 | 27.28 | 20.48 | 43.81 | 19.67 | 41.71 | **53.39** |
| **Best** | **33.29** | **44.49** | **26.28** | **41.87** | **52.07** | **16.81** | **14.42** | **20.27** | **29.31** | **26.19** | **24.22** | **27.76** | **9.68** | **14.02** | **9.95** | **31.98** | **5.91** | **18.69** | **27.29** |

### Language Key / 语言代码

| Code | Language / 语言 | Region / 地区 |
|:-----|:----------------|:-------------|
| IRQ | Iraqi Arabic / 伊拉克阿拉伯语 | Middle East |
| DZA | Algerian Arabic / 阿尔及利亚阿拉伯语 | North Africa |
| ARE | Emirati Arabic / 阿联酋阿拉伯语 | Middle East |
| EGY | Egyptian Arabic / 埃及阿拉伯语 | North Africa |
| MAR | Moroccan Arabic / 摩洛哥阿拉伯语 | North Africa |
| SAU | Saudi Arabic / 沙特阿拉伯语 | Middle East |
| SYR | Syrian Arabic / 叙利亚阿拉伯语 | Middle East |
| IDN | Indonesian / 印度尼西亚语 | Southeast Asia |
| MYS | Malay / 马来语 | Southeast Asia |
| PHL | Filipino / 菲律宾语 | Southeast Asia |
| VNM | Vietnamese / 越南语 | Southeast Asia |
| THA | Thai / 泰语 | Southeast Asia |
| JPN | Japanese / 日语 | East Asia |
| KOR | Korean / 韩语 | East Asia |

---

## Dataset

### Overview / 概览

| Stat | Value |
|:-----|:------|
| Languages | 14 (+ 2 hard sets) |
| Total Duration | ~308 hours |
| Total Segments | 260,000+ |
| Audio Format | WAV (16kHz mono) |
| Annotation | Human-annotated transcription with speaker metadata |
| Source | YouTube, curated per-language |

### Data Format / 数据格式

Each audio file has a corresponding JSON annotation:

每个音频文件对应一个 JSON 标注：

```json
{
  "audio_name": "ARE#UCIJXOvggjKtCagMfxvcCzAA#RVSrDuhYDZA#raw",
  "segments": [
    {
      "start": 165.613,
      "end": 169.92,
      "text": "ياسيدي هذي مشكلة يعني طويلة، الواقع هو شوف احنا.",
      "status": "valid",
      "age_group": "Adults",
      "gender": "Male",
      "emotion": "Neutral",
      "speaker": "Speaker1",
      "index": 1,
      "text_en": "Sir, this is indeed a complex problem...",
      "text_zh": "先生，这个问题确实很复杂..."
    }
  ]
}
```

| Field | Type | Description |
|:------|:-----|:------------|
| `audio_name` | string | Audio identifier (also the wav filename stem) / 音频标识符 |
| `segments[].start` | float | Segment start time in seconds / 片段起始时间（秒） |
| `segments[].end` | float | Segment end time in seconds / 片段结束时间（秒） |
| `segments[].text` | string | Transcription / 转写文本 |
| `segments[].status` | string | `valid` or `invalid` / 有效或无效 |
| `segments[].text_en` | string | English translation (optional) / 英文翻译 |
| `segments[].text_zh` | string | Chinese translation (optional) / 中文翻译 |

---

## Quick Start

### Requirements / 环境依赖

```bash
pip install kaldialign
```

### Full Evaluation Pipeline / 完整评测流程

```bash
# Step 1: Generate reference JSON from raw annotations
# 步骤1：从原始标注生成标准 ref JSON
python data_process/generate_ref_json.py

# Step 2: Generate hypothesis JSON from model outputs
# 步骤2：从模型输出生成标准 hyp JSON
python data_process/generate_hyp_json.py

# Step 3: Text normalization (punctuation, casing, etc.)
# 步骤3：文本归一化（标点、大小写等）
python data_process/normalization_single_ref.py
python data_process/normalization_single_hyp.py

# Step 4: Compute WER/CER
# 步骤4：计算 WER/CER
python scripts/compute_wer.py

# Step 5: Generate Excel report
# 步骤5：生成 Excel 报告
python scripts/excel_single.py
python scripts/merge_excel.py
```

Or run the entire pipeline with one command:

或一键运行完整流程：

```bash
bash example.sh Low-Resource-Languages
```

### Adding a New Model / 接入新模型

Place your model output in the standard JSON format:

将模型输出整理为标准 JSON 格式：

```json
[
  {
    "audio_name": "ARE#UCIJXOvggjKtCagMfxvcCzAA#RVSrDuhYDZA#raw",
    "text": "your transcription here",
    "model": "your-model-name",
    "start": 165.613,
    "end": 169.92
  }
]
```

Save as `{LANG}_{MODEL}.json` in the hyp directory, then re-run the pipeline.

保存为 `{LANG}_{MODEL}.json` 到 hyp 目录，然后重新运行流程。

---

## Evaluation

### ASR Evaluation / 语音识别评测

- **WER** (Word Error Rate): For alphabetic languages (Arabic, Indonesian, Vietnamese, etc.)
- **CER** (Character Error Rate): For CJK languages (Japanese, Korean, Chinese)
- Text normalization is applied per-language before scoring

### Speech Translation Evaluation / 语音翻译评测

Supports BLEU, chrF++, TER, and neural metrics (COMET):

```bash
# Basic metrics (BLEU / chrF / TER)
python scripts/eval_st_pipeline.py

# With COMET (requires OpenSTBench)
pip install "OpenSTBench[comet]"
python third_party/gemini_translation/eval_st_openstbench.py --results_dir data/st_results --use_comet
```

---

## Project Structure / 项目结构

```
Multilingual-ASR-Benchmark/
├── data_process/          # Data preprocessing scripts / 数据预处理脚本
├── text_norm/             # Per-language text normalizers / 各语言文本归一化
├── scripts/               # Evaluation & reporting / 评测与报告生成
├── third_party/           # Model integration scripts / 模型接入脚本
│   ├── Azure/
│   ├── Chirp3/
│   ├── gemeni/            # Gemini ASR
│   ├── gemini_translation/# Gemini Speech Translation
│   ├── Qwen3ASR/
│   ├── Qwen3LiveTranslate/
│   ├── whisper-large-v3/
│   └── ...
├── build_gradio/          # Gradio visualization UI / 可视化界面
├── example.sh             # One-click pipeline / 一键运行脚本
└── README.md
```

---

## Contributing

We welcome contributions of new model results. Please:

欢迎贡献新模型的评测结果，请：

1. Run your ASR model on our test set / 在测试集上运行模型
2. Format output as standard JSON / 按标准格式输出
3. Submit a Pull Request with the hyp JSON files / 提交包含 hyp JSON 的 PR

---

## License

This project is for **non-commercial research purposes only**. The audio data is sourced from publicly available content and is subject to the original content creators' licenses.

本项目仅供**非商业研究用途**。音频数据来源于公开内容，受原始内容创作者许可协议约束。

---

## Citation

If you use this benchmark in your research, please cite:

```bibtex
@misc{multilingual-asr-benchmark,
  title={Multilingual ASR Benchmark: A Large-Scale Evaluation for Low-Resource Languages},
  year={2026},
  url={https://github.com/AlexTYJ/Multilingual-ASR-Benchmark}
}
```
