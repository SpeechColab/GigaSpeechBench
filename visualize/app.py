#!/usr/bin/env python3
"""
ASR Benchmark Leaderboard & Model Evaluation

Usage:
    conda activate asr_bench
    python visualize/app.py [--port 7860] [--share]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import gradio as gr
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_FILE = Path(__file__).resolve().parent / "static_results.json"
DEFAULT_STAGING = str(BASE_DIR.parent / "data" / "release_hash")

# ─── Language groups ───
LR_GROUPS = {
    "East Asian": ["JPN", "KOR"],
    "Southeast Asian": ["IDN", "MYS", "PHL", "THA", "VNM"],
    "Arabic": ["ARE", "DZA", "EGY", "IRQ", "MAR", "SAU", "SYR"],
}
CED_GROUPS = {
    "Chinese Dialects": ["GAN", "JIN", "MIN", "WU", "XIANG", "YUE"],
    "English Accents": ["CHN-EN", "IND-EN", "JPN-EN", "PHL-EN", "SCT-EN", "SGP-EN"],
}
VD_GROUPS = {
    "Vertical-Domain-CH": ["AGR-CH", "AIT-CH", "ART-CH", "BIO-CH", "ECM-CH", "ENG-CH",
                           "ENT-CH", "FIN-CH", "HUM-CH", "LAW-CH", "MED-CH", "MIL-CH"],
    "Vertical-Domain-EN": ["AGR-EN", "AIT-EN", "ART-EN", "BIO-EN", "ECM-EN", "ENG-EN",
                           "ENT-EN", "FIN-EN", "HUM-EN", "LAW-EN", "MED-EN", "MIL-EN"],
}

MODULE_GROUPS = {
    "Low-Resource-Languages": LR_GROUPS,
    "CH-EN-Dialects": CED_GROUPS,
    "Vertical-Domain": VD_GROUPS,
}

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


# ─── Result parsing ───

def parse_results_dir(results_dir: str) -> dict:
    results = {}
    p = Path(results_dir)
    if not p.exists():
        return results
    for country_dir in sorted(p.iterdir()):
        if not country_dir.is_dir():
            continue
        country = country_dir.name
        results[country] = {}
        for model_dir in sorted(country_dir.iterdir()):
            if not model_dir.is_dir():
                continue
            for err_file in model_dir.glob("errs-*"):
                line = open(err_file).readline().strip()
                if line.startswith("%WER") or line.startswith("%CER"):
                    try:
                        results[country][model_dir.name] = float(line.split("=")[1].strip())
                    except (ValueError, IndexError):
                        pass
                break
    return results


def parse_hotword_results_dir(results_dir: str) -> dict:
    """Parse hotword B-WER results from results_hotword_mindur directory."""
    results = {}
    p = Path(results_dir)
    if not p.exists():
        return results
    for country_dir in sorted(p.iterdir()):
        if not country_dir.is_dir():
            continue
        country = country_dir.name
        results[country] = {}
        for model_dir in sorted(country_dir.iterdir()):
            if not model_dir.is_dir():
                continue
            hw_file = model_dir / "hotword_result.txt"
            if hw_file.exists():
                for line in open(hw_file):
                    if line.startswith("b_wer="):
                        try:
                            results[country][model_dir.name] = float(line.split("=")[1].strip())
                        except (ValueError, IndexError):
                            pass
                        break
    return results


def build_sub_leaderboard(results: dict, group_name: str, langs: list,
                          highlight_model: str = None) -> pd.DataFrame:
    all_models = set()
    for l in langs:
        if l in results:
            all_models.update(results[l].keys())
    if not all_models:
        return pd.DataFrame()

    rows = []
    for model in sorted(all_models):
        vals = []
        row = {"Model": model}
        for l in langs:
            if l in results and model in results[l]:
                row[l] = round(results[l][model], 2)
                vals.append(results[l][model])
            else:
                row[l] = None
        row["AVG(%)"] = round(sum(vals) / len(vals), 2) if vals else None
        row["Coverage"] = f"{len(vals)}/{len(langs)}"
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values("AVG(%)", ascending=True).reset_index(drop=True)

    # Reorder: Model, AVG, per-lang, Coverage
    cols = ["Model", "AVG(%)"] + langs + ["Coverage"]
    df = df[[c for c in cols if c in df.columns]]

    # Add medals and highlight
    models_col = []
    for i, row in df.iterrows():
        name = row["Model"]
        rank = i + 1
        medal = MEDALS.get(rank, "")
        if highlight_model and name.upper() == highlight_model.upper():
            name = f"⭐ {name}"
        if medal:
            name = f"{medal} {name}"
        models_col.append(name)
    df["Model"] = models_col
    df.index = df.index + 1
    df.index.name = "#"
    return df


def get_results_path(module: str) -> str:
    return str(BASE_DIR / "data" / f"results_{module}_mindur")


def get_hotword_results_path() -> str:
    return str(BASE_DIR / "data" / "results_hotword_mindur")


# ─── Static loading ───

def load_static():
    if not STATIC_FILE.exists():
        return {}
    with open(STATIC_FILE) as f:
        data = json.load(f)
    dfs = {}
    for key, records in data.items():
        df = pd.DataFrame(records)
        if "#" in df.columns:
            df = df.set_index("#")
        dfs[key] = df
    return dfs


# ─── New model submission ───

def ensure_ref_ready(module: str, staging: Path, progress=None):
    """Ensure REF is converted, normalized, and duration-filtered. Cached/skipped if already done."""
    text_dir = BASE_DIR / "data" / "text" / module
    norm_dir = BASE_DIR / "data" / "text_normalized" / module
    mindur_dir = BASE_DIR / "data" / "text_normalized_mindur" / module

    ref_out = text_dir / "ref"
    norm_ref = norm_dir / "ref"
    mindur_ref = mindur_dir / "ref"

    py = sys.executable
    staging_module = staging / module

    # Step 1: Convert REF from staging (skip if exists)
    if not ref_out.exists() or not list(ref_out.glob("*.json")):
        if progress:
            progress(0.05, desc="Converting REF from staging...")
        subprocess.run([py, str(BASE_DIR / "data_process" / "convert_staging.py"),
                        "--staging_root", str(staging_module),
                        "--module", module,
                        "--out_root", str(BASE_DIR),
                        "--models", "__REF_ONLY__"],  # special: no HYP
                       capture_output=True, text=True, cwd=str(BASE_DIR))
        # convert_staging with non-existent model name -> only REF is produced
        # Actually let's just run it without models filter for ref
        if not ref_out.exists() or not list(ref_out.glob("*.json")):
            subprocess.run([py, str(BASE_DIR / "data_process" / "convert_staging.py"),
                            "--staging_root", str(staging_module),
                            "--module", module,
                            "--out_root", str(BASE_DIR)],
                           capture_output=True, text=True, cwd=str(BASE_DIR))

    # Step 2: Normalize REF (skip if exists)
    if not norm_ref.exists() or not list(norm_ref.glob("*.json")):
        if progress:
            progress(0.1, desc="Normalizing REF...")
        subprocess.run([py, str(BASE_DIR / "data_process" / "normalize_ref.py"),
                        "--ref_root", str(ref_out),
                        "--out_root", str(norm_dir),
                        "--skip_existing", "1"],
                       capture_output=True, text=True, cwd=str(BASE_DIR))

    # Step 3: Duration filter REF (skip if exists)
    if not mindur_ref.exists() or not list(mindur_ref.glob("*.json")):
        if progress:
            progress(0.15, desc="Filtering by duration...")
        subprocess.run([py, str(BASE_DIR / "scripts" / "filter_duration.py"),
                        "--norm_root", str(norm_dir),
                        "--out_root", str(mindur_dir),
                        "--min_duration", "0.5"],
                       capture_output=True, text=True, cwd=str(BASE_DIR))


def eval_single_model(model_name: str, json_file: str, module: str, staging: Path, progress=None):
    """Evaluate a single new model without touching other models' data."""
    text_dir = BASE_DIR / "data" / "text" / module
    norm_dir = BASE_DIR / "data" / "text_normalized" / module
    mindur_dir = BASE_DIR / "data" / "text_normalized_mindur" / module
    results_dir = BASE_DIR / "data" / "new_model" / model_name

    hyp_out = text_dir / "hyp"
    norm_hyp = norm_dir / "hyp"
    mindur_hyp = mindur_dir / "hyp"

    py = sys.executable
    staging_module = staging / module

    # Step 1: Inject model into staging temporarily (skip if already there)
    target_dir = staging_module / "results"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{model_name}.json"
    src_path = Path(json_file).resolve()
    injected = False
    if src_path != target_file.resolve():
        shutil.copy2(json_file, target_file)
        injected = True

    try:
        # Step 2: Convert only this model's HYP
        if progress:
            progress(0.2, desc="Converting HYP...")
        subprocess.run([py, str(BASE_DIR / "data_process" / "convert_staging.py"),
                        "--staging_root", str(staging_module),
                        "--module", module,
                        "--out_root", str(BASE_DIR),
                        "--models", model_name],
                       capture_output=True, text=True, cwd=str(BASE_DIR))

        # Step 3: Normalize this model's HYP
        if progress:
            progress(0.4, desc="Normalizing HYP...")
        subprocess.run([py, str(BASE_DIR / "data_process" / "normalize_hyp.py"),
                        "--hyp_root", str(hyp_out),
                        "--out_root", str(norm_dir),
                        "--skip_existing", "1"],
                       capture_output=True, text=True, cwd=str(BASE_DIR))

        # Step 4: Duration filter HYP
        if progress:
            progress(0.5, desc="Filtering HYP by duration...")
        subprocess.run([py, str(BASE_DIR / "scripts" / "filter_duration.py"),
                        "--norm_root", str(norm_dir),
                        "--out_root", str(mindur_dir),
                        "--min_duration", "0.5"],
                       capture_output=True, text=True, cwd=str(BASE_DIR))

        # Step 5: Compute WER (only new model will be computed, others skipped by skip_existing)
        if progress:
            progress(0.6, desc="Computing WER/CER...")
        results_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([py, str(BASE_DIR / "scripts" / "compute_wer.py"),
                        "--ref_root", str(mindur_dir / "ref"),
                        "--hyp_root", str(mindur_dir / "hyp"),
                        "--out_root", str(results_dir),
                        "--skip_existing", "0"],
                       capture_output=True, text=True, cwd=str(BASE_DIR))
    finally:
        # Clean staging (only if we injected)
        if injected and target_file.exists():
            target_file.unlink()

    return results_dir


