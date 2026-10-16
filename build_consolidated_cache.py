"""
Build a consolidated memory cache from a frozen robust A-MEM cache.

Reads ``<source_cache>/memory_cache_sample_<i>.pkl`` and the retriever files,
runs the offline consolidation pass (LLM verify + merge, information-loss
check, append-only apply), and writes the result to a separate directory.
The source cache is never modified.

Example:
    .venv/bin/python build_consolidated_cache.py --samples 0 1
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import shutil
import tempfile
from datetime import datetime

from sentence_transformers import SentenceTransformer

from memory_consolidation import ConsolidationConfig, consolidate_bank, content_embeddings
from memory_layer import SimpleEmbeddingRetriever
from memory_layer_robust import RobustAgenticMemorySystem, RobustLLMController


def default_output_dir(source_dir: str, config: ConsolidationConfig, tag: str) -> str:
    return f"{source_dir.rstrip('/')}_consolidated_tau{config.similarity_threshold:.2f}_{tag}"


def load_sample(source_dir: str, sample_idx: int) -> RobustAgenticMemorySystem:
    """Memory system from cache files, without creating an LLM client."""
    system = RobustAgenticMemorySystem.__new__(RobustAgenticMemorySystem)
    with open(os.path.join(source_dir, f"memory_cache_sample_{sample_idx}.pkl"), "rb") as handle:
        system.memories = pickle.load(handle)
    retriever = SimpleEmbeddingRetriever("all-MiniLM-L6-v2")
    system.retriever = retriever.load(
        os.path.join(source_dir, f"retriever_cache_sample_{sample_idx}.pkl"),
        os.path.join(source_dir, f"retriever_cache_embeddings_sample_{sample_idx}.npy"),
    )
    if system.retriever.embeddings is None or len(system.retriever.embeddings) != len(system.memories):
        raise ValueError(f"sample {sample_idx}: retriever cache does not match memory cache")
    return system


def save_sample(system: RobustAgenticMemorySystem, output_dir: str, sample_idx: int) -> None:
    """Write the three cache files atomically (temp dir, then move)."""
    os.makedirs(output_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_dir) as tmp:
        memory_file = os.path.join(tmp, f"memory_cache_sample_{sample_idx}.pkl")
        retriever_file = os.path.join(tmp, f"retriever_cache_sample_{sample_idx}.pkl")
        embeddings_file = os.path.join(tmp, f"retriever_cache_embeddings_sample_{sample_idx}.npy")
        with open(memory_file, "wb") as handle:
            pickle.dump(system.memories, handle)
        system.retriever.save(retriever_file, embeddings_file)
        for path in (memory_file, retriever_file, embeddings_file):
            shutil.move(path, os.path.join(output_dir, os.path.basename(path)))


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--source_cache", default="cached_memories_robust_openai_gpt-4o-mini")
    parser.add_argument("--output_dir", default=None)
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--backend", default="openai")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--threshold", type=float, default=ConsolidationConfig.similarity_threshold)
    parser.add_argument("--max_group_size", type=int, default=ConsolidationConfig.max_group_size)
    parser.add_argument("--allow_cross_speaker", action="store_true")
    parser.add_argument("--merge_retries", type=int, default=2)
    parser.add_argument("--tag", default="v2", help="version tag for the output cache and log names")
    parser.add_argument("--log_dir", default="analysis")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = ConsolidationConfig(
        similarity_threshold=args.threshold,
        max_group_size=args.max_group_size,
        require_same_speaker=not args.allow_cross_speaker,
    )
    output_dir = args.output_dir or default_output_dir(args.source_cache, config, args.tag)
    if os.path.abspath(output_dir) == os.path.abspath(args.source_cache):
        raise SystemExit("output_dir must differ from source_cache")

    llm = RobustLLMController(args.backend, args.model).llm
    encoder = SentenceTransformer(config.embedding_model)
    os.makedirs(args.log_dir, exist_ok=True)

    for sample_idx in args.samples:
        target = os.path.join(output_dir, f"memory_cache_sample_{sample_idx}.pkl")
        if os.path.exists(target) and not args.overwrite:
            print(f"sample {sample_idx}: {target} exists, skipping (use --overwrite)")
            continue

        system = load_sample(args.source_cache, sample_idx)
        notes_before = len(system.memories)
        embeddings = content_embeddings(list(system.memories.values()), encoder)
        log = consolidate_bank(system, llm, embeddings, config, merge_retries=args.merge_retries)
        save_sample(system, output_dir, sample_idx)

        log.update({
            "sample": sample_idx,
            "source_cache": args.source_cache,
            "output_dir": output_dir,
            "model": args.model,
            "tag": args.tag,
            "notes_before": notes_before,
            "notes_after": len(system.memories),
            "built_at": datetime.now().isoformat(timespec="seconds"),
        })
        log_path = os.path.join(args.log_dir, f"consolidation_log_sample_{sample_idx}_{args.tag}.json")
        with open(log_path, "w", encoding="utf-8") as handle:
            json.dump(log, handle, indent=2, ensure_ascii=False)
        c = log["counts"]
        print(
            f"sample {sample_idx}: {c['groups']} groups -> {c['merged']} merged, "
            f"{c['different']} kept separate, {c['rejected']} rejected; "
            f"{c['llm_calls']} LLM calls; notes {notes_before} -> {len(system.memories)}; log {log_path}"
        )


if __name__ == "__main__":
    main()
