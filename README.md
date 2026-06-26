# 🌍 GigaSpeechBench

<p align="center">
  <b>A Real-World Multilingual Speech-to-Text Benchmark</b>
</p>

<p align="center">
  <a href="README_zh.md">🇨🇳 中文版</a>
</p>

---

## 🏆 Leaderboard

> **WER/CER (%) ↓ — Lower is better. Duration > 0.5s filter applied.**

#### 🌸 Low-Resource — East Asian (CER %)

| Model | AVG(%) | JPN | KOR |
|:---|:---:|:---:|:---:|
| 🥇 FUNASR-REALTIME | 17.68 | 25.44 | 9.92 |
| 🥈 QWEN3.5-OMNI-PLUS | 20.23 | 27.36 | 13.10 |
| 🥉 AZURE | 20.32 | 27.51 | 13.13 |
| ELEVENLABS-SCRIBE-V2 | 20.88 | 29.95 | 11.81 |
| QWEN3-ASR-1.7B | 22.34 | 31.77 | 12.90 |
| FUNASR-MLT-NANO | 22.80 | 29.03 | 16.57 |
| QWEN3-ASR-FLASH | 22.96 | 28.40 | 17.52 |
| CHIRP-3 | 26.09 | 36.22 | 15.96 |
| GEMINI-3.0-FLASH | 28.31 | 39.84 | 16.78 |
| WHISPER-LARGE-V3 | 28.91 | 39.28 | 18.53 |
| NVIDIA-NEMO | 32.31 | 32.31 | - |
| DOLPHIN-BASE | 34.10 | 39.61 | 28.59 |
| DOLPHIN-SMALL | 39.67 | 40.30 | 39.05 |
| META-OMNIASR-3B | 42.75 | 58.74 | 26.76 |
| GPT-4O-TRANSCRIBE | 42.83 | 44.34 | 41.31 |

#### 🌏 Low-Resource — Southeast Asian (WER %)

| Model | AVG(%) | IDN | MYS | PHL | THA | VNM |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🥇 FUNASR-REALTIME | 16.85 | 14.87 | 25.20 | 23.69 | 10.76 | 9.75 |
| 🥈 QWEN3.5-OMNI-PLUS | 19.61 | 18.05 | 28.78 | 26.21 | 15.10 | 9.90 |
| 🥉 CHIRP-3 | 20.87 | 19.98 | 29.04 | 28.18 | 17.52 | 9.63 |
| ELEVENLABS-SCRIBE-V2 | 22.60 | 22.91 | 38.52 | 27.15 | 13.90 | 10.52 |
| AZURE | 22.68 | 25.50 | 35.20 | 26.08 | 15.66 | 10.95 |
| GEMINI-3.0-FLASH | 26.51 | 24.18 | 40.92 | 29.17 | 26.58 | 11.69 |
| FUNASR-MLT-NANO | 28.38 | 27.68 | 43.01 | 36.45 | 20.75 | 14.02 |
| WHISPER-LARGE-V3 | 29.92 | 27.40 | 46.15 | 30.88 | 27.02 | 18.17 |
| QWEN3-ASR-1.7B | 30.32 | 22.29 | 50.68 | 51.58 | 15.14 | 11.90 |
| QWEN3-ASR-FLASH | 31.37 | 20.45 | 60.18 | 47.83 | 17.08 | 11.31 |
| DOLPHIN-SMALL | 38.38 | 32.53 | 52.19 | 61.08 | 24.40 | 21.68 |
| META-OMNIASR-3B | 40.41 | 37.91 | 68.79 | 45.03 | 30.72 | 19.60 |
| DOLPHIN-BASE | 40.49 | 31.29 | 54.24 | 68.36 | 26.97 | 21.59 |
| GPT-4O-TRANSCRIBE | 41.37 | 37.95 | 52.30 | 38.60 | 48.78 | 29.24 |

#### 🌍 Low-Resource — Arabic (WER %)

