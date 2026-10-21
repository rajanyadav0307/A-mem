"""
Summarize a fresh run folder (A-MEM, T-MEM V2, T-MEM V2 + consolidation).

Reads <dir>/results/<system>_seed<N>.json and writes <dir>/REPORT.md with a
simple stacked table: each system's scores and its gain over A-MEM.

Example:
    .venv/bin/python summarize_fresh_run.py --dir experiments/fresh_run_2026-10-21_14-27
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics
from datetime import datetime

from analyze_consolidation_qa import classify_cat5
from compare_qa_runs import load, per_question_f1

SYSTEMS = [
    ("amem", "A-MEM (starting point)"),
    ("tmem_v2", "+ time ranking (T-MEM V2)"),
    ("tmem_v2_consolidated", "+ consolidation (T-MEM V2 + C)"),
]


def scores(result: dict) -> dict:
    rows = list(per_question_f1(result).values())
    refusals = [classify_cat5(r["prediction"], r["reference"]) == "not_mentioned"
                for r in result["individual_results"] if str(r["category"]) == "5"]
    return {
        "answerable_f1": statistics.mean(f for _, f, c in rows if c != 5),
        "time_f1": statistics.mean(f for _, f, c in rows if c == 2),
        "trap_refusal": statistics.mean(refusals),
        "overall_f1_paper": statistics.mean(f for _, f, _ in rows),
        "questions": len(rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()

    manifest = json.load(open(os.path.join(args.dir, "manifest.json"), encoding="utf-8"))
    started = open(os.path.join(args.dir, "started_at.txt")).read().strip() if os.path.exists(
        os.path.join(args.dir, "started_at.txt")) else "unknown"
    finished = open(os.path.join(args.dir, "finished_at.txt")).read().strip() if os.path.exists(
        os.path.join(args.dir, "finished_at.txt")) else "unknown"

    per_system = {}
    for key, _ in SYSTEMS:
        files = sorted(glob.glob(os.path.join(args.dir, "results", f"{key}_seed*.json")))
        runs = {}
        for path in files:
            seed = re.search(r"_seed(\d+)\.json$", path).group(1)
            result = load(path)
            if result["total_questions"] != manifest["questions"]:
                raise SystemExit(f"{path}: {result['total_questions']} questions, expected {manifest['questions']}")
            runs[seed] = scores(result)
        per_system[key] = runs

    seeds = sorted(per_system["amem"])
    for key, runs in per_system.items():
        if sorted(runs) != seeds:
            raise SystemExit(f"{key} has seeds {sorted(runs)}, A-MEM has {seeds}")

    def mean(key, metric):
        return statistics.mean(per_system[key][s][metric] for s in seeds)

    lines = [
        f"# Fresh run {os.path.basename(args.dir.rstrip('/'))}",
        "",
        f"- Started (UTC): {started}",
        f"- Finished (UTC): {finished}",
        f"- Report written (local): {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Code: `{manifest['git_commit'][:8]}` on `{manifest['branch']}`",
        f"- Samples {manifest['samples']}, {manifest['questions']} questions, k = {manifest['retrieve_k']}, "
        f"seeds {', '.join(seeds)}, model {manifest['model']}",
        "",
        "## Results (average of the runs)",
        "",
        "| Step | System | Answerable questions F1 | Time questions F1 | Trap questions refused | Overall F1 (paper scoring) |",
        "|---|---|---|---|---|---|",
    ]
    for i, (key, label) in enumerate(SYSTEMS, start=1):
        lines.append(f"| {i} | {label} | {mean(key, 'answerable_f1'):.3f} | {mean(key, 'time_f1'):.3f} | "
                     f"{mean(key, 'trap_refusal'):.1%} | {mean(key, 'overall_f1_paper'):.3f} |")

    lines += ["", "## Gain over A-MEM", "",
              "| System | Answerable questions | Time questions | Trap refusals |", "|---|---|---|---|"]
    for key, label in SYSTEMS[1:]:
        lines.append(f"| {label} | {mean(key, 'answerable_f1') - mean('amem', 'answerable_f1'):+.3f} | "
                     f"{mean(key, 'time_f1') - mean('amem', 'time_f1'):+.3f} | "
                     f"{(mean(key, 'trap_refusal') - mean('amem', 'trap_refusal')) * 100:+.1f} points |")

    lines += ["", "## Each run", "",
              "| System | Seed | Answerable F1 | Time F1 | Trap refused | Overall F1 |", "|---|---|---|---|---|---|"]
    for key, label in SYSTEMS:
        for s in seeds:
            r = per_system[key][s]
            lines.append(f"| {label} | {s} | {r['answerable_f1']:.3f} | {r['time_f1']:.3f} | "
                         f"{r['trap_refusal']:.1%} | {r['overall_f1_paper']:.3f} |")

    lines += ["", "**What the columns mean**",
              "- *Answerable questions*: categories 1–4 (233 questions).",
              "- *Time questions*: category 2 (63 questions), the questions T-MEM V2 is built for.",
              "- *Trap questions refused*: category 5 (71 questions) are about things never said; "
              "answering \"Not mentioned\" is correct.",
              "- *Overall F1 (paper scoring)*: all 304 questions, scored as in the paper (category 5 counts "
              "the trap answer as right)."]

    report = "\n".join(lines) + "\n"
    with open(os.path.join(args.dir, "REPORT.md"), "w", encoding="utf-8") as handle:
        handle.write(report)
    with open(os.path.join(args.dir, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump({"seeds": seeds, "per_system": per_system}, handle, indent=2)
    print(report)


if __name__ == "__main__":
    main()
