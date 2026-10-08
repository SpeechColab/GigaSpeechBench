# Run a GigaSpeechBench category with one command

Prerequisites: Linux, `uv`, internet access for first-time package/model downloads,
and an NVIDIA GPU with a driver compatible with the selected Torch wheel. The
tested hardware is H100 80 GB. The command creates separate Python 3.12 environments;
it does not install drivers or change other running GPU processes.
**FunASR base installs a CUDA 13.0 Torch wheel and requires a compatible driver
(normally R580 or newer).** An older driver that runs Qwen/Whisper may still fail
for this backend. See the [driver check and explicit compatibility setup](../Fun-ASR-Nano/vllm/README.md#cuda-driver-check)
before downloading the base environment. All vLLM requirements include the
`audio` extra; installing bare `vllm` can produce a healthy server whose audio
requests fail because `librosa` is absent.

From the repository root, using a downloaded
[speechcolab/GigaSpeechBench](https://huggingface.co/datasets/speechcolab/GigaSpeechBench)
snapshot:

```bash
# Qwen3-ASR-1.7B: all low-resource language groups.
bash third_party/vllm_asr/run.sh --model qwen --subset low-resource \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/qwen_low_resource_r1 --gpus 0

# Whisper: Chinese/English vertical domains and dialect groups.
bash third_party/vllm_asr/run.sh --model whisper --subset zh-en \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/whisper_zh_en_r1 --gpus 0

# FunASR: selects MLT + Ray for this entire category, including Japanese.
bash third_party/vllm_asr/run.sh --model funasr --subset low-resource \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/funasr_mlt_r1 \
  --gpus 0 --actors-per-gpu 2

# FunASR: selects base + native vLLM for Chinese/English and dialects.
bash third_party/vllm_asr/run.sh --model funasr --subset zh-en \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/funasr_base_r1 --gpus 0
```

Replace the model or subset selector as needed. Add `--download` to any command
to download only its selected metadata and audio archives, excluding published
system results. Downloads use dataset revision
`680d3057641b7507a1ef14974407c7b0a7964e64` by default; the requested revision and
actual metadata hashes are recorded. A pre-existing local dataset is used as-is,
so the recorded requested revision does not certify the origin of local files.

| `--subset` | Categories |
| --- | --- |
| `low-resource` | Low-Resource-Languages |
| `zh-en` | Vertical-Domain and CH-EN-Dialects |
| `vertical-domain` | Vertical-Domain only |
| `dialects` | CH-EN-Dialects only |
| `older-children` | Older-Children from a compatible local/newer release |
| `all` | The three categories present in the pinned public HF snapshot |

The pinned public snapshot has **no Older-Children**. The runner supports the
same local layout for that category, and routes FunASR to base + vLLM. It does
not silently invent a download, substitute another dataset, or skip a missing
category. Use `--dataset-repo` and `--dataset-revision` explicitly for a newer
release with the same layout; arbitrary private archive layouts are not inferred.

## Input layout and preparation

```text
GigaSpeechBench/
  Low-Resource-Languages/data/KOR/
    metadata.json
    audio.tar.gz
  Vertical-Domain/data/ECM-CH/
    metadata.json
    audio.tar.gz
```

An extracted `audio/` directory may replace `audio.tar.gz`. Metadata must contain
`audios[]`, with `aid` and `segments[]`; segment times may be `begin_time/end_time`
or `start/end`. Audio filenames must have the recording `aid` as their stem.
Recordings retain their official `GROUP#...` identity. Only valid segments are
selected when a status field exists; segments without status are included, as in
the public release. References and entity annotations remain local metadata.

Preparation reads recordings from archives without unpacking arbitrary member
paths. It crops at rounded source sample indices, averages stereo channels if
needed, resamples to 16 kHz with polyphase filtering, and writes PCM16 mono clips.
End timestamps may exceed the recording by up to 10 ms due to release rounding;
only the crop boundary is clamped, while the original evaluation timestamps are
preserved. Each clamp is listed in `preparation_report.json` and the row metadata.
The full public YUE group has 230 such boundaries, at most 5 ms over the file end.
Use `--end-tolerance-ms 0` for strict bounds. Larger mismatches, duplicate identities,
missing audio, and segments over 30 s fail explicitly. There is no VAD, silence removal, or text normalization.
Source files are never modified. Prepared clips are cached inside the work directory
and reused only when metadata and preparation settings match.

## What the command manages

1. Optionally download the selected HF inputs.
2. Prepare the selected groups and create relative-path manifests.
3. Install the appropriate isolated model environment and obtain weights.
4. Start vLLM, wait for health, and validate one real transcription before bulk submission;
   or start persistent Ray actors for MLT.
5. Transcribe all groups in the category using the same loaded model(s).
6. Export both staging JSON and flat pipeline JSON, retaining empty strings.
7. Shut down the server/actors created by this invocation.

An occupied server port is an error; another user's process is never stopped or
silently reused. A server startup failure reports its log path. Request failures
remain in raw output and make the command exit nonzero; incomplete runs are not
presented as completed official-format results. The real-request probe is retained
and resumed without duplicate inference. The HTTP client stops scheduling a group
after 50 request errors by default (in-flight requests are drained); its direct
CLI exposes `--stop-after-errors`. Use Ctrl-C to interrupt; a managed
vLLM server is stopped in cleanup, including SIGTERM/SIGHUP during startup. Ray shutdown is also performed in cleanup.

## Smaller tests, resume and tuning

```bash
bash third_party/vllm_asr/run.sh --model funasr --subset low-resource \
  --groups KOR ARE --limit-per-group 2 --data-root ./data/GigaSpeechBench \
  --work-dir ./outputs/funasr_smoke_r1 --gpus 0 --actors-per-gpu 2
```

`--limit-per-group` deliberately produces a smaller evaluation subset, recorded
in `run.json`; never report that as a complete benchmark. `--groups` selects exact
subgroup names. Missing requested groups fail instead of being silently skipped.
`--prepare-only` performs only data preparation. Run the same command again with
`--resume` to continue; add `--retry-errors` to resubmit previously failed requests.
Successful empty transcripts stay completed. Set `--empty-retries 10` before
starting a new run to allow ten extra attempts per empty prediction. The policy
cannot be changed while resuming an existing experiment.

`--workers` controls vLLM client concurrency. Ray uses `--actors-per-gpu` and
`--gpus 0,1` for replicas on multiple GPUs. With vLLM, use one GPU by default;
advanced Qwen/Whisper tensor parallelism can use `TENSOR_PARALLEL_SIZE` with the
corresponding visible GPU list. FunASR base defaults to a single GPU.
`--port` and `--startup-timeout` control the managed vLLM endpoint.

`--python-bin` uses an existing model venv without installing packages.
`--env-root` puts automatically created model venvs under a chosen directory.
`GSB_TOOLS_ENV` overrides the lightweight orchestrator venv. `--model-path` uses a
local checkpoint. A combined FunASR `--subset all` run needs separate base and MLT
environments/models, so these single-environment/checkpoint overrides require
running its categories separately. `RAY_TMPDIR` can select a short writable Ray
temporary directory if the system's default path exceeds Unix socket limits.
Ray adds session/socket suffixes, so keep the chosen base short (roughly 40 bytes
or less), for example `RAY_TMPDIR=./ray_tmp` from a short working-directory path.
The full socket path must fit within 107 bytes on Linux. Changing only replica
count/GPU assignment on resume is allowed; avoid concurrent writers to one run.

## Results and official evaluation

```text
WORK/run.json                              # selection, model/backend routing, source hashes
WORK/prepared/MODULE/GROUP/                # clips and source manifest
WORK/raw/MODULE/MODEL/GROUP/                # append-only predictions and diagnostics
WORK/staging/MODULE/data/GROUP/metadata.json
WORK/staging/MODULE/results/MODEL.json      # audios[] / segments[] format
WORK/pipeline/data/text/MODULE/ref/GROUP.json
WORK/pipeline/data/text/MODULE/hyp/GROUP/GROUP_MODEL.json
```

The original reference metadata, including entities, is retained for scoring.
Transcript fields contain only the model text, including `""` for persistent
empty outputs. No debug labels are inserted. Base and MLT have different result
filenames so their measurements cannot be mistaken for the same checkpoint.

To evaluate, use the repository's existing evaluation environment and pipeline:

```bash
STAGING_ROOT=./outputs/funasr_base_r1/staging bash run_ASR.sh Vertical-Domain
```

The inference command does not install the evaluation dependencies or recompute
scores automatically. Evaluation uses the repository's normalization, duration
filter, and entity-aware BWER/BCER implementation. The existing evaluation runner
skips some already existing outputs, so use a clean evaluation checkout/output
area when comparing revisions. Do not silently reuse older normalized files.

## Model and runtime boundaries

Qwen and Whisper use separate vLLM versions. Whisper pins 0.14.1 because the
earlier 0.14.0 setup showed GPU memory growth. FunASR base uses native vLLM 0.27.1;
MLT uses the traditional Ray/FunASR backend. See [FunASR's explicit limitations](../Fun-ASR-Nano/README.md).
The same model weights on different backends are not a guarantee of identical
decoding. The public leaderboard's MLT results are not interchangeable with base.

For CPU-only contract/preparation tests, install `requirements.txt` in a tools
environment and run `python -m unittest discover -s third_party/vllm_asr -p 'test_*.py'`
from the repository root. Real-model smoke checks and clean-environment installation
are distinct validation steps; consult the validation record rather than assuming
that a passing mocked test proves either one.

See the [validation record](VALIDATION.md) for tested environments, real-model checks,
resolved issues, and remaining scope limits.