| Model | AVG(%) | ARE | DZA | EGY | IRQ | MAR | SAU | SYR |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🥇 QWEN3.5-OMNI-PLUS | 32.80 | 35.15 | 47.11 | 37.12 | 28.54 | 51.34 | 16.56 | 13.76 |
| 🥈 GEMINI-3.0-FLASH | 36.22 | 45.06 | 44.22 | 41.22 | 36.55 | 51.99 | 20.10 | 14.40 |
| 🥉 CHIRP-3 | 38.23 | 42.88 | 53.11 | 42.71 | 35.71 | 52.30 | 16.76 | 24.13 |
| AZURE | 38.68 | 42.82 | 51.22 | 47.65 | 34.61 | 56.64 | 20.09 | 17.74 |
| QWEN3-ASR-FLASH | 40.79 | 44.24 | 57.18 | 48.78 | 33.21 | 68.51 | 19.21 | 14.41 |
| ELEVENLABS-SCRIBE-V2 | 41.11 | 46.10 | 50.43 | 44.44 | 38.67 | 60.06 | 33.33 | 14.73 |
| META-OMNIASR-3B | 44.05 | 50.83 | 57.68 | 52.37 | 38.80 | 65.52 | 25.31 | 17.86 |
| DEEPGRAM-NOVA-3 | 46.56 | 52.06 | 57.90 | 52.77 | 47.54 | 60.00 | 25.02 | 30.61 |
| QWEN3-ASR-1.7B | 48.31 | 53.22 | 63.43 | 59.23 | 41.27 | 76.65 | 25.85 | 18.50 |
| NVIDIA-NEMO | 48.54 | 56.00 | 62.66 | 54.83 | 43.22 | 73.65 | 29.28 | 20.13 |
| GPT-4O-TRANSCRIBE | 50.50 | 26.26 | 63.14 | 64.23 | 54.53 | 71.26 | 42.38 | 31.67 |
| FUNASR-REALTIME | 55.11 | 66.70 | 66.30 | 63.33 | 53.44 | 74.10 | 37.67 | 24.24 |
| WHISPER-LARGE-V3 | 57.86 | 68.41 | 72.02 | 69.78 | 51.04 | 91.89 | 32.79 | 19.12 |
| DOLPHIN-SMALL | 63.10 | 75.62 | 72.44 | 74.70 | 62.05 | 75.96 | 50.91 | 30.03 |
| DOLPHIN-BASE | 70.26 | 82.87 | 78.26 | 85.31 | 65.20 | 89.74 | 52.35 | 38.12 |

#### 🗣️ CH-EN Dialects — Chinese Dialects (CER %)

| Model | AVG(%) | GAN | JIN | MIN | WU | XIANG | YUE |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🥇 FUNASR-REALTIME | 22.79 | 43.20 | 22.83 | 27.72 | 16.96 | 19.92 | 6.13 |
| 🥈 QWEN3.5-OMNI-PLUS | 27.22 | 45.18 | 24.19 | 39.85 | 24.64 | 21.52 | 7.94 |
| 🥉 SEEDASR | 29.41 | 53.77 | 23.89 | 33.99 | 32.11 | 22.41 | 10.30 |
| BIGASR | 29.74 | 53.63 | 23.81 | 36.85 | 31.28 | 22.31 | 10.54 |
| QWEN3-ASR-1.7B | 31.74 | 49.48 | 27.62 | 56.98 | 24.20 | 25.01 | 7.13 |
| QWEN3-ASR-FLASH | 34.92 | 47.32 | 31.68 | 59.60 | 31.93 | 27.38 | 11.63 |
| FUNASR-MLT-NANO | 36.43 | 54.77 | 28.09 | 68.87 | 29.21 | 28.96 | 8.66 |
| DOLPHIN-SMALL | 39.91 | 60.60 | 32.67 | 59.45 | 25.77 | 37.08 | 23.86 |
| AZURE | 41.80 | 58.37 | 36.48 | 67.20 | 33.70 | 43.26 | 11.77 |
| DOLPHIN-BASE | 47.39 | 65.21 | 40.13 | 68.14 | 32.45 | 49.70 | 28.70 |
| ELEVENLABS-SCRIBE-V2 | 56.08 | 68.39 | 44.86 | 71.41 | 65.45 | 54.27 | 32.09 |
| WHISPER-LARGE-V3 | 60.45 | 66.13 | 53.78 | 69.14 | 73.32 | 60.58 | 39.75 |
| GPT-4O-TRANSCRIBE | 62.15 | 74.33 | 63.48 | 69.95 | 74.59 | 71.26 | 19.29 |
| META-OMNIASR-3B | 65.29 | 65.79 | 50.98 | 90.17 | 73.68 | 62.77 | 48.36 |
| GEMINI-3.0-FLASH | 70.38 | 73.42 | 61.23 | 74.87 | 72.35 | 116.02 | 24.39 |
| CHIRP-3 | 70.77 | 71.06 | 59.38 | 89.34 | 85.23 | 71.88 | 47.70 |
| NVIDIA-NEMO | 87.66 | 83.69 | 80.16 | 94.74 | 86.42 | 85.49 | 95.44 |

