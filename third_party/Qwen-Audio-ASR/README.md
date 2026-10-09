# Qwen-Audio ASR: Bailian HTTP inference

Self-contained API runner for three hosted models. No GPU or local ASR environment
is required. This directory does not depend on the existing `Qwen3ASR` integration
or any sibling model directory.

| Short name | Exact `--model` value |
|---|---|
| 3.1 Flash | `qwen-audio-3.1-asr-flash` |
| 3.1 Filetrans | `qwen-audio-3.1-asr-flash-filetrans` |
| 3.0 Flash | `qwen-audio-3.0-asr-flash` |

These are API model IDs, not the local `Qwen3-ASR-1.7B` checkpoint.

## Setup

Requires Linux, `uv`, a regional Bailian API key, and an OSS bucket with permission
to read object metadata, upload objects, and download audio. Calls and OSS usage
may incur provider charges. Set credentials in your shell or secret manager:

```bash
export DASHSCOPE_API_KEY='YOUR_BAILIAN_KEY'
export OSS_ACCESS_KEY_ID='YOUR_OSS_KEY_ID'
export OSS_ACCESS_KEY_SECRET='YOUR_OSS_KEY_SECRET'
export OSS_BUCKET_NAME='YOUR_BUCKET'
export OSS_REGION='cn-shanghai'
```

Optional: `OSS_SESSION_TOKEN` for STS, `OSS_ENDPOINT` for an internal upload
endpoint, and `DASHSCOPE_BASE_URL` for another regional/workspace API endpoint.
The default is `https://dashscope.aliyuncs.com/api/v1` (Beijing). Singapore uses
`https://dashscope-intl.aliyuncs.com/api/v1` and requires a Singapore API key.
The public audio signing endpoint follows `OSS_REGION`, not the upload endpoint.
Never commit credentials or signed URLs. This runner does not load `.env` files.

## One-command category inference

```bash
cd third_party/Qwen-Audio-ASR
bash run.sh --model qwen-audio-3.1-asr-flash \
  --subset zh-en --data-root ../../../datasets/GigaSpeechBench \
  --work-dir ./outputs/flash31_zh_en --oss-prefix YOUR_NAMESPACE/gsb/clips

bash run.sh --model qwen-audio-3.1-asr-flash-filetrans \
  --subset low-resource --data-root ../../../datasets/GigaSpeechBench \
  --work-dir ./outputs/filetrans31_low_resource --oss-prefix YOUR_NAMESPACE/gsb/clips

bash run.sh --model qwen-audio-3.0-asr-flash \
  --subset older-children --data-root ../../../datasets/GigaSpeechBench \
  --work-dir ./outputs/flash30_older_children --oss-prefix YOUR_NAMESPACE/gsb/clips
```

All CLI paths are relative to the caller's working directory. `run.sh` creates
a Python 3.12 environment with `uv venv --seed` and installs only this directory's
requirements. Set `ASR_ENV` to place the environment elsewhere. After setup, use
`.venv/bin/python run.py ...` to skip dependency installation.

Expected downloaded layout: `CATEGORY/data/GROUP/metadata.json` (`audios[]` with
segments) plus `audio.tar.gz` or extracted `audio/`. Audio is cropped to annotated
segments and converted to mono 16 kHz PCM WAV. Recording-end rounding overruns of
up to 10 ms are clamped and recorded by the preparation helper.

`--subset` supports `low-resource`, `zh-en`, `vertical-domain`, `dialects`,
`older-children`, and `all`. `zh-en` includes Vertical-Domain and CH-EN-Dialects;
`all` covers the three categories in the pinned public snapshot. Add `--download`
to fetch inputs from `speechcolab/GigaSpeechBench` at revision
`680d3057641b7507a1ef14974407c7b0a7964e64`. Older-Children is absent from that pinned
snapshot and requires a compatible downloaded/local release. Override the repo
and revision only for datasets with the documented layout.

For already cropped data, including the Paired-20261001 experiment input:

```bash
bash run.sh --model qwen-audio-3.1-asr-flash \
  --prepared-root ../../../datasets/Paired-20261001 \
  --module Older-Children --work-dir ./outputs/flash31_paired \
  --oss-prefix YOUR_NAMESPACE/gsb/clips
```

