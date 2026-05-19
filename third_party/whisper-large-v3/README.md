# Whisper Large V3 (OpenAI)

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch ASR transcription using OpenAI's Whisper Large V3 model. Supports full-audio and segment-based inference modes. Uses `uv` for environment management.

## Scripts

| File | Description |
|:-----|:------------|
| `whisper_asr.py` | Whisper ASR wrapper |
| `auto_infer.py` | Full-audio batch inference |
| `auto_infer_with_segments.py` | Segment-based inference |
| `language_mapping.py` | Language code mapping |

## Setup

```bash
uv sync
# Or: pip install openai-whisper torch
```

## Usage

Edit the configuration constants at the top of `auto_infer.py` before running:

```python
DATA_DIR    = '/path/to/audio_root'    # Audio dataset directory
RESULTS_DIR = './results'              # Output results directory
MODEL_DIR   = '/path/to/model'         # Model directory
```

```bash
python auto_infer.py              # Full-audio batch inference
python auto_infer.py --force      # Force reprocessing
python auto_infer_with_segments.py  # Segment-based inference
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
