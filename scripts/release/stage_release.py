#!/usr/bin/env python3
"""
Stage ALL modules for HuggingFace release.
Copies only audio files that have matching ref JSONs.
Does NOT modify the original repo. Archives extracted to /tmp.

5 Modules:
  1. Low-Resource-Languages (excluding JPN, KOR)
  2. fleurs
  3. common-voice
  4. CH-EN-Dialects
  5. Vertical-Domain

Staging structure:
  dataset_staging/{MODULE}/data/{LANG}/
    audio/*
    ref/*.json

Usage:
  python3 scripts/stage_release.py
  python3 scripts/stage_release.py --dry_run
  python3 scripts/stage_release.py --module Low-Resource-Languages
"""

import argparse
import glob
import json
import os
import re
import shutil
import tarfile
import tempfile


def load_json_tolerant(path):
    """Load JSON with tolerance for trailing commas."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return json.loads(text)

BENCH = "/home/v-yujietu/BenchData/Multilingual-ASR-Benchmark"
STAGING_DIR = "/home/v-yujietu/dataset_staging"

# ── Module definitions ──────────────────────────────────────────

MODULES = {
    "Low-Resource-Languages": {
        "base": os.path.join(BENCH, "Low-Resource-Languages"),
        "audio_batches": ["audio/testbatch", "audio/batch_1", "audio/batch_2"],
        "ref_root": "text/ref",
        "langs": [
            "ARE", "DZA", "EGY", "IDN", "IRQ", "MAR", "MYS",
            "PHL", "PHL_EN", "PHL_noEN",
            "SAU", "SYR", "THA", "VNM",
        ],
        "audio_lang_map": {"PHL_EN": "PHL", "PHL_noEN": "PHL"},
        "archives": {"SYR": "audio/SYR.tar.gz"},
    },
    "fleurs": {
        "base": os.path.join(BENCH, "fleurs"),
        "audio_batches": ["audio"],
        "ref_root": "text/ref",
        "langs": ["EGY", "IDN", "JPN", "KOR", "MYS", "PHL", "THA", "VNM"],
        "audio_lang_map": {},
        "archives": {},
    },
    "common-voice": {
        "base": os.path.join(BENCH, "common-voice"),
        "audio_batches": ["audio"],
        "ref_root": "text/ref",
        "langs": ["AR", "IDN", "JPN", "KOR", "THA", "VNM"],
        "audio_lang_map": {},
        "archives": {},
        "audio_exts": [".mp3", ".wav"],
    },
    "CH-EN-Dialects": {
        "base": os.path.join(BENCH, "CH-EN-Dialects"),
        "audio_batches": ["audio/testbatch", "audio/batch_1"],
        "ref_root": "text/ref",
        "langs": [
            "CHN-EN", "IDN-EN", "JIN", "JPN-EN", "PHL-EN",
            "SCT-EN", "SGP-EN", "XIANG",
            "GAN", "MIN", "WU", "YUE",
        ],
        "audio_lang_map": {},
        "archives": {
            "__all__": "audio/audio_list_20260315.tar.gz",
            "MIN": "MIN.tar.gz",
            "WU": "WU.tar.gz",
            "YUE": "YUE.tar.gz",
        },
        # MIN/WU/YUE audio_name includes .wav extension, use as-is
        "audio_name_is_filename": ["MIN", "WU", "YUE"],
        # Extra ref zips to merge into ref dirs
        "ref_zips": ["Delivery_0410.zip", "Delivery_0417.zip"],
    },
    "Vertical-Domain": {
        "base": os.path.join(BENCH, "Vertical-Domain"),
        "audio_batches": ["audio/testbatch"],
        "ref_root": "text/ref",
        "langs": [
            "AGR-CH", "AGR-EN", "AIT-CH", "AIT-EN", "ART-CH", "ART-EN",
            "BIO-CH", "BIO-EN", "ECM-CH", "ECM-EN", "EDU-CH", "EDU-EN",
            "ENG-CH", "ENG-EN", "ENT-CH", "ENT-EN", "FIN-CH", "FIN-EN",
            "HUM-CH", "HUM-EN", "LAW-CH", "LAW-EN", "MED-CH", "MED-EN",
            "MIL-CH", "MIL-EN",
        ],
        "audio_lang_map": {},
        "archives": {"__all__": "audio/batch_1/vertical_20260325.tar.gz"},
    },
}


def find_audio_file(audio_name, audio_lang, audio_roots, extra_roots=None,
                    exts=(".wav",)):
    """Search for audio file across roots. Tries hash and underscore naming."""
    candidates = []
    for ext in exts:
        candidates.append(audio_name + ext)
        candidates.append(audio_name.replace("#", "_") + ext)
    # Also try audio_name as-is if it already has extension
    for ext in exts:
        if audio_name.endswith(ext):
            candidates.append(audio_name)
            break

    search = list(audio_roots)
    if extra_roots:
        search.extend(extra_roots)

    # Search in {root}/{audio_lang}/{filename}
    for root in search:
        for fname in candidates:
            path = os.path.join(root, audio_lang, fname)
            if os.path.isfile(path):
                return path

    # Flat/recursive search in extra roots (for archives)
    if extra_roots:
        for root in extra_roots:
            for dirpath, _, filenames in os.walk(root):
                for fname in candidates:
                    if fname in filenames:
                        return os.path.join(dirpath, fname)
    return None


def extract_archive(archive_path, label=""):
    """Extract tar.gz to temp dir. Returns temp dir path or None."""
    if not os.path.isfile(archive_path):
        print(f"  [WARN] Archive not found: {archive_path}")
        return None
    tmp_dir = tempfile.mkdtemp(prefix=f"stage_{label}_")
    print(f"  Extracting {os.path.basename(archive_path)} to {tmp_dir} ...",
          flush=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(tmp_dir)
    print(f"  Done.", flush=True)
    return tmp_dir


def extract_ref_zips(base, ref_root, ref_zips, dry_run=False):
    """Extract ref zip files into the ref directory structure."""
    import zipfile
    for zname in ref_zips:
        # Try base dir and ref_root
        for search_dir in [base, ref_root]:
            zpath = os.path.join(search_dir, zname)
            if os.path.isfile(zpath):
                break
        else:
            print(f"  [WARN] Ref zip not found: {zname}")
            continue

        if dry_run:
            print(f"  (dry run, skip extracting ref zip {zname})")
            continue

        print(f"  Extracting ref zip {zname} ...", flush=True)
        with zipfile.ZipFile(zpath, 'r') as z:
            for member in z.namelist():
                if not member.endswith('.json'):
                    continue
                # e.g. Delivery_0417/JPN-EN/xxx.json -> extract to ref_root/JPN-EN/
                parts = member.split('/')
                if len(parts) >= 3:
                    lang = parts[-2]
                    fname = parts[-1]
                    dest_dir = os.path.join(ref_root, lang)
                    dest = os.path.join(dest_dir, fname)
                    if not os.path.exists(dest):
                        os.makedirs(dest_dir, exist_ok=True)
                        with z.open(member) as src, open(dest, 'wb') as dst:
                            dst.write(src.read())
        print(f"  Done.", flush=True)


def stage_module(module_name, mod_cfg, dry_run=False):
    """Stage one module. Returns list of (lang, ref_count, audio_count, missing)."""
    base = mod_cfg["base"]
    audio_roots = [os.path.join(base, b) for b in mod_cfg["audio_batches"]]
    ref_root = os.path.join(base, mod_cfg["ref_root"])
    lang_map = mod_cfg.get("audio_lang_map", {})
    archives = mod_cfg.get("archives", {})
    exts = tuple(mod_cfg.get("audio_exts", [".wav"]))
    name_is_filename = set(mod_cfg.get("audio_name_is_filename", []))

    # Extract ref zips first (adds extra ref JSONs to ref dirs)
    ref_zips = mod_cfg.get("ref_zips", [])
    if ref_zips:
        extract_ref_zips(base, ref_root, ref_zips, dry_run)

    # Extract archives to tmp
    tmp_dirs = []
    extra_roots_map = {}  # lang -> [extra_root_dirs]
    for key, archive_rel in archives.items():
        archive_path = os.path.join(base, archive_rel)
        if dry_run:
            print(f"  (dry run, skip extracting {os.path.basename(archive_path)})")
        else:
            tmp = extract_archive(archive_path, label=f"{module_name}_{key}")
            if tmp:
                tmp_dirs.append(tmp)
                if key == "__all__":
                    for lang in mod_cfg["langs"]:
                        extra_roots_map.setdefault(lang, []).append(tmp)
                else:
                    extra_roots_map.setdefault(key, []).append(tmp)

    staging_base = os.path.join(STAGING_DIR, module_name, "data")
    results = []

    for lang in mod_cfg["langs"]:
        audio_lang = lang_map.get(lang, lang)
        ref_dir = os.path.join(ref_root, lang)

        if not os.path.isdir(ref_dir):
            results.append((lang, 0, 0, 0))
            continue

        staging_audio = os.path.join(staging_base, lang, "audio")
        staging_ref = os.path.join(staging_base, lang, "ref")
        if not dry_run:
            os.makedirs(staging_audio, exist_ok=True)
            os.makedirs(staging_ref, exist_ok=True)

        extra = extra_roots_map.get(lang)
        copied_ref = copied_audio = missing_audio = 0
        seen_audio = set()
        is_filename_mode = lang in name_is_filename

        for ref_file in sorted(os.listdir(ref_dir)):
            if not ref_file.endswith(".json"):
                continue
            ref_path = os.path.join(ref_dir, ref_file)
            try:
                data = load_json_tolerant(ref_path)
                audio_name = data.get("audio_name", "")
            except Exception:
                continue
            if not audio_name:
                continue

            # For MIN/WU/YUE: audio_name is already the filename (e.g. "xxx.wav")
            # For others: audio_name is stem, need to append extension
            if is_filename_mode:
                # Strip extension for find_audio_file, it will re-add
                stem = audio_name
                for ext in exts:
                    if audio_name.endswith(ext):
                        stem = audio_name[:-len(ext)]
                        break
                audio_path = find_audio_file(stem, audio_lang, audio_roots,
                                             extra, exts)
            else:
                audio_path = find_audio_file(audio_name, audio_lang, audio_roots,
                                             extra, exts)
            if audio_path is None:
                missing_audio += 1
                continue

            # Copy ref
            dst_ref = os.path.join(staging_ref, ref_file)
            if not dry_run and not os.path.exists(dst_ref):
                shutil.copy2(ref_path, dst_ref)
            copied_ref += 1

            # Copy audio (deduplicate)
            wav_name = os.path.basename(audio_path)
            if wav_name not in seen_audio:
                dst_audio = os.path.join(staging_audio, wav_name)
                if not dry_run and not os.path.exists(dst_audio):
                    shutil.copy2(audio_path, dst_audio)
                seen_audio.add(wav_name)
                copied_audio += 1

        results.append((lang, copied_ref, copied_audio, missing_audio))

    # Cleanup temp dirs
    for tmp in tmp_dirs:
        if os.path.isdir(tmp):
            print(f"  Cleaning up {tmp}", flush=True)
            shutil.rmtree(tmp)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--module", type=str, default=None,
                        help="Run only one module (e.g. 'fleurs')")
    args = parser.parse_args()

    modules_to_run = {}
    if args.module:
        if args.module not in MODULES:
            print(f"Unknown module: {args.module}")
            print(f"Available: {', '.join(MODULES.keys())}")
            return
        modules_to_run[args.module] = MODULES[args.module]
    else:
        modules_to_run = MODULES

    print(f"Staging dir: {STAGING_DIR}")
    print(f"Modules: {', '.join(modules_to_run.keys())}")
    print(f"Dry run: {args.dry_run}\n")

    grand_ref = grand_audio = grand_missing = 0

    for mod_name, mod_cfg in modules_to_run.items():
        print(f"\n{'='*60}")
        print(f"Module: {mod_name}")
        print(f"{'='*60}")

        results = stage_module(mod_name, mod_cfg, args.dry_run)

        print(f"\n{'Lang':<12} {'Ref':>6} {'Audio':>6} {'Missing':>8}")
        print("-" * 35)
        t_r = t_a = t_m = 0
        for lang, r, a, m in results:
            if r > 0 or m > 0:
                print(f"{lang:<12} {r:>6} {a:>6} {m:>8}")
            t_r += r; t_a += a; t_m += m
        print("-" * 35)
        print(f"{'SUBTOTAL':<12} {t_r:>6} {t_a:>6} {t_m:>8}")
        grand_ref += t_r; grand_audio += t_a; grand_missing += t_m

    print(f"\n{'='*60}")
    print(f"GRAND TOTAL: {grand_ref} ref, {grand_audio} audio, {grand_missing} missing")
    print(f"{'='*60}")

    if not args.dry_run:
        print(f"\nStaging complete: {STAGING_DIR}/")


if __name__ == "__main__":
    main()