#### 🗣️ CH-EN Dialects — English Accents (WER %)

| Model | AVG(%) | CHN-EN | IDN-EN | JPN-EN | PHL-EN | SCT-EN | SGP-EN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🥇 QWEN3.5-OMNI-PLUS | 14.05 | 12.98 | 7.21 | 15.67 | 11.73 | 24.27 | 12.47 |
| 🥈 FUNASR-REALTIME | 14.40 | 13.27 | 7.70 | 15.25 | 11.10 | 26.60 | 12.45 |
| 🥉 QWEN3-ASR-1.7B | 15.12 | 14.62 | 7.04 | 21.52 | 10.81 | 24.29 | 12.44 |
| WHISPER-LARGE-V3 | 16.28 | 17.28 | 7.91 | 17.55 | 13.68 | 27.24 | 14.02 |
| QWEN3-ASR-FLASH | 16.49 | 16.67 | 11.66 | 20.23 | 14.22 | 23.68 | 12.49 |
| CHIRP-3 | 17.23 | 16.76 | 8.11 | 18.69 | 11.96 | 31.32 | 16.56 |
| SEEDASR | 18.96 | 14.09 | 9.21 | 24.79 | 14.00 | 35.82 | 15.86 |
| BIGASR | 18.97 | 14.13 | 9.22 | 24.81 | 13.99 | 35.83 | 15.86 |
| GEMINI-3.0-FLASH | 20.99 | 20.64 | 8.31 | 30.43 | 15.79 | 34.43 | 16.34 |
| AZURE | 21.22 | 17.35 | 33.00 | 21.48 | 12.95 | 28.22 | 14.34 |
| ELEVENLABS-SCRIBE-V2 | 21.89 | 18.69 | 11.76 | 25.60 | 20.13 | 36.44 | 18.75 |
| NVIDIA-NEMO | 24.09 | 24.38 | 10.56 | 29.25 | 21.29 | 41.64 | 17.45 |
| FUNASR-MLT-NANO | 26.77 | 17.84 | 8.51 | 72.09 | 14.00 | 33.92 | 14.28 |
| GPT-4O-TRANSCRIBE | 39.88 | 66.12 | 17.12 | 38.57 | 38.04 | 43.57 | 35.85 |
| META-OMNIASR-3B | 41.01 | 37.11 | 21.67 | 44.21 | 44.65 | 54.22 | 44.18 |

#### 🏢 Vertical Domain — Chinese B-CER (%) [Hotword]

