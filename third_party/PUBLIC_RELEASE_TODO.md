# Public Release TODO

Secondary issues that were identified during cleanup but intentionally **not fixed** in this mission,
because they do not affect functionality or are out of scope for a content/translation cleanup.

## 1. `breakpoint()` Call in Production Code

- **File**: `whisper-large-v3/whisper_asr.py`
- **Line**: 223
- **Issue**: A `breakpoint()` call exists in production code. This will trigger a Python debugger pause if the condition is met, which is not appropriate for a public release.
- **Recommendation**: Remove or replace with a logging statement or error-handling logic before public release.

## 2. Chinese Hugging Face Mirror URL (`hf-mirror.com`)

- **Files**:
  - `whisper-large-v3/install_model.sh`
  - `whisper-large-v3/hfd.sh`
- **Issue**: These scripts use `hf-mirror.com` (a Chinese mirror of Hugging Face) instead of the official `huggingface.co`. This may be intentional for users in regions with restricted access to Hugging Face, but could also confuse international users.
- **Recommendation**: Consider adding a comment explaining why `hf-mirror.com` is used, or provide an option to switch to the official URL. Alternatively, replace with the official `huggingface.co` URL if the mirror is not strictly necessary.

## 3. Real Google Cloud Project IDs in Chirp3 Scripts

- **Files**:
  - `Chirp3/Chirp3.py`
  - `Chirp3/run_syr_missing.py`
- **Issue**: These files contain hardcoded real Google Cloud project IDs (`steady-fin-478206-g9`, `project-b8b84a33-1939-4f27-bda`) that could be considered sensitive information if they are not meant to be public.
- **Recommendation**: Replace with placeholder project IDs (e.g., `your-gcp-project-id`) before public release, or confirm these IDs are intentionally public and meant to be shared.
