"""
Compare A-MEM and T-MEM evaluation result JSON files.

Example:
    .venv/bin/python compare_eval_results.py \
      --amem results_amem_2samples_gpt-4o-mini.json \
      --tmem results_tmem_2samples_gpt-4o-mini.json
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Dict, Iterable, List, Tuple


DEFAULT_METRICS = [
    "exact_match",
    "f1",
    "rougeL_f",
    "bleu1",
    "bert_f1",
    "meteor",
    "sbert_similarity",
]


def _load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _metric_mean(results: Dict, split: str, metric: str) -> float | None:
    try:
        return float(results["aggregate_metrics"][split][metric]["mean"])
    except KeyError:
        return None


def _format_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def _format_delta(delta: float | None) -> str:
    if delta is None:
        return "n/a"
    return f"{delta:+.4f}"


def _category_splits(results: Dict) -> List[str]:
    return sorted(
        [key for key in results.get("aggregate_metrics", {}) if key.startswith("category_")],
        key=lambda name: int(name.split("_")[1]),
    )


def _safe_delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return right - left


def _question_key(item: Dict) -> Tuple[int, str, str]:
    return (
        int(item.get("sample_id", -1)),
        str(item.get("category", "")),
        str(item.get("question", "")),
    )


def _question_level_summary(amem: Dict, tmem: Dict) -> Dict[str, int]:
    amem_map = {_question_key(item): item for item in amem.get("individual_results", [])}
    tmem_map = {_question_key(item): item for item in tmem.get("individual_results", [])}
    keys = sorted(set(amem_map) & set(tmem_map))

    wins = losses = ties = 0
    for key in keys:
        amem_f1 = float(amem_map[key]["metrics"].get("f1", 0.0))
        tmem_f1 = float(tmem_map[key]["metrics"].get("f1", 0.0))
        if tmem_f1 > amem_f1:
            wins += 1
        elif tmem_f1 < amem_f1:
            losses += 1
        else:
            ties += 1

    return {
        "matched_questions": len(keys),
        "tmem_f1_wins": wins,
        "tmem_f1_losses": losses,
        "ties": ties,
    }


def _build_table_rows(
    amem: Dict,
    tmem: Dict,
    split: str,
    metrics: Iterable[str],
) -> List[str]:
    rows = [
        f"### {split.replace('_', ' ').title()}",
        "",
        "| Metric | A-MEM | T-MEM | Delta (T-A) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric in metrics:
        amem_value = _metric_mean(amem, split, metric)
        tmem_value = _metric_mean(tmem, split, metric)
        delta = _safe_delta(amem_value, tmem_value)
        rows.append(
            f"| {metric} | {_format_float(amem_value)} | {_format_float(tmem_value)} | {_format_delta(delta)} |"
        )
    rows.append("")
    return rows


def compare_results(amem: Dict, tmem: Dict, metrics: Iterable[str]) -> str:
    lines: List[str] = []
    lines.append("# A-MEM vs T-MEM Comparison")
    lines.append("")
    lines.append(f"- A-MEM file: `{amem.get('memory_layer', 'unknown')}`")
    lines.append(f"- T-MEM file: `{tmem.get('memory_layer', 'unknown')}`")
    lines.append(f"- Dataset: `{amem.get('dataset', 'unknown')}` vs `{tmem.get('dataset', 'unknown')}`")
    lines.append(f"- Total questions: `{amem.get('total_questions', 'unknown')}` vs `{tmem.get('total_questions', 'unknown')}`")

    if "temporal_config" in tmem:
        cfg = tmem["temporal_config"]
        lines.append(
            "- T-MEM temporal config: "
            f"`alpha={cfg.get('blend_alpha')}`, "
            f"`lambda={cfg.get('decay_lambda')}`, "
            f"`decay_only={cfg.get('use_decay_only_temporal')}`"
        )
    lines.append("")

    question_summary = _question_level_summary(amem, tmem)
    lines.append("## Question-Level F1 Summary")
    lines.append("")
    lines.append(
        f"- Matched questions: `{question_summary['matched_questions']}`"
    )
    lines.append(
        f"- T-MEM better F1: `{question_summary['tmem_f1_wins']}`"
    )
    lines.append(
        f"- A-MEM better F1: `{question_summary['tmem_f1_losses']}`"
    )
    lines.append(
        f"- Ties: `{question_summary['ties']}`"
    )
    lines.append("")

    lines.extend(_build_table_rows(amem, tmem, "overall", metrics))

    splits = sorted(set(_category_splits(amem)) | set(_category_splits(tmem)), key=lambda name: int(name.split("_")[1]))
    for split in splits:
        lines.extend(_build_table_rows(amem, tmem, split, metrics))

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare A-MEM and T-MEM evaluation JSON outputs")
    parser.add_argument("--amem", required=True, help="Path to A-MEM result JSON")
    parser.add_argument("--tmem", required=True, help="Path to T-MEM result JSON")
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=DEFAULT_METRICS,
        help="Metrics to compare (default: common headline metrics)",
    )
    parser.add_argument("--output", help="Optional path to save a Markdown report")
    args = parser.parse_args()

    amem_path = os.path.abspath(args.amem)
    tmem_path = os.path.abspath(args.tmem)
    amem = _load_json(amem_path)
    tmem = _load_json(tmem_path)

    report = compare_results(amem, tmem, args.metrics)
    print(report)

    if args.output:
        output_path = os.path.abspath(args.output)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(report)
            handle.write("\n")
        print(f"\nSaved report to {output_path}")


if __name__ == "__main__":
    main()