| Model | AVG(%) | AGR-CH | AIT-CH | ART-CH | BIO-CH | ECM-CH | ENG-CH | ENT-CH | FIN-CH | HUM-CH | LAW-CH | MED-CH | MIL-CH |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🥇 FUNASR-REALTIME | 10.91 | 6.11 | 15.75 | 9.03 | 14.07 | 22.54 | 9.87 | 20.21 | 2.45 | 10.56 | 9.20 | 8.74 | 2.41 |
| 🥈 QWEN3.5-OMNI-PLUS | 11.89 | 8.70 | 18.09 | 9.36 | 14.10 | 22.79 | 12.51 | 20.52 | 2.95 | 10.99 | 9.85 | 9.74 | 3.08 |
| 🥉 SEEDASR | 14.79 | 12.71 | 20.10 | 11.94 | 19.81 | 23.09 | 17.33 | 22.08 | 4.55 | 15.89 | 10.63 | 14.26 | 5.10 |
| BIGASR | 14.93 | 12.88 | 20.26 | 12.01 | 20.50 | 23.09 | 17.26 | 22.46 | 4.61 | 15.89 | 10.72 | 14.42 | 5.05 |
| QWEN3-ASR-FLASH | 17.56 | 15.55 | 26.75 | 17.95 | 20.02 | 27.78 | 15.78 | 27.89 | 4.69 | 14.98 | 16.06 | 15.54 | 7.68 |
| QWEN3-ASR-1.7B | 18.63 | 20.48 | 23.28 | 14.57 | 19.47 | 30.28 | 19.72 | 34.33 | 5.07 | 22.84 | 10.06 | 18.13 | 5.29 |
| GEMINI-3.0-FLASH | 19.74 | 21.50 | 18.43 | 17.44 | 20.42 | 38.12 | 18.25 | 39.90 | 7.26 | 18.40 | 14.71 | 15.62 | 6.79 |
| FUNASR-MLT-NANO | 22.58 | 27.91 | 31.69 | 18.38 | 26.47 | 30.86 | 25.85 | 31.25 | 6.81 | 31.44 | 10.97 | 22.92 | 6.37 |
| ELEVENLABS-SCRIBE-V2 | 22.98 | 29.40 | 26.86 | 18.59 | 27.90 | 37.66 | 25.20 | 32.79 | 6.90 | 27.15 | 12.31 | 24.93 | 6.04 |
| AZURE | 27.64 | 35.98 | 32.83 | 27.17 | 30.12 | 37.71 | 37.76 | 34.52 | 9.97 | 37.97 | 14.21 | 26.04 | 7.44 |
| CHIRP-3 | 29.81 | 33.06 | 32.92 | 25.96 | 30.05 | 42.10 | 25.39 | 47.54 | 11.30 | 31.00 | 42.92 | 24.02 | 11.50 |
| GPT-4O-TRANSCRIBE | 32.68 | 38.49 | 32.46 | 30.67 | 33.27 | 53.67 | 48.55 | 46.97 | 17.90 | 29.30 | 18.87 | 30.93 | 11.06 |
| WHISPER-LARGE-V3 | 35.07 | 47.07 | 36.10 | 33.15 | 37.45 | 45.13 | 39.39 | 50.03 | 16.95 | 39.91 | 19.67 | 42.22 | 13.81 |
| DOLPHIN-SMALL | 36.02 | 44.02 | 55.23 | 32.93 | 38.09 | 42.12 | 41.58 | 44.83 | 17.82 | 39.02 | 14.05 | 41.90 | 20.59 |
| META-OMNIASR-3B | 40.82 | 54.40 | 58.14 | 35.54 | 45.07 | 46.85 | 48.02 | 52.78 | 19.24 | 41.88 | 19.11 | 47.62 | 21.15 |
| DOLPHIN-BASE | 42.09 | 51.83 | 62.50 | 38.04 | 45.86 | 46.77 | 46.53 | 53.57 | 25.05 | 43.06 | 17.48 | 47.62 | 26.71 |
| NVIDIA-NEMO | 60.11 | 69.15 | 78.49 | 55.91 | 65.51 | 68.51 | 65.91 | 74.94 | 40.25 | 56.88 | 33.29 | 65.70 | 46.80 |

