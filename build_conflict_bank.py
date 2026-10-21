"""
Build conflict-aware memory banks (T-MEM Module 3) from an existing bank.

Reads <source_cache> (default: the v3 consolidated bank), runs
memory_conflicts.detect_and_apply on each sample, and writes the annotated
bank to a separate directory. No notes are added or removed, so the retriever
files are saved unchanged. The source bank is never modified.

AI answers are cached in the log folder; --seed_cache_dir copies the caches of
an earlier run (for example step 0) first, so identical prompts cost nothing.

Example:
    .venv/bin/python build_conflict_bank.py --samples 0 1 \
        --seed_cache_dir analysis/conflict_step0_v2_2026-10-21
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime

from sentence_transformers import SentenceTransformer

from build_consolidated_cache import load_sample, save_sample
from measure_conflicts import KNOWN_CASES
from memory_conflicts import ConflictConfig, detect_and_apply
from memory_layer_robust import RobustLLMController


def check_known_cases(system, log, encoder, sample_idx: int, status_duplicate: float) -> list:
    notes = list(system.memories.values())
    labels = {(p["old"], p["new"]): p["label"] for p in log["pairs"]}
    find = lambda text: [i for i, n in enumerate(notes) if n.note_type == "raw" and text.lower() in n.content.lower()]  # noqa: E731
    status = lambda i: notes[i].timeline_status or ""  # noqa: E731
    results = []
    for ks, old_text, new_text, ok in KNOWN_CASES:
        if ks != sample_idx:
            continue
        olds, news = find(old_text), find(new_text)
        out = {"old_text": old_text, "new_text": new_text, "expected": sorted(ok)}
        if not olds or not news:
            out["result"] = "text not found"
        else:
            a, b = olds[0], news[0]
            if notes[a].timeline_id is None or notes[b].timeline_id is None:
                out["result"] = "not in a timeline"
            elif notes[a].timeline_id != notes[b].timeline_id:
                out["result"] = "different topics"
            else:
                ea = encoder.encode([status(a)], normalize_embeddings=True)[0]
                into_b = [(x, lab) for (x, y), lab in labels.items() if y == b]
                similar = [(x, lab) for x, lab in into_b
                           if x == a or float(encoder.encode([status(x)], normalize_embeddings=True)[0] @ ea)
                           >= status_duplicate]
                if any(lab in ok for _, lab in similar):
                    out["result"] = "found"
                elif similar:
                    out["result"] = "wrong label (" + ", ".join(sorted({lab for _, lab in similar})) + ")"
                else:
                    out["result"] = "not compared"
                out["labels_into_newer"] = sorted({lab for _, lab in into_b})
        results.append(out)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--source_cache", default="cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80_v3")
    parser.add_argument("--output_dir", default=None)
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--tag", default="v1")
    parser.add_argument("--seed_cache_dir", default=None)
    parser.add_argument("--log_dir", default=None)
    parser.add_argument("--max_compare", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir or f"{args.source_cache.rstrip('/')}_conflicts_{args.tag}"
    if os.path.abspath(output_dir) == os.path.abspath(args.source_cache):
        raise SystemExit("output_dir must differ from source_cache")
    log_dir = args.log_dir or os.path.join("analysis", f"conflict_build_{args.tag}_" +
                                           datetime.now().strftime("%Y-%m-%d_%H-%M"))
    os.makedirs(log_dir, exist_ok=True)
    if args.seed_cache_dir:
        for name in os.listdir(args.seed_cache_dir):
            if name.startswith(("state_cache_sample_", "pair_cache_sample_")) and name.endswith(".json"):
                target = os.path.join(log_dir, name)
                if not os.path.exists(target):
                    shutil.copy(os.path.join(args.seed_cache_dir, name), target)

    config = ConflictConfig(max_compare=args.max_compare)
    llm = RobustLLMController("openai", args.model).llm
    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    summary = {"created": datetime.now().isoformat(timespec="seconds"), "source_cache": args.source_cache,
               "output_dir": output_dir, "model": args.model, "tag": args.tag, "samples": {}}

    for s in args.samples:
        target = os.path.join(output_dir, f"memory_cache_sample_{s}.pkl")
        if os.path.exists(target) and not args.overwrite:
            print(f"sample {s}: {target} exists, skipping (use --overwrite)")
            continue
        system = load_sample(args.source_cache, s)
        n_before = len(system.memories)
        log = detect_and_apply(system, llm, encoder, log_dir, s, config)
        if len(system.memories) != n_before:
            raise RuntimeError("conflict handling must not add or remove notes")
        log["known_cases"] = check_known_cases(system, log, encoder, s, config.status_duplicate)
        save_sample(system, output_dir, s)
        with open(os.path.join(log_dir, f"conflict_log_sample_{s}.json"), "w", encoding="utf-8") as handle:
            json.dump(log, handle, indent=2, ensure_ascii=False)
        summary["samples"][str(s)] = {k: log[k] for k in ("raw_notes", "state_notes", "labels", "new_llm_calls")}
        summary["samples"][str(s)].update({"timelines": len(log["timelines"]), "replaced": len(log["replaced"]),
                                           "contradictions": len(log["contradictions"]),
                                           "known_cases": log["known_cases"]})
        print(f"sample {s}: {log['state_notes']} situation notes, {len(log['timelines'])} timelines, "
              f"labels {log['labels']}, replaced {len(log['replaced'])}, contradictions {len(log['contradictions'])}, "
              f"new AI calls {log['new_llm_calls']}")
        for k in log["known_cases"]:
            print(f"   known case: {k['old_text'][:35]!r} -> {k['new_text'][:35]!r}: {k['result']}")

    with open(os.path.join(log_dir, "build_summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    print(f"log: {log_dir}")


if __name__ == "__main__":
    main()