def submit_new_model(json_file: str, progress=gr.Progress()):
    """Evaluate a new model JSON. Auto-detect module from content."""
    json_file = json_file.strip() if isinstance(json_file, str) else ""

    if not json_file or not os.path.isfile(json_file):
        return "❌ File not found. Please provide a valid path.", "", None, None, None

    if not json_file.endswith(".json"):
        return "❌ File must be .json", "", None, None, None

    # Load and validate
    try:
        with open(json_file) as f:
            data = json.load(f)
        if not isinstance(data, dict) or "audios" not in data:
            return '❌ Invalid format. Expected: {"audios": [...]}', "", None, None, None
    except Exception as e:
        return f"❌ JSON parse error: {e}", "", None, None, None

    # Derive model name from filename
    model_name = Path(json_file).stem

    # Validate segments
    total_audios = len(data["audios"])
    audios_no_segs = 0
    audios_empty_segs = 0
    total_segs = 0
    for audio in data["audios"]:
        segs = audio.get("segments")
        if segs is None:
            audios_no_segs += 1
        elif len(segs) == 0:
            audios_empty_segs += 1
        else:
            total_segs += len(segs)

    if audios_no_segs == total_audios:
        return ("## ❌ ERROR: No segments found!\n\n"
                "All audios are missing the `segments` field.\n\n"
                "Each audio must have a `segments` list with transcription results:\n"
                "```json\n"
                '{"audios": [{"aid": "...", "language": "...", "segments": [{"sid": "...", "begin_time": "...", "end_time": "...", "text": "..."}]}]}\n'
                "```"), "", None, None, None

    seg_warnings = []
    if audios_no_segs > 0 or audios_empty_segs > 0:
        bad = audios_no_segs + audios_empty_segs
        seg_warnings.append(f"## ⚠️ {bad}/{total_audios} audios missing segments!")
        seg_warnings.append(f"- Missing `segments` field: **{audios_no_segs}**")
        seg_warnings.append(f"- Empty `segments` list: **{audios_empty_segs}**")
        seg_warnings.append(f"- Valid segments used for evaluation: **{total_segs}**")
        seg_warnings.append("")

    # Detect module from language codes in data
    langs_in_data = set()
    for audio in data["audios"]:
        lang = audio.get("language", "")
        if lang:
            langs_in_data.add(lang)

    all_lr = set(l for ls in LR_GROUPS.values() for l in ls)
    all_ced = set(l for ls in CED_GROUPS.values() for l in ls)
    all_vd = set(l for ls in VD_GROUPS.values() for l in ls)

    lr_overlap = langs_in_data & all_lr
    ced_overlap = langs_in_data & all_ced
    vd_overlap = langs_in_data & all_vd

    # Pick best matching module
    overlaps = [("Low-Resource-Languages", lr_overlap, all_lr),
                ("CH-EN-Dialects", ced_overlap, all_ced),
                ("Vertical-Domain", vd_overlap, all_vd)]
    overlaps.sort(key=lambda x: len(x[1]), reverse=True)
    module, matched_langs, expected_langs = overlaps[0]

    if not matched_langs:
        return ("❌ Cannot detect module. Languages in your JSON don't match any benchmark.\n"
                f"Found: {sorted(langs_in_data)[:10]}"), "", None, None, None

    # Coverage warning
    missing_langs = expected_langs - matched_langs
    coverage_pct = len(matched_langs) / len(expected_langs) * 100
    warnings = []
    if missing_langs:
        warnings.append(f"## ⚠️ Partial Coverage: {len(matched_langs)}/{len(expected_langs)} languages ({coverage_pct:.0f}%)")
        warnings.append(f"**Missing:** {', '.join(sorted(missing_langs))}")
        warnings.append("")
        warnings.append("Results below only reflect the languages you submitted.")

    # Ensure REF is ready
    staging = Path(DEFAULT_STAGING)
    if not staging.exists():
        return f"❌ Benchmark data not found at: {staging}", "", None, None, None

    progress(0.05, desc="Preparing REF data...")
    ensure_ref_ready(module, staging, progress)

    # Evaluate new model only
    progress(0.2, desc=f"Evaluating {model_name} on {module}...")
    results_dir = eval_single_model(model_name, json_file, module, staging, progress)

    progress(0.9, desc="Building leaderboards...")

    # Load static results + new model results
    new_results = parse_results_dir(str(results_dir))

    # Merge with static data for ranking
    static = load_static()
    groups = MODULE_GROUPS[module]
    group_names = list(groups.keys())
    prefix_map = {"Low-Resource-Languages": "LR", "CH-EN-Dialects": "CED", "Vertical-Domain": "VD"}
    prefix = prefix_map[module]

    dfs = []
    rank_info = []
    for gname in group_names:
        static_key = f"{prefix}_{gname}"
        static_df = static.get(static_key, pd.DataFrame())

        # Build new model row from new_results
        langs = groups[gname]
        new_row = {"Model": f"⭐ {model_name}"}
        vals = []
        for l in langs:
            if l in new_results and model_name.upper() in new_results[l]:
                v = round(new_results[l][model_name.upper()], 2)
                new_row[l] = v
                vals.append(v)
            else:
                new_row[l] = None
        new_row["AVG(%)"] = round(sum(vals) / len(vals), 2) if vals else None
        new_row["Coverage"] = f"{len(vals)}/{len(langs)}"

        # Insert into static DataFrame
        if not static_df.empty and new_row["AVG(%)"] is not None:
            new_df = pd.DataFrame([new_row])
            combined = pd.concat([static_df.reset_index(), new_df], ignore_index=True)
            combined = combined.sort_values("AVG(%)", ascending=True).reset_index(drop=True)
            combined.index = combined.index + 1
            combined.index.name = "#"
            # Find rank
            for idx, row in combined.iterrows():
                if "⭐" in str(row["Model"]):
                    rank_info.append(f"**{gname}**: Rank #{idx}/{len(combined)}")
                    break
            dfs.append(combined)
        else:
            dfs.append(static_df)

    # Pad to 3
    while len(dfs) < 3:
        dfs.append(pd.DataFrame())

    # Build status
    status_parts = [f"✅ **{model_name}** evaluated on **{module}**"]
    status_parts.append(f"📁 Results: `{results_dir}`")
    status_parts.append("")
    status_parts.append("### Ranking:")
    status_parts.extend(rank_info)
    if seg_warnings:
        status_parts.append("")
        status_parts.extend(seg_warnings)
    if warnings:
        status_parts.append("")
        status_parts.extend(warnings)

    status = "\n".join(status_parts)
    labels = "\n".join([f"**Tab {i+1}**: {gname}" for i, gname in enumerate(group_names)])

    return status, labels, dfs[0], dfs[1], dfs[2]