#### 🏢 Vertical Domain — Chinese CER (%)

| Model | AVG(%) | AGR-CH | AIT-CH | ART-CH | BIO-CH | ECM-CH | ENG-CH | ENT-CH | FIN-CH | HUM-CH | LAW-CH | MED-CH | MIL-CH |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🥇 FUNASR-REALTIME | 3.12 | 3.15 | 3.33 | 2.60 | 2.07 | 9.10 | 2.65 | 3.41 | 1.44 | 1.68 | 4.97 | 1.56 | 1.49 |
| 🥈 QWEN3.5-OMNI-PLUS | 3.36 | 3.54 | 3.74 | 2.65 | 2.28 | 9.35 | 3.49 | 3.59 | 1.62 | 1.71 | 5.06 | 1.70 | 1.64 |
| 🥉 SEEDASR | 3.84 | 4.02 | 4.33 | 2.91 | 2.89 | 9.62 | 4.18 | 4.05 | 2.17 | 2.03 | 5.73 | 2.09 | 2.02 |
| BIGASR | 3.84 | 4.02 | 4.35 | 2.91 | 2.92 | 9.58 | 4.15 | 4.10 | 2.20 | 2.03 | 5.74 | 2.11 | 2.00 |
| QWEN3-ASR-1.7B | 3.95 | 4.65 | 4.42 | 2.95 | 2.81 | 10.01 | 4.18 | 4.76 | 1.82 | 2.45 | 5.20 | 2.27 | 1.91 |
| FUNASR-MLT-NANO | 4.67 | 5.83 | 5.09 | 3.60 | 4.11 | 10.49 | 4.92 | 5.23 | 2.13 | 3.80 | 5.68 | 2.71 | 2.41 |
| ELEVENLABS-SCRIBE-V2 | 5.24 | 6.61 | 5.22 | 4.03 | 4.84 | 12.25 | 5.94 | 5.94 | 2.52 | 3.51 | 6.38 | 3.24 | 2.36 |
| AZURE | 5.92 | 7.31 | 5.55 | 5.30 | 6.09 | 11.91 | 7.34 | 6.05 | 2.75 | 5.88 | 6.38 | 3.80 | 2.66 |
| QWEN3-ASR-FLASH | 6.20 | 4.84 | 5.37 | 9.21 | 5.25 | 11.36 | 5.13 | 4.92 | 2.88 | 2.32 | 10.33 | 6.88 | 5.92 |
| DOLPHIN-SMALL | 7.55 | 9.64 | 9.54 | 6.29 | 8.01 | 12.46 | 7.85 | 8.74 | 3.53 | 6.86 | 6.97 | 5.64 | 5.11 |
| GEMINI-3.0-FLASH | 8.79 | 10.92 | 9.92 | 7.85 | 6.44 | 18.42 | 9.19 | 11.05 | 5.57 | 5.39 | 10.79 | 4.79 | 5.20 |
| CHIRP-3 | 9.38 | 9.63 | 8.98 | 7.40 | 6.45 | 15.63 | 8.58 | 9.26 | 4.55 | 5.84 | 26.44 | 4.83 | 5.02 |
| WHISPER-LARGE-V3 | 9.83 | 11.57 | 9.90 | 10.29 | 10.05 | 17.17 | 10.97 | 9.63 | 5.89 | 8.12 | 10.49 | 7.79 | 6.04 |
| DOLPHIN-BASE | 9.88 | 12.20 | 11.42 | 8.29 | 11.04 | 14.86 | 9.99 | 11.71 | 5.17 | 10.13 | 8.76 | 7.96 | 7.04 |
| META-OMNIASR-3B | 11.85 | 14.07 | 14.98 | 10.58 | 12.73 | 18.85 | 14.42 | 11.61 | 7.49 | 9.45 | 10.87 | 9.63 | 7.52 |
| GPT-4O-TRANSCRIBE | 15.29 | 15.50 | 19.58 | 15.11 | 11.58 | 29.30 | 29.63 | 12.61 | 13.32 | 7.08 | 13.58 | 8.73 | 7.41 |
| NVIDIA-NEMO | 26.95 | 29.95 | 36.11 | 23.80 | 26.53 | 38.86 | 29.07 | 31.71 | 20.30 | 22.06 | 22.75 | 21.75 | 20.47 |

