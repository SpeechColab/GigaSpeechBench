# NVIDIA NeMo ASR

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch ASR transcription using NVIDIA NeMo pre-trained models. Includes language-specific scripts for Arabic, Japanese, Korean, Chinese dialects, and English dialects.

## Scripts

| File | Description |
|:-----|:------------|
| `ar_asr.py` | Arabic ASR |
| `jpn_asr.py` | Japanese ASR |
| `kor_asr.py` | Korean ASR |
| `ZH-Dialects.py` | Chinese dialects ASR |
| `EN_Dialects.py` | English dialects ASR |
| `download.py` | Model download helper |

## Setup

```bash
pip install nemo_toolkit[asr]
```

## Usage

```bash
python ar_asr.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
