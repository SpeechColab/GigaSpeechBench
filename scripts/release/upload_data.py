#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Upload YUE dataset tarball to HuggingFace Dataset Repo.
"""

import os
from huggingface_hub import HfApi
from pathlib import Path

# 禁用 node uploader（避免 OOM）
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

# =========================
# HF 配置
# =========================

HF_TOKEN = "REDACTED_HF_TOKEN"
REPO_ID = "AlexTYJ/Multilingual-ASR-Benchmark"
REPO_TYPE = "dataset"

api = HfApi(token=HF_TOKEN)

# =========================
# 本地文件
# =========================

LOCAL_FILE = Path(
"/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/Multilingual-ASR-Benchmark/Low-Resource-Languages/audio/JPN_KOR_hard/JPN_20260323.tar.gz"
)

assert LOCAL_FILE.exists(), f"❌ 文件不存在: {LOCAL_FILE}"

# =========================
# 上传
# =========================

print(f"⬆️ Uploading {LOCAL_FILE.name} ...")

api.upload_file(
    path_or_fileobj=str(LOCAL_FILE),
    path_in_repo=f"Low-Resource-Languages/audio/JPN_KOR_hard/{LOCAL_FILE.name}",
    repo_id=REPO_ID,
    repo_type=REPO_TYPE,
    commit_message=f"Upload {LOCAL_FILE.name}",
)

print("✅ Upload finished!")