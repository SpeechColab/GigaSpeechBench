#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path


def parse_segment_check(p: Path):
    vals = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
    return vals


def collect_unaligned(results_root: Path):
    rows = []
    for p in sorted(results_root.glob("*/*/segment_check.txt")):
        country = p.parent.parent.name
        model = p.parent.name
        vals = parse_segment_check(p)
        try:
            ref_n = int(float(vals.get("ref_segments", 0)))
        except Exception:
            ref_n = 0
        try:
            hyp_n = int(float(vals.get("hyp_segments", 0)))
        except Exception:
            hyp_n = 0
        try:
            matched = int(float(vals.get("matched_segments", 0)))
        except Exception:
            matched = 0

        miss_in_hyp = ref_n - matched
        miss_in_ref = hyp_n - matched

        first_unmatched = ""
        if miss_in_hyp > 0:
            first_unmatched = vals.get("first_unmatched_in_hyp", "")
        elif miss_in_ref > 0:
            first_unmatched = vals.get("first_unmatched_in_ref", "")

        if matched < ref_n or matched < hyp_n:
            rows.append((country, model, ref_n, hyp_n, matched, miss_in_hyp, miss_in_ref, first_unmatched))
    return rows


def main():
    parser = argparse.ArgumentParser(description="Collect unaligned entries from segment_check.txt files.")
    parser.add_argument("--results_root", required=True)
    parser.add_argument("--out_txt", required=True)
    args = parser.parse_args()

    rows = collect_unaligned(Path(args.results_root))
    out = Path(args.out_txt)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        f.write("country\tmodel\tref_segments\thyp_segments\tmatched_segments\tmissing_in_hyp\tmissing_in_ref\tfirst_unmatched\n")
        for row in rows:
            f.write("\t".join(str(x) for x in row) + "\n")

    print(f"unaligned_entries={len(rows)}")
    print(f"output={out}")


if __name__ == "__main__":
    main()
