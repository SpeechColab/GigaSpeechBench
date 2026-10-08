# Validation record (2026-10-08)

## Automated checks

All 15 tests passed in a newly created Python 3.12 tools environment. Coverage
includes multipart request allowlists, reference exclusion, empty/error retries,
resume guards, relative audio paths, archive and extracted-file input, stereo
conversion/resampling, entity preservation, category routing, Arabic country
codes, the venv interpreter symlink regression, and the pinned FunASR Tensor-input
and generation-limit contract.

The shell bootstrap created a fresh tools venv, installed its dependencies, and
prepared a real ECM-EN clip from the downloaded HF archive. Ray's pinned
requirements resolved and installed into a separate fresh model venv. The vLLM
checks used the existing pinned model environments; those full environments were
not reinstalled from scratch during this check.

## Real model execution

All tests below started from the public HF `metadata.json` and `audio.tar.gz`
layout and ran through preparation, model startup, inference, export and shutdown.
Each selected group used its first two valid segments.

| Model/backend | Groups | Clips | Request/model errors | Empty outputs |
| --- | --- | ---: | ---: | ---: |
| Qwen3-ASR-1.7B / vLLM 0.14.0 | JPN, KOR | 4 | 0 | 0 |
| Whisper large-v3 / vLLM 0.14.1 | ECM-CH, ECM-EN | 4 | 0 | 0 |
| Fun-ASR-Nano base / vLLM 0.27.1 | ECM-CH, ECM-EN | 4 | 0 | 0 |
| Fun-ASR-MLT-Nano / FunASR 1.3.3 + Ray 2.55.1 | ARE, KOR | 4 | 0 | 0 |

Hardware: H100 80 GB. The MLT test used two independently loaded actors on one
GPU. Their process identities and installed versions were captured in `actors.json`.
The local MLT weight SHA-256 and both configuration files matched the pinned
public HF revision. A subsequent MLT resume attempted zero new segments and left
the raw output byte-for-byte unchanged.

For all four paths, the generated staging files were read by the repository's
unchanged `data_process/convert_staging.py`. Its reference and hypothesis rows
matched our flat exports exactly in recording ID, timestamps and text.

## Issues found and resolved

- Resolving a supplied venv Python symlink selected system Python and lost the
  installed dependencies. The override now retains the venv executable path.
- The old Ray environment lacked a dependency needed by the shared modules.
  Installation from the new pinned requirements into a fresh environment was tested.
- The pinned FunASR model entry point requires a Torch Tensor rather than a NumPy
  audio array. The Ray worker now supplies Tensor audio.
- The token cap must be passed as `max_length` at the FunASR boundary, not repeated
  in `llm_kwargs`. Greedy generation and the 512-token cap are explicit.
- The MLT configuration declares optional CTC alignment modules whose weights are
  absent. `ctc_decoder=None` explicitly disables that branch for text-only ASR;
  this is recorded in the run spec and documented, not concealed as successful alignment.

## Scope limits

These are execution and format smoke tests, not a rerun of the full benchmark or
a reproduction of published scores. No Older-Children data is present in the
pinned public HF snapshot. Multi-GPU Ray scaling, all language groups, and other
GPU/driver combinations were not validated here. Dataset/model network downloads
use the HF client; the model execution checks reused already downloaded files.
