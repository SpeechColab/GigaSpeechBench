# GPT-4o Transcribe (OpenAI)

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch ASR transcription using OpenAI's GPT-4o audio transcription API.

## Scripts

| File | Description |
|:-----|:------------|
| `chatgpt4o-transcribe.py` | Main transcription script |
| `run_fleurs_missing.py` | Rerun missing FLEURS segments |

## Setup

```bash
export OPENAI_API_KEY=your_key
```

## Usage

```bash
python chatgpt4o-transcribe.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
