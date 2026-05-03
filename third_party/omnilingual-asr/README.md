# Omnilingual ASR (Meta)

<p align="center"><a href="README_zh.md">🇨🇳 中文版</a></p>

ASR transcription using Meta's omnilingual-asr model built on fairseq2. LLM-series decoding requires lang_id; CTC-series does not.

## Scripts

| File | Description |
|:-----|:------------|
| `omniasr.py` | Main transcription script |
| `test_label_decode.py` | Label decode test |

## Setup

```bash
# See: https://github.com/facebookresearch/omnilingual-asr
conda install libsndfile
pip install fairseq2
```

## Usage

```bash
python omniasr.py --input_dir /path/to/audio --output_dir /path/to/results
```

## Output Format

Results should be saved in GigaSpeech-style JSON format using `scripts/save_results.py`:

```python
from scripts.save_results import ResultWriter

writer = ResultWriter()
writer.add(audio_name="ARE#UC...#raw", begin_time=0.0, end_time=5.0, text="transcribed text", lang="ARE")
writer.save("results/model_name.json")
```
