"""
Compare two consolidation runs from their merge logs.

Both versions are scored with the current checks, so differences come from
the merges themselves, not from a change in how they are judged.

Example:
    .venv/bin/python compare_consolidation_versions.py --old v1 --new v2 --samples 0 1
"""

from __future__ import annotations

import argparse
import json
import os
import statistics

from memory_consolidation import (
    compression_ratio,
    dropped_relative_times,
    missing_facts,
    unresolved_relative_times,
)
from memory_layer_robust import RobustMemoryNote


def _sources(group):
    return [
        RobustMemoryNote(content=s["content"], timestamp=s["timestamp"], keywords=[], tags=[],
                         context="", category="")
        for s in group["sources"]
    ]


def score_log(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        log = json.load(handle)
    merged = [g for g in log["groups"] if g["outcome"] == "merged"]
    ratios, missing, relative, dropped, over_length = [], 0, 0, 0, 0
    for group in merged:
        sources = _sources(group)
        text = group["consolidated_content"]
        ratio = compression_ratio(sources, text)
        ratios.append(ratio)
        missing += bool(missing_facts(sources, text))
        relative += bool(unresolved_relative_times(text))
        dropped += bool(dropped_relative_times(sources, text))
        over_length += ratio > 1.0
    return {
        "groups": log["counts"]["groups"],
        "merged": len(merged),
        "kept_separate": log["counts"]["different"],
        "rejected": log["counts"]["rejected"],
        "llm_calls": log["counts"]["llm_calls"],
        "median_ratio": statistics.median(ratios) if ratios else None,
        "mean_ratio": statistics.mean(ratios) if ratios else None,
        "merges_longer_than_sources": over_length,
        "merges_missing_facts": missing,
        "merges_with_relative_times": relative,
        "merges_dropping_times": dropped,
        "labels": {g["label"]: sum(1 for x in log["groups"] if x["label"] == g["label"]) for g in log["groups"]},
        "by_indices": {tuple(g["indices"]): g for g in log["groups"]},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--old", default="v1")
    parser.add_argument("--new", default="v2")
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--log_dir", default="analysis")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    rows = ["merged", "kept_separate", "rejected", "llm_calls", "median_ratio", "mean_ratio",
            "merges_longer_than_sources", "merges_missing_facts", "merges_with_relative_times",
            "merges_dropping_times"]
    report = {}
    for sample in args.samples:
        old = score_log(os.path.join(args.log_dir, f"consolidation_log_sample_{sample}_{args.old}.json"))
        new = score_log(os.path.join(args.log_dir, f"consolidation_log_sample_{sample}_{args.new}.json"))
        label_changes = [
            {"indices": list(k), args.old: old["by_indices"][k]["label"], args.new: g["label"]}
            for k, g in new["by_indices"].items()
            if k in old["by_indices"] and old["by_indices"][k]["label"] != g["label"]
        ]
        print(f"\n=== sample {sample} ===")
        print(f"{'metric':<30} {args.old:>8} {args.new:>8}")
        for row in rows:
            a, b = old[row], new[row]
            fmt = (lambda v: f"{v:>8.2f}") if isinstance(a, float) else (lambda v: f"{v:>8}")
            print(f"{row:<30} {fmt(a)} {fmt(b)}")
        print(f"label changes: {label_changes or 'none'}")
        report[str(sample)] = {
            args.old: {k: v for k, v in old.items() if k != "by_indices"},
            args.new: {k: v for k, v in new.items() if k != "by_indices"},
            "label_changes": label_changes,
        }

    output = args.output or os.path.join(args.log_dir, f"consolidation_compare_{args.old}_vs_{args.new}.json")
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(f"\nWrote {output}")


if __name__ == "__main__":
    main()
