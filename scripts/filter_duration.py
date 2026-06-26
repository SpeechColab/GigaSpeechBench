#!/usr/bin/env python3
"""Filter normalized ref/hyp JSON files by segment duration.

Reads from text_normalized/{module}/ and writes filtered versions to
text_normalized_mindur/{module}/ keeping only segments where (end - start) > threshold.
"""
import argparse
import json
import os


def filter_by_duration(data: list, min_duration: float) -> list:
    """Keep segments where duration > min_duration."""
    return [seg for seg in data if (float(seg.get("end", 0)) - float(seg.get("start", 0))) > min_duration]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--norm_root", required=True, help="e.g. data/text_normalized/Low-Resource-Languages")
    parser.add_argument("--out_root", required=True, help="e.g. data/text_normalized_mindur/Low-Resource-Languages")
    parser.add_argument("--min_duration", type=float, default=0.5)
    args = parser.parse_args()

    ref_dir = os.path.join(args.norm_root, "ref")
    hyp_dir = os.path.join(args.norm_root, "hyp")
    out_ref = os.path.join(args.out_root, "ref")
    out_hyp = os.path.join(args.out_root, "hyp")

    # Filter ref (duration only)
    if os.path.isdir(ref_dir):
        os.makedirs(out_ref, exist_ok=True)
        for fname in os.listdir(ref_dir):
            if not fname.endswith(".json"):
                continue
            src = os.path.join(ref_dir, fname)
            data = json.load(open(src, encoding="utf-8"))
            filtered = filter_by_duration(data, args.min_duration)
            dst = os.path.join(out_ref, fname)
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(filtered, f, ensure_ascii=False)
            print(f"  ref {fname}: {len(data)} -> {len(filtered)}")

    # Filter hyp (duration only)
    if os.path.isdir(hyp_dir):
        for country in os.listdir(hyp_dir):
            country_dir = os.path.join(hyp_dir, country)
            if not os.path.isdir(country_dir):
                continue
            out_country = os.path.join(out_hyp, country)
            os.makedirs(out_country, exist_ok=True)
            for fname in os.listdir(country_dir):
                if not fname.endswith(".json"):
                    continue
                src = os.path.join(country_dir, fname)
                data = json.load(open(src, encoding="utf-8"))
                filtered = filter_by_duration(data, args.min_duration)
                dst = os.path.join(out_country, fname)
                with open(dst, "w", encoding="utf-8") as f:
                    json.dump(filtered, f, ensure_ascii=False)
            print(f"  hyp {country}: done")

    print(f"Filtered (duration > {args.min_duration}s) -> {args.out_root}")


if __name__ == "__main__":
    main()
