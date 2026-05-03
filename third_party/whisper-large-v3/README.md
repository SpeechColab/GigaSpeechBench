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

```bash
python auto_infer.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