Prepared layout: `GROUP/input_prepare.json` (JSON array or JSONL), with each row
containing `segment_key`, `audio_path` relative to the manifest, `ref_text`, and
`meta.ref_audio_name/start_time/end_time` in seconds. Audio must be 16 kHz mono WAV.
References are read for export and never included in an API request.

Use `--groups CHILD-CH CHILD-EN --limit-per-group 2` for a smoke test.
`--language en` overrides language mapping. Unsupported group mappings fail
explicitly rather than silently selecting a language. `--prepare-only` builds
the local manifest without uploading or making ASR calls; then use `--resume`
with the same inputs and settings to perform inference.

## Parameters, retries, and limitations

- Language hints follow each subgroup. No context or hotwords are sent.
- 3.1 uses `keep_dialect=false` and disabled diarization on both routes.
- Filetrans selects channel 0 and explicitly disables the built-in sensitive-word
  filter with empty custom lists. The HTTP string field contains serialized JSON.
- 3.0 omits the unsupported dialect and diarization controls.
- No undocumented VAD, text-polishing, ITN, temperature, or alignment flags are
  sent. Timestamps cannot be disabled for these models. Hidden server behavior
  may differ: equivalent exposed settings do not make the models interchangeable.
- Default: 32 Flash workers / 64 Filetrans workers, 6 submissions per second per
  process. `--workers` and `--rps` are configurable. Filetrans query/download calls
  share a 12 RPS limiter. Multiple processes using the same model/account or
  multiple Filetrans processes must divide the published limits themselves.
- Transient HTTP failures and 429 responses use bounded backoff. Empty recognition
  receives ten extra attempts by default (`--empty-retries`), then remains `""`.
  Empty recognition is distinct from a failed request and does not prove silence.
- Resume with `--resume`: successful results are reused, failures are attempted
  again, and saved async task IDs are polled instead of blindly resubmitted.
  If an async submission's outcome is unknown after a transport failure, its
  state is retained and requires investigation. Task/results expire after 24 h;
  resume promptly. Incomplete runs never receive a completed export.
- A run fingerprints source metadata, audio, model, parameters, and Python code.
  Use a new work directory after changing these. Credentials are not fingerprinted.

Uploads use SHA256-based object names below the requested prefix, check existing
object content, and request no overwrites. No objects are deleted and no bucket
ACL is changed. New recognition attempts sign a public GET URL valid for 24 h;
HTTP retries within one submission may reuse that URL. Logs redact signed URLs
and credentials. Source audio must remain available during resume.

## Outputs and evaluation

- `pipeline/data/text/CATEGORY/{ref,hyp}`: official flat evaluation input; hyp
  includes the full uppercase model ID.
- `staging/CATEGORY/{data,results}`: audios/segments structure with matching group
  prefixes on reference and prediction IDs; `identity_map.json` records changes.
- `legacy/MODEL/CATEGORY/{ref,hyp}/GROUP.json`: audio_name/start/end/text.
- `responses/`, `states/`, `http.jsonl`, `protocol.json`: resume and diagnostic
  records. These local artifacts may include local paths; do not publish them as
  source code. `status.json` reaches `phase=complete` only after successful export.

Evaluation remains in the existing repository pipeline, with its own environment
and frozen normalization. Use identical segments across models; preserve empty
predictions. BWER/BCER require entity annotations and should not be filled with
zeros when those annotations are absent. This runner exports the actual model
identity rather than renaming it to fit any leaderboard whitelist.

## References

- [Flash HTTP API](https://www.alibabacloud.com/help/en/model-studio/fun-asr-flash-recorded-speech-recognition-http-api)
- [Filetrans HTTP API](https://www.alibabacloud.com/help/en/model-studio/fun-asr-recorded-speech-recognition-http-api)
- [Defaults, filtering, timestamps](https://www.alibabacloud.com/help/en/model-studio/non-realtime-speech-recognition-user-guide)
- [Rate limits](https://help.aliyun.com/zh/model-studio/rate-limit)

The client is adapted from the Paired-20261001 experiment; audio preparation is
adapted from this repository's local Qwen3-ASR-1.7B runner and kept self-contained.
