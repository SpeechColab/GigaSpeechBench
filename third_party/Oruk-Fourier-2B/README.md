# Oruk Fourier 2B on Filipino-accented English

The runner transcribes all 8,637 annotated utterances from the 37 recordings in **PHL-EN**. Fourier receives each 16 kHz mono clip and a fixed English language prompt. It uses greedy decoding (maximum 256 output tokens), preserves the release's annotated boundaries and writes merged prediction JSON for the standard GigaSpeechBench scorer.

| PHL-EN scoring condition | Scored segments | Word errors / reference words | WER |
| --- | ---: | ---: | ---: |
| All | 8,498 | 11,509 / 117,741 | 9.77% |
| Duration > 0.5 s | 8,117 | 11,361 / 117,311 | 9.68% |

## Rescore an existing prediction file

From the root of GigaSpeechBench, use Linux, Python 3.12 and the repository's unmodified scoring scripts. Download the two public data shards and install the scoring dependencies:

```sh
pip install huggingface_hub -r third_party/Oruk-Fourier-2B/requirements.txt
hf download speechcolab/GigaSpeechBench --repo-type dataset \
  --revision 55ce5222f21f314759f5bfe8212eff34cd730aa2 \
  --include 'CH-EN-Dialects/data/PHL-EN/test/*.tar' --local-dir ./gsb-release
python third_party/Oruk-Fourier-2B/run.py \
  --data ./gsb-release/CH-EN-Dialects/data/PHL-EN --out ./fourier-score \
  --score-only /path/to/Oruk-Fourier-2B.json
```

The CPU scoring path checks every recording ID, segment ID and boundary against the release. The two reports in `fourier-score/scored/data/` cover all segments and the standard duration >0.5 s subset. The official scorer omits empty normalized references from WER.

## Regenerate predictions

On a checkout from before [the shard-aware cropper](https://github.com/SpeechColab/GigaSpeechBench/pull/13) was merged, apply the single tested cropper file in a clean working tree. This keeps the Fourier runner in place. CPU rescoring above works on main.

```sh
git fetch https://github.com/SpeechColab/GigaSpeechBench.git refs/pull/13/head
git cat-file -e fe4804db37450264995255c8f693a41e973b9893^{commit}
git restore --source=fe4804db37450264995255c8f693a41e973b9893 -- third_party/Qwen3-ASR-1.7B/prepare.py
```

The tested inference environment is vLLM 0.34.0 on a 24 GB NVIDIA A10G. After downloading the two shards above, run from the checkout, with a new output directory:

```sh
docker run --rm --gpus all --ipc=host \
  -v "$PWD:/benchmark" -w /benchmark --entrypoint /bin/bash \
  vllm/vllm-openai@sha256:cf5b2fdd087eb4f6d261736967cc5cde974bd22ff4df50365f8fa419b6b4c484 \
  -c 'python3 -m pip install -r third_party/Oruk-Fourier-2B/requirements.txt && python3 third_party/Oruk-Fourier-2B/run.py --data gsb-release/CH-EN-Dialects/data/PHL-EN --out fourier-eval'
```

The runner checks the native BF16 checkpoint hash and transcribes locally. Source data are licensed CC BY 4.0. Model weights are licensed CC BY-NC 4.0. [Dataset](https://huggingface.co/datasets/speechcolab/GigaSpeechBench/tree/55ce5222f21f314759f5bfe8212eff34cd730aa2/CH-EN-Dialects/data/PHL-EN/test) · [Model](https://huggingface.co/oruk/oruk-fourier-2b/tree/8c2a8871f1304aa2f634da4fb95e24438c4945b9)
