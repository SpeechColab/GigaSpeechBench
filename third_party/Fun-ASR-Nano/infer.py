"""Batch inference using a local fun-asr-nano vLLM service."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vllm_asr"))
from client import main


if __name__ == "__main__":
    main("funasr")
