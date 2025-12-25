#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import uuid
from pathlib import Path
import gradio as gr

# ==========================================================
# Project root
# ==========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# ==========================================================
# 🧩 Imports from your offline pipeline (保持一致)
# ==========================================================
# 从 generate_hyp_json 复用 online 专用的 run_gradio + BATCHES & ROOT
from data_process.generate_hyp_json import (
    run_gradio as gen_hyp,
    BATCHES as OFFLINE_REF_BATCHES,
    ROOT as OFFLINE_TEXT_ROOT,
)

# 👉 归一化用 normalize_folder（你给的新版函数名）
from data_process.normalization import normalize_folder

# 👉 计算WER/CER
from build_gradio.compute_wer_gradio import run_compute_wer


# ==========================================================
# 常量
# ==========================================================
QUERY_ROOT = PROJECT_ROOT / "build_gradio" / "query"

# 需要走 CER 的语言
CER_LANGS = ["JPN", "KOR", "THA", "CHN"]


# ==========================================================
# Utils
# ==========================================================
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(e)
        return None


# ==========================================================
# 🌐 Gradio Online 主流程
# ==========================================================
def process_request(uploaded_files):

    # 一个 session 对应一次评估
    session_id = uuid.uuid4().hex[:10]

    if not uploaded_files:
        return (
            "❌ 未上传文件",
            "",
            None,
            "",
            "",
            session_id,
        )

    # ------------------------------------------------------
    # 🌲 session 临时根目录
    # ------------------------------------------------------
    temp_root = QUERY_ROOT / session_id

    text_root = temp_root / "text" / "gradio_batch"
    raw_hyp_dir = text_root / "raw_hyp"                     # 用户上传
    hyp_dir = text_root / "hyp"                            # gen_hyp 输出
    norm_root = temp_root / "text_normalized" / "gradio_batch"
    results_dir = temp_root / "results"                    # compute_wer 输出

    raw_hyp_dir.mkdir(parents=True, exist_ok=True)
    hyp_dir.mkdir(parents=True, exist_ok=True)
    norm_root.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------
    # 👀 输入检查：国家 + 模型 必须统一
    # ------------------------------------------------------
    merged = []
    detected_country = None
    detected_model = None

    for fp in uploaded_files:
        js = load_json(fp)
        if js is None:
            return (
                f"❌ JSON 解析失败: {fp}",
                "",
                None,
                str(temp_root),
                "",
                session_id,
            )

        fname = os.path.basename(fp)
        country = fname[:3]

        if detected_country is None:
            detected_country = country
        elif detected_country != country:
            return (
                "❌ 多国家混合输入（不允许）",
                "",
                None,
                str(temp_root),
                "",
                session_id,
            )

        model = js[0].get("model", "")
        if detected_model is None:
            detected_model = model
        elif detected_model != model:
            return (
                "❌ 多模型混合输入（不允许）",
                "",
                None,
                str(temp_root),
                "",
                session_id,
            )

        merged.extend(js)

    # ------------------------------------------------------
    # 1️⃣ 保存 raw hyp（用于 run_gradio）
    # ------------------------------------------------------
    raw_hyp_path = raw_hyp_dir / f"{detected_country}_{detected_model}.json"
    with open(raw_hyp_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------
    # 2️⃣ 生成 HYP（与 offline process_file 对齐）
    # ------------------------------------------------------
    ref_roots = [
        os.path.join(OFFLINE_TEXT_ROOT, b, "ref")
        for b in OFFLINE_REF_BATCHES
    ]

    gen_hyp(
        hyp_json_path=str(raw_hyp_path),
        country=detected_country,
        ref_roots=ref_roots,
        out_root=str(hyp_dir),
    )

    # ------------------------------------------------------
    # 3️⃣ Normalize（只处理 hyp，不处理 ref）
    # ------------------------------------------------------
    normalize_folder(
        input_root=str(text_root),                    # temp_root/text/gradio_batch
        output_root=str(norm_root),                  # temp_root/text_normalized/gradio_batch
        process_ref=False,                           # ⚠️ 在线不处理ref
        workers=None
    )

    # ------------------------------------------------------
    # 4️⃣ Compute WER / CER (自动检测语言类型)
    # ------------------------------------------------------
    run_compute_wer(str(temp_root))

    metric = "cer" if detected_country in CER_LANGS else "wer"
    model_dir = f"{detected_country}_{detected_model}"

    summary_path = (
        results_dir
        / detected_country
        / model_dir
        / f"{metric}-summary-{detected_country}-{detected_country}_{detected_model}.txt"
    )
    recogs_path = (
        results_dir
        / detected_country
        / model_dir
        / f"recogs-{detected_country}-{detected_country}_{detected_model}.txt"
    )
    errs_path = (
        results_dir
        / detected_country
        / model_dir
        / f"errs-{detected_country}-{detected_country}_{detected_model}.txt"
    )

    if not summary_path.exists():
        return (
            f"❌ Summary 未生成: {summary_path}",
            "",
            None,
            str(temp_root),
            "",
            session_id,
        )

    summary_text = open(summary_path, "r", encoding="utf-8").read()
    errs_text = open(errs_path, "r", encoding="utf-8").read() if errs_path.exists() else ""

    return (
        summary_text,
        errs_text,
        str(recogs_path),
        str(temp_root),
        str(summary_path),
        session_id,
    )


# ==========================================================
# 🎛️ Gradio UI
# ==========================================================
def build_ui():

    with gr.Blocks(title="ASR Bench Online WER/CER") as demo:

        gr.Markdown("## 🔥 ASR Bench 在线评估（GradioBatch）")

        file_box = gr.File(
            label="上传 HYP JSON（同国家 / 同模型）",
            file_count="multiple",
            type="filepath",
        )

        run_btn = gr.Button("开始评估 🚀")

        summary_out = gr.Textbox(label="WER / CER 结果", lines=10)
        errs_out = gr.Textbox(label="错误统计（如有）", lines=10)
        recogs_out = gr.File(label="下载 recogs 文件")
        temp_root_out = gr.Textbox(label="Session 临时目录")
        summary_path_out = gr.Textbox(label="Summary 路径")
        session_out = gr.Textbox(label="Session ID")

        run_btn.click(
            fn=process_request,
            inputs=[file_box],
            outputs=[
                summary_out,
                errs_out,
                recogs_out,
                temp_root_out,
                summary_path_out,
                session_out,
            ],
        )

    return demo


# ==========================================================
# 🚪 Entry
# ==========================================================
if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="0.0.0.0", server_port=7864)

