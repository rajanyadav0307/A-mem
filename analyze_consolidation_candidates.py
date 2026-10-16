"""
Step 0 diagnostic: how many consolidation candidates does a cached memory bank have?

No LLM calls. Loads the frozen robust A-MEM cache, embeds note content only,
sweeps similarity thresholds, and writes example groups for manual review.

Example:
    .venv/bin/python analyze_consolidation_candidates.py --samples 0 1
"""

from __future__ import annotations

import argparse
import json
import os
import pickle

from sentence_transformers import SentenceTransformer

from memory_consolidation import (
    ConsolidationConfig,
    content_embeddings,
    find_candidate_groups,
    note_speaker,
)


def load_cached_notes(cache_dir: str, sample_idx: int):
    path = os.path.join(cache_dir, f"memory_cache_sample_{sample_idx}.pkl")
    with open(path, "rb") as handle:
        return list(pickle.load(handle).values())


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--cache_dir", default="cached_memories_robust_openai_gpt-4o-mini")
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.80, 0.85, 0.90])
    parser.add_argument("--max_group_size", type=int, default=5)
    parser.add_argument("--allow_cross_speaker", action="store_true")
    parser.add_argument("--examples", type=int, default=15)
    parser.add_argument("--output", default="analysis/consolidation_candidates.json")
    args = parser.parse_args()

    model = SentenceTransformer("all-MiniLM-L6-v2")
    report = {"cache_dir": args.cache_dir, "samples": {}}

    for sample_idx in args.samples:
        notes = load_cached_notes(args.cache_dir, sample_idx)
        embeddings = content_embeddings(notes, model)
        sample_report = {"notes": len(notes), "thresholds": {}}
        print(f"\n=== sample {sample_idx}: {len(notes)} notes ===")
        print(f"{'tau':>5} {'groups':>7} {'notes':>6} {'share':>6} {'largest':>8}")

        for tau in args.thresholds:
            cfg = ConsolidationConfig(
                similarity_threshold=tau,
                max_group_size=args.max_group_size,
                require_same_speaker=not args.allow_cross_speaker,
            )
            groups = find_candidate_groups(notes, embeddings, cfg)
            covered = sum(len(g.indices) for g in groups)
            largest = max((len(g.indices) for g in groups), default=0)
            print(f"{tau:>5.2f} {len(groups):>7} {covered:>6} {covered / len(notes):>6.1%} {largest:>8}")

            examples = []
            for group in sorted(groups, key=lambda g: -g.mean_similarity)[:args.examples]:
                examples.append({
                    **group.to_dict(),
                    "speaker": note_speaker(notes[group.indices[0]]),
                    "notes": [
                        {"index": i, "timestamp": notes[i].timestamp, "content": notes[i].content}
                        for i in group.indices
                    ],
                })
            sample_report["thresholds"][f"{tau:.2f}"] = {
                "groups": len(groups),
                "notes_in_groups": covered,
                "largest_group": largest,
                "all_groups": [g.to_dict() for g in groups],
                "examples": examples,
            }
        report["samples"][str(sample_idx)] = sample_report

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