#### 🏢 Vertical Domain — English B-WER (%) [Hotword]

| Model | AVG(%) | AGR-EN | AIT-EN | ART-EN | BIO-EN | ECM-EN | ENG-EN | ENT-EN | FIN-EN | HUM-EN | LAW-EN | MED-EN | MIL-EN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🥇 QWEN3.5-OMNI-PLUS | 12.80 | 6.82 | 25.83 | 6.47 | 14.33 | 14.45 | 10.23 | 16.93 | 10.24 | 5.39 | 12.77 | 12.31 | 17.77 |
| 🥈 FUNASR-REALTIME | 12.94 | 7.80 | 22.51 | 8.92 | 14.92 | 13.34 | 9.21 | 20.48 | 10.27 | 5.05 | 14.95 | 12.35 | 15.47 |
| 🥉 GEMINI-3.0-FLASH | 13.67 | 7.68 | 27.05 | 7.04 | 14.56 | 16.05 | 11.56 | 19.15 | 11.55 | 5.66 | 13.03 | 12.45 | 18.24 |
| QWEN3-ASR-1.7B | 13.81 | 7.36 | 26.79 | 8.20 | 15.67 | 15.71 | 11.70 | 19.42 | 10.35 | 6.12 | 15.13 | 13.52 | 15.79 |
| WHISPER-LARGE-V3 | 14.67 | 7.60 | 28.53 | 9.00 | 16.34 | 16.26 | 12.64 | 19.47 | 11.64 | 6.11 | 15.64 | 13.78 | 18.99 |
| CHIRP-3 | 14.69 | 7.92 | 27.63 | 8.58 | 15.12 | 16.13 | 13.28 | 21.16 | 12.05 | 6.25 | 15.97 | 13.10 | 19.06 |
| QWEN3-ASR-FLASH | 14.90 | 6.91 | 26.54 | 14.61 | 15.85 | 14.54 | 11.32 | 17.51 | 10.27 | 8.48 | 19.93 | 14.65 | 18.15 |
| ELEVENLABS-SCRIBE-V2 | 16.16 | 9.54 | 29.95 | 9.46 | 16.46 | 18.31 | 13.46 | 20.32 | 14.33 | 8.56 | 17.18 | 14.19 | 22.15 |
| BIGASR | 16.17 | 11.05 | 29.01 | 10.94 | 16.74 | 17.27 | 11.70 | 24.58 | 13.30 | 7.13 | 17.45 | 15.45 | 19.42 |
| SEEDASR | 16.39 | 12.79 | 29.48 | 11.13 | 16.83 | 17.17 | 11.62 | 24.97 | 13.20 | 7.19 | 17.48 | 15.36 | 19.46 |
| FUNASR-MLT-NANO | 16.43 | 10.02 | 28.24 | 10.96 | 19.33 | 17.45 | 12.93 | 25.42 | 12.78 | 7.79 | 18.75 | 15.30 | 18.14 |
| AZURE | 16.48 | 9.84 | 28.56 | 12.02 | 18.52 | 19.45 | 14.74 | 21.19 | 13.17 | 7.79 | 17.78 | 14.88 | 19.76 |
| NVIDIA-NEMO | 19.67 | 14.50 | 31.73 | 17.18 | 24.07 | 23.98 | 18.50 | 36.01 | 13.34 | 10.19 | 20.66 | 14.36 | 11.53 |
| GPT-4O-TRANSCRIBE | 24.79 | 15.06 | 44.01 | 18.79 | 17.09 | 36.64 | 29.04 | 29.87 | 19.75 | 10.48 | 20.85 | 32.10 | 23.87 |
| META-OMNIASR-3B | 26.56 | 22.69 | 42.15 | 22.60 | 28.45 | 27.60 | 26.53 | 40.29 | 22.74 | 12.22 | 27.87 | 24.59 | 21.03 |

