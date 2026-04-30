# 🌍 Multilingual ASR Benchmark

<p align="center">
  <b>A Large-Scale Multilingual Speech Recognition Benchmark for Low-Resource Languages</b><br>
  <b>面向低资源语言的大规模多语种语音识别基准</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Languages-14+-blue" alt="Languages">
  <img src="https://img.shields.io/badge/Duration-308h-green" alt="Duration">
  <img src="https://img.shields.io/badge/Segments-260K+-orange" alt="Segments">
  <img src="https://img.shields.io/badge/Models-14+-red" alt="Models">
  <img src="https://img.shields.io/badge/License-Non--Commercial-lightgrey" alt="License">
</p>

<p align="center">
  <a href="#-leaderboard--排行榜">🏆 Leaderboard</a> •
  <a href="#-dataset--数据集">📦 Dataset</a> •
  <a href="#-quick-start--快速开始">🚀 Quick Start</a> •
  <a href="#-evaluation--评测">📊 Evaluation</a> •
  <a href="#-contributing--贡献">🤝 Contributing</a>
</p>

---

## 👥 Participating Institutions / 参与机构

<!-- TODO: Fill in participating institutions / 请补充参与机构 -->

---

## 🏆 Leaderboard / 排行榜

> **Low-Resource Languages ASR — WER/CER (%) ↓**
>
> 低资源语言 ASR — 词/字错误率 (%) ↓
>
> 📊 14 languages & dialects • ⏱ ~308 hours • 🎙 260K+ segments

<!-- Leaderboard table / image placeholder -->
<!-- TODO: Insert leaderboard image or interactive table here -->
<!-- 排行榜表格/图片占位 -->

<p align="center">
  <i>📋 Full results available in <code>data/all_results_besteff.xlsx</code></i><br>
  <i>📋 完整结果请查看 <code>data/all_results_besteff.xlsx</code></i>
</p>

### 🗺 Language Key / 语言代码

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

## 📦 Dataset / 数据集

### 📈 Overview / 概览

| Stat | Value |
|:-----|:------|
| Languages | 14 (+ 2 hard sets) |
| Total Duration | ~308 hours |
| Total Segments | 260,000+ |
| Audio Format | WAV (16kHz mono) |
| Annotation | Human-annotated transcription with speaker metadata |
| Source | YouTube, curated per-language |

### 📝 Data Format / 数据格式

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

## 🚀 Quick Start / 快速开始

### ⚙️ Requirements / 环境依赖

```bash
pip install kaldialign
```

### 🔄 Full Evaluation Pipeline / 完整评测流程

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

### ➕ Adding a New Model / 接入新模型

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

## 📊 Evaluation / 评测

### 🎯 ASR Evaluation / 语音识别评测

- **WER** (Word Error Rate): For alphabetic languages (Arabic, Indonesian, Vietnamese, etc.)
- **CER** (Character Error Rate): For CJK languages (Japanese, Korean, Chinese)
- Text normalization is applied per-language before scoring

### 🌐 Speech Translation Evaluation / 语音翻译评测

Supports BLEU, chrF++, TER, and neural metrics (COMET):

```bash
# Basic metrics (BLEU / chrF / TER)
python scripts/eval_st_pipeline.py

# With COMET (requires OpenSTBench)
pip install "OpenSTBench[comet]"
python third_party/gemini_translation/eval_st_openstbench.py --results_dir data/st_results --use_comet
```

---

## 📁 Project Structure / 项目结构

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

## 🤝 Contributing / 贡献

We welcome contributions of new model results. Please:

欢迎贡献新模型的评测结果，请：

1. Run your ASR model on our test set / 在测试集上运行模型
2. Format output as standard JSON / 按标准格式输出
3. Submit a Pull Request with the hyp JSON files / 提交包含 hyp JSON 的 PR

---

## 📄 License / 许可

This project is for **non-commercial research purposes only**. The audio data is sourced from publicly available content and is subject to the original content creators' licenses.

本项目仅供**非商业研究用途**。音频数据来源于公开内容，受原始内容创作者许可协议约束。

---

## 📖 Citation / 引用

If you use this benchmark in your research, please cite:

```bibtex
@misc{multilingual-asr-benchmark,
  title={Multilingual ASR Benchmark: A Large-Scale Evaluation for Low-Resource Languages},
  year={2026},
  url={https://github.com/AlexTYJ/Multilingual-ASR-Benchmark}
}
```
