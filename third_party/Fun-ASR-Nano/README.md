# Fun-ASR-Nano: two checkpoints, two inference backends

The base and multilingual (MLT) checkpoints are different weights with different
language coverage. Changing a language option does not turn base into MLT.
This directory provides both production paths, selected by benchmark category:

| Category | Checkpoint | Backend | Implementation |
| --- | --- | --- | --- |
| Low-Resource-Languages (including Japanese) | Fun-ASR-MLT-Nano-2512 | Persistent Ray + FunASR replicas | [ray/](ray/) |
| Vertical-Domain | Fun-ASR-Nano-2512 base | Native vLLM | [vllm/](vllm/) |
| CH-EN-Dialects | Fun-ASR-Nano-2512 base | Native vLLM | [vllm/](vllm/) |
| Older-Children, if supplied locally | Fun-ASR-Nano-2512 base | Native vLLM | [vllm/](vllm/) |

## One command from a downloaded HF dataset

Run from the repository root. Requires Linux, `uv`, and a compatible NVIDIA GPU/driver.
The command installs the appropriate isolated environment, prepares clips, loads
models once per module, runs all selected groups, and exports official-format results.

```bash
# Multilingual checkpoint, two Ray replicas on one GPU.
bash third_party/vllm_asr/run.sh --model funasr --subset low-resource \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/funasr_mlt_r1 \
  --gpus 0 --actors-per-gpu 2

# Base checkpoint with vLLM, vertical-domain Chinese/English and dialects.
bash third_party/vllm_asr/run.sh --model funasr --subset zh-en \
  --data-root ./data/GigaSpeechBench --work-dir ./outputs/funasr_base_r1 --gpus 0
```

Add `--download` to obtain the selected HF audio archives and metadata automatically.
Add `--groups KOR ARE --limit-per-group 2` to the first command for a small test.
Use `--subset older-children` for a local compatible release. The pinned public
HF snapshot currently has no Older-Children category; the command reports this
instead of quietly skipping it. See the [complete workflow guide](../vllm_asr/ONE_CLICK.md).

## Limitations we do not hide

- **MLT is not native vLLM here.** We verified public native-vLLM weights for base;
  we did not find a publicly accessible equivalent MLT checkpoint. The MLT path
  uses the actual multilingual weights with Ray/FunASR. It is not a stub, silent
  substitution, or a claim of equivalent vLLM performance.
- **Separate environments are required.** The base environment pins vLLM 0.27.1
  and Torch 2.13.0. The recovered Ray environment pins FunASR 1.3.3, Ray 2.55.1,
  and Torch/torchaudio 2.6.0. Mixing these environments is unsupported.
- **Separate result labels are required.** Base exports as `Fun-ASR-Nano-2512`;
  MLT exports as `Fun-ASR-MLT-Nano-2512`. Published leaderboard entries named
  FUNASR-MLT-NANO use MLT and should not be compared as if base used the same weights.
- **Replicas cost memory.** Every Ray actor holds a full model. Start with two
  actors per GPU and tune `--actors-per-gpu` for your hardware. `--gpus 0,1`
  exposes two GPUs to Ray; replicas are reused across all selected groups.
- **MLT alignment weights are absent.** The tested MLT config declares an optional
  CTC branch without the corresponding checkpoint weights. The Ray path explicitly
  disables CTC alignment and records the setting; it performs ASR text decoding only.
- **Outputs can still be wrong or empty.** No transcript cleanup conceals model
  repetition. `--empty-retries 10` is an explicit optional policy. Persistent
  empty text stays `""`; repeated emptiness does not prove the recording is silent.
- **Validation has a defined scope.** A small smoke test checks execution and
  format, not full-benchmark quality or published-score reproducibility. Decoder,
  frontend, precision, and model variants can change the scores.

The former root-level `serve.sh`, `infer.py`, and `requirements.txt` now live under
`vllm/`; use the one-command entry point above or the backend-specific guides.

Upstream sources: [base native checkpoint](https://huggingface.co/FunAudioLLM/Fun-ASR-Nano-2512-vllm),
[MLT checkpoint](https://huggingface.co/FunAudioLLM/Fun-ASR-MLT-Nano-2512).

See the [validation record](../vllm_asr/VALIDATION.md) for the tested Ray and vLLM paths.
