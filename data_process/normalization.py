#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================
📌 JSON 文本归一化脚本 — 自动国家识别，稳态大规模处理
===============================================

修复语义（确认版）：
- 单句 text 归一化失败 → 保持原样
- JSON 文件始终生成
- 仅在文件级错误时记录到 normalize_fail.log
===============================================
"""

import os
import sys
import json
from glob import glob
from multiprocessing import Pool
import traceback
from tqdm import tqdm
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from text_norm import get_normalizer  # noqa

# 全局
PROCESS_IN = None
PROCESS_OUT = None
PROCESS_REF = True

FAIL_LOG = "normalize_fail.log"

MODEL_KEYS = {
    "model", "model_name", "modelname", "asr_model", "asrmodel",
    "system", "system_name", "engine", "engine_name",
    "recognizer", "recognizer_name", "name", "backend"
}


def safe_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def upper_model_name_in_json(obj):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            lk = str(k).lower()
            if lk in MODEL_KEYS and isinstance(v, str):
                obj[k] = v.upper()
            else:
                upper_model_name_in_json(v)
    elif isinstance(obj, list):
        for it in obj:
            upper_model_name_in_json(it)


############################################################
# 单文件处理
############################################################
def process_one(path_in: str):
    try:
        rel = os.path.relpath(path_in, PROCESS_IN)
        parts = rel.split(os.sep)
        if len(parts) < 3:
            return False

        second = parts[1]
        path_out = os.path.join(PROCESS_OUT, rel)

        if second == "ref":
            if not PROCESS_REF:
                return False
            country = os.path.splitext(os.path.basename(rel))[0]
            out_rel = rel

        elif second == "hyp":
            if len(parts) < 4:
                return False
            country = parts[2]
            base = os.path.basename(rel)
            stem, ext = os.path.splitext(base)
            base_up = stem.upper() + ext
            out_rel = os.path.join(*parts[:-1], base_up)

        else:
            return False

        path_out = os.path.join(PROCESS_OUT, out_rel)

        if os.path.exists(path_out):
            return True

        os.makedirs(os.path.dirname(path_out), exist_ok=True)

        with open(path_in, "r", encoding="utf-8") as f:
            data = json.load(f)

        normalizer = get_normalizer(country)

        # ===============================
        # ⭐ FIX：sentence 级容错
        # ===============================
        if isinstance(data, dict):
            if "text" in data and isinstance(data["text"], str):
                try:
                    data["text"] = normalizer(data["text"])
                except Exception:
                    pass  # 保持原样

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                    try:
                        item["text"] = normalizer(item["text"])
                    except Exception:
                        pass  # 保持原样

        # 模型名字段转大写（不影响 text）
        upper_model_name_in_json(data)

        safe_write(path_out, data)
        return True

    except Exception:
        with open(FAIL_LOG, "a", encoding="utf-8") as fw:
            fw.write(path_in + "\n")
        print(f"❌ File-level Error: {path_in}")
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

    cpu = 8
    workers = 4
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


if __name__ == "__main__":
    normalize_folder()
