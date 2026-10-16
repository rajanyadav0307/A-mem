"""
Compare fixes for consolidated notes crowding the top-k, using evidence recall.

No LLM calls. Each variant sets the retrieval mode plus options on a loaded
consolidated cache: the text embedded for consolidated notes, hiding
small-talk summaries, a score penalty, and a cap on consolidated notes in the
top-k. "off" is the May 6 baseline.

Example:
    .venv/bin/python evaluate_consolidation_fixes.py --samples 0 1
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List

from evaluate_evidence_recall import (
    actual_context,
    context_indices,
    load_system,
    note_dia_ids,
    parse_evidence,
    render,
    summarize,
)
from load_dataset import load_locomo_dataset
from memory_consolidation import attach_labels_from_log, reembed_consolidated_notes


# name -> settings. Keys: mode, recipe, hide_small_talk, penalty, cap
VARIANTS: Dict[str, Dict] = {
    "off": {"mode": "off"},
    "pe": {"mode": "primary_expand"},
    "pe+content": {"mode": "primary_expand", "recipe": "content"},
    "pe+content_context": {"mode": "primary_expand", "recipe": "content_context"},
    "pe+hide_small_talk": {"mode": "primary_expand", "hide_small_talk": True},
    "pe+penalty0.05": {"mode": "primary_expand", "penalty": 0.05},
    "pe+penalty0.10": {"mode": "primary_expand", "penalty": 0.10},
    "pe+cap1": {"mode": "primary_expand", "cap": 1},
    "pe+cap0": {"mode": "primary_expand", "cap": 0},
    "pe+penalty0.15": {"mode": "primary_expand", "penalty": 0.15},
    "pe+hide+cap1": {"mode": "primary_expand", "hide_small_talk": True, "cap": 1},
    "pe+content_context+hide+cap1": {
        "mode": "primary_expand", "recipe": "content_context", "hide_small_talk": True, "cap": 1,
    },
    "pe+content_context+hide+penalty0.05": {
        "mode": "primary_expand", "recipe": "content_context", "hide_small_talk": True, "penalty": 0.05,
    },
    "primary+content_context+hide+cap1": {
        "mode": "primary", "recipe": "content_context", "hide_small_talk": True, "cap": 1,
    },
}


def configure(system, settings: Dict, log: Dict) -> None:
    attach_labels_from_log(system, log)
    system.consolidation_mode = settings["mode"]
    if settings.get("recipe", "union") != "union":
        reembed_consolidated_notes(system, settings["recipe"])
    system.hide_small_talk_summaries = bool(settings.get("hide_small_talk", False))
    system.consolidated_score_penalty = float(settings.get("penalty", 0.0))
    system.consolidated_top_k_cap = settings.get("cap")


def evaluate_variants(args) -> Dict:
    dataset = load_locomo_dataset(args.dataset)
    rows: List[Dict] = []
    for sample_idx in args.samples:
        sample = dataset[sample_idx]
        with open(args.log_pattern.format(sample=sample_idx), encoding="utf-8") as handle:
            log = json.load(handle)
        for system_name in args.systems:
            for variant in args.variants:
                settings = VARIANTS[variant]
                system = load_system(system_name, args.cache_dir, sample_idx)
                configure(system, settings, log)
                notes = list(system.memories.values())
                covered = note_dia_ids(sample, notes)
                raw_pos = {next(iter(c)): p for p, c in enumerate(covered) if notes[p].note_type == "raw"}
                for q_idx, qa in enumerate(sample.qa):
                    category = int(qa.category)
                    evidence = [e for e in parse_evidence(qa.evidence) if e in raw_pos]
                    if not evidence:
                        continue
                    seeds, order = context_indices(system_name, system, qa.question, args.retrieve_k, category)
                    expected = actual_context(system_name, system, qa.question, args.retrieve_k, category)
                    if render(notes, order) != expected:
                        raise AssertionError(f"mirror mismatch: {system_name}/{variant} q{q_idx}")
                    ctx = set(order)
                    in_ctx = set().union(*(covered[i] for i in ctx)) if ctx else set()
                    in_seeds = set().union(*(covered[i] for i in seeds)) if seeds else set()
                    raw_ctx = {i for i in ctx if notes[i].note_type == "raw"}
                    found = [e for e in evidence if e in in_ctx]
                    rows.append({
                        "system": system_name,
                        "mode": variant,
                        "sample": sample_idx,
                        "question_index": q_idx,
                        "category": category,
                        "recall": len(found) / len(evidence),
                        "raw_recall": sum(raw_pos[e] in raw_ctx for e in evidence) / len(evidence),
                        "seed_recall": sum(e in in_seeds for e in evidence) / len(evidence),
                        "all_found": len(found) == len(evidence),
                        "context_notes": len(order),
                        "unique_context_notes": len(ctx),
                        "consolidated_in_context": sum(notes[i].note_type == "consolidated" for i in ctx),
                    })
    return {"per_question": rows, "summary": summarize(rows)}


def print_table(summary: Dict, systems: List[str], variants: List[str]) -> None:
    cols = ["overall", "1", "2", "3", "4", "5"]
    for system_name in systems:
        base = summary[f"{system_name}/off"]
        print(f"\n{system_name}: recall (overall and by category), seed recall, all found; "
              f"Δ = change vs off in recall")
        print(f"{'variant':<38} " + " ".join(f"{c:>6}" for c in cols) + f" {'seed':>6} {'all':>6} {'Δ':>7}")
        for variant in variants:
            m = summary[f"{system_name}/{variant}"]
            cells = " ".join(f"{m[c]['recall']:>6.3f}" for c in cols)
            delta = m["overall"]["recall"] - base["overall"]["recall"]
            print(f"{variant:<38} {cells} {m['overall']['seed_recall']:>6.3f} "
                  f"{m['overall']['all_found']:>6.3f} {delta:>+7.3f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dataset", default="data/locomo10.json")
    parser.add_argument("--cache_dir", default="cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80_v3")
    parser.add_argument("--log_pattern", default="analysis/consolidation_log_sample_{sample}_v3.json")
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--systems", nargs="+", default=["amem", "tmem_v2"])
    parser.add_argument("--variants", nargs="+", choices=list(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--retrieve_k", type=int, default=10)
    parser.add_argument("--output", default="analysis/consolidation_fixes_recall.json")
    args = parser.parse_args()

    result = evaluate_variants(args)
    result["config"] = {**vars(args), "variant_settings": {v: VARIANTS[v] for v in args.variants}}
    print_table(result["summary"], args.systems, args.variants)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
