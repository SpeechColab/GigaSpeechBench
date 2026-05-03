# Google Gemini ASR

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch audio transcription using Google Gemini multimodal models. Supports multi-threaded parallel processing for long audio.

## Scripts

| File | Description |
|:-----|:------------|
| `gemini.py` | Main transcription script |
| `gemini_MYS.py` | MYS-specific script |
| `run_syr_missing.py` | Rerun missing SYR segments |

## Setup

```bash
export GOOGLE_API_KEY=your_key
```

## Usage

```bash
python gemini.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
