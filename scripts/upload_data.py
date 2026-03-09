#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Upload FLEURS submit tarballs to HuggingFace Dataset Repo.

Local files:
- fleurs_audio.tar.gz
- fleurs_text_ref.tar.gz

HF Repo structure:
fleurs/
├── fleurs_audio.tar.gz
└── fleurs_text_ref.tar.gz
"""

from huggingface_hub import HfApi
from pathlib import Path

# =========================
# HF 配置
# =========================

HF_TOKEN = "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"
REPO_ID = "AlexTYJ/Multilingual-ASR-Benchmark"
REPO_TYPE = "dataset"

api = HfApi(token=HF_TOKEN)

# =========================
# 本地路径
# =========================

SUBMIT_DIR = Path(
    "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/common-voice/submit"
)

AUDIO_TAR = SUBMIT_DIR / "common-voice_audio.tar.gz"
TEXT_TAR = SUBMIT_DIR / "common-voice_text_ref.tar.gz"

for p in [AUDIO_TAR, TEXT_TAR]:
    assert p.exists(), f"❌ 文件不存在: {p}"

# =========================
# 单文件上传（大文件最稳）
# =========================

def upload_one(local_path: Path):
    print(f"⬆️  Uploading {local_path.name} ...")
    api.upload_file(
        path_or_fileobj=str(local_path),
        path_in_repo=f"common-voice/{local_path.name}",
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        commit_message=f"Upload {local_path.name}",
    )
    print(f"✅ Done: {local_path.name}")


# =========================
# 执行
# =========================

upload_one(AUDIO_TAR)
upload_one(TEXT_TAR)

print("🎉 FLEURS submit upload finished successfully!")
