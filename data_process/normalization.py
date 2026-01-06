#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================
📌 JSON 文本归一化脚本 — 自动国家识别，稳态大规模处理
===============================================

输入路径结构要求：

INPUT_ROOT/
 ├─ <BATCH_NAME>/
 │    ├─ hyp/
 │    │    └─ <LANG_CODE>/
 │    │           ├─ xx.json
 │    │           └─ ...
 │    └─ ref/
 │         ├─ <LANG_CODE>.json
 │         └─ ...

输出目录结构镜像 INPUT_ROOT
===============================================
"""

import os
import sys
import json
from glob import glob
from multiprocessing import Pool, cpu_count
import traceback
from tqdm import tqdm
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from text_norm import get_normalizer

# 全局
PROCESS_IN = None
PROCESS_OUT = None
PROCESS_REF = True

FAIL_LOG = "normalize_fail.log"


def safe_write(path, data):
    """确保不会写坏 JSON"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


############################################################
# 单文件处理
############################################################
def process_one(path_in: str):
    try:
        rel = os.path.relpath(path_in, PROCESS_IN)
        path_out = os.path.join(PROCESS_OUT, rel)

        # 如果已存在 -> 跳过（断点续执行）
        if os.path.exists(path_out):
            return True

        parts = rel.split(os.sep)
        if len(parts) < 3:
            return False

        second = parts[1]

        # ref: batch/ref/CHN.json
        if second == "ref":
            if not PROCESS_REF:
                return False
            country = os.path.splitext(os.path.basename(rel))[0]
        # hyp: batch/hyp/CHN/*.json
        elif second == "hyp":
            if len(parts) < 4:
                return False
            country = parts[2]
        else:
            return False

        os.makedirs(os.path.dirname(path_out), exist_ok=True)

        with open(path_in, "r", encoding="utf-8") as f:
            data = json.load(f)

        normalizer = get_normalizer(country)

        if isinstance(data, dict):
            if "text" in data:
                data["text"] = normalizer(data["text"])
        else:
            for item in data:
                if isinstance(item, dict) and "text" in item:
                    item["text"] = normalizer(item["text"])

        safe_write(path_out, data)
        return True

    except Exception:
        with open(FAIL_LOG, "a", encoding="utf-8") as fw:
            fw.write(path_in + "\n")
        print(f"❌ Error: {path_in}")
        traceback.print_exc()
        return False


############################################################
# 主入口
############################################################
def normalize_folder(
        input_root="data/text",
        output_root="data/text_normalized",
        process_ref=True,
        workers=None
):
    global PROCESS_IN, PROCESS_OUT, PROCESS_REF
    PROCESS_IN = os.path.abspath(input_root)
    PROCESS_OUT = os.path.abspath(output_root)
    PROCESS_REF = process_ref

    os.makedirs(PROCESS_OUT, exist_ok=True)

    print("\n📂 输入:", PROCESS_IN)
    print("📁 输出:", PROCESS_OUT)
    print(f"📝 是否处理 ref: {process_ref}")

    # 查找所有 JSON
    hyp_files = glob(os.path.join(PROCESS_IN, "*", "hyp", "*", "*.json"))
    ref_files = glob(os.path.join(PROCESS_IN, "*", "ref", "*.json")) if process_ref else []

    files = sorted(hyp_files + ref_files)

    print(f"🔍 hyp 数: {len(hyp_files)}")
    if process_ref:
        print(f"🔍 ref 数: {len(ref_files)}")
    print(f"👉 待处理总计: {len(files)}")

    if not files:
        print("❌ 无 JSON，请检查目录结构")
        return

    # 自适应 CPU + IO
    #cpu = cpu_count()
    cpu = 8
    if workers is None:
        workers = min(8, max(2, cpu // 8))  # I/O友好配置
    print(f"⚙️ 启动并行进程数: {workers}/{cpu}")

    t0 = time.time()

    with Pool(processes=workers) as pool:
        list(tqdm(
            pool.imap_unordered(process_one, files),
            total=len(files),
            desc="🚀 Normalizing",
            ncols=100
        ))

    print(f"\n✨ 完成！耗时 {time.time() - t0:.2f}s")
    print("📌 输出文件:", PROCESS_OUT)
    print("📌 错误日志:", FAIL_LOG)


############################################################
if __name__ == "__main__":
    normalize_folder()
