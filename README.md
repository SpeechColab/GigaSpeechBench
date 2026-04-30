# 🌍 Multilingual ASR Benchmark

<p align="center">
  <b>A Large-Scale Multilingual Speech Recognition Benchmark for Low-Resource Languages</b>
</p>

<p align="center">
  <a href="README_zh.md">🇨🇳 中文版</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Languages-14+-blue" alt="Languages">
  <img src="https://img.shields.io/badge/Duration-308h-green" alt="Duration">
  <img src="https://img.shields.io/badge/Segments-260K+-orange" alt="Segments">
  <img src="https://img.shields.io/badge/Models-14+-red" alt="Models">
  <img src="https://img.shields.io/badge/License-Non--Commercial-lightgrey" alt="License">
</p>

<p align="center">
  <a href="#-leaderboard">🏆 Leaderboard</a> •
  <a href="#-dataset">📦 Dataset</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-evaluation">📊 Evaluation</a> •
  <a href="#-contributing">🤝 Contributing</a>
</p>

---

## 👥 Participating Institutions

<!-- TODO: Fill in participating institutions -->

---

## 🏆 Leaderboard

> **Low-Resource Languages ASR — WER/CER (%) ↓**
>
> 📊 14 languages & dialects • ⏱ ~308 hours • 🎙 260K+ segments

<!-- Leaderboard table / image placeholder -->
<!-- TODO: Insert leaderboard image or interactive table here -->

<p align="center">
  <i>📋 Full results available in <code>data/all_results_besteff.xlsx</code></i>
</p>

### 🗺 Language Key

| Code | Language | Region |
|:-----|:---------|:-------|
| IRQ | Iraqi Arabic | Middle East |
| DZA | Algerian Arabic | North Africa |
| ARE | Emirati Arabic | Middle East |
| EGY | Egyptian Arabic | North Africa |
| MAR | Moroccan Arabic | North Africa |
| SAU | Saudi Arabic | Middle East |
| SYR | Syrian Arabic | Middle East |
| IDN | Indonesian | Southeast Asia |
| MYS | Malay | Southeast Asia |
| PHL | Filipino | Southeast Asia |
| VNM | Vietnamese | Southeast Asia |
| THA | Thai | Southeast Asia |
| JPN | Japanese | East Asia |
| KOR | Korean | East Asia |

---

## 📦 Dataset

### 📈 Overview

| Stat | Value |
|:-----|:------|
| Languages | 14 (+ 2 hard sets) |
| Total Duration | ~308 hours |
| Total Segments | 260,000+ |
| Audio Format | WAV (16kHz mono) |
| Annotation | Human-annotated transcription with speaker metadata |
| Source | YouTube, curated per-language |

### 📝 Data Format

Each audio file has a corresponding JSON annotation:

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
| `audio_name` | string | Audio identifier (also the wav filename stem) |
| `segments[].start` | float | Segment start time in seconds |
| `segments[].end` | float | Segment end time in seconds |
| `segments[].text` | string | Transcription in the source language |
| `segments[].status` | string | `valid` or `invalid` |
| `segments[].text_en` | string | English translation (optional) |
| `segments[].text_zh` | string | Chinese translation (optional) |

---

## 🚀 Quick Start

### ⚙️ Requirements

```bash
pip install kaldialign
```

### 🔄 Full Evaluation Pipeline

```bash
# Step 1: Generate reference JSON from raw annotations
python data_process/generate_ref_json.py

# Step 2: Generate hypothesis JSON from model outputs
python data_process/generate_hyp_json.py

# Step 3: Text normalization (punctuation, casing, etc.)
python data_process/normalization_single_ref.py
python data_process/normalization_single_hyp.py

# Step 4: Compute WER/CER
python scripts/compute_wer.py

# Step 5: Generate Excel report
python scripts/excel_single.py
python scripts/merge_excel.py
```

Or run the entire pipeline with one command:

```bash
bash example.sh Low-Resource-Languages
```

### ➕ Adding a New Model

Place your model output in the standard JSON format:

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

---

## 📊 Evaluation

- **WER** (Word Error Rate): For alphabetic languages (Arabic, Indonesian, Vietnamese, etc.)
- **CER** (Character Error Rate): For CJK languages (Japanese, Korean, Chinese)
- Language-specific text normalization is applied before scoring

---

## 📁 Project Structure

```
Multilingual-ASR-Benchmark/
├── data_process/          # Data preprocessing scripts
├── text_norm/             # Per-language text normalizers
├── scripts/               # Evaluation & reporting
├── third_party/           # Model integration scripts
│   ├── Azure/
│   ├── Chirp3/
│   ├── gemeni/            # Gemini ASR
│   ├── Qwen3ASR/
│   ├── whisper-large-v3/
│   └── ...
├── build_gradio/          # Gradio visualization UI
├── example.sh             # One-click pipeline
└── README.md
```

---

## 🤝 Contributing

We welcome contributions of new model results. Please:

1. Run your ASR model on our test set
2. Format output as standard JSON
3. Submit a Pull Request with the hyp JSON files

---

## 📄 License

This project is for **non-commercial research purposes only**. The audio data is sourced from publicly available content and is subject to the original content creators' licenses.

---

## 📖 Citation

If you use this benchmark in your research, please cite:

```bibtex
@misc{multilingual-asr-benchmark,
  title={Multilingual ASR Benchmark: A Large-Scale Evaluation for Low-Resource Languages},
  year={2026},
  url={https://github.com/AlexTYJ/Multilingual-ASR-Benchmark}
}
```
