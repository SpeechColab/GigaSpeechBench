# SeedASR (ByteDance Volcengine)

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch ASR transcription using ByteDance Volcengine's Doubao recording recognition model 2.0 API. Supports resume and failure logging.

## Scripts

| File | Description |
|:-----|:------------|
| `seed_asr_infer_list.py` | Main transcription script |

## Setup

```bash
# See https://console.volcengine.com/speech/service/10012
```

## Usage

```bash
python seed_asr_infer_list.py
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
