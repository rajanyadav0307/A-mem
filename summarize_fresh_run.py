"""
Summarize a fresh run folder (A-MEM, T-MEM V2, T-MEM V2 + consolidation).

Reads <dir>/results/<system>_seed<N>.json and writes <dir>/REPORT.md with a
simple stacked table: each system's scores and its gain over A-MEM.
With --include_from, systems missing from <dir> are read from earlier run
folders (for example steps 1-3 from an earlier fresh run, step 4 from <dir>).

Example:
    .venv/bin/python summarize_fresh_run.py --dir experiments/fresh_run_2026-10-21_14-27
    .venv/bin/python summarize_fresh_run.py --dir experiments/fresh_run_2026-10-21_16-21_step4_conflict \
        --include_from experiments/fresh_run_2026-10-21_14-27
"""

from __future__ import annotations

import argparse
import collections
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
    ("tmem_v2_consolidated_conflict", "+ conflict handling (T-MEM V2 + C + CH)"),
]


def scores(result: dict, subset=None) -> dict:
    keyed = per_question_f1(result)  # (sample, position) -> (question, f1, category)
    rows = list(keyed.values())
    refusals = [classify_cat5(r["prediction"], r["reference"]) == "not_mentioned"
                for r in result["individual_results"] if str(r["category"]) == "5"]
    out = {}
    if subset:
        raw = {}
        pos = collections.Counter()
        for r in result["individual_results"]:
            key = (str(r["sample_id"]), pos[str(r["sample_id"])])
            pos[str(r["sample_id"])] += 1
            raw[key] = r
        sub = [keyed[k] for k in subset]
        sub5 = [raw[k] for k in subset if keyed[k][2] == 5]
        out = {
            "subset_answerable_f1": statistics.mean(f for _, f, c in sub if c != 5),
            "subset_trap_refusal": statistics.mean(
                classify_cat5(r["prediction"], r["reference"]) == "not_mentioned" for r in sub5) if sub5 else None,
        }
    return out | {
        "answerable_f1": statistics.mean(f for _, f, c in rows if c != 5),
        "time_f1": statistics.mean(f for _, f, c in rows if c == 2),
        "trap_refusal": statistics.mean(refusals),
        "overall_f1_paper": statistics.mean(f for _, f, _ in rows),
        "questions": len(rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dir", required=True)
    parser.add_argument("--include_from", nargs="*", default=[],
                        help="earlier run folders to take missing systems from")
    parser.add_argument("--subset", default=None,
                        help="JSON with a fixed question subset (e.g. analysis/conflict_timeline_questions.json)")
    parser.add_argument("--systems", nargs="*", default=None,
                        help='systems to report as "key=label"; the first is the reference (default: the 4 steps)')
    parser.add_argument("--vs_first", action="store_true",
                        help="compare every system with the first one, instead of each step with the step before")
    args = parser.parse_args()
    systems_wanted = [tuple(x.split("=", 1)) for x in args.systems] if args.systems else SYSTEMS

    manifest = json.load(open(os.path.join(args.dir, "manifest.json"), encoding="utf-8"))
    started = open(os.path.join(args.dir, "started_at.txt")).read().strip() if os.path.exists(
        os.path.join(args.dir, "started_at.txt")) else "unknown"
    finished = open(os.path.join(args.dir, "finished_at.txt")).read().strip() if os.path.exists(
        os.path.join(args.dir, "finished_at.txt")) else "unknown"

    subset, subset_info = None, None
    if args.subset:
        subset_info = json.load(open(args.subset, encoding="utf-8"))
        subset = [(str(q["sample"]), q["question_index"]) for q in subset_info["questions"]]
    per_system, source_of = {}, {}
    for key, _ in systems_wanted:
        files = []
        for folder in [args.dir] + list(args.include_from):
            files = sorted(glob.glob(os.path.join(folder, "results", f"{key}_seed*.json")))
            if files:
                source_of[key] = folder
                break
        if not files:
            continue
        runs = {}
        for path in files:
            seed = re.search(r"_seed(\d+)\.json$", path).group(1)
            result = load(path)
            if result["total_questions"] != manifest["questions"]:
                raise SystemExit(f"{path}: {result['total_questions']} questions, expected {manifest['questions']}")
            runs[seed] = scores(result, subset)
        per_system[key] = runs

    systems = [(k, label) for k, label in systems_wanted if k in per_system]
    seeds = sorted(per_system[systems[0][0]])
    for key, runs in per_system.items():
        if sorted(runs) != seeds:
            raise SystemExit(f"{key} has seeds {sorted(runs)}, {systems[0][0]} has {seeds}")

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
    ] + [f"- {label}: runs from `{source_of[key]}`" for key, label in systems] + [
        "",
        "## Results (average of the runs)",
        "",
        "| Step | System | Answerable questions F1 | Time questions F1 | Trap questions refused | Overall F1 (paper scoring) |",
        "|---|---|---|---|---|---|",
    ]
    for i, (key, label) in enumerate(systems, start=1):
        lines.append(f"| {i} | {label} | {mean(key, 'answerable_f1'):.3f} | {mean(key, 'time_f1'):.3f} | "
                     f"{mean(key, 'trap_refusal'):.1%} | {mean(key, 'overall_f1_paper'):.3f} |")

    base_key, base_label = systems[0]
    lines += ["", f"## Gain over {base_label}", "",
              "| System | Answerable questions | Time questions | Trap refusals |", "|---|---|---|---|"]
    for key, label in systems[1:]:
        lines.append(f"| {label} | {mean(key, 'answerable_f1') - mean(base_key, 'answerable_f1'):+.3f} | "
                     f"{mean(key, 'time_f1') - mean(base_key, 'time_f1'):+.3f} | "
                     f"{(mean(key, 'trap_refusal') - mean(base_key, 'trap_refusal')) * 100:+.1f} points |")

    pairs = [(base_key, k, label) for k, label in systems[1:]] if args.vs_first else \
        [(prev, k, label) for (prev, _), (k, label) in zip(systems, systems[1:])]
    title = f"Each setup vs {base_label} (matching runs)" if args.vs_first else \
        "Each step vs the step before (matching runs)"
    for metric, metric_name in (("answerable_f1", "answerable F1"), ("time_f1", "time F1")):
        lines += ["", f"## {title}: {metric_name}", "",
                  f"Change in {metric_name} for each seed; the last column counts the runs where it helped.", "",
                  "| Setup | " + " | ".join(f"Seed {sd}" for sd in seeds) + " | Mean change | Runs better |",
                  "|---|" + "---|" * (len(seeds) + 2)]
        for prev, key, label in pairs:
            deltas = [per_system[key][sd][metric] - per_system[prev][sd][metric] for sd in seeds]
            lines.append(f"| {label} | " + " | ".join(f"{d:+.3f}" for d in deltas) +
                         f" | {statistics.mean(deltas):+.3f} | {sum(d > 0 for d in deltas)} of {len(deltas)} |")

    lines += ["", "## Each run", "",
              "| System | Seed | Answerable F1 | Time F1 | Trap refused | Overall F1 |", "|---|---|---|---|---|---|"]
    for key, label in systems:
        for s in seeds:
            r = per_system[key][s]
            lines.append(f"| {label} | {s} | {r['answerable_f1']:.3f} | {r['time_f1']:.3f} | "
                         f"{r['trap_refusal']:.1%} | {r['overall_f1_paper']:.3f} |")

    if subset:
        n5 = sum(q["category"] == 5 for q in subset_info["questions"])
        lines += ["", f"## Timeline questions only ({len(subset)} questions, fixed before results)", "",
                  f"Rule: {subset_info['rule']}. Answerable: {len(subset) - n5}, trap questions: {n5}.", "",
                  "| System | Answerable F1 | Trap questions refused |", "|---|---|---|"]
        for key, label in systems:
            refusal = [per_system[key][sd]["subset_trap_refusal"] for sd in seeds]
            lines.append(f"| {label} | {mean(key, 'subset_answerable_f1'):.3f} | "
                         f"{statistics.mean(refusal):.1%} |")

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
