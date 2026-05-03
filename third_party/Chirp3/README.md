# Google Chirp 3 (Cloud Speech-to-Text V2)

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch ASR transcription using Google Cloud Speech-to-Text V2 API with the Chirp 3 model. Designed for short audio (<60s) synchronous inference.

## Scripts

| File | Description |
|:-----|:------------|
| `Chirp3.py` | Main transcription script |
| `run_syr_missing.py` | Rerun missing SYR segments |

## Setup

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

## Usage

```bash
python Chirp3.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
