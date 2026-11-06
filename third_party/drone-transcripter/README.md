# Drone Transcripter 4 / 4 Mini

Egyptian Arabic ASR models trained on recorded secondary-school lectures (dialect mixed with
English technical terms and numbers). Labels follow a fixed CODA-style orthography and were
built with an audio-grounded LLM pseudo-label correction loop. No GigaSpeech 3 data and no
GigaSpeechBench audio was used in training.

| Model | Params | Architecture | Licence |
|:------|:-------|:-------------|:--------|
| [Drone Transcripter 4](https://huggingface.co/AbdelrhmanX2/drone-transcripter-4) | 809M | Whisper large-v3-turbo, full fine-tune (transformers checkpoint in `drone-transcripter-v4/`, plus ggml f16 / q5_0) | Apache-2.0 |
| [Drone Transcripter 4 Mini](https://huggingface.co/AbdelrhmanX2/drone-transcripter-4-mini) | 115M | NeMo FastConformer hybrid RNN-T/CTC, distilled from v4's labels (`.nemo`, plus int8 sherpa-onnx export in `onnx/`) | CC-BY-4.0 |

Evaluation toolkit (normaliser, multi-reference WER, orthography rules):
https://github.com/drone-academy-labs/egy-asr-toolkit

## Scripts

| File | Description |
|:-----|:------------|
| `drone_transcripter_asr.py` | Transcribes a test set from `metadata.json` + audio and writes the result JSON |
| `results/EGY_Drone-Transcripter-4.json` | Drone Transcripter 4 on the EGY set |
| `results/EGY_Drone-Transcripter-4-Mini.json` | Drone Transcripter 4 Mini on the EGY set |

## Setup

Requires `ffmpeg` on `PATH` and an NVIDIA GPU (CPU works, slowly).

```bash
# Drone Transcripter 4
pip install torch transformers huggingface_hub numpy

# Drone Transcripter 4 Mini
pip install torch "nemo_toolkit[asr]" huggingface_hub numpy soundfile
```

Checkpoints are downloaded from Hugging Face on first run; pass `--model_path` to use a local copy.

## Usage

```bash
python drone_transcripter_asr.py --model v4 \
  --audio_root /path/to/GigaSpeechBench/Low-Resource-Languages/data/EGY/audio \
  --metadata /path/to/GigaSpeechBench/Low-Resource-Languages/data/EGY/metadata.json \
  --output results/EGY_Drone-Transcripter-4.json

python drone_transcripter_asr.py --model mini \
  --audio_root /path/to/GigaSpeechBench/Low-Resource-Languages/data/EGY/audio \
  --metadata /path/to/GigaSpeechBench/Low-Resource-Languages/data/EGY/metadata.json \
  --output results/EGY_Drone-Transcripter-4-Mini.json
```

Options: `--device` (default `cuda` if available), `--batch_size` (default 64),
`--decoder rnnt|ctc` (Mini only, default `rnnt`), `--language` (default taken from the `aid`).

## Decoding settings

- Each reference segment is cut from its recording using the metadata timestamps, converted to
  16 kHz mono and transcribed on its own. Segments shorter than 0.1 s are replaced by 0.1 s of silence.
- Greedy decoding, 64 segments per batch, no prompt, no temperature fallback, no post-processing.
  The models output no punctuation.
- Drone Transcripter 4: Hugging Face transformers, float16, language forced to Arabic
  (`language="ar"`, `task="transcribe"`), `max_new_tokens=200`, input truncated to 30 s.
- Drone Transcripter 4 Mini: NeMo, RNN-T head, bfloat16 autocast.

## Results (EGY)

Scored with this repository's pipeline unchanged (`run_ASR.sh Low-Resource-Languages`,
`text_norm/EGY.py`). Both files cover all 87 recordings and 17,747 segments.

| Model | WER (all segments) | WER (segments > 0.5 s) |
|:------|:------------------:|:----------------------:|
| Drone Transcripter 4 | 48.46 | 48.51 |
| Drone Transcripter 4 Mini | 47.90 | 47.98 |

## Citation

Paper: *Egyptian Arabic Lecture ASR with a Fixed Orthography and Audio-Grounded LLM Pseudo-Label
Correction*, Abdelrhman Slim, Drone Academy, 2026 (preprint pending).

```bibtex
@misc{slim2026droneasr,
  title  = {Egyptian Arabic Lecture ASR with a Fixed Orthography and Audio-Grounded LLM Pseudo-Label Correction},
  author = {Slim, Abdelrhman},
  year   = {2026},
  note   = {Drone Academy. Preprint, link to follow}
}
```
