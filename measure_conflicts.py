"""
Step 0 for conflict handling: how many real conflicts are in a memory bank?

Reads the May 6 memory bank (never modifies it) and, with gpt-4o-mini at
temperature 0:
  1. tags every note: is it about the speaker's own changeable situation,
     and if so, which topic and what status
  2. groups each speaker's state notes into topics (topic-name similarity)
     and sorts each topic by date, giving "timelines"
  3. checks each step of a timeline across different days: SAME, PROGRESS,
     CHANGE, CONTRADICTION, COMPATIBLE or UNRELATED

LLM answers are cached in the output folder, so a rerun costs nothing.

Example:
    .venv/bin/python measure_conflicts.py --samples 0 1
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pickle
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from sentence_transformers import SentenceTransformer

from llm_text_parsers import (
    CONFLICT_CHECK_PROMPT,
    STATE_EXTRACT_PROMPT,
    parse_conflict_label,
    parse_state_extract,
)
from load_dataset import load_locomo_dataset
from memory_consolidation import note_speaker, parse_timestamp
from memory_layer_robust import RobustLLMController

SPEAKER_PREFIX = re.compile(r"^Speaker\s+.+?says\s*:\s*")
CONFLICT_KINDS = ("PROGRESS", "CHANGE", "CONTRADICTION")


def day_label(timestamp: str) -> str:
    parsed = parse_timestamp(timestamp)
    return f"{parsed.day} {parsed.strftime('%B')} {parsed.year}" if parsed else timestamp


def cached_calls(prompts: dict, cache_path: str, llm, workers: int) -> dict:
    """Run prompts not yet in the cache; return {key: response}."""
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    todo = {k: p for k, p in prompts.items() if k not in cache}
    if todo:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            answers = pool.map(lambda kp: (kp[0], llm.get_completion(kp[1], temperature=0.0)), todo.items())
            for key, answer in answers:
                cache[key] = answer
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(cache, handle, indent=1, ensure_ascii=False)
    return {k: cache[k] for k in prompts}, len(todo)


def topic_groups(topics: list, encoder, threshold: float) -> list:
    """Cluster topic names by meaning (average linkage, cosine)."""
    if len(topics) == 1:
        return [0]
    emb = encoder.encode(topics, normalize_embeddings=True)
    tree = linkage(emb, method="average", metric="cosine")
    return list(fcluster(tree, t=1.0 - threshold, criterion="distance"))


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--cache_dir", default="cached_memories_robust_openai_gpt-4o-mini")
    parser.add_argument("--dataset", default="data/locomo10.json")
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--topic_threshold", type=float, default=0.70)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out_dir", default=None)
    args = parser.parse_args()

    out_dir = args.out_dir or os.path.join("analysis", "conflict_step0_" + datetime.now().strftime("%Y-%m-%d_%H-%M"))
    os.makedirs(out_dir, exist_ok=True)
    llm = RobustLLMController("openai", args.model).llm
    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    dataset = load_locomo_dataset(args.dataset)
    report = {"created": datetime.now().isoformat(timespec="seconds"), "model": args.model,
              "topic_threshold": args.topic_threshold, "samples": {}}
    total_new_calls = 0

    for s in args.samples:
        with open(os.path.join(args.cache_dir, f"memory_cache_sample_{s}.pkl"), "rb") as handle:
            notes = list(pickle.load(handle).values())

        # 1. State tagging
        prompts = {str(i): STATE_EXTRACT_PROMPT.format(
            date=day_label(n.timestamp), speaker=note_speaker(n) or "Speaker",
            text=SPEAKER_PREFIX.sub("", n.content).strip()) for i, n in enumerate(notes)}
        answers, new = cached_calls(prompts, os.path.join(out_dir, f"state_cache_sample_{s}.json"), llm, args.workers)
        total_new_calls += new
        states = {int(k): parse_state_extract(v) for k, v in answers.items()}

        # 2. Timelines: per speaker, cluster topic names, sort by time
        timelines = []
        by_speaker = collections.defaultdict(list)
        for i, st in states.items():
            if st["is_state"]:
                by_speaker[note_speaker(notes[i])].append(i)
        for speaker, idxs in by_speaker.items():
            labels = topic_groups([states[i]["topic"] for i in idxs], encoder, args.topic_threshold)
            groups = collections.defaultdict(list)
            for i, lab in zip(idxs, labels):
                groups[lab].append(i)
            for members in groups.values():
                members.sort(key=lambda i: (parse_timestamp(notes[i].timestamp), i))
                days = {parse_timestamp(notes[i].timestamp).date() for i in members}
                if len(days) >= 2:
                    name = collections.Counter(states[i]["topic"] for i in members).most_common(1)[0][0]
                    timelines.append({"speaker": speaker, "topic": name, "notes": members})

        # 3. Check each step across different days
        pair_prompts, pair_meta = {}, {}
        for t_id, tl in enumerate(timelines):
            members = tl["notes"]
            last_by_day = []
            for i in members:
                if last_by_day and parse_timestamp(notes[last_by_day[-1]].timestamp).date() == \
                        parse_timestamp(notes[i].timestamp).date():
                    last_by_day[-1] = i  # keep the latest note of each day
                else:
                    last_by_day.append(i)
            for a, b in zip(last_by_day, last_by_day[1:]):
                key = f"{a}-{b}"
                pair_meta[key] = (t_id, a, b)
                pair_prompts[key] = CONFLICT_CHECK_PROMPT.format(
                    old_date=day_label(notes[a].timestamp), old_text=SPEAKER_PREFIX.sub("", notes[a].content).strip(),
                    new_date=day_label(notes[b].timestamp), new_text=SPEAKER_PREFIX.sub("", notes[b].content).strip())
        answers, new = cached_calls(pair_prompts, os.path.join(out_dir, f"pair_cache_sample_{s}.json"), llm, args.workers)
        total_new_calls += new
        pairs = []
        for key, answer in answers.items():
            t_id, a, b = pair_meta[key]
            parsed = parse_conflict_label(answer)
            pairs.append({"timeline": t_id, "topic": timelines[t_id]["topic"], "old": a, "new": b,
                          "old_date": day_label(notes[a].timestamp), "new_date": day_label(notes[b].timestamp),
                          "old_text": notes[a].content, "new_text": notes[b].content, **parsed})

        # Questions whose evidence touches a note in a PROGRESS/CHANGE/CONTRADICTION step
        dia = [t.dia_id for sess in dataset[s].conversation.sessions.values() for t in sess.turns]
        involved = {p[k] for p in pairs if p["label"] in CONFLICT_KINDS for k in ("old", "new")}
        involved_dia = {dia[i] for i in involved}
        touched = [{"question": qa.question, "category": int(qa.category), "answer": qa.final_answer}
                   for qa in dataset[s].qa if set(e.strip() for e in qa.evidence) & involved_dia]

        counts = collections.Counter(p["label"] for p in pairs)
        report["samples"][str(s)] = {
            "notes": len(notes),
            "state_notes": sum(st["is_state"] for st in states.values()),
            "timelines": len(timelines),
            "timeline_steps_checked": len(pairs),
            "labels": dict(counts),
            "timelines_with_conflict": len({p["timeline"] for p in pairs if p["label"] in CONFLICT_KINDS}),
            "questions_touching_conflict_notes": dict(collections.Counter(q["category"] for q in touched)),
            "timeline_list": [{**tl, "dates": [day_label(notes[i].timestamp) for i in tl["notes"]],
                               "statuses": [states[i]["status"] for i in tl["notes"]]} for tl in timelines],
            "pairs": pairs,
            "touched_questions": touched,
        }
        r = report["samples"][str(s)]
        print(f"sample {s}: {r['notes']} notes, {r['state_notes']} state notes, {r['timelines']} timelines, "
              f"{r['timeline_steps_checked']} steps checked -> {dict(sorted(counts.items()))}; "
              f"timelines with a conflict: {r['timelines_with_conflict']}; "
              f"questions touching conflict notes: {r['questions_touching_conflict_notes']}")

    report["new_llm_calls"] = total_new_calls
    with open(os.path.join(out_dir, "step0_report.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(f"new LLM calls: {total_new_calls}; wrote {out_dir}/step0_report.json")


if __name__ == "__main__":
    main()
