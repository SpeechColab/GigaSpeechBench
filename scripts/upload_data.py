#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将本地 Dialect-testbatch 目录【原样结构】上传到 HuggingFace Dataset Repo

本地：
/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/
└── data/Multilingual-ASR-Benchmark/audio/Dialect-testbatch
    ├── JIN/
    │   ├── index.txt
    │   ├── JIN#unknown#xxx.wav
    ├── XIANG/
    └── ...

HF Repo（完全一致）：
AlexTYJ/Multilingual-ASR-Benchmark
└── audio/Dialect-testbatch
    ├── JIN/
    ├── XIANG/
    └── ...
"""

from huggingface_hub import HfApi
from pathlib import Path

# =========================
# HF 配置
# =========================

HF_TOKEN = "REDACTED_HF_TOKEN"
REPO_ID = "AlexTYJ/Multilingual-ASR-Benchmark"
REPO_TYPE = "dataset"

api = HfApi(token=HF_TOKEN)

# =========================
# 本地路径（你给的）
# =========================

LOCAL_FOLDER = Path(
    "/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/"
    "data/Multilingual-ASR-Benchmark/audio/Dialect-testbatch"
)

assert LOCAL_FOLDER.exists(), f"本地路径不存在: {LOCAL_FOLDER}"

# =========================
# 上传（结构完全一致）
# =========================

api.upload_folder(
    folder_path=str(LOCAL_FOLDER),
    repo_id=REPO_ID,
    repo_type=REPO_TYPE,
    path_in_repo="audio/Dialect-testbatch",  # ✅ 与本地一致
    allow_patterns=["*.wav", "*.txt", "*.json"],
    commit_message="Upload Dialect-testbatch audio (structure-preserved)",
)

print("✅ Upload Done! 目录结构与本地完全一致")
