#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
from pathlib import Path
import gradio as gr
from shutil import copyfile

# === Local Imports ===
from build_gradio.compute_wer_gradio import run_compute_wer
from data_process.normalization import run as norm_hyp


# -----------------------------
# Global Settings
# -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GRADIO_ROOT = PROJECT_ROOT / "build_gradio"
QUERY_ROOT = GRADIO_ROOT / "query"

REF_ROOT_BASE = PROJECT_ROOT / "data" / "text"      # 读取三个 batch 的 ref
NORM_SCRIPT_ROOT = PROJECT_ROOT / "data"            # normalization 默认根

BATCHES = ["testbatch", "20251212", "20251205"]

CER_LANGS = ["JPN", "KOR", "THA", "CHN"]


# ============================================================
# Helper: load JSON safely
# ============================================================
def load_json_file(p):
    try:
        return json.load(open(p, "r", encoding="utf-8"))
    except:
        return None


# ============================================================
# Main processing logic
# ============================================================
def process_request(uploaded_files):

    if not uploaded_files:
        return "❌ 请上传 JSON 文件", None, None, None, None

    # -------------------------------
    # Step 1 — create temp_root
    # -------------------------------
    session_id = uuid.uuid4().hex[:10]
    temp_root = QUERY_ROOT / session_id
    text_root = temp_root / "text" / "gradio_batch"
    hyp_root = text_root / "hyp"
    ref_root = text_root / "ref"
    norm_root = temp_root / "text_normalized" / "gradio_batch"
    results_root = temp_root / "results"

    hyp_root.mkdir(parents=True, exist_ok=True)
    ref_root.mkdir(parents=True, exist_ok=True)

    # -------------------------------
    # Step 2 — load hyp JSONs, detect model & country
    # -------------------------------
    detected_country = None
    detected_model = None

    merged_hyp = []   # batch 合并后的 hyp

    for file_obj in uploaded_files:
        js = load_json_file(file_obj.name)
        if js is None:
            return f"❌ JSON 解析失败: {file_obj.name}", None, None, None, None

        # detect country from filename: "IRQ_xxxx.json" → "IRQ"
        fname = os.path.basename(file_obj.name)
        country = fname[:3]

        # detect model from first item
        if not js:
            return f"❌ JSON 内无内容: {file_obj.name}", None, None, None, None
        model = js[0].get("model", "").strip()
        if not model:
            return f"❌ 未找到 model 字段: {file_obj.name}", None, None, None, None

        # enforce consistency
        if detected_country is None:
            detected_country = country
        elif detected_country != country:
            return f"❌ 多个国家混合: {detected_country} vs {country}", None, None, None, None

        if detected_model is None:
            detected_model = model
        elif detected_model != model:
            return f"❌ 多个模型混合: {detected_model} vs {model}", None, None, None, None

        # merge hyp
        merged_hyp.extend(js)

    # -------------------------------
    # Step 3 — write merged HYP into temp_root (deterministic name)
    # -------------------------------
    hyp_country_dir = hyp_root / detected_country
    hyp_country_dir.mkdir(parents=True, exist_ok=True)

    merged_hyp_path = hyp_country_dir / f"{detected_country}_{detected_model}.json"
    json.dump(merged_hyp, open(merged_hyp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # -------------------------------
    # Step 4 — copy REF from original 3 batches
    # -------------------------------
    for batch in BATCHES:
        batch_ref_dir = REF_ROOT_BASE / batch / "ref" / detected_country
        if batch_ref_dir.exists():
            out_dir = ref_root / batch / detected_country
            out_dir.mkdir(parents=True, exist_ok=True)

            for f in batch_ref_dir.glob("*.json"):
                copyfile(f, out_dir / f.name)

    # -------------------------------
    # Step 5 — normalization (only hyp)
    # -------------------------------
    norm_hyp(
        hyp_root=str(text_root),
        out_root=str(norm_root),
        target_country=detected_country
    )

    # -------------------------------
    # Step 6 — compute WER/CER
    # -------------------------------
    metric = "cer" if detected_country in CER_LANGS else "wer"

    run_compute_wer(
        ref_base=str(ref_root),
        hyp_base=str(norm_root),
        out_base=str(results_root)
    )

    # -------------------------------
    # Step 7 — deterministic output paths
    # -------------------------------
    summary_file = results_root / detected_country / detected_model / f"{metric}-summary-{detected_country}-{detected_model}.txt"
    errs_file = results_root / detected_country / detected_model / f"errs-{detected_country}-{detected_model}.txt"
    recogs_file = results_root / detected_country / detected_model / f"recogs-{detected_country}-{detected_model}.txt"

    if not summary_file.exists():
        return f"❌ summary 文件不存在: {summary_file}", None, None, None, None

    summary_text = open(summary_file, "r", encoding="utf-8").read()
    errs_text = open(errs_file, "r", encoding="utf-8").read() if errs_file.exists() else "（无错误文件）"

    # -------------------------------
    # 返回结果 (保持临时目录可见)
    # -------------------------------
    return (
        f"国家: {detected_country}\n模型: {detected_model}\n\n" + summary_text,
        errs_text,
        str(recogs_file),
        str(temp_root),
        str(summary_file)
    )


# ============================================================
# Gradio UI
# ============================================================
def build_ui():
    with gr.Blocks(title="ASR-Bench WER Evaluator") as demo:
        gr.Markdown("## 🔍 ASR-Bench 在线 WER/CER 评估")

        with gr.Row():
            file_box = gr.File(label="上传多个 HYP JSON", file_count="multiple", type="file")

        run_btn = gr.Button("开始计算 WER")

        summary_out = gr.Textbox(label="WER / CER 结果（含错误统计）", lines=12)
        errs_out = gr.Textbox(label="插入/删除/替换 详细错误", lines=12)
        recogs_out = gr.File(label="下载 recogs 文件")
        temp_path_out = gr.Textbox(label="临时目录路径（保留）")
        summary_path_out = gr.Textbox(label="summary 文件路径")

        run_btn.click(
            fn=process_request,
            inputs=[file_box],
            outputs=[summary_out, errs_out, recogs_out, temp_path_out, summary_path_out]
        )

    return demo


if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860)