# ─── UI ───

def create_ui():
    static = load_static()

    def s(key):
        return static.get(key, pd.DataFrame())

    css = """
    .leaderboard-table { font-size: 14px !important; }
    .gr-dataframe td { padding: 4px 8px !important; }
    """

    with gr.Blocks(title="ASR Benchmark", css=css) as app:
        gr.Markdown(
            """
            # 🏆 Multilingual ASR Benchmark
            *Lower WER/CER = Better. Duration > 0.5s filter applied.*
            """
        )

        with gr.Tabs():
            # ─── LR ───
            with gr.Tab("🌍 Low-Resource Languages"):
                with gr.Tabs():
                    with gr.Tab("East Asian (JPN/KOR)"):
                        gr.Dataframe(value=s("LR_East Asian"), interactive=False, wrap=True)
                    with gr.Tab("Southeast Asian"):
                        gr.Dataframe(value=s("LR_Southeast Asian"), interactive=False, wrap=True)
                    with gr.Tab("Arabic"):
                        gr.Dataframe(value=s("LR_Arabic"), interactive=False, wrap=True)

            # ─── CED ───
            with gr.Tab("🗣️ CH-EN Dialects"):
                with gr.Tabs():
                    with gr.Tab("Chinese Dialects"):
                        gr.Dataframe(value=s("CED_Chinese Dialects"), interactive=False, wrap=True)
                    with gr.Tab("English Accents"):
                        gr.Dataframe(value=s("CED_English Accents"), interactive=False, wrap=True)

            # ─── VD ───
            with gr.Tab("🏢 Vertical Domain"):
                with gr.Tabs():
                    with gr.Tab("Chinese Domains"):
                        gr.Markdown("### B-CER (Hotword)")
                        gr.Dataframe(value=s("VD_Vertical-Domain-CH_BWER"), interactive=False, wrap=True)
                        gr.Markdown("### CER")
                        gr.Dataframe(value=s("VD_Vertical-Domain-CH"), interactive=False, wrap=True)
                    with gr.Tab("English Domains"):
                        gr.Markdown("### B-WER (Hotword)")
                        gr.Dataframe(value=s("VD_Vertical-Domain-EN_BWER"), interactive=False, wrap=True)
                        gr.Markdown("### WER")
                        gr.Dataframe(value=s("VD_Vertical-Domain-EN"), interactive=False, wrap=True)

            # ─── Submit ───
            with gr.Tab("➕ Evaluate Your Model"):
                gr.Markdown(
                    """
                    ## Evaluate Your ASR Model

                    Provide the path to your results JSON file. The module will be auto-detected from language codes.
                    """
                )
                with gr.Row():
                    model_path_input = gr.Textbox(
                        label="JSON File Path",
                        placeholder="/path/to/YourModel.json",
                        scale=5,
                    )
                    submit_btn = gr.Button("🎯 Evaluate", variant="primary", scale=1, size="lg")

                submit_status = gr.Markdown(label="Results")
                sub_labels = gr.Textbox(visible=False)

                with gr.Row():
                    sub1 = gr.Dataframe(label="Sub-leaderboard 1", interactive=False, wrap=True)
                    sub2 = gr.Dataframe(label="Sub-leaderboard 2", interactive=False, wrap=True)
                sub3 = gr.Dataframe(label="Sub-leaderboard 3", interactive=False, wrap=True)

                gr.Markdown(
                    """
                    ---
                    ### JSON Format

                    Your results file must follow this structure:
                    ```json
                    {
                      "audios": [
                        {
                          "aid": "LANG#hash_id",
                          "language": "ARE",
                          "segments": [
                            {
                              "sid": "LANG#hash_id#begin_time#end_time",
                              "begin_time": "165.613",
                              "end_time": "169.920",
                              "text": "transcribed text here",
                              "lang": "ARE"
                            }
                          ]
                        }
                      ]
                    }
                    ```

                    - `aid`: Audio identifier (language prefix + hash)
                    - `language`: ISO language/region code matching the benchmark
                    - `segments`: List of transcribed segments with timestamps
                    - The model name is derived from the filename (e.g., `MyModel.json` → model name "MyModel")
                    - The benchmark module is auto-detected from languages present in your file
                    """
                )

                submit_btn.click(
                    fn=submit_new_model,
                    inputs=[model_path_input],
                    outputs=[submit_status, sub_labels, sub1, sub2, sub3],
                )

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=args.port, share=args.share)
