# Validation record (2026-10-08)

## Fresh README reproduction

The initial reproduction cloned the public `feat/vllm-asr-runners` branch at
`f22b1b8` over HTTPS into a new directory. A clean tools environment and all four
model environments were created with `uv venv --python 3.12 --seed`. Package,
model and dataset caches started empty. No old model directory or `--python-bin`
override was supplied. Inputs came from the pinned public HF revision through
`--download`, not from the original private batch directories.

The original instructions did **not** work unchanged on this host for every
backend. The failures below were retained and diagnosed before rerunning from
new work directories with the fixes. Hardware: four H100 80 GB GPUs, host driver
550.127.08. Only FunASR base received explicitly configured CUDA compatibility
libraries; the other environments used the host runtime normally.

| Model/backend | Complete groups tested | Clips | Errors after fixes | Empty outputs |
| --- | --- | ---: | ---: | ---: |
| Qwen3-ASR-1.7B / vLLM 0.14.0 | KOR | 11,880 | 0 | 5 |
| Whisper large-v3 / vLLM 0.14.1 | ECM-CH, ECM-EN | 11,679 | 0 | 0 |
| Fun-ASR-Nano base / vLLM 0.27.1 | YUE | 8,807 | 0 | 0 |
| Fun-ASR-MLT-Nano / FunASR 1.3.3 + Ray 2.55.1 | KOR | 11,880 | 0 | 0 |

These runs used the README defaults, including zero extra empty-output retries.
Empty predictions remain `""`; they are neither discarded nor treated as proof
of silent audio. Qwen also completed the original fresh-install run before the
shared fixes, with the same count and five empty outputs. The table uses its
second full run through the patched entry point.

Qwen's batch client took 92.0 s for 11,879 segments after the first-request probe;
Whisper took 115.0 s for the remaining 6,019 Chinese segments and 103.3 s for all
5,659 English segments. FunASR base took 490.9 s for the remaining 8,806 YUE
segments. These are client wall times on one H100 per vLLM service, excluding
preparation, installation, model downloads/startup and the first probe. They are
not cold-start times or a controlled cross-model speed comparison: groups differ
and other jobs ran concurrently.

## Failures found and changes made

- **Missing audio dependencies.** The bare Whisper vLLM installation passed
  `/health` but returned HTTP 500 on real audio because `librosa` was absent.
  All three vLLM requirements now request `vllm[audio]`. The category runner
  validates one real request before submitting the batch and retains that result
  without resubmitting it. The client also stops new submissions within a group
  after its configurable error budget, instead of flooding a broken endpoint.
- **Real timestamp rounding.** YUE contains 230 end boundaries beyond the actual
  recording, with a maximum overrun of 5 ms. The former one-sample tolerance
  rejected this valid public input. Preparation now allows a configurable 10 ms
  tolerance, logs every clamp, and preserves original reference timestamps.
  Larger overruns still fail. All 8,807 YUE segments were prepared; none were skipped.
