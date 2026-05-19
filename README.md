<h1 align="center">🌍 GigaSpeechBench</h1>

<p align="center">
  <b>A large-scale multilingual ASR & AST benchmark (600+ hours) spanning low-resource languages, dialects, accents, and domains. The low-resource language subset includes Chinese–English–Japanese translations for speech translation (AST) evaluation.</b>
</p>

<p align="center">
  <a href="README_zh.md">🇨🇳 中文版</a>
</p>

<p align="center">
  ⭐ <b>Star this repo to stay updated!</b> Full dataset release on HuggingFace coming soon.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Languages-14+-blue" alt="Languages">
  <img src="https://img.shields.io/badge/Duration-600%2Bh-green" alt="Duration">
  <img src="https://img.shields.io/badge/Models-16+-red" alt="Models">
  <img src="https://img.shields.io/badge/License-Non--Commercial-lightgrey" alt="License">
</p>

<p align="center">
  <a href="#-call-for-contributions">📣 Call for Contributions</a> •
  <a href="#-leaderboard">🏆 Leaderboard</a> •
  <a href="#-dataset">📦 Dataset</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-evaluation">📊 Evaluation</a>
</p>

---

## 📣 Call for Contributions

**We need your help!** GigaSpeechBench covers 14+ low-resource languages and dialects, but our team lacks native speakers for many of them. The `text_norm/` module — which handles language-specific text normalization before WER/CER scoring — has significant room for improvement.

**If you are a native speaker** of any of our supported languages (Arabic dialects, Indonesian, Malay, Filipino/Tagalog, Vietnamese, Thai, Japanese, Korean), we warmly invite you to:

