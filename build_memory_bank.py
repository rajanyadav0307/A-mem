"""
Build A-MEM memory banks from scratch, exactly as the QA script does.

Uses RobustAdvancedMemAgent from test_advanced_robust.py and the same loop:
every turn becomes "Speaker <name>says : <text>" with the session date, added
with add_memory (note analysis + memory evolution). The memory pickle and
retriever files are written to --output_dir in the usual cache format.

Fallbacks that the May 6 code makes silently (content analysis or evolution
errors) are counted and reported, so a bank built with errors is visible.

Example:
    .venv/bin/python build_memory_bank.py --samples 2 --output_dir <folder>
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import time
from datetime import datetime

from load_dataset import load_locomo_dataset
from test_advanced_robust import RobustAdvancedMemAgent


class CountingHandler(logging.Handler):
    """Counts warning/error records from the memory layer."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.records = []

    def emit(self, record):
        self.records.append(f"{record.levelname}: {record.getMessage()[:200]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dataset", default="data/locomo10.json")
    parser.add_argument("--samples", type=int, nargs="+", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--backend", default="openai")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    handler = CountingHandler()
    logging.getLogger("amem_robust").addHandler(handler)
    dataset = load_locomo_dataset(args.dataset)
    report = {}

    for s in args.samples:
        memory_file = os.path.join(args.output_dir, f"memory_cache_sample_{s}.pkl")
        if os.path.exists(memory_file) and not args.overwrite:
            print(f"sample {s}: {memory_file} exists, skipping")
            continue
        handler.records.clear()
        agent = RobustAdvancedMemAgent(args.model, args.backend, 10, 0.5)
        sample = dataset[s]
        started = time.time()
        n = 0
        total = sum(len(sess.turns) for sess in sample.conversation.sessions.values())
        for _, session in sample.conversation.sessions.items():
            for turn in session.turns:
                agent.add_memory("Speaker " + turn.speaker + "says : " + turn.text, time=session.date_time)
                n += 1
                if n % 50 == 0 or n == total:
                    print(f"sample {s}: {n}/{total} turns, {time.time() - started:.0f}s", flush=True)
        with open(memory_file, "wb") as handle:
            pickle.dump(agent.memory_system.memories, handle)
        agent.memory_system.retriever.save(
            os.path.join(args.output_dir, f"retriever_cache_sample_{s}.pkl"),
            os.path.join(args.output_dir, f"retriever_cache_embeddings_sample_{s}.npy"),
        )
        report[str(s)] = {
            "turns": total,
            "notes": len(agent.memory_system.memories),
            "seconds": round(time.time() - started),
            "finished": datetime.now().isoformat(timespec="seconds"),
            "warnings_or_errors": len(handler.records),
            "examples": handler.records[:20],
        }
        print(f"sample {s}: built {report[str(s)]['notes']} notes in {report[str(s)]['seconds']}s, "
              f"{report[str(s)]['warnings_or_errors']} warnings/errors")

    path = os.path.join(args.output_dir, "build_report.json")
    existing = json.load(open(path)) if os.path.exists(path) else {}
    existing.update(report)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(existing, handle, indent=2)


if __name__ == "__main__":
    main()
