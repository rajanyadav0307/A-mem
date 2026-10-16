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

With a consolidated cache, ``--modes`` picks how retrieval treats
consolidated notes. A consolidated note in the context counts as containing
the evidence of its source notes ("recall"); "raw_recall" counts only the
original turn notes.

Example:
    .venv/bin/python evaluate_evidence_recall.py --samples 0 1
    .venv/bin/python evaluate_evidence_recall.py \
        --cache_dir cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80_v3 \
        --modes off add_only primary primary_expand
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
from memory_layer_robust import CONSOLIDATION_MODES, RobustAgenticMemorySystem
from memory_layer_tmem_robust import (
    TemporalAwareRobustAgenticMemorySystem,
    TemporalRetrievalConfig,
)


SYSTEMS = ("amem", "tmem_v2")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_system(system_name: str, cache_dir: str, sample_idx: int, mode: str = "off"):
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
    system.consolidation_mode = mode
    return system


def note_dia_ids(sample, notes) -> List[set]:
    """Evidence dia_ids covered by each note position.

    Raw notes map one-to-one to turns (checked against note content).
    A consolidated note covers the dia_ids of its source notes.
    """
    turns = []
    for session in sample.conversation.sessions.values():
        for turn in session.turns:
            turns.append((turn.dia_id, "Speaker " + turn.speaker + "says : " + turn.text))
    raw = [n for n in notes if n.note_type == "raw"]
    if len(turns) != len(raw):
        raise ValueError(f"{len(raw)} raw notes but {len(turns)} turns")
    covered: List[set] = []
    for pos, note in enumerate(notes):
        if note.note_type == "raw":
            dia_id, expected = turns[pos]
            if note.content != expected:
                raise ValueError(f"note {pos} content does not match turn order")
            covered.append({dia_id})
        else:
            covered.append({turns[i][0] for i in note.source_indices})
    return covered


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
    temporal = system_name == "tmem_v2" and system._should_apply_temporal(category)
    if system.consolidation_mode == "off":
        # Independent re-implementation of the May 6 retrieval on the raw bank.
        with system.raw_only_view():
            notes = list(system.memories.values())
            if temporal:
                seeds, _ = system._rank_memories_temporally(query, k)
                return list(seeds), expand_with_neighbors(notes, seeds, k, skip_invalid=True)
            seeds = [int(i) for i in system.retriever.search(query, k)]
            return seeds, expand_with_neighbors(notes, seeds, k, skip_invalid=False)
    if temporal:
        seeds, _ = system._rank_memories_temporally(query, k)
        seeds = [int(i) for i in seeds]
    else:
        seeds = system.search_retrievable(query, k)
    return seeds, system.consolidated_context_order(query, k, seeds=seeds)


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
    modes: Optional[List[str]] = None,
    check_mirror: bool = True,
) -> Dict:
    dataset = load_locomo_dataset(dataset_path)
    per_question = []

    for sample_idx in samples:
        sample = dataset[sample_idx]
        for system_name in systems:
            for mode in modes or ["off"]:
                system = load_system(system_name, cache_dir, sample_idx, mode)
                notes = list(system.memories.values())
                covered = note_dia_ids(sample, notes)
                raw_pos = {next(iter(c)): pos for pos, c in enumerate(covered) if notes[pos].note_type == "raw"}

                for q_idx, qa in enumerate(sample.qa):
                    category = int(qa.category)
                    evidence = [e for e in parse_evidence(qa.evidence) if e in raw_pos]
                    if not evidence:
                        continue
                    seeds, order = context_indices(system_name, system, qa.question, k, category)
                    if check_mirror:
                        expected = actual_context(system_name, system, qa.question, k, category)
                        if render(notes, order) != expected:
                            raise AssertionError(
                                f"mirror mismatch: {system_name}/{mode} sample {sample_idx} question {q_idx}"
                            )
                    ctx = set(order)
                    in_ctx = set().union(*(covered[i] for i in ctx)) if ctx else set()
                    in_seeds = set().union(*(covered[i] for i in seeds)) if seeds else set()
                    raw_ctx = {i for i in ctx if notes[i].note_type == "raw"}
                    found = [e for e in evidence if e in in_ctx]
                    per_question.append({
                        "system": system_name,
                        "mode": mode,
                        "sample": sample_idx,
                        "question_index": q_idx,
                        "category": category,
                        "evidence": evidence,
                        "recall": len(found) / len(evidence),
                        "raw_recall": sum(raw_pos[e] in raw_ctx for e in evidence) / len(evidence),
                        "seed_recall": sum(e in in_seeds for e in evidence) / len(evidence),
                        "all_found": len(found) == len(evidence),
                        "context_notes": len(order),
                        "unique_context_notes": len(ctx),
                        "consolidated_in_context": sum(notes[i].note_type == "consolidated" for i in ctx),
                    })

    return {"per_question": per_question, "summary": summarize(per_question)}


def summarize(rows: List[Dict]) -> Dict:
    groups: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for row in rows:
        key = f"{row['system']}/{row.get('mode', 'off')}"
        groups[(key, "overall")].append(row)
        groups[(key, str(row["category"]))].append(row)

    metrics = ("recall", "raw_recall", "seed_recall", "all_found", "context_notes",
               "unique_context_notes", "consolidated_in_context")
    summary: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(dict)
    for (key, split), items in sorted(groups.items()):
        n = len(items)
        summary[key][split] = {"questions": n}
        for metric in metrics:
            summary[key][split][metric] = sum(float(r[metric]) for r in items) / n
    return dict(summary)


def print_summary(summary: Dict) -> None:
    splits = ["overall", "1", "2", "3", "4", "5"]
    print(f"{'system/mode':<24} {'split':<8} {'n':>4} {'recall':>7} {'raw':>7} {'seed':>7} "
          f"{'all':>7} {'ctx':>6} {'uniq':>6} {'cons':>5}")
    for key, by_split in summary.items():
        for split in splits:
            if split not in by_split:
                continue
            m = by_split[split]
            print(
                f"{key:<24} {split:<8} {m['questions']:>4} {m['recall']:>7.3f} {m['raw_recall']:>7.3f} "
                f"{m['seed_recall']:>7.3f} {m['all_found']:>7.3f} {m['context_notes']:>6.1f} "
                f"{m['unique_context_notes']:>6.1f} {m['consolidated_in_context']:>5.2f}"
            )


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dataset", default="data/locomo10.json")
    parser.add_argument("--cache_dir", default="cached_memories_robust_openai_gpt-4o-mini")
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--retrieve_k", type=int, default=10)
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=list(SYSTEMS))
    parser.add_argument("--modes", nargs="+", choices=CONSOLIDATION_MODES, default=["off"])
    parser.add_argument("--skip_mirror_check", action="store_true")
    parser.add_argument("--output", default="analysis/evidence_recall_baseline.json")
    args = parser.parse_args(argv)

    result = evaluate(
        args.dataset, args.cache_dir, args.samples, args.retrieve_k, args.systems,
        modes=args.modes, check_mirror=not args.skip_mirror_check,
    )
    result["config"] = vars(args)
    print_summary(result["summary"])

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
