#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================
📌 ASR-Bench 多源数据对齐与全量评测脚本 (防 null 终极版)
================================================

功能：
- 读取 RAW HYP 获取原始识别文本。
- 读取 NORM HYP 获取归一化识别文本（用于计算 WER/CER）。
- 读取 REF 获取原文与归一化参考文本。
- 将上述所有字段及 I/D/S 统计数据合并，生成最终带 Metrics 的 JSON。
- 生成语料库级别的 txt 统计报告 (层级: 国家/BATCH/模型)。
- 全局防御 null 导致的崩溃。
"""

import os
import json
import logging
import traceback
from pathlib import Path
from collections import defaultdict
from multiprocessing import Pool
from tqdm import tqdm
import kaldialign
import gc

# =========================
# 日志配置
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# 常量与语言配置
# =========================
WER_LANGS = ["IRQ","DZA","ARE","EGY","MAR","SAU","IDN","MYS","PHL","VNM","SYR","USA",
             "CHN-EN","IDN-EN","JPN-EN","PHL-EN","SCT-EN","SGP-EN","AGR-EN","AIT-EN",
             "ART-EN","BIO-EN","ECM-EN","EDU-EN","ENG-EN","ENT-EN","FIN-EN","HUM-EN",
             "LAW-EN","MED-EN","MIL-EN"]
CER_LANGS = ["JPN","KOR","THA","CHN","JIN","XIANG","YUE","WU","MIN","AGR-CH","AIT-CH",
             "ART-CH","BIO-CH","ECM-CH","EDU-CH","ENG-CH","ENT-CH","FIN-CH","HUM-CH",
             "LAW-CH","MED-CH","MIL-CH"]
ERR = "*"
MATCH_TOL = 0.1

# =========================
# 路径配置 (💡 以后只需修改这里)
# =========================
DATASET_NAME = "Low-Resource-Languages"  # 例如改为 "Low-Resource-Languages"
BATCH_NAME = "ALL"

# 1. 原始 HYP 文本路径 (获取 text)
RAW_HYP_ROOT = f"/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text/{DATASET_NAME}/hyp"

# 2. 归一化 HYP 文本路径 (获取 text_normalized)
NORM_HYP_ROOT = f"/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/Multilingual-ASR-Benchmark/data/text_normalized/{DATASET_NAME}/hyp"

# 3. REF 路径 (包含 batch/<country>.json)
REF_ROOT = f"/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/ASRBench_gradio/{DATASET_NAME}/text/ref"

# 4. 最终输出路径
OUT_JSON_ROOT = f"/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/ASRBench_gradio/{DATASET_NAME}/text/hyp"
OUT_REPORT_ROOT = f"/inspire/hdd/project/multilingualspeechrecognition/chenxie-25019/yujietu/data/ASRBench_gradio/{DATASET_NAME}/text/reports"

# =========================
# 核心函数
# =========================

def norm_audio_name(name: str) -> str:
    """归一化 audio_name，去掉后缀以便精准匹配"""
    if not name: return ""
    name = name.replace("\\", "/")
    base = os.path.basename(name)
    for ext in [".wav", ".mp3", ".mp4", ".flac", ".m4a", ".ogg"]:
        if base.lower().endswith(ext):
            base = base[:-len(ext)]
            break
    return base

def write_errs_and_summary(out_dir, country, model, stats, compute_CER):
    """写入语料库级别的 txt 报告"""
    N = stats["N"]
    err = stats["S"] + stats["D"] + stats["I"]
    wer = 100.0 * err / N if N > 0 else 0.0

    with open(out_dir / f"errs-{country}-{model}.txt", "w", encoding="utf8") as f:
        print(f"%WER = {wer:.2f}", file=f)
        print(f"Errors: {stats['I']} insertions, {stats['D']} deletions, "
              f"{stats['S']} substitutions, over {N} units ({stats['C']} correct)", file=f)

    metric = "cer" if compute_CER else "wer"
    with open(out_dir / f"{metric}-summary-{country}-{model}.txt", "w", encoding="utf8") as f:
        print("model\tWER/CER", file=f)
        print(f"{model}\t{wer:.2f}", file=f)

# =========================
# 业务逻辑
# =========================

def process_country_eval(country):
    """处理单个国家的数据对齐与评测"""
    try:
        # --- 路径定义 ---
        ref_path = os.path.join(REF_ROOT, country, BATCH_NAME, f"{country}.json")
        norm_hyp_dir = os.path.join(NORM_HYP_ROOT, country)
        raw_hyp_dir = os.path.join(RAW_HYP_ROOT, country)
        
        if not os.path.exists(ref_path): return f"⚠️ {country}: 未找到 REF 文件 ({ref_path})"
        if not os.path.exists(norm_hyp_dir): return f"⚠️ {country}: 未找到 NORM HYP 目录"

        compute_CER = country in CER_LANGS
        metric_key = "cer" if compute_CER else "wer"

        # --- 1. 加载 REF 并建立索引 ---
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_items = json.load(f)
        
        ref_index = defaultdict(list)
        for r in ref_items:
            ref_index[norm_audio_name(r.get("audio_name", ""))].append(r)

        # --- 2. 遍历模型 ---
        json_files = [f for f in os.listdir(norm_hyp_dir) if f.endswith(".json")]
        
        for hfn in json_files:
            model = hfn[:-5]
            
            # 读取 NORM HYP
            with open(os.path.join(norm_hyp_dir, hfn), "r", encoding="utf-8") as f:
                norm_hyp_items = json.load(f)

            # 读取 RAW HYP
            raw_hyp_items = []
            raw_path = os.path.join(raw_hyp_dir, hfn)
            if os.path.exists(raw_path):
                with open(raw_path, "r", encoding="utf-8") as f:
                    raw_hyp_items = json.load(f)
            
            # 建立 RAW HYP 索引
            raw_hyp_index = defaultdict(list)
            for h in raw_hyp_items:
                raw_hyp_index[norm_audio_name(h.get("audio_name", ""))].append(h)

            if not isinstance(norm_hyp_items, list): continue

            # 初始化报告数据
            stats = defaultdict(int)
            
            # 💡 确保层级为: OUT_REPORT_ROOT / 国家 / BATCH_NAME / 模型
            model_report_dir = Path(OUT_REPORT_ROOT) / country / BATCH_NAME / model
            model_report_dir.mkdir(parents=True, exist_ok=True)
            rec_f = open(model_report_dir / f"recogs-{country}-{model}.txt", "w", encoding="utf8")

            valid = 0
            final_json_data = []

            # --- 3. 对齐并计算 ---
            for h_norm in norm_hyp_items:
                name = norm_audio_name(h_norm.get("audio_name", ""))
                start_hyp = float(h_norm.get("start", 0.0))
                end_hyp = float(h_norm.get("end", 0.0))
                
                # 获取 Normalized HYP (防御 null)
                hyp_text_norm = h_norm.get("text_normalized") or h_norm.get("text") or ""

                # 寻找对应的 RAW HYP (防御 null)
                hyp_text_raw = hyp_text_norm # Fallback
                for h_raw in raw_hyp_index.get(name, []):
                    if (
                        abs(float(h_raw.get("start", 0.0)) - start_hyp) <= MATCH_TOL
                        and abs(float(h_raw.get("end", 0.0)) - end_hyp) <= MATCH_TOL
                    ):
                        hyp_text_raw = h_raw.get("text") or ""
                        break

                # 寻找对应的 REF
                matched_ref = None
                for r in ref_index.get(name, []):
                    if (
                        abs(float(r.get("start", 0.0)) - start_hyp) <= MATCH_TOL
                        and abs(float(r.get("end", 0.0)) - end_hyp) <= MATCH_TOL
                    ):
                        matched_ref = r
                        break

                # 构造基础 Item
                new_item = {
                    "audio_name": h_norm.get("audio_name", ""),
                    "start": h_norm.get("start", 0.0),
                    "end": h_norm.get("end", 0.0),
                    "text": hyp_text_raw,                # 原文来自 RAW_HYP
                    "text_normalized": hyp_text_norm,    # 归一化来自 NORM_HYP
                    "model": h_norm.get("model", model)
                }

                # 注入 REF 数据并计算评测指标
                if matched_ref:
                    valid += 1
                    # 防御 REF 里的 null
                    ref_raw = matched_ref.get("text") or ""
                    ref_norm = matched_ref.get("text_normalized") or ref_raw

                    # 分词进行对齐
                    if compute_CER:
                        ref_tok = list(ref_norm.replace(" ", ""))
                        hyp_tok = list(hyp_text_norm.replace(" ", ""))
                    else:
                        ref_tok = ref_norm.split()
                        hyp_tok = hyp_text_norm.split()

                    I = D = S = C = N = 0
                    if not ref_tok and not hyp_tok:
                        pass
                    elif not ref_tok and hyp_tok:
                        I = len(hyp_tok)
                    else:
                        ali = kaldialign.align(ref_tok, hyp_tok, ERR)
                        for a, b in ali:
                            if a == ERR: I += 1
                            elif b == ERR: D += 1; N += 1
                            elif a != b: S += 1; N += 1
                            else: C += 1; N += 1

                    stats["I"] += I; stats["D"] += D; stats["S"] += S; stats["C"] += C; stats["N"] += N

                    # 记录评测结果到 item
                    new_item["ref_text"] = ref_raw
                    new_item["ref_text_normalized"] = ref_norm
                    new_item[metric_key] = round((I + D + S) / N, 4) if N > 0 else 0.0
                    new_item["insertions"] = I
                    new_item["deletions"] = D
                    new_item["substitutions"] = S
                    new_item["ref_length"] = N

                    # 写入 recogs.txt
                    cut_id = f"{name}_{start_hyp}"
                    print(f"{cut_id}:\tref={' '.join(ref_tok)}", file=rec_f)
                    print(f"{cut_id}:\thyp={' '.join(hyp_tok)}", file=rec_f)
                
                else:
                    # 未匹配上的数据也保留，但置空
                    new_item["ref_text"] = None
                    new_item["ref_text_normalized"] = None
                    new_item[metric_key] = None
                    new_item["insertions"] = None
                    new_item["deletions"] = None
                    new_item["substitutions"] = None
                    new_item["ref_length"] = None

                final_json_data.append(new_item)

            rec_f.close()

            # 生成报告
            write_errs_and_summary(model_report_dir, country, model, stats, compute_CER)
            with open(model_report_dir / "segment_check.txt", "w", encoding="utf8") as f:
                f.write(f"ref_segments={len(ref_items)}\nhyp_segments={len(norm_hyp_items)}\nmatched_segments={valid}\n")

            # --- 4. 写入最终带 Metrics 的 JSON ---
            out_json_dir = Path(OUT_JSON_ROOT) / country / BATCH_NAME
            out_json_dir.mkdir(parents=True, exist_ok=True)
            
            with open(out_json_dir / hfn, "w", encoding="utf-8") as f:
                json.dump(final_json_data, f, ensure_ascii=False, indent=2)

        del ref_items
        gc.collect()

        return f"✅ {country}: 完成评测并合并 JSON (共 {len(json_files)} 个模型)"

    except Exception:
        return f"❌ {country} 报错: {traceback.format_exc()}"

# =========================
# 主入口
# =========================

def main(workers=12):
    os.makedirs(OUT_JSON_ROOT, exist_ok=True)
    os.makedirs(OUT_REPORT_ROOT, exist_ok=True)

    countries = sorted([
        d for d in os.listdir(REF_ROOT) 
        if os.path.isdir(os.path.join(REF_ROOT, d))
    ])

    logging.info("====== 🚀 开始多源数据对齐与评测 ======")
    logging.info(f"📁 当前 Dataset: {DATASET_NAME}")
    logging.info(f"📁 当前 Batch: {BATCH_NAME}")
    logging.info(f"📁 最终 JSON 输出: {OUT_JSON_ROOT}")
    logging.info(f"📁 统计报告输出: {OUT_REPORT_ROOT}")

    with Pool(processes=workers) as pool:
        results = list(tqdm(pool.imap_unordered(process_country_eval, countries), 
                           total=len(countries), desc="Evaluating"))
        
        for r in results:
            if "❌" in r or "⚠️" in r:
                logging.warning(r)

    logging.info("====== 🎉 评测与合并任务全部完成 ======")

if __name__ == "__main__":
    main()