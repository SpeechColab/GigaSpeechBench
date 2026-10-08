# Multilingual Fun-ASR-MLT-Nano with Ray

This is the traditional FunASR/Transformers inference path. Each persistent Ray
actor loads the multilingual model once and accepts audio plus an explicit language.
The driver alone retains references and source metadata. No VAD, hotwords, speaker
model, or reference prompt is added. The optional CTC alignment branch is disabled
(`ctc_decoder=None`): the tested MLT configuration declares that branch, but the
checkpoint does not provide its weights. This workflow only requires ASR text,
not CTC alignment or timestamps. This override is recorded explicitly.
ITN is enabled, generation is greedy, and
`max_new_tokens` is 512 (passed as `max_length` through the pinned FunASR API).
Audio is supplied as a Torch Tensor; this FunASR version does not accept a NumPy
array at that model entry point. These settings are recorded in each run specification.

Use the [category-based entry point](../README.md) for HF dataset preparation and
export. To run on already prepared manifests:

```bash
cd third_party/Fun-ASR-Nano/ray
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -r requirements.txt
CUDA_VISIBLE_DEVICES=0 .venv/bin/python infer.py \
  --input-root ../../../data/prepared/Low-Resource-Languages \
  --output-root ./outputs/mlt_r1 --num-gpus 1 --actors-per-gpu 2
```

Weights are downloaded from `FunAudioLLM/Fun-ASR-MLT-Nano-2512`, revision
`2c088f535108689beff7e11cdc3d792af7d56552`. `--model-path ./models/MLT` selects an
existing checkpoint. The installed FunASR package provides the model class; no
unversioned `model.py` is downloaded or copied from a private project.

Language mapping explicitly covers the public GigaSpeechBench groups, including
all seven Arabic country codes, Filipino, Malay, and Korean. An English-accent
suffix such as JPN-EN maps to English, not Japanese. Invalid languages fail before
inference. The low-resource category uses MLT for every subgroup, including JPN.

Resume uses `--resume`; failed rows require `--resume --retry-errors`. Ray does
not silently restart failed actors or replay model requests. Runtime errors are
preserved as empty hypotheses with error diagnostics outside the transcript.
The process exits nonzero while errors remain. `--empty-retries N` retries only
successful empty predictions. A failed later attempt preserves a prior successful
empty response. Each attempted raw text is retained.

Use a short writable temporary path via `RAY_TMPDIR` if Ray reports an AF_UNIX
socket-path length error. Multiple replicas and Ray's shared-memory object store
consume RAM as well as GPU memory. The object store is capped at 512 MiB;
requests carry paths rather than full recordings through Ray. This path is independent of the vLLM server;
it should not be installed into that environment.
