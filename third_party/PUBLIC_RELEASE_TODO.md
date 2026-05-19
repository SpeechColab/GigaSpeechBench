# Public Release TODO

Secondary issues identified during cleanup that should be addressed before or after public release, but were intentionally **not fixed** during this cleanup mission to avoid changing functional behavior.

## 1. `breakpoint()` call in whisper-large-v3

- **File**: `third_party/whisper-large-v3/whisper_asr.py:223`
- **Issue**: A `breakpoint()` call remains in the production code. This will trigger a Python debugger pause if that line is reached during execution.
- **Recommendation**: Remove or replace with `logging.debug()` or a conditional debug flag.
- **Severity**: Medium — only triggers if specific code path is reached; unlikely in normal batch usage but possible during error handling.

## 2. Chinese Hugging Face mirror URL (`hf-mirror.com`)

- **File**: `third_party/whisper-large-v3/install_model.sh:4`
- **Issue**: The script downloads models from `hf-mirror.com`, a Chinese mirror of Hugging Face. This is useful for users in China who cannot access huggingface.co directly, but international users may prefer the official URL.
- **Recommendation**: Consider making the mirror URL configurable (via environment variable or CLI flag) rather than hardcoded. Default to `huggingface.co` for international users.
- **Severity**: Low — functional for Chinese users; may cause confusion for international users expecting official HuggingFace.

## 3. Real Google Cloud project IDs in Chirp3

- **Files**: 
  - `third_party/Chirp3/Chirp3.py:25` — `project_id="steady-fin-478206-g9"`
  - `third_party/Chirp3/run_syr_missing.py:33` — `project_id="steady-fin-478206-g9"`
  - `third_party/Chirp3/Chirp3.py:29` — `location="us-central1"`
- **Issue**: These are real Google Cloud project IDs and regions used by the original authors. While functional for users who have access to these specific projects, other users will need to replace them with their own project IDs.
- **Recommendation**: Replace hardcoded project IDs with placeholders like `YOUR_PROJECT_ID` and `YOUR_REGION` in the default values, while keeping the current values as commented examples.
- **Severity**: Low — the argparse defaults work for users with access to the specific project; other users can override via CLI args.
