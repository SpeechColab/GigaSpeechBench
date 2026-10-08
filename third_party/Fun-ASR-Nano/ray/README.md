# Multilingual checkpoint with Ray

Uses `FunAudioLLM/Fun-ASR-MLT-Nano-2512`, revision
`2c088f535108689beff7e11cdc3d792af7d56552`, through FunASR 1.3.3 and Ray 2.55.1.
Each persistent actor loads a complete model and receives only audio and language.
The driver retains references. This environment is separate from base/vLLM.

Use the [category entry point](../README.md) for HF data. For prepared manifests:

```bash
cd third_party/Fun-ASR-Nano/ray
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -r requirements.txt
CUDA_VISIBLE_DEVICES=0 .venv/bin/python infer.py \
  --input-root ./prepared --output-root ./outputs/raw --num-gpus 1 --actors-per-gpu 2
```

The requirements pin a matching Torch/torchaudio pair; choose a supported CUDA
wheel/index for your machine using PyTorch's installation guidance. No local
ModelScope checkout or private model implementation is required. `--model-path`
selects downloaded weights. Keep `RAY_TMPDIR` short: generated Unix socket paths
must fit within 107 bytes on Linux. Tune replica count to available GPU and host RAM.

Decoding is greedy, ITN enabled, with a 512-token limit passed through FunASR's
`max_length`. The checkpoint lacks weights for its optional CTC alignment branch,
so `ctc_decoder=None` disables alignment explicitly. Input uses Torch tensors.
`--resume --retry-errors` resubmits failures; `--empty-retries 10` retries empty
predictions. Persistent empty text stays `""`, with diagnostics stored separately.
