"""
Retrieval-only evaluation: does the retrieved context contain the evidence turns?

No LLM calls, so results are deterministic. Each robust A-MEM note is one
LoCoMo turn stored in order, so note position i maps to a dia_id such as
"D1:3", and each QA lists its evidence dia_ids.

The QA pipeline queries retrieval with LLM-generated keywords; this script
uses the question text instead, so recall here is a proxy for the QA path.

For every question, the context indices computed here are rendered back to
text and compared with the real ``find_related_memories_raw`` output, so the
script fails loudly if it ever drifts from the retrieval code it measures.

Example:
    .venv/bin/python evaluate_evidence_recall.py --samples 0 1
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
import pickle
from typing import Dict, List, Optional, Tuple

from load_dataset import load_locomo_dataset
from memory_layer import SimpleEmbeddingRetriever
from memory_layer_robust import RobustAgenticMemorySystem
from memory_layer_tmem_robust import (
    TemporalAwareRobustAgenticMemorySystem,
    TemporalRetrievalConfig,
)


SYSTEMS = ("amem", "tmem_v2")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_system(system_name: str, cache_dir: str, sample_idx: int):
    """Build a memory system from the cache without creating an LLM client."""
    cls = RobustAgenticMemorySystem if system_name == "amem" else TemporalAwareRobustAgenticMemorySystem
    system = cls.__new__(cls)
    with open(os.path.join(cache_dir, f"memory_cache_sample_{sample_idx}.pkl"), "rb") as handle:
        system.memories = pickle.load(handle)
    retriever = SimpleEmbeddingRetriever("all-MiniLM-L6-v2")
    system.retriever = retriever.load(
        os.path.join(cache_dir, f"retriever_cache_sample_{sample_idx}.pkl"),
        os.path.join(cache_dir, f"retriever_cache_embeddings_sample_{sample_idx}.npy"),
    )
    if system_name == "tmem_v2":
        system.temporal_config = TemporalRetrievalConfig()
    return system


def note_dia_ids(sample, notes) -> List[str]:
    """dia_id for each note position, checked against note content."""
    dia_ids = []
    for session in sample.conversation.sessions.values():
        for turn in session.turns:
            dia_ids.append((turn.dia_id, "Speaker " + turn.speaker + "says : " + turn.text))
    if len(dia_ids) != len(notes):
        raise ValueError(f"{len(notes)} notes but {len(dia_ids)} turns")
    for pos, ((_, expected), note) in enumerate(zip(dia_ids, notes)):
        if note.content != expected:
            raise ValueError(f"note {pos} content does not match turn order")
    return [dia_id for dia_id, _ in dia_ids]


def parse_evidence(evidence: List[str]) -> List[str]:
    ids = []
    for item in evidence:
        for part in str(item).replace(",", ";").split(";"):
            part = part.strip()
            if part:
                ids.append(part)
    return ids


# ---------------------------------------------------------------------------
# Context indices (mirrors find_related_memories_raw)
# ---------------------------------------------------------------------------

def expand_with_neighbors(notes, seeds: List[int], k: int, skip_invalid: bool) -> List[int]:
    """Seed notes plus linked neighbors, in the order the prompt sees them."""
    order: List[int] = []
    for i in seeds:
        order.append(int(i))
        j = 0
        for neighbor in notes[i].links:
            if skip_invalid and neighbor >= len(notes):
                continue
            order.append(int(neighbor))
            if j >= k:
                break
            j += 1
    return order


def context_indices(system_name: str, system, query: str, k: int, category: int) -> Tuple[List[int], List[int]]:
    notes = list(system.memories.values())
    if system_name == "tmem_v2" and system._should_apply_temporal(category):
        seeds, _ = system._rank_memories_temporally(query, k)
        return list(seeds), expand_with_neighbors(notes, seeds, k, skip_invalid=True)
    seeds = [int(i) for i in system.retriever.search(query, k)]
    return seeds, expand_with_neighbors(notes, seeds, k, skip_invalid=False)


def render(notes, order: List[int]) -> str:
    return "".join(
        "talk start time:" + notes[i].timestamp +
        "memory content: " + notes[i].content +
        "memory context: " + notes[i].context +
        "memory keywords: " + str(notes[i].keywords) +
        "memory tags: " + str(notes[i].tags) + "\n"
        for i in order
    )


def actual_context(system_name: str, system, query: str, k: int, category: int) -> str:
    if system_name == "tmem_v2":
        return system.find_related_memories_raw(query, k=k, question_category=category)
    return system.find_related_memories_raw(query, k=k)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(
    dataset_path: str,
    cache_dir: str,
    samples: List[int],
    k: int,
    systems: List[str],
    check_mirror: bool = True,
) -> Dict:
    dataset = load_locomo_dataset(dataset_path)
    per_question = []

    for sample_idx in samples:
        sample = dataset[sample_idx]
        for system_name in systems:
            system = load_system(system_name, cache_dir, sample_idx)
            notes = list(system.memories.values())
            dia_ids = note_dia_ids(sample, notes)
            pos_of = {dia_id: pos for pos, dia_id in enumerate(dia_ids)}

            for q_idx, qa in enumerate(sample.qa):
                category = int(qa.category)
                evidence = [e for e in parse_evidence(qa.evidence) if e in pos_of]
                if not evidence:
                    continue
                seeds, order = context_indices(system_name, system, qa.question, k, category)
                if check_mirror:
                    expected = actual_context(system_name, system, qa.question, k, category)
                    if render(notes, order) != expected:
                        raise AssertionError(
                            f"mirror mismatch: {system_name} sample {sample_idx} question {q_idx}"
                        )
                ctx = set(order)
                seed_set = set(seeds)
                found = [e for e in evidence if pos_of[e] in ctx]
                found_seed = [e for e in evidence if pos_of[e] in seed_set]
                per_question.append({
                    "system": system_name,
                    "sample": sample_idx,
                    "question_index": q_idx,
                    "category": category,
                    "evidence": evidence,
                    "recall": len(found) / len(evidence),
                    "seed_recall": len(found_seed) / len(evidence),
                    "all_found": len(found) == len(evidence),
                    "context_notes": len(order),
                    "unique_context_notes": len(ctx),
                })

    return {"per_question": per_question, "summary": summarize(per_question)}


def summarize(rows: List[Dict]) -> Dict:
    groups: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for row in rows:
        groups[(row["system"], "overall")].append(row)
        groups[(row["system"], str(row["category"]))].append(row)

    summary: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(dict)
    for (system, split), items in sorted(groups.items()):
        n = len(items)
        summary[system][split] = {
            "questions": n,
            "recall": sum(r["recall"] for r in items) / n,
            "seed_recall": sum(r["seed_recall"] for r in items) / n,
            "all_found": sum(r["all_found"] for r in items) / n,
            "context_notes": sum(r["context_notes"] for r in items) / n,
            "unique_context_notes": sum(r["unique_context_notes"] for r in items) / n,
        }
    return dict(summary)


def print_summary(summary: Dict) -> None:
    splits = ["overall", "1", "2", "3", "4", "5"]
    print(f"{'system':<9} {'split':<8} {'n':>4} {'recall':>7} {'seed':>7} {'all':>7} {'ctx':>6} {'uniq':>6}")
    for system, by_split in summary.items():
        for split in splits:
            if split not in by_split:
                continue
            s = by_split[split]
            print(
                f"{system:<9} {split:<8} {s['questions']:>4} {s['recall']:>7.3f} {s['seed_recall']:>7.3f} "
                f"{s['all_found']:>7.3f} {s['context_notes']:>6.1f} {s['unique_context_notes']:>6.1f}"
            )


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dataset", default="data/locomo10.json")
    parser.add_argument("--cache_dir", default="cached_memories_robust_openai_gpt-4o-mini")
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--retrieve_k", type=int, default=10)
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=list(SYSTEMS))
    parser.add_argument("--skip_mirror_check", action="store_true")
    parser.add_argument("--output", default="analysis/evidence_recall_baseline.json")
    args = parser.parse_args(argv)

    result = evaluate(
        args.dataset, args.cache_dir, args.samples, args.retrieve_k, args.systems,
        check_mirror=not args.skip_mirror_check,
    )
    result["config"] = vars(args)
    print_summary(result["summary"])

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
