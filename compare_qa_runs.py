"""
Compare several QA result files (A-MEM, T-MEM, with or without consolidation).

Prints overall and per-category means for the thesis metrics, then a
question-level F1 comparison of every run against a baseline run with an
exact two-sided sign test. Optionally writes a Markdown report.

Example:
    .venv/bin/python compare_qa_runs.py \
        --run "A-MEM=path/amem.json" --run "T-MEM V2=path/tmem.json" \
        --baseline "A-MEM" --output report.md
"""

from __future__ import annotations

import argparse
import json
import math
from typing import Dict, List, Tuple

METRICS = ["f1", "exact_match", "rougeL_f", "bleu1", "meteor", "bert_f1", "sbert_similarity"]
SPLITS = ["overall", "category_1", "category_2", "category_3", "category_4", "category_5"]
SPLIT_NAMES = {
    "overall": "Overall", "category_1": "Cat 1 multi-hop", "category_2": "Cat 2 temporal",
    "category_3": "Cat 3 open-domain", "category_4": "Cat 4 single-hop", "category_5": "Cat 5 adversarial",
}


def load(path: str) -> Dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def mean(result: Dict, split: str, metric: str):
    try:
        return float(result["aggregate_metrics"][split][metric]["mean"])
    except KeyError:
        return None


def per_question_f1(result: Dict) -> Dict[Tuple[str, int], Tuple[str, float, int]]:
    """(sample, position in sample) -> (question, f1, category)."""
    out, position = {}, {}
    for item in result["individual_results"]:
        sample = str(item["sample_id"])
        pos = position.get(sample, 0)
        position[sample] = pos + 1
        metrics = item["metrics"]
        if isinstance(metrics, str):
            metrics = eval(metrics)  # noqa: S307 - older result files stored a dict repr
        out[(sample, pos)] = (item["question"], float(metrics["f1"]), int(item["category"]))
    return out


def sign_test(better: int, worse: int) -> float:
    n = better + worse
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(better, worse) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--run", action="append", required=True, help='"Label=path/to/results.json"')
    parser.add_argument("--baseline", required=True, help="label of the run to compare against")
    parser.add_argument("--output", default=None, help="optional Markdown report path")
    args = parser.parse_args()

    runs: List[Tuple[str, Dict]] = []
    for spec in args.run:
        label, path = spec.split("=", 1)
        runs.append((label, load(path)))
    labels = [label for label, _ in runs]
    if args.baseline not in labels:
        raise SystemExit(f"baseline {args.baseline!r} not among runs {labels}")
    by_label = dict(runs)

    lines: List[str] = []

    def emit(text: str = "") -> None:
        print(text)
        lines.append(text)

    emit("## F1 by category")
    emit("")
    emit("| Split | n | " + " | ".join(labels) + " |")
    emit("|---|---|" + "---|" * len(labels))
    for split in SPLITS:
        n = by_label[args.baseline]["aggregate_metrics"].get(split, {}).get("f1", {}).get("count", "")
        cells = [mean(r, split, "f1") for _, r in runs]
        best = max(c for c in cells if c is not None)
        shown = [f"**{c:.4f}**" if c == best else f"{c:.4f}" for c in cells]
        emit(f"| {SPLIT_NAMES[split]} | {n} | " + " | ".join(shown) + " |")

    emit("")
    emit("## All metrics, overall")
    emit("")
    emit("| Metric | " + " | ".join(labels) + " |")
    emit("|---|" + "---|" * len(labels))
    for metric in METRICS:
        cells = [mean(r, "overall", metric) for _, r in runs]
        best = max(c for c in cells if c is not None)
        shown = [f"**{c:.4f}**" if c == best else f"{c:.4f}" for c in cells]
        emit(f"| {metric} | " + " | ".join(shown) + " |")

    emit("")
    emit(f"## Question-level F1 vs {args.baseline}")
    emit("")
    emit("| Run | Better | Worse | Same | Sign-test p |")
    emit("|---|---|---|---|---|")
    base = per_question_f1(by_label[args.baseline])
    for label, result in runs:
        if label == args.baseline:
            continue
        other = per_question_f1(result)
        better = worse = same = 0
        for key, (question, f1, _) in base.items():
            if key not in other or other[key][0] != question:
                raise SystemExit(f"{label}: question mismatch at {key}")
            delta = other[key][1] - f1
            better += delta > 1e-9
            worse += delta < -1e-9
            same += abs(delta) <= 1e-9
        emit(f"| {label} | {better} | {worse} | {same} | {sign_test(better, worse):.2f} |")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
