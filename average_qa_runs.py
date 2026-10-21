"""
Average QA results over repeated runs (seeds) and compare setups.

Each --config gives a label and a comma-separated list of result files, one
per seed, in the same seed order for every config. Prints the mean ± standard
deviation across runs, seed-matched differences for each --pair, and a sign
test on question-level F1 averaged over the runs.

Example:
    .venv/bin/python average_qa_runs.py \
        --config "A-MEM=a42.json,a43.json,a44.json" \
        --config "A-MEM + C=c42.json,c43.json,c44.json" \
        --pair "A-MEM + C:A-MEM" --seeds 42 43 44 --output report.md
"""

from __future__ import annotations

import argparse
import statistics
from typing import Dict, List

from compare_qa_runs import METRICS, SPLIT_NAMES, SPLITS, load, mean, per_question_f1, sign_test


def fmt(values: List[float]) -> str:
    if len(values) == 1:
        return f"{values[0]:.4f}"
    return f"{statistics.mean(values):.4f} ± {statistics.stdev(values):.4f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--config", action="append", required=True, help='"Label=f1.json,f2.json,..."')
    parser.add_argument("--pair", action="append", default=[], help='"Label B:Label A" reports B minus A')
    parser.add_argument("--seeds", nargs="+", default=None, help="seed of each file, for display")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    configs: Dict[str, List[Dict]] = {}
    for spec in args.config:
        label, paths = spec.split("=", 1)
        configs[label] = [load(p) for p in paths.split(",")]
    labels = list(configs)
    n_runs = {len(v) for v in configs.values()}
    if len(n_runs) != 1:
        raise SystemExit("every config needs the same number of runs")
    n_runs = n_runs.pop()
    seeds = args.seeds or [str(i + 1) for i in range(n_runs)]

    lines: List[str] = []

    def emit(text: str = "") -> None:
        print(text)
        lines.append(text)

    emit(f"## F1 by category, mean ± std over {n_runs} runs (seeds {', '.join(seeds)})")
    emit("")
    emit("| Split | " + " | ".join(labels) + " |")
    emit("|---|" + "---|" * len(labels))
    for split in SPLITS:
        cells = []
        means = {lab: statistics.mean(mean(r, split, "f1") for r in runs) for lab, runs in configs.items()}
        best = max(means.values())
        for lab, runs in configs.items():
            text = fmt([mean(r, split, "f1") for r in runs])
            cells.append(f"**{text}**" if means[lab] == best else text)
        emit(f"| {SPLIT_NAMES[split]} | " + " | ".join(cells) + " |")

    emit("")
    emit("## All metrics, overall, mean ± std")
    emit("")
    emit("| Metric | " + " | ".join(labels) + " |")
    emit("|---|" + "---|" * len(labels))
    for metric in METRICS:
        means = {lab: statistics.mean(mean(r, "overall", metric) for r in runs) for lab, runs in configs.items()}
        best = max(means.values())
        cells = []
        for lab, runs in configs.items():
            text = fmt([mean(r, "overall", metric) for r in runs])
            cells.append(f"**{text}**" if means[lab] == best else text)
        emit(f"| {metric} | " + " | ".join(cells) + " |")

    emit("")
    emit("## Per-run overall F1")
    emit("")
    emit("| Config | " + " | ".join(f"seed {s}" for s in seeds) + " | Range |")
    emit("|---|" + "---|" * (len(seeds) + 1))
    for lab, runs in configs.items():
        vals = [mean(r, "overall", "f1") for r in runs]
        emit(f"| {lab} | " + " | ".join(f"{v:.4f}" for v in vals) + f" | {max(vals) - min(vals):.4f} |")

    for spec in args.pair:
        b_label, a_label = spec.split(":", 1)
        a_runs, b_runs = configs[a_label], configs[b_label]
        emit("")
        emit(f"## {b_label} minus {a_label}")
        emit("")
        emit("| Split | " + " | ".join(f"seed {s}" for s in seeds) + " | Mean Δ | Seeds where B > A |")
        emit("|---|" + "---|" * (len(seeds) + 2))
        for split in SPLITS:
            deltas = [mean(b, split, "f1") - mean(a, split, "f1") for a, b in zip(a_runs, b_runs)]
            wins = sum(d > 0 for d in deltas)
            emit(f"| {SPLIT_NAMES[split]} | " + " | ".join(f"{d:+.4f}" for d in deltas)
                 + f" | {statistics.mean(deltas):+.4f} | {wins}/{len(deltas)} |")

        # Question-level F1 averaged over runs, then a sign test.
        a_maps = [per_question_f1(r) for r in a_runs]
        b_maps = [per_question_f1(r) for r in b_runs]
        better = worse = same = 0
        for key in a_maps[0]:
            for m in a_maps + b_maps:
                if m[key][0] != a_maps[0][key][0]:
                    raise SystemExit(f"question mismatch at {key}")
            a_avg = statistics.mean(m[key][1] for m in a_maps)
            b_avg = statistics.mean(m[key][1] for m in b_maps)
            better += b_avg - a_avg > 1e-9
            worse += a_avg - b_avg > 1e-9
            same += abs(b_avg - a_avg) <= 1e-9
        emit("")
        emit(f"Question-level F1 averaged over runs: {better} better, {worse} worse, {same} same; "
             f"sign-test p = {sign_test(better, worse):.2f}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