- 🔍 Review the normalization rules in `text_norm/{LANG}.py`
- 🐛 Report issues with incorrect normalization
- � Open an [Issue](https://github.com/AlexTYJ/GigaSpeechBench/issues) to suggest improvements for your language

We also welcome:
- 📊 New model evaluation results (use `scripts/save_results.py`)
- 🌐 Support for additional languages

---

## 📅 Timeline

> 🚀 **2026-05-04** — GitHub repository released  
> 📦 **Coming soon** — Full dataset release on HuggingFace

---

## 🏆 Leaderboard

> **ASR — WER/CER (%) ↓**


<!--
<p align="center">
  <img src="assets/low-resource-results.png" alt="ASR Performance for Low Resource Languages" width="100%">
</p>
-->

#### 🌸 East Asia (CER % ↓)

| Model | JPN | KOR | Avg |
|:------|:---:|:---:|:---:|
| Fun-Realtime-ASR | **⭐25.44** | **⭐9.92** | **⭐17.68** |
| Qwen3.5-omni-plus | 27.36 | 13.10 | 20.23 |
| Azure | 27.51 | 13.13 | 20.32 |
| ElevenLabs Scribe v2 | 29.95 | 11.81 | 20.88 |
| Chirp3 | 36.22 | 15.96 | 26.09 |
| Nvidia-Nemo | 32.31 | 22.61 | 27.46 |
| Gemini 3.0 Flash | 39.84 | 16.78 | 28.31 |
| Dolphin Base | 39.61 | 28.59 | 34.10 |
| Dolphin Small | 40.30 | 39.05 | 39.67 |
| OmniASR LLM 3B | 58.74 | 26.76 | 42.75 |
| GPT-4o Transcribe | 44.34 | 41.31 | 42.83 |

#### 🌏 Southeast Asia (WER % ↓)

| Model | IDN | MYS | PHL | VNM | THA | Avg |
|:------|:---:|:---:|:---:|:---:|:---:|:---:|
| Fun-Realtime-ASR | **⭐14.87** | **⭐25.20** | **⭐23.69** | 9.75 | **⭐10.76** | **⭐16.85** |
| Qwen3.5-omni-plus | 18.05 | 28.78 | 26.13 | 9.90 | 15.10 | 19.59 |
| Chirp3 | 19.98 | 29.04 | 28.18 | **⭐9.63** | 17.52 | 20.87 |
| ElevenLabs Scribe v2 | 22.91 | 38.52 | 27.15 | 10.52 | 13.90 | 22.60 |
| Azure | 25.50 | 35.20 | 26.08 | 10.95 | 15.66 | 22.68 |
| Gemini 3.0 Flash | 24.18 | 40.92 | 29.17 | 11.69 | 26.58 | 26.51 |
| FunASR-mlt-nano | 27.68 | 43.01 | 36.45 | 14.02 | 20.75 | 28.38 |
| Whisper | 27.40 | 46.15 | 30.88 | 18.17 | 27.02 | 29.92 |
| Qwen3-ASR-1.7B | 22.29 | 50.68 | 51.58 | 11.90 | 15.14 | 30.32 |
| Qwen3-ASR-Flash | 20.45 | 60.18 | 47.83 | 11.31 | 17.08 | 31.37 |
| Dolphin Small | 32.53 | 52.19 | 61.08 | 21.68 | 24.40 | 38.38 |
| OmniASR LLM 3B | 37.91 | 68.79 | 45.03 | 19.60 | 30.72 | 40.41 |
| Dolphin Base | 31.29 | 54.24 | 68.36 | 21.59 | 26.97 | 40.49 |
| GPT-4o Transcribe | 37.95 | 52.30 | 38.60 | 29.24 | 48.78 | 41.37 |

#### 🌍 Arabic Region (WER % ↓)

| Model | IRQ | DZA | ARE | EGY | MAR | SAU | SYR | Avg |
|:------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen3.5-omni-plus | **⭐28.54** | 47.11 | 35.15 | **⭐37.12** | **⭐51.34** | **⭐16.56** | **⭐13.76** | **⭐32.80** |
| Gemini 3.0 Flash | 36.55 | **⭐44.22** | 45.06 | 41.22 | 51.99 | 20.10 | 14.40 | 36.22 |
| Chirp3 | 35.71 | 53.11 | 42.88 | 42.71 | 52.30 | 16.76 | 24.13 | 38.23 |
| Azure | 34.61 | 51.22 | 42.82 | 47.65 | 56.64 | 20.09 | 17.74 | 38.68 |
| Qwen3-ASR-Flash | 33.21 | 57.18 | 44.24 | 48.78 | 68.51 | 19.21 | 14.41 | 40.79 |
| ElevenLabs Scribe v2 | 38.67 | 50.43 | 46.10 | 44.44 | 60.06 | 33.33 | 14.73 | 41.11 |
| OmniASR LLM 3B | 38.80 | 57.68 | 50.83 | 52.37 | 65.52 | 25.31 | 17.86 | 44.05 |
| Qwen3-ASR-1.7B | 41.27 | 63.43 | 53.22 | 59.23 | 76.65 | 25.85 | 18.50 | 48.31 |
| Nvidia-Nemo | 43.22 | 62.66 | 56.00 | 54.83 | 73.65 | 29.28 | 20.13 | 48.54 |
| GPT-4o Transcribe | 54.53 | 63.25 | **⭐26.26** | 64.23 | 71.26 | 42.38 | 31.67 | 50.51 |
| Fun-Realtime-ASR | 53.44 | 66.30 | 66.70 | 63.33 | 74.10 | 37.67 | 24.24 | 55.11 |
| Whisper | 51.04 | 72.02 | 68.41 | 69.78 | 91.89 | 32.79 | 19.12 | 57.86 |
| Dolphin Small | 62.05 | 72.44 | 75.62 | 74.70 | 75.96 | 50.91 | 30.03 | 63.10 |
| Dolphin Base | 65.20 | 78.26 | 82.87 | 85.31 | 89.74 | 52.35 | 38.12 | 70.26 |

> **Note**: ⭐ = SOTA (best result for that language), **bold** = SOTA, `-` = not evaluated. JPN and KOR use **CER** (Character Error Rate) while all other languages use **WER** (Word Error Rate). Models are ordered roughly by average performance across all evaluated languages (best → worst).

### 🗺 Language Key

| Code | Language | Region | Duration |
|:-----|:---------|:-------|:---------|
| IRQ | Iraqi Arabic | Arab Region | 20.37h |
| DZA | Algerian Arabic | Arab Region | 19.96h |
| ARE | Emirati Arabic | Arab Region | 19.33h |
| EGY | Egyptian Arabic | Arab Region | 20.16h |
| MAR | Moroccan Arabic | Arab Region | 19.96h |
| SAU | Saudi Arabic | Arab Region | 20.30h |
| SYR | Syrian Arabic | Arab Region | 20.23h |
| IDN | Indonesian | Southeast Asia | 21.18h |
| MYS | Malay | Southeast Asia | 18.90h |
| PHL | Filipino (Tagalog) | Southeast Asia | 21.46h |
| VNM | Vietnamese | Southeast Asia | 21.27h |
| THA | Thai | Southeast Asia | 20.89h |
| JPN | Japanese | East Asia | 20.00h |
| KOR | Korean | East Asia | 20.00h |

### 🗣 English Accents

| Code | Language | Duration |
|:-----|:---------|:---------|
| CHN-EN | Chinese-accented English | 9.43h |
| IDN-EN | Indonesian-accented English | 10.41h |
| JPN-EN | Japanese-accented English | 3.77h |
| PHL-EN | Filipino-accented English | 10.75h |
| SCT-EN | Scottish-accented English | 4.44h |
| SGP-EN | Singaporean English | 10.63h |

### 🀄 Chinese Dialects

| Code | Language | Duration |
|:-----|:---------|:---------|
| XIANG | Xiang (湘语) | 10.63h |
| JIN | Jin (晋语) | 7.38h |
| MIN | Min (闽语) | 10.75h |
| YUE | Yue (粤语) | 11.34h |
| WU | Wu (吴语) | 9.75h |

### 🏭 Chinese Vertical Domains

| Code | Domain | Duration |
|:-----|:-------|:---------|
| AGR-CH | Agriculture | 6.69h |
| AIT-CH | AI & Technology | 10.32h |
| ART-CH | Art | 9.85h |
| BIO-CH | Biology | 9.68h |
| ECM-CH | E-Commerce | 8.88h |
| ENG-CH | Engineering | 10.76h |
| ENT-CH | Entertainment | 8.14h |
| FIN-CH | Finance | 10.64h |
| HUM-CH | Humanities | 10.28h |
| LAW-CH | Law | 9.83h |
| MED-CH | Medicine | 9.68h |
| MIL-CH | Military | 10.33h |

### 🏭 English Vertical Domains

| Code | Domain | Duration |
|:-----|:-------|:---------|
| AGR-EN | Agriculture | 8.82h |
| AIT-EN | AI & Technology | 3.71h |
| ART-EN | Art | 7.78h |
| BIO-EN | Biology | 10.50h |
| ECM-EN | E-Commerce | 10.57h |
| ENG-EN | Engineering | 8.60h |
| ENT-EN | Entertainment | 9.53h |
| FIN-EN | Finance | 10.20h |
| HUM-EN | Humanities | 2.96h |
| LAW-EN | Law | 2.08h |
| MED-EN | Medicine | 8.40h |
| MIL-EN | Military | 9.97h |

---

## 📦 Dataset

### 📈 Languages Overview

| Stat | Value |
|:-----|:------|
| Languages | 16 |
| Total Duration | ~600+ hours |
| Audio Format | WAV (16kHz mono) |
| Annotation | Human-annotated transcription with speaker metadata |

### 📝 Data Format (GigaSpeech-style)

Each language has a `metadata.json` following the GigaSpeech format:

```json
{
  "audios": [
    {
      "aid": "ARE#UCIJXOvggjKtCagMfxvcCzAA#RVSrDuhYDZA#raw",
      "duration": 228.195,
      "segments": [
        {
          "sid": "ARE#UCIJXOvggjKtCagMfxvcCzAA#RVSrDuhYDZA#raw_1",
          "begin_time": 165.613,
          "end_time": 169.92,
          "text": "ياسيدي هذي مشكلة يعني طويلة، الواقع هو شوف احنا.",
          "speaker": "Speaker1",
          "gender": "Male"
        }
      ]
    }
  ]
}
```

Model results also follow the same GigaSpeech-style format:

```json
{
  "audios": [
    {
      "aid": "ARE#UCIJXOvggjKtCagMfxvcCzAA#RVSrDuhYDZA#raw",
      "segments": [
        {
          "sid": "ARE#...#raw_1",
          "begin_time": 165.613,
          "end_time": 169.92,
          "text": "model transcription here",
          "lang": "ARE"
        }
      ]
    }
  ]
}
```

### 📂 Directory Layout

```
dataset/
├── data/{LANG}/
│   ├── metadata.json       # GigaSpeech-style ref annotations
│   ├── audio/*.wav          # Audio files
│   └── md5                  # Audio checksums
└── results/
    ├── azure.json           # Model hypotheses (GigaSpeech-style)
    ├── chirp3.json
    └── ...
```

---

## 🚀 Quick Start

### ⚙️ Requirements

```bash
pip install -r requirements.txt
```

### 🔄 Run Evaluation

```bash
bash example.sh /path/to/dataset
```

This runs the full 4-step pipeline:
1. **Convert** — Parse GigaSpeech-style JSON into flat format
2. **Normalize** — Language-specific text normalization (parallel, cached)
3. **Evaluate** — Compute WER/CER with segment alignment
4. **Report** — Generate Excel with per-model, per-language results

Options:
```bash
bash example.sh /path/to/dataset --force         # Overwrite all outputs
bash example.sh /path/to/dataset --workers 8     # Parallel normalization
```

### ➕ Adding a New Model

Use the helper to generate correctly formatted results:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
for segment in my_results:
    writer.add(
        audio_name="ARE#UC...#raw",
        begin_time=0.0,
        end_time=5.0,
        text="transcribed text",
        lang="ARE"
    )
writer.save("results/my_model.json")
```

Then re-run the pipeline.

---

## 📊 Evaluation

- **WER** (Word Error Rate): For alphabetic languages (Arabic, Indonesian, Vietnamese, etc.)
- **CER** (Character Error Rate): For CJK languages (Japanese, Korean, Thai)
- Language-specific text normalization is applied before scoring
- Segment matching uses (audio_name, start, end) with 0.1s tolerance

---

## 📁 Project Structure

```
GigaSpeechBench/
├── example.sh              # One-command evaluation pipeline
├── requirements.txt        # Python dependencies
├── data_process/
│   ├── convert_data.py     # GigaSpeech JSON → flat format
│   └── normalize.py        # Parallel text normalization with caching
├── scripts/
│   ├── compute_wer_single.py  # WER/CER computation
│   ├── excel_single.py     # Per-module Excel report
│   ├── merge_excel.py      # Merge all results into one Excel
│   ├── save_results.py     # Helper for model output formatting
│   └── check.py            # Submission format validator
├── text_norm/              # Per-language text normalizers (contributions welcome!)
└── third_party/            # Model integration scripts
    ├── Azure/
    ├── Chirp3/
    ├── Qwen3ASR/
    ├── whisper-large-v3/
    └── ...
```

---

## 📄 License

This project is for **non-commercial research purposes only**. The audio data is sourced from publicly available content and is subject to the original content creators' licenses.

