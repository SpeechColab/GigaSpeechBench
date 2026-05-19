# Qwen3 ASR (DashScope API)

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

Batch ASR transcription using Alibaba Qwen3 ASR models via DashScope API. Supports qwen3-asr-flash, qwen3-asr-1.7b, and qwen3.5-omni-flash.

## Scripts

| File | Description |
|:-----|:------------|
| `qwen3asr.py` | Main transcription script |
| `run_qwen35_cv_threaded.py` | Threaded qwen3.5-omni-flash inference |
| `run_qwen35_omni_fleurs.py` | qwen3.5-omni-flash on FLEURS |
| `run_cv_vnm_missing.py` | qwen3-asr-flash on missing VNM segments |

## Setup

```bash
export DASHSCOPE_API_KEY=your_key
```

## Usage

Edit the configuration constants at the top of `qwen3asr.py` before running:

```python
REF_ROOT_DIR = "/path/to/ref_root"    # Reference text directory
AUDIO_ROOT_DIR = "/path/to/audio_root"  # Audio directory
```

```bash
python qwen3asr.py
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