#### 🏢 Vertical Domain — English WER (%)

| Model | AVG(%) | AGR-EN | AIT-EN | ART-EN | BIO-EN | ECM-EN | ENG-EN | ENT-EN | FIN-EN | HUM-EN | LAW-EN | MED-EN | MIL-EN |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🥇 QWEN3-ASR-1.7B | 6.64 | 5.44 | 8.85 | 5.18 | 5.66 | 8.93 | 5.29 | 8.09 | 6.24 | 6.77 | 9.13 | 5.02 | 5.04 |
| 🥈 FUNASR-REALTIME | 6.95 | 6.39 | 9.11 | 5.58 | 5.63 | 8.86 | 4.88 | 9.16 | 7.36 | 6.37 | 9.67 | 5.19 | 5.26 |
| 🥉 QWEN3.5-OMNI-PLUS | 7.26 | 7.10 | 10.58 | 6.13 | 5.49 | 8.99 | 5.32 | 9.47 | 7.33 | 6.94 | 9.20 | 5.10 | 5.53 |
| CHIRP-3 | 7.67 | 6.92 | 10.46 | 5.58 | 5.87 | 10.05 | 6.77 | 9.29 | 7.93 | 7.22 | 10.18 | 5.51 | 6.22 |
| BIGASR | 7.99 | 7.25 | 10.81 | 6.50 | 6.46 | 9.80 | 6.03 | 10.65 | 7.55 | 7.41 | 11.34 | 5.91 | 6.20 |
| AZURE | 8.16 | 7.00 | 10.58 | 6.37 | 6.94 | 10.94 | 7.40 | 9.84 | 8.18 | 7.34 | 10.79 | 6.06 | 6.48 |
| SEEDASR | 8.23 | 9.14 | 11.61 | 6.54 | 6.50 | 9.79 | 5.99 | 10.63 | 7.54 | 7.47 | 11.39 | 5.90 | 6.20 |
| FUNASR-MLT-NANO | 8.50 | 8.16 | 11.87 | 7.31 | 7.09 | 9.87 | 6.23 | 11.50 | 8.40 | 7.87 | 11.80 | 5.91 | 5.99 |
| QWEN3-ASR-FLASH | 8.57 | 6.63 | 11.26 | 11.86 | 6.78 | 8.78 | 5.63 | 9.21 | 7.20 | 9.14 | 13.20 | 7.09 | 6.11 |
| GEMINI-3.0-FLASH | 8.77 | 8.36 | 12.09 | 6.66 | 6.38 | 11.25 | 6.49 | 12.54 | 8.65 | 7.56 | 13.26 | 5.82 | 6.22 |
| WHISPER-LARGE-V3 | 8.79 | 9.43 | 13.56 | 7.29 | 6.29 | 10.52 | 6.67 | 11.61 | 9.37 | 7.66 | 11.25 | 5.69 | 6.08 |
| NVIDIA-NEMO | 10.62 | 10.59 | 14.46 | 8.19 | 9.33 | 13.10 | 8.35 | 17.02 | 8.93 | 9.32 | 15.86 | 6.63 | 5.63 |
| ELEVENLABS-SCRIBE-V2 | 13.13 | 13.61 | 15.13 | 10.80 | 9.89 | 15.37 | 10.27 | 18.44 | 13.76 | 12.21 | 16.82 | 9.87 | 11.43 |
| GPT-4O-TRANSCRIBE | 23.36 | 21.86 | 34.51 | 18.87 | 9.77 | 35.10 | 24.20 | 30.51 | 20.53 | 17.53 | 21.96 | 30.62 | 14.84 |
| META-OMNIASR-3B | 29.29 | 34.76 | 36.49 | 40.12 | 16.73 | 24.02 | 23.73 | 57.73 | 32.71 | 17.89 | 35.39 | 21.05 | 10.89 |

