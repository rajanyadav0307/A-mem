"""Stage 2: make the shared search words, one file per run (seed).

The words come from A-MEM's own generate_query_llm (same prompt, same parsing,
same temperature), called once per question per run. Every setup of that run
then reads them with --keywords_file. A file is written only when every one of
the 757 questions has non-empty words; an existing file is never overwritten.

    caffeinate -dims .venv/bin/python <exp>/scripts/make_keywords.py --seeds 42 43 44 45 46
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

sys.path.insert(0, common.REPO)
os.chdir(common.REPO)

from load_dataset import load_locomo_dataset  # noqa: E402
from shared_keywords import keyword_key  # noqa: E402
from test_advanced_robust import RobustAdvancedMemAgent  # noqa: E402


def main():
    common.keep_awake()
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()

    ds = load_locomo_dataset("data/locomo10.json")
    questions = [(s, i, qa.question) for s in common.SAMPLES for i, qa in enumerate(ds[s].qa)]
    assert len(questions) == common.TOTAL_QUESTIONS, len(questions)
    agent = RobustAdvancedMemAgent(common.MODEL, "openai", int(common.RETRIEVE_K), 0.5)
    os.makedirs(common.KEYWORDS_DIR, exist_ok=True)

    def make(item):
        s, i, question = item
        last = None
        for _ in range(args.attempts):
            try:
                words = agent.generate_query_llm(question)
                if isinstance(words, str) and words.strip():
                    return keyword_key(s, i), words
                last = ValueError("empty search words")
            except Exception as exc:  # noqa: BLE001
                last = exc
        raise RuntimeError(f"question {keyword_key(s, i)}: {last}")

    for seed in args.seeds:
        path = common.keywords_file(seed)
        if os.path.exists(path):
            sys.exit(f"STOP: {path} already exists; files are never overwritten")
        started = datetime.datetime.now().isoformat(timespec="seconds")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pairs = list(pool.map(make, questions))
        table = dict(pairs)
        if len(table) != common.TOTAL_QUESTIONS or any(not v.strip() for v in table.values()):
            sys.exit(f"STOP: seed {seed}: {len(table)} entries, not written")
        data = {"seed": seed, "model": common.MODEL, "made_with": common.git_commit(),
                "maker": "test_advanced_robust.RobustAdvancedMemAgent.generate_query_llm",
                "started": started, "finished": datetime.datetime.now().isoformat(timespec="seconds"),
                "questions": len(table), "keywords": table}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, ensure_ascii=False)
        os.replace(tmp, path)
        print(f"seed {seed}: {len(table)} questions written to {path}")


if __name__ == "__main__":
    main()
