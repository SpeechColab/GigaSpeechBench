#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge per-module results.xlsx into a single all_results.xlsx with 3 sheets.
Enforces a fixed column order per sheet; extra columns appended alphabetically.
Adds bold headers, center alignment, and a MIN row at the bottom.
"""

import os
import pandas as pd
import argparse
from openpyxl.styles import Font, Alignment

# Columns to exclude
EXCLUDE_COLS = {"EDU-EN", "EDU-CH"}

# Fixed column orders per module
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
    "Vertical-Domain-CH": [
        "AGR-CH", "AIT-CH", "ART-CH", "BIO-CH", "ECM-CH", "ENG-CH",
        "ENT-CH", "FIN-CH", "HUM-CH", "LAW-CH", "MED-CH", "MIL-CH",
    ],
    "Vertical-Domain-EN": [
        "AGR-EN", "AIT-EN", "ART-EN", "BIO-EN", "ECM-EN",
        "ENG-EN", "ENT-EN", "FIN-EN", "HUM-EN", "LAW-EN", "MED-EN", "MIL-EN",
    ],
    "fleurs": [
        "EGY", "IDN", "JPN", "KOR", "MYS", "PHL", "THA", "VNM",
    ],
    "common-voice": [
        "AR", "IDN", "JPN", "KOR", "THA", "VNM",
    ],
}

MODULE_ORDER = ["Low-Resource-Languages", "CH-EN-Dialects", "Vertical-Domain-CH", "Vertical-Domain-EN", "fleurs", "common-voice"]


def reorder_columns(df: pd.DataFrame, fixed_order: list, strict: bool = False) -> pd.DataFrame:
    # Drop excluded columns
    df = df.drop(columns=[c for c in EXCLUDE_COLS if c in df.columns], errors="ignore")
    ordered = [c for c in fixed_order if c in df.columns]
    if strict:
        return df[ordered]
    extras = sorted(c for c in df.columns if c not in fixed_order)
    return df[ordered + extras]


def add_min_row(df: pd.DataFrame) -> pd.DataFrame:
    """Append a MIN row at the bottom (only for numeric columns)."""
    min_vals = {}
    for col in df.columns:
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.notna().any():
            min_vals[col] = numeric.min()
        else:
            min_vals[col] = "-"
    min_row = pd.DataFrame(min_vals, index=["MIN"])
    return pd.concat([df, min_row])


def style_worksheet(ws):
    """Apply bold header, center alignment, and bold MIN row."""
    bold_font = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")

    # Bold + center header row
    for cell in ws[1]:
        cell.font = bold_font
        cell.alignment = center

    # Center all data cells
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
        for cell in row:
            cell.alignment = center

    # Bold the MIN row (last row)
    for cell in ws[ws.max_row]:
        cell.font = bold_font

    # Auto-width
    for col_cells in ws.columns:
        max_len = 0
        col_letter = col_cells[0].column_letter
        for cell in col_cells:
            val = str(cell.value) if cell.value is not None else ""
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = max_len + 3


def main(base_dir: str):
    out = os.path.join(base_dir, "data", "all_results.xlsx")
    # Vertical-Domain-CH and Vertical-Domain-EN both read from results_Vertical-Domain
    SOURCE_MAP = {
        "Vertical-Domain-CH": "Vertical-Domain",
        "Vertical-Domain-EN": "Vertical-Domain",
    }
    # These sheets only keep columns in their fixed order (no extras)
    STRICT_MODULES = {"Vertical-Domain-CH", "Vertical-Domain-EN"}
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for module in MODULE_ORDER:
            source = SOURCE_MAP.get(module, module)
            path = os.path.join(base_dir, f"data/results_{source}/results.xlsx")
            if not os.path.isfile(path):
                print(f"⚠️  {module}: {path} not found, skipped")
                continue
            df = pd.read_excel(path, index_col=0)
            df = reorder_columns(df, COLUMN_ORDER.get(module, []), strict=module in STRICT_MODULES)
            df = add_min_row(df)
            df.to_excel(writer, sheet_name=module)
            style_worksheet(writer.sheets[module])
            print(f"✅ {module}: {df.shape} cols={list(df.columns)}")
    print(f"\n📄 Written -> {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge per-module Excel into one file")
    parser.add_argument("--base_dir", type=str,
                        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        help="Project root (default: auto-detect from script location)")
    args = parser.parse_args()
    main(args.base_dir)
