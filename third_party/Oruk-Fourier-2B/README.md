# Oruk Fourier 2B on English GigaSpeechBench (All 20 English Splits)

This runner evaluates **Oruk Fourier 2B** ([`oruk/oruk-fourier-2b`](https://huggingface.co/oruk/oruk-fourier-2b), pinned commit `8c2a8871f1304aa2f634da4fb95e24438c4945b9`) across all **20 English splits** (141,456 valid annotated segments) spanning `CH-EN-Dialects`, `Vertical-Domain`, and `Older-Children`.

Fourier receives each 16 kHz mono pre-cut clip with a fixed English language prompt, uses greedy decoding (`temperature=0.0`, `max_tokens=256`), preserves all release segment boundaries, and emits merged per-module prediction JSON files for GigaSpeechBench's unmodified `run_ASR.sh` scorer (including `hotword_wer.py` for `Vertical-Domain`).

## Verified Results (Duration > 0.5 s, official `run_ASR.sh`)

### CH-EN-Dialects — English Accents (WER %)

| Split | Scored segs (>0.5 s) | Word errors / ref words (>0.5 s) | WER (>0.5 s) | WER (All) | Qwen3-ASR-1.7B (>0.5 s) | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `CHN-EN` | 6,139 | 9,174 / 72,194 | **12.71%** | 12.73% | 14.62% | -1.91 pp |
| `IND-EN` | 5,465 | 7,676 / 116,171 | **6.61%** | 6.61% | 7.04% | -0.43 pp |
| `JPN-EN` | 8,996 | 11,104 / 76,469 | **14.52%** | 14.61% | 21.52% | -7.00 pp |
| `PHL-EN`\* | 8,117 | 11,410 / 117,311 | **9.73%** | 9.81% | 10.81% | -1.08 pp |
| `SCT-EN` | 12,213 | 31,157 / 142,779 | **21.82%** | 21.91% | 24.29% | -2.47 pp |
| `SGP-EN` | 8,939 | 14,497 / 131,622 | **11.01%** | 11.09% | 12.44% | -1.43 pp |
| **Mean (6 splits)** | **49,869** | — | **12.73%** | **12.79%** | 15.12% | **-2.39 pp** |

*\*Note: The initial single-split PR #14 run on an NVIDIA A10G measured `9.68%` (`11,361 / 117,311`) on `PHL-EN`; this unified 20-split NVIDIA L40S run measures `9.73%` (`11,410 / 117,311`), within `0.05 pp` BF16 GPU variance. The companion HF dataset JSON (`CH-EN-Dialects/results/Oruk-Fourier-2B.json`) reproduces the exact table above.*

### Vertical-Domain — English WER & Hotword B-WER (%)

| Split | Word errors / ref words (>0.5 s) | WER (>0.5 s) | WER (All) | Qwen3-ASR-1.7B WER | B-WER (>0.5 s) | Qwen3-ASR-1.7B B-WER |
|---|---:|---:|---:|---:|---:|---:|
| `AGR-EN` | 6,150 / 122,229 | **5.03%** | 5.07% | 5.44% | 7.41% | 7.36% |
| `AIT-EN` | 9,162 / 109,556 | **8.36%** | 8.37% | 8.85% | **26.22%** | 26.79% |
| `ART-EN` | 4,995 / 101,866 | **4.90%** | 4.91% | 5.18% | 8.27% | 8.20% |
| `BIO-EN` | 5,480 / 102,551 | **5.34%** | 5.35% | 5.66% | **14.94%** | 15.67% |
| `ECM-EN` | 10,933 / 138,215 | **7.91%** | 7.91% | 8.93% | **14.93%** | 15.71% |
| `ENG-EN` | 5,638 / 117,146 | **4.81%** | 4.81% | 5.29% | **10.44%** | 11.70% |
| `ENT-EN` | 9,353 / 125,706 | **7.44%** | 7.50% | 8.09% | 20.21% | 19.42% |
| `FIN-EN` | 7,877 / 140,072 | **5.62%** | 5.66% | 6.24% | 10.44% | 10.35% |
| `HUM-EN` | 5,808 / 98,270 | **5.91%** | 5.92% | 6.77% | **5.57%** | 6.12% |
| `LAW-EN` | 9,091 / 110,303 | **8.24%** | 8.26% | 9.13% | **14.40%** | 15.13% |
| `MED-EN` | 5,217 / 108,828 | **4.79%** | 4.79% | 5.02% | **13.45%** | 13.52% |
| `MIL-EN` | 6,075 / 128,907 | **4.71%** | 4.71% | 5.04% | **15.70%** | 15.79% |
| **Mean (12 splits)** | — | **6.09%** | **6.10%** | 6.64% | **13.50%** | 13.81% |

### Older-Children — English (WER %)

| Split | Scored segs (>0.5 s) | Word errors / ref words (>0.5 s) | WER (>0.5 s) | WER (All) | Qwen3-ASR-1.7B (>0.5 s) | Delta |
|---|---:|---:|---:|---:|---:|---:|
| `CHILD-EN` | 10,442 | 15,841 / 88,059 | **17.99%** | 18.02% | 18.26% | -0.27 pp |
| `OLD-EN` | 5,958 | 10,823 / 80,666 | **13.42%** | 13.44% | 13.54% | -0.12 pp |
| **Mean (2 EN splits)** | **16,400** | — | **15.70%** | **15.73%** | 15.90% | **-0.20 pp** |

## Rescore existing prediction files on CPU

From the root of GigaSpeechBench on Linux (Python 3.12), download the public release shards and run `run.py --score-only` for each module:

```sh
pip install huggingface_hub -r third_party/Oruk-Fourier-2B/requirements.txt

# Example: rescore all 6 English accents in CH-EN-Dialects
hf download speechcolab/GigaSpeechBench --repo-type dataset \
  --revision 55ce5222f21f314759f5bfe8212eff34cd730aa2 \
  --include 'CH-EN-Dialects/data/*-EN/test/*.tar' --local-dir ./gsb-release
python third_party/Oruk-Fourier-2B/run.py \
  --module CH-EN-Dialects --groups all \
  --data ./gsb-release/CH-EN-Dialects/data --out ./fourier-score-dialects \
  --score-only /path/to/CH-EN-Dialects/results/Oruk-Fourier-2B.json

# Vertical-Domain (12 EN domains + hotword B-WER)
python third_party/Oruk-Fourier-2B/run.py \
  --module Vertical-Domain --groups all \
  --data ./gsb-release/Vertical-Domain/data --out ./fourier-score-vertical \
  --score-only /path/to/Vertical-Domain/results/Oruk-Fourier-2B.json

# Older-Children (CHILD-EN, OLD-EN)
python third_party/Oruk-Fourier-2B/run.py \
  --module Older-Children --groups all \
  --data ./gsb-release/Older-Children/data --out ./fourier-score-older \
  --score-only /path/to/Older-Children/results/Oruk-Fourier-2B.json
```

Single-group invocation (`--data ./gsb-release/CH-EN-Dialects/data/PHL-EN`) remains supported for backward compatibility.

## Regenerate predictions on GPU

On a checkout from before [the shard-aware cropper](https://github.com/SpeechColab/GigaSpeechBench/pull/13) was merged, restore `third_party/Qwen3-ASR-1.7B/prepare.py` from `fe4804db37450264995255c8f693a41e973b9893`, then run inside the tested vLLM 0.34.0 container:

```sh
docker run --rm --gpus all --ipc=host \
  -v "$PWD:/benchmark" -w /benchmark --entrypoint /bin/bash \
  vllm/vllm-openai@sha256:cf5b2fdd087eb4f6d261736967cc5cde974bd22ff4df50365f8fa419b6b4c484 \
  -c 'python3 -m pip install -r third_party/Oruk-Fourier-2B/requirements.txt && python3 third_party/Oruk-Fourier-2B/run.py --module CH-EN-Dialects --groups all --data gsb-release/CH-EN-Dialects/data --out fourier-eval-dialects'
```

The runner checks the pinned native BF16 checkpoint SHA-256 (`model.safetensors`: `e64765ff...`, `tokenizer.json`: `bd2a97b5...`) and transcribes locally. Source data are licensed CC BY 4.0. Model weights are licensed CC BY-NC 4.0.

- [Dataset Release (`55ce5222`)](https://huggingface.co/datasets/speechcolab/GigaSpeechBench/tree/55ce5222f21f314759f5bfe8212eff34cd730aa2)
- [Model Checkpoint (`8c2a8871`)](https://huggingface.co/oruk/oruk-fourier-2b/tree/8c2a8871f1304aa2f634da4fb95e24438c4945b9)
- HF Jobs provenance (1× NVIDIA L40S, vLLM 0.34.0):
  - `CH-EN-Dialects` + `Older-Children`: `https://huggingface.co/jobs/oruk/6b06d176d91f621b9307908e`
  - `Vertical-Domain`: `https://huggingface.co/jobs/oruk/6b06d177d91f621b93079090`