- **CUDA major-version mismatch.** The base vLLM environment installs Torch
  2.13.0+cu130. The host's R550 driver alone failed CUDA initialization. A freshly
  downloaded NVIDIA 580.65.06 compatibility package and a per-invocation
  `LD_LIBRARY_PATH` enabled this local run. The [base README](../Fun-ASR-Nano/vllm/README.md#cuda-driver-check)
  gives the driver prerequisite, package checksum and explicit configuration.
  R550 is not a supported target in NVIDIA's current compatibility matrix;
  successful execution here is not a support guarantee for that driver family.
- **Ray socket paths.** Our long shared-filesystem temporary directory made the
  generated Unix socket exceed 107 bytes. A shorter `RAY_TMPDIR` resolved it.
  This was a deployment-path issue, not a model failure; the documented short-path
  requirement now includes a concrete length guideline.
- **Interrupted service cleanup.** Interrupting the initial failed Whisper run
  through a tmux wrapper left a detached service. Cleanup now tolerates repeated
  interruption, handles SIGTERM/SIGHUP during startup, and terminates surviving
  members of its own process group even if the API parent has already exited.

The clean install used approximately 35 GB for four model environments, 17 GB
for model cache, 32 GB for the package cache, and 6.3 GB for the selected source
dataset groups, before prepared clips and repeated run directories. Package
copies were used in this test. Storage use varies with cache/link policy; allow
space for environments, download caches and cropped audio, not only weights.

## Export, resume and automated checks

MLT first ran with two actors on one GPU, resumed with six actors per GPU on two
GPUs, then resumed on all four GPUs with 24 distinct actors (six per GPU).
`actors.json` verified placement. The final resume preserved all 5,178 saved
segment keys and processed the remaining 6,702 in 455.6 s of client wall time.
The completed 11,880-row file had no duplicate segment keys. The full MLT run
kept its published worker/launcher code unchanged while resuming; its only initial
deployment fix was shortening `RAY_TMPDIR`. A separate two-clip MLT run then
validated the final patched shared launcher and completed inference/export with
zero errors or empty predictions in a new work directory.

Completed staging outputs were processed by the repository's unchanged
`data_process/convert_staging.py`. Recording IDs, original timestamps and text
matched the direct flat exports exactly. Raw outputs were checked for complete
key coverage, unique segment keys, string hypotheses and no model/request errors.
Source segment annotations, including reference/entity metadata, were also compared
against the downloaded HF metadata and remained unchanged in staging.

All **20** CPU contract/preparation/lifecycle tests passed in the fresh tools
environment. Coverage includes request-field allowlists and reference exclusion,
empty/error retries, resume guards, the bounded error budget, first-request
continuation without duplicates, relative audio paths, safe archive reads,
stereo conversion/resampling, end-clamp reporting, category/language routing,
venv symlink handling, the pinned Ray model-input contract, and actual process
cleanup on SIGINT/SIGTERM/SIGHUP during server startup.

The package installs also recorded exact Torch/Transformers versions: Qwen and
Whisper used Torch 2.9.1 + Transformers 4.57.6; base used Torch 2.13.0 +
Transformers 5.18.0; MLT used Torch 2.6.0 + Transformers 4.57.6. These are separate
venvs, not a claim that one shared environment can serve all three models.

The downloaded Qwen checkpoint resolved to
`7278e1e70fe206f11671096ffdd38061171dd6e5`, and Whisper to
`06f233fe06e710322aca913c1bc4249a0d71fce1`. Their launchers now pin these tested
revisions instead of following a moving upstream default; `MODEL_REVISION`
provides an explicit override. FunASR checkpoint revisions were already pinned.
All four final environments passed `uv pip check`.

## Earlier model integration checks

Before this full-group reproduction, four clips per backend were tested from
public archives: JPN/KOR for Qwen, ECM-CH/ECM-EN for Whisper and base, and ARE/KOR
for MLT. All 16 completed without errors or empty predictions. Those vLLM checks
reused existing model environments, which is why they did not reveal the clean
Whisper installation failure.

The integration work also found and fixed venv symlink resolution selecting
system Python, the MLT model's requirement for Tensor rather than NumPy input,
and its `max_length` generation argument. The MLT configuration declares an
optional CTC alignment branch whose weights are absent; `ctc_decoder=None`
explicitly disables it for text-only ASR. That override remains recorded and
documented, rather than being presented as working CTC alignment.

## Scope limits

This validates installation, selected complete groups, inference and export;
it does not reproduce leaderboard WER/CER/BWER/BCER scores or every language.
No Older-Children data is present in the pinned public HF snapshot. Other GPU
architectures and host-driver configurations remain untested. The traditional
MLT backend and native base backend use different checkpoints; their outputs
must retain different model labels. Passing requests does not establish transcript
accuracy or the absence of rare repetitive decoding. A finite successful Whisper
batch is not a proof that all possible long-running memory-growth cases are fixed.
