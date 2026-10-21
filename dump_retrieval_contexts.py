"""
Dump the exact retrieval context A-MEM and T-MEM v2 build for every LoCoMo question.

Used to prove that a code change leaves retrieval untouched: run it once with
old code and once with new code, then compare the hashes. ``--code_dir`` puts
another copy of the memory-layer modules (for example, an export of the May 6
commit) first on the import path. No LLM calls: the question text is the query.

Example:
    .venv/bin/python dump_retrieval_contexts.py --output contexts.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--code_dir", default=None, help="import memory-layer modules from here first")
    parser.add_argument("--dataset", default="data/locomo10.json")
    parser.add_argument("--cache_dir", default="cached_memories_robust_openai_gpt-4o-mini")
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--retrieve_k", type=int, default=10)
    parser.add_argument("--mode", default=None, help="consolidation_mode to set (omit for old code)")
    parser.add_argument("--cap", type=int, default=None, help="consolidated_top_k_cap to set")
    parser.add_argument("--conflict_mode", default=None, help="conflict_mode to set (omit for old code)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.code_dir:
        sys.path.insert(0, os.path.abspath(args.code_dir))

    from load_dataset import load_locomo_dataset
    from memory_layer import SimpleEmbeddingRetriever
    import memory_layer_robust
    import memory_layer_tmem_robust

    dataset = load_locomo_dataset(args.dataset)
    records = []
    for sample_idx in args.samples:
        sample = dataset[sample_idx]
        for system_name, cls in (
            ("amem", memory_layer_robust.RobustAgenticMemorySystem),
            ("tmem_v2", memory_layer_tmem_robust.TemporalAwareRobustAgenticMemorySystem),
        ):
            system = cls.__new__(cls)
            with open(os.path.join(args.cache_dir, f"memory_cache_sample_{sample_idx}.pkl"), "rb") as handle:
                system.memories = pickle.load(handle)
            system.retriever = SimpleEmbeddingRetriever("all-MiniLM-L6-v2").load(
                os.path.join(args.cache_dir, f"retriever_cache_sample_{sample_idx}.pkl"),
                os.path.join(args.cache_dir, f"retriever_cache_embeddings_sample_{sample_idx}.npy"),
            )
            if system_name == "tmem_v2":
                system.temporal_config = memory_layer_tmem_robust.TemporalRetrievalConfig()
            if args.mode is not None:
                system.consolidation_mode = args.mode
            if args.cap is not None:
                system.consolidated_top_k_cap = args.cap
            if args.conflict_mode is not None:
                system.conflict_mode = args.conflict_mode

            for q_idx, qa in enumerate(sample.qa):
                system.current_question = qa.question
                if system_name == "tmem_v2":
                    context = system.find_related_memories_raw(
                        qa.question, k=args.retrieve_k, question_category=int(qa.category)
                    )
                else:
                    context = system.find_related_memories_raw(qa.question, k=args.retrieve_k)
                records.append({
                    "system": system_name,
                    "sample": sample_idx,
                    "question_index": q_idx,
                    "category": int(qa.category),
                    "sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
                    "length": len(context),
                })

    payload = {
        "code_dir": args.code_dir,
        "memory_layer_robust_file": memory_layer_robust.__file__,
        "cache_dir": args.cache_dir,
        "mode": args.mode,
        "cap": args.cap,
        "conflict_mode": args.conflict_mode,
        "records": records,
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1)
    print(f"{len(records)} contexts from {memory_layer_robust.__file__} -> {args.output}")


if __name__ == "__main__":
    main()
