# ElevenLabs Scribe v2

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch ASR transcription using ElevenLabs Scribe v2 speech recognition API.

## Scripts

| File | Description |
|:-----|:------------|
| `elevenlabs_asr.py` | Main transcription script |

## Setup

```bash
export ELEVENLABS_API_KEY=your_key
```

## Usage

```bash
python elevenlabs_asr.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