---

## 📦 Modules

| Module | Languages | Description |
|:-------|:----------|:------------|
| **Low-Resource-Languages** | ARE, DZA, EGY, IRQ, MAR, SAU, SYR, IDN, MYS, PHL, THA, VNM, JPN, KOR | Low-resource & dialectal |
| **CH-EN-Dialects** | GAN, JIN, MIN, WU, XIANG, YUE, CHN-EN, IDN-EN, JPN-EN, PHL-EN, SCT-EN, SGP-EN | Chinese dialects & accented English |
| **Vertical-Domain** | 12 CH + 12 EN domains (AGR, AIT, ART, BIO, ECM, ENG, ENT, FIN, HUM, LAW, MED, MIL) | Domain-specific with hotword eval |

---

## 🚀 Quick Start

### Requirements

```bash
conda create -n asr_bench python=3.10
conda activate asr_bench
pip install -r requirements.txt
```

### Evaluate Your Model (Gradio UI)

```bash
python visualize/app.py --port 7860
```

1. Open browser → "➕ Evaluate Your Model" tab
2. Enter your result JSON file path (see format below)
3. Click **Evaluate** → results auto-computed and ranked against baselines

**What happens automatically:**
- Reference data is prepared on first run (cached for subsequent evaluations)
- Only your model is evaluated (no re-run of existing models)
- WER/CER computed → results saved to `data/new_model/<YourModel>/`
- Your model is highlighted with ⭐ in the ranked leaderboard

### Full Pipeline via CLI

```bash
# Single module
STAGING_ROOT=/path/to/benchmark_data PYTHON_BIN=python3 bash run_ASR.sh Low-Resource-Languages

# All modules
STAGING_ROOT=/path/to/benchmark_data PYTHON_BIN=python3 bash run_ASR.sh all
```

### Input JSON Format

Your model output must follow this structure:

```json
{
  "audios": [
    {
      "aid": "LANG#audio_id",
      "language": "ARE",
      "segments": [
        {
          "sid": "LANG#audio_id#begin_time#end_time",
          "begin_time": "165.613",
          "end_time": "169.920",
          "text": "your transcription here"
        }
      ]
    }
  ]
}
```

| Field | Description |
|:------|:------------|
| `aid` | Audio identifier (must match reference `aid`) |
| `language` | Language code (e.g. `ARE`, `JPN`, `AGR-CH`) |
| `segments[].sid` | Segment ID: `aid#begin_time#end_time` |
| `segments[].text` | Your model's transcription |

- **Model name** = filename stem (e.g. `MyModel.json` → "MyModel")
- **Module** auto-detected from language codes in the file
- Partial coverage OK (missing languages shown as warning)

---

## 🖥 Gradio UI

```bash
python visualize/app.py [--port 7860] [--share]
```

- **Leaderboard** — 9 tables: 3 LR + 2 CED + 4 VD (CER/WER + B-CER/B-WER)
- **Evaluate Your Model** — Submit JSON → auto pipeline → ranked with ⭐

---

## 📊 Metrics

| Metric | Description | Used For |
|:-------|:------------|:---------|
| **WER** | Word Error Rate | Alphabetic languages |
| **CER** | Character Error Rate | CJK languages |
| **B-WER / B-CER** | Error rate on entity tokens | Vertical-Domain |
| **Hotword Recall** | Entity recall: TP / (TP+FN) | Vertical-Domain |

---

## 📄 License

Non-commercial research purposes only.

## 📖 Citation

```bibtex
@misc{gigaspeechbench,
  title={GigaSpeechBench: A Large-Scale Multilingual Speech Recognition Benchmark},
  year={2026},
  url={https://github.com/AlexTYJ/Multilingual-ASR-Benchmark}
}
```
