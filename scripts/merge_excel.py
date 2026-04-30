#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge per-module results into a single all_results.xlsx with 6 sheets.

Sheet order (固定):
    1. Low-Resource-Languages
    2. CH-EN-Dialects
    3. fleurs
    4. common-voice
    5. Vertical-Domain-CH
    6. Vertical-Domain-EN

Cell logic:
    - 若 matched_segments == ref_segments  -> 显示 WER/CER 数值
    - 若不完全对齐                         -> 显示 "matched/ref" 字符串且单元格背景红色
    - 若没数据                              -> 显示 "-"
"""

import os
import re
import json
import argparse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter


# =========================
# 模型白名单 + 显示名称映射
# =========================
MODEL_ORDER = [
    ("Azure",                   {"AZURE"}),
    ("Chirp3",                  {"CHIRP3"}),
    ("elevenlabs_scribe_v2",    {"ELEVENLABS_SCRIBE_V2"}),
    ("meta(omniASR_LLM_3B)",    {"OMNIASR_LLM_3B"}),
    ("qwen3-asr-flash",         {"QWEN3-ASR-FLASH"}),
    ("qwen3-asr",               {"QWEN3-ASR-1.7B"}),
    ("nvidia-nemo",             {"NVIDIA-NEMO"}),
    ("gpt4o-transcribe",        {"GPT4O-TRANSCRIBE"}),
    ("gemini 3.0 flash",        {"GEMINI_3_0_FLASH", "GEMINI-3-FLASH-PREVIEW", "GEMINI"}),
    ("whisper",                 {"WHISPER", "WHISPER-LARGE-V3"}),
    ("dolphin_small",           {"DOLPHIN_SMALL"}),
    ("dolphin_base",            {"DOLPHIN_BASE"}),
    ("fun-asr-mlt-nano",        {"FUN-ASR-MLT-NANO", "FUN-ASR-NANO"}),
    ("funasr1.5",               {"FUN-ASR", "FUNASR_V1.5"}),
    ("qwen3.5-omni-flash",      {"QWEN3.5-OMNI-FLASH"}),
    ("seedasr-1-BIGASR_V400",   {"BIGASR_V400", "SEEDASR"}),
    ("SEEDASR_2.0",             {"SEEDASR_2.0", "SEEDASR2"}),
]
_INT2DISP = {i: d for d, internals in MODEL_ORDER for i in internals}
_DISP_ORDER = [d for d, _ in MODEL_ORDER]


# =========================
# 每个 sheet 的列顺序 (国家/语言)
# =========================
EXCLUDE_COLS = {"EDU-EN", "EDU-CH"}

COLUMN_ORDER = {
    "Low-Resource-Languages": [
        "IRQ", "DZA", "ARE", "EGY", "MAR", "SAU", "SYR",
        "IDN", "MYS", "PHL", "PHL_EN", "PHL_noEN", "VNM", "THA",
        "JPN", "JPN_hard", "KOR", "KOR_hard",
    ],
    "CH-EN-Dialects": [
        "CHN-EN", "IDN-EN", "JPN-EN", "PHL-EN", "SCT-EN", "SGP-EN",
        "XIANG", "JIN", "GAN", "MIN", "YUE", "WU",
    ],
    "fleurs": [
        "EGY", "IDN", "MYS", "PHL", "VNM", "THA", "JPN", "KOR",
    ],
    "common-voice": [
        "AR", "IDN", "VNM", "THA", "JPN", "KOR",
    ],
    "Vertical-Domain-CH": [
        "AGR-CH", "AIT-CH", "ART-CH", "BIO-CH", "ECM-CH", "ENG-CH",
        "ENT-CH", "FIN-CH", "HUM-CH", "LAW-CH", "MED-CH", "MIL-CH",
    ],
    "Vertical-Domain-EN": [
        "AGR-EN", "AIT-EN", "ART-EN", "BIO-EN", "ECM-EN",
        "ENG-EN", "ENT-EN", "FIN-EN", "HUM-EN", "LAW-EN", "MED-EN", "MIL-EN",
    ],
}

# 顺序固定：低资源 → 方言 → fleurs → commonvoice → 中文垂类 → 英文垂类 → hotword CH/EN
SHEET_ORDER = [
    "Low-Resource-Languages",
    "CH-EN-Dialects",
    "fleurs",
    "common-voice",
    "Vertical-Domain-CH",
    "Vertical-Domain-EN",
    "Hotword-CH",
    "Hotword-EN",
]

# Hotword sheets: same column list as Vertical-Domain-{CH,EN}
COLUMN_ORDER["Hotword-CH"] = COLUMN_ORDER["Vertical-Domain-CH"]
COLUMN_ORDER["Hotword-EN"] = COLUMN_ORDER["Vertical-Domain-EN"]

# Hotword model display mapping (internal dir name -> display name).
# 目录命名和 results_Vertical-Domain 下略有差异 (BIGASR 无后缀, SEEDASR, etc.)
HOTWORD_INT2DISP = {
    "AZURE": "Azure",
    "CHIRP3": "Chirp3",
    "ELEVENLABS_SCRIBE_V2": "elevenlabs_scribe_v2",
    "OMNIASR_LLM_3B": "meta(omniASR_LLM_3B)",
    "QWEN3-ASR-FLASH": "qwen3-asr-flash",
    "QWEN3-ASR-1.7B": "qwen3-asr",
    "NVIDIA-NEMO": "nvidia-nemo",
    "GPT4O-TRANSCRIBE": "gpt4o-transcribe",
    "GEMINI": "gemini 3.0 flash",
    "GEMINI_3_0_FLASH": "gemini 3.0 flash",
    "GEMINI-3-FLASH-PREVIEW": "gemini 3.0 flash",
    "WHISPER": "whisper",
    "WHISPER-LARGE-V3": "whisper",
    "DOLPHIN_SMALL": "dolphin_small",
    "DOLPHIN_BASE": "dolphin_base",
    "FUN-ASR-MLT-NANO": "fun-asr-mlt-nano",
    "FUN-ASR-NANO": "fun-asr-mlt-nano",
    "FUN-ASR": "funasr1.5",
    "QWEN3.5-OMNI-FLASH": "qwen3.5-omni-flash",
    "BIGASR": "seedasr-1-BIGASR_V400",
    "BIGASR_V400": "seedasr-1-BIGASR_V400",
    "SEEDASR": "seedasr-1-BIGASR_V400",
    "SEEDASR_2.0": "SEEDASR_2.0",
    "SEEDASR2": "SEEDASR_2.0",
}

# 模块 -> results_<dir>
SOURCE_MAP = {
    "Vertical-Domain-CH": "Vertical-Domain",
    "Vertical-Domain-EN": "Vertical-Domain",
}

# 模块 -> data/text/<dir>/ref  (用于统计有效 ref 时长)
TEXT_SOURCE_MAP = {
    "Low-Resource-Languages": "Low-Resource-Languages",
    "CH-EN-Dialects": "CH-EN-Dialects",
    "fleurs": "fleurs",
    "common-voice": "common-voice",
    "Vertical-Domain-CH": "Vertical-Domain",
    "Vertical-Domain-EN": "Vertical-Domain",
    "Hotword-CH": "Vertical-Domain",
    "Hotword-EN": "Vertical-Domain",
}


# =========================
# 工具
# =========================
def normalize_model_name(model: str) -> str:
    m = re.match(r"^([A-Z]{3})_(.+)$", model)
    if m:
        rest = m.group(2)
        if rest in _INT2DISP:
            return rest
    return model


def pick_err_file(m_dir: str):
    if not os.path.isdir(m_dir):
        return None
    names = [n for n in os.listdir(m_dir) if os.path.isfile(os.path.join(m_dir, n))]
    if not names:
        return None
    err = [n for n in names if n.lower().startswith("err")]
    if err:
        txts = [n for n in err if n.lower().endswith(".txt")]
        return os.path.join(m_dir, sorted(txts or err)[0])
    txts = sorted(n for n in names if n.lower().endswith(".txt"))
    return os.path.join(m_dir, txts[0]) if txts else None


def extract_wer(path: str):
    try:
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("%WER"):
                    m = re.search(r"%WER\s*=\s*([0-9]+(?:\.[0-9]+)?)", line)
                    if m:
                        return float(m.group(1))
    except Exception:
        return None
    return None


def read_segment_check(m_dir: str):
    """Return (ref_n, matched_n) or None if missing."""
    p = os.path.join(m_dir, "segment_check.txt")
    if not os.path.isfile(p):
        return None
    vals = {}
    try:
        with open(p, "r", encoding="utf8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    vals[k.strip()] = v.strip()
        ref_n = int(vals.get("ref_segments", -1))
        matched_n = int(vals.get("matched_segments", -2))
        if ref_n < 0 or matched_n < 0:
            return None
        return ref_n, matched_n
    except Exception:
        return None


def load_ref_durations(base_dir: str, module: str, countries: list):
    """
    读取 data/text/<source>/ref/<country>.json (valid 过滤后的扁平 ref) 并按
    (end-start) 累加，返回 {country: 小时数}. 找不到文件的返回 None.
    """
    src = TEXT_SOURCE_MAP.get(module)
    out = {}
    if not src:
        return out
    ref_root = os.path.join(base_dir, "data", "text", src, "ref")
    for country in countries:
        path = os.path.join(ref_root, f"{country}.json")
        if not os.path.isfile(path):
            out[country] = None
            continue
        try:
            with open(path, "r", encoding="utf8") as f:
                data = json.load(f)
        except Exception:
            out[country] = None
            continue
        total_sec = 0.0
        if isinstance(data, list):
            for seg in data:
                try:
                    s = float(seg.get("start", 0))
                    e = float(seg.get("end", 0))
                    if e > s:
                        total_sec += (e - s)
                except Exception:
                    continue
        elif isinstance(data, dict):
            # 兼容可能的 {audio: {segments:[...]}} 结构
            for v in data.values():
                segs = v.get("segments", []) if isinstance(v, dict) else []
                for seg in segs:
                    if seg.get("status") == "invalid":
                        continue
                    try:
                        s = float(seg.get("start", 0))
                        e = float(seg.get("end", 0))
                        if e > s:
                            total_sec += (e - s)
                    except Exception:
                        continue
        out[country] = total_sec / 3600.0
    return out


# =========================
# 扫描一个模块, 返回 {display_model: {country: (cell_value, is_matched_or_None)}}
# is_matched: True/False/None  (None = 没有数据)
# =========================
def scan_module(results_root: str, countries: list):
    table = {disp: {} for disp in _DISP_ORDER}
    for country in countries:
        c_dir = os.path.join(results_root, country)
        if not os.path.isdir(c_dir):
            continue
        for model in os.listdir(c_dir):
            m_dir = os.path.join(c_dir, model)
            if not os.path.isdir(m_dir):
                continue
            model_clean = normalize_model_name(model)
            display = _INT2DISP.get(model_clean)
            if not display:
                continue
            seg = read_segment_check(m_dir)
            err_path = pick_err_file(m_dir)
            wer = extract_wer(err_path) if err_path else None
            if seg is None:
                if wer is not None:
                    table[display][country] = (wer, True, None, None)
                continue
            ref_n, matched_n = seg
            if ref_n == matched_n:
                if wer is not None:
                    table[display][country] = (wer, True, ref_n, matched_n)
                else:
                    table[display][country] = ("-", None, ref_n, matched_n)
            else:
                # 对齐失败：保留 wer 和段数信息
                table[display][country] = (wer, False, ref_n, matched_n)
    return table


# =========================
# 把一个模块写入 worksheet
# =========================
def write_sheet(ws, table: dict, columns: list, durations: dict = None, mode: str = "default"):
    """
    mode:
      "default"  - 原始行为：完全对齐显示 WER，不对齐显示 matched/ref 标红
      "besteff"  - 能测尽测：有 WER 就显示（不对齐也显示，标红），无数据才 "-"
      "counts"   - 只显示 matched/ref，不对齐标红
    """
    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    red_font = Font(color="9C0006", bold=True)
    dur_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    durations = durations or {}

    # Row 1: 时长 (valid ref)
    dc = ws.cell(row=1, column=1, value="Duration (valid ref)")
    dc.font = bold
    dc.alignment = center
    dc.fill = dur_fill
    for ci, col in enumerate(columns, start=2):
        h = durations.get(col)
        cell = ws.cell(row=1, column=ci)
        if h is None:
            cell.value = "-"
        else:
            cell.value = f"{h:.2f}h"
        cell.font = bold
        cell.alignment = center
        cell.fill = dur_fill

    # Row 2: 表头 (Model / 国家)
    ws.cell(row=2, column=1, value="Model").font = bold
    ws.cell(row=2, column=1).alignment = center
    for ci, col in enumerate(columns, start=2):
        c = ws.cell(row=2, column=ci, value=col)
        c.font = bold
        c.alignment = center

    # 数据行 (从 row 3 开始)
    for ri, disp in enumerate(_DISP_ORDER, start=3):
        ws.cell(row=ri, column=1, value=disp).font = bold
        ws.cell(row=ri, column=1).alignment = center
        for ci, col in enumerate(columns, start=2):
            entry = table.get(disp, {}).get(col)
            cell = ws.cell(row=ri, column=ci)
            cell.alignment = center
            if entry is None:
                cell.value = "-"
                continue
            value, matched, ref_n, matched_n = entry

            if mode == "counts":
                # 只显示 matched/ref
                if ref_n is not None and matched_n is not None:
                    cell.value = f"{matched_n}/{ref_n}"
                    if matched is False:
                        cell.fill = red_fill
                        cell.font = red_font
                elif value == "-":
                    cell.value = "-"
                else:
                    cell.value = "-"
            elif mode == "besteff":
                # 能测尽测：有 WER 就显示，不对齐标红
                if matched is True and isinstance(value, float):
                    cell.value = round(value, 2)
                    cell.number_format = "0.00"
                elif matched is False:
                    if isinstance(value, float):
                        cell.value = round(value, 2)
                        cell.number_format = "0.00"
                        cell.fill = red_fill
                        cell.font = red_font
                    elif matched_n is not None and matched_n > 0:
                        cell.value = f"{matched_n}/{ref_n}"
                        cell.fill = red_fill
                        cell.font = red_font
                    else:
                        cell.value = "-"
                else:
                    cell.value = "-" if value == "-" else value
            else:
                # default: 原始行为
                if matched is False:
                    cell.value = f"{matched_n}/{ref_n}" if ref_n is not None else "-"
                    cell.fill = red_fill
                    cell.font = red_font
                elif matched is True and isinstance(value, float):
                    cell.value = round(value, 2)
                    cell.number_format = "0.00"
                else:
                    cell.value = value

    # MIN 行 (仅完全对齐的数值列 — default/counts; besteff 包含所有有值的)
    min_row_idx = len(_DISP_ORDER) + 3
    ws.cell(row=min_row_idx, column=1, value="MIN").font = bold
    ws.cell(row=min_row_idx, column=1).alignment = center
    for ci, col in enumerate(columns, start=2):
        vals = []
        for disp in _DISP_ORDER:
            entry = table.get(disp, {}).get(col)
            if not entry:
                continue
            value, matched, ref_n, matched_n = entry
            if mode == "besteff":
                if isinstance(value, float):
                    vals.append(value)
            elif mode != "counts":
                if matched is True and isinstance(value, float):
                    vals.append(value)
                vals.append(entry[0])
        cell = ws.cell(row=min_row_idx, column=ci)
        cell.alignment = center
        cell.font = bold
        if vals:
            cell.value = round(min(vals), 2)
            cell.number_format = "0.00"
        else:
            cell.value = "-"

    # AVG 列 (每个模型的平均值，只算有数值结果的列)
    avg_fill = PatternFill(start_color="DAEEF3", end_color="DAEEF3", fill_type="solid")
    avg_ci = len(columns) + 2
    # Duration row
    ws.cell(row=1, column=avg_ci, value="").fill = dur_fill
    ws.cell(row=1, column=avg_ci).alignment = center
    # Header
    hdr = ws.cell(row=2, column=avg_ci, value="AVG")
    hdr.font = bold
    hdr.alignment = center
    hdr.fill = avg_fill
    # Model rows
    for ri, disp in enumerate(_DISP_ORDER, start=3):
        vals = []
        for col in columns:
            entry = table.get(disp, {}).get(col)
            if not entry:
                continue
            value, matched, ref_n, matched_n = entry
            if mode == "besteff":
                if isinstance(value, float):
                    vals.append(value)
            elif mode == "counts":
                pass  # no avg for counts
            else:
                if matched is True and isinstance(value, float):
                    vals.append(value)
        cell = ws.cell(row=ri, column=avg_ci)
        cell.alignment = center
        cell.fill = avg_fill
        if vals:
            cell.value = round(sum(vals) / len(vals), 2)
            cell.number_format = "0.00"
            cell.font = bold
        else:
            cell.value = "-"
    # MIN row AVG
    min_avgs = []
    for disp in _DISP_ORDER:
        cell_val = ws.cell(row=_DISP_ORDER.index(disp) + 3, column=avg_ci).value
        if isinstance(cell_val, (int, float)):
            min_avgs.append(cell_val)
    min_avg_cell = ws.cell(row=min_row_idx, column=avg_ci)
    min_avg_cell.alignment = center
    min_avg_cell.font = bold
    min_avg_cell.fill = avg_fill
    if min_avgs:
        min_avg_cell.value = round(min(min_avgs), 2)
        min_avg_cell.number_format = "0.00"
    else:
        min_avg_cell.value = "-"

    # 列宽
    ws.column_dimensions["A"].width = 26
    for ci in range(2, avg_ci + 1):
        ws.column_dimensions[get_column_letter(ci)].width = 14


# =========================
# Hotword 结果扫描与写入
# =========================
HOTWORD_METRICS = [
    ("WER (%)", "CER (%)", "wer"),
    ("U-WER (%)", "U-CER (%)", "u_wer"),
    ("B-WER (%)", "B-CER (%)", "b_wer"),
    ("Recall (%)", "Recall (%)", "recall"),
]


def _parse_hotword_result(path: str):
    out = {}
    try:
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
    except Exception:
        return None
    try:
        matched = int(out.get("matched_segments", "0"))
        skipped = int(out.get("skipped_segments", "0"))
    except ValueError:
        return None
    metrics = {}
    for key in ("wer", "u_wer", "b_wer", "recall"):
        v = out.get(key)
        if v is None:
            continue
        try:
            metrics[key] = float(v)
        except ValueError:
            continue
    return {"matched": matched, "skipped": skipped, "metrics": metrics}


def scan_hotword(results_root: str, domains: list):
    """Return {display_model: {domain: {metric: (value, is_matched)}}}."""
    # 按 hotword 目录下的模型名显示
    table = {}
    display_order = []
    for domain in domains:
        d_dir = os.path.join(results_root, domain)
        if not os.path.isdir(d_dir):
            continue
        for model in sorted(os.listdir(d_dir)):
            m_dir = os.path.join(d_dir, model)
            if not os.path.isdir(m_dir):
                continue
            model_clean = normalize_model_name(model)
            display = HOTWORD_INT2DISP.get(model_clean)
            if not display:
                continue
            if display not in table:
                table[display] = {}
                if display not in display_order:
                    display_order.append(display)
            p = os.path.join(m_dir, "hotword_result.txt")
            if not os.path.isfile(p):
                continue
            parsed = _parse_hotword_result(p)
            if parsed is None:
                continue
            total = parsed["matched"] + parsed["skipped"]
            is_matched = parsed["skipped"] == 0
            cell_map = {}
            for _, _, key in HOTWORD_METRICS:
                v = parsed["metrics"].get(key)
                if v is None:
                    cell_map[key] = None
                elif is_matched:
                    cell_map[key] = (v, True, total, parsed["matched"])
                else:
                    cell_map[key] = (v, False, total, parsed["matched"])
            table[display][domain] = cell_map

    # 按 _DISP_ORDER 排序
    ordered = [d for d in _DISP_ORDER if d in table]
    ordered += [d for d in display_order if d not in _DISP_ORDER]
    return table, ordered


def write_hotword_sheet(ws, table: dict, ordered_models: list, columns: list, durations: dict = None, mode: str = "default", is_chinese: bool = False):
    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    red_font = Font(color="9C0006", bold=True)
    section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    dur_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    durations = durations or {}

    # 最顶部: 时长行 (valid ref)
    dc = ws.cell(row=1, column=1, value="Duration (valid ref)")
    dc.font = bold
    dc.alignment = center
    dc.fill = dur_fill
    for ci, col in enumerate(columns, start=2):
        h = durations.get(col)
        cell = ws.cell(row=1, column=ci)
        cell.value = "-" if h is None else f"{h:.2f}h"
        cell.font = bold
        cell.alignment = center
        cell.fill = dur_fill

    row = 2
    for en_label, ch_label, metric_key in HOTWORD_METRICS:
        metric_label = ch_label if is_chinese else en_label
        # Section title
        ws.cell(row=row, column=1, value=metric_label).font = Font(bold=True, size=12)
        ws.cell(row=row, column=1).fill = section_fill
        for ci in range(2, len(columns) + 2):
            ws.cell(row=row, column=ci).fill = section_fill
        row += 1

        # Header row
        ws.cell(row=row, column=1, value="Model").font = bold
        ws.cell(row=row, column=1).alignment = center
        for ci, col in enumerate(columns, start=2):
            c = ws.cell(row=row, column=ci, value=col)
            c.font = bold
            c.alignment = center
        row += 1

        # Data rows
        for disp in ordered_models:
            ws.cell(row=row, column=1, value=disp).font = bold
            ws.cell(row=row, column=1).alignment = center
            for ci, col in enumerate(columns, start=2):
                cell_map = table.get(disp, {}).get(col)
                cell = ws.cell(row=row, column=ci)
                cell.alignment = center
                if not cell_map:
                    cell.value = "-"
                    continue
                entry = cell_map.get(metric_key)
                if entry is None:
                    cell.value = "-"
                    continue
                value, is_matched, total, matched_n = entry
                if mode == "counts":
                    cell.value = f"{matched_n}/{total}"
                    if not is_matched:
                        cell.fill = red_fill
                        cell.font = red_font
                elif mode == "besteff":
                    if isinstance(value, float):
                        cell.value = round(value, 2)
                        cell.number_format = "0.00"
                        if not is_matched:
                            cell.fill = red_fill
                            cell.font = red_font
                    else:
                        cell.value = "-"
                else:
                    if not is_matched:
                        cell.value = f"{matched_n}/{total}"
                        cell.fill = red_fill
                        cell.font = red_font
                    elif isinstance(value, float):
                        cell.value = round(value, 2)
                        cell.number_format = "0.00"
                    else:
                        cell.value = value
            row += 1

        # MIN 行 (only for besteff/default with WER metric)
        if mode != "counts" and metric_key == "wer":
            ws.cell(row=row, column=1, value="MIN").font = bold
            ws.cell(row=row, column=1).alignment = center
            for ci, col in enumerate(columns, start=2):
                vals = []
                for disp in ordered_models:
                    cell_map = table.get(disp, {}).get(col)
                    if not cell_map:
                        continue
                    entry = cell_map.get(metric_key)
                    if entry is None:
                        continue
                    value, is_matched, total, matched_n = entry
                    if mode == "besteff":
                        if isinstance(value, float):
                            vals.append(value)
                    else:
                        if is_matched and isinstance(value, float):
                            vals.append(value)
                cell = ws.cell(row=row, column=ci)
                cell.alignment = center
                cell.font = bold
                if vals:
                    cell.value = round(min(vals), 2)
                    cell.number_format = "0.00"
                else:
                    cell.value = "-"
            row += 1

        # blank separator row
        row += 1

    ws.column_dimensions["A"].width = 26
    for ci in range(2, len(columns) + 2):
        ws.column_dimensions[get_column_letter(ci)].width = 14


# =========================
# main
# =========================
def main(base_dir: str):
    # Generate both Excel files
    for mode, suffix in [("besteff", "_besteff"), ("counts", "_counts")]:
        out_path = os.path.join(base_dir, "data", f"all_results{suffix}.xlsx")
        wb = Workbook()
        wb.remove(wb.active)

        for module in SHEET_ORDER:
            if module in ("Hotword-CH", "Hotword-EN"):
                results_root = os.path.join(base_dir, "data", "results_hotword")
                if not os.path.isdir(results_root):
                    continue
                cols = [c for c in COLUMN_ORDER[module] if c not in EXCLUDE_COLS]
                table, ordered_models = scan_hotword(results_root, cols)
                ws = wb.create_sheet(title=module[:31])
                durations = load_ref_durations(base_dir, module, cols)
                is_ch = module.endswith("-CH")
                write_hotword_sheet(ws, table, ordered_models, cols, durations, mode, is_ch)
                continue

            source = SOURCE_MAP.get(module, module)
            results_root = os.path.join(base_dir, "data", f"results_{source}")
            if not os.path.isdir(results_root):
                continue
            cols = [c for c in COLUMN_ORDER[module] if c not in EXCLUDE_COLS]
            table = scan_module(results_root, cols)

            matched_cnt = unmatched_cnt = empty_cnt = 0
            for disp in _DISP_ORDER:
                for col in cols:
                    entry = table.get(disp, {}).get(col)
                    if entry is None:
                        empty_cnt += 1
                    elif entry[1] is True:
                        matched_cnt += 1
                    elif entry[1] is False:
                        unmatched_cnt += 1
                    else:
                        empty_cnt += 1

            ws = wb.create_sheet(title=module[:31])
            durations = load_ref_durations(base_dir, module, cols)
            write_sheet(ws, table, cols, durations, mode)
            if mode == "besteff":
                print(
                    f"✅ {module}: matched={matched_cnt}  "
                    f"unmatched(red)={unmatched_cnt}  empty={empty_cnt}  cols={len(cols)}"
                )

        wb.save(out_path)
        print(f"\n📄 Written -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge per-module results into one Excel")
    parser.add_argument(
        "--base_dir", type=str,
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="Project root (default: auto-detect from script location)",
    )
    args = parser.parse_args()
    main(args.base_dir)
