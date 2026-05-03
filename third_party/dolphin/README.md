# Dolphin ASR

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch ASR transcription using the Dolphin multilingual speech recognition model.

## Scripts

| File | Description |
|:-----|:------------|
| `dolphin_asr.py` | Main transcription script |

## Setup

```bash
# Install dolphin model dependencies
```

## Usage

```bash
python dolphin_asr.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
