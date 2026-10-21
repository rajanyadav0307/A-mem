"""
Step 0 for conflict handling: how many real conflicts are in a memory bank?

Reads the May 6 memory bank (never modifies it) and, with gpt-4o-mini at
temperature 0:
  1. tags every note: is it about the speaker's own changeable situation,
     and if so, which topic and what status
  2. groups each speaker's state notes into topics (topic-name similarity)
     and sorts each topic by date, giving "timelines"
  3. checks steps of each timeline across different days: SAME, PROGRESS,
     CHANGE, CONTRADICTION, COMPATIBLE or UNRELATED

Two methods:
  v1 (first try)  - loose tagging prompt, topic threshold 0.70, each note
                    compared only with the note just before it
  v2 (default)    - strict tagging prompt (concrete facts only), topic
                    threshold 0.78, each note compared with every earlier
                    distinct status of the same topic (up to --max_compare)
v2 also checks that known cases from samples 0-1 are found.

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
    STATE_EXTRACT_PROMPT_STRICT,
    parse_conflict_label,
    parse_state_extract,
)
from load_dataset import load_locomo_dataset
from memory_consolidation import note_speaker, parse_timestamp
from memory_layer_robust import RobustLLMController

SPEAKER_PREFIX = re.compile(r"^Speaker\s+.+?says\s*:\s*")
CONFLICT_KINDS = ("PROGRESS", "CHANGE", "CONTRADICTION")

# Known cases, found by reading samples 0-1 (2026-10-21). Used only to check
# that the method can find them: (sample, older text, newer text, acceptable labels).
KNOWN_CASES = [
    (1, "on the hunt for the ideal spot for my dance studio", "I love running my own studio", {"PROGRESS"}),
    (1, "I love running my own studio", "Still working on opening a dance studio", {"CONTRADICTION", "CHANGE"}),
    (1, "lost my job at Door Dash", "ad campaign for my clothing store", {"CHANGE", "PROGRESS"}),
    (0, "Researching adoption agencies", "first step towards becoming a mom", {"PROGRESS"}),
    (0, "first step towards becoming a mom", "passed the adoption agency interviews", {"PROGRESS"}),
    (0, "signed up for a pottery class", "made this bowl in my class", {"PROGRESS", "COMPATIBLE", "SAME"}),
]


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
    parser.add_argument("--method", choices=["v1", "v2"], default="v2")
    parser.add_argument("--topic_threshold", type=float, default=None, help="default: 0.70 (v1), 0.78 (v2)")
    parser.add_argument("--max_compare", type=int, default=8, help="v2: earlier statuses compared per note")
    parser.add_argument("--status_duplicate", type=float, default=0.85,
                        help="v2: statuses this similar count as the same status")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out_dir", default=None)
    args = parser.parse_args()
    if args.topic_threshold is None:
        args.topic_threshold = 0.70 if args.method == "v1" else 0.78

    out_dir = args.out_dir or os.path.join("analysis", "conflict_step0_" + datetime.now().strftime("%Y-%m-%d_%H-%M"))
    os.makedirs(out_dir, exist_ok=True)
    llm = RobustLLMController("openai", args.model).llm
    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    dataset = load_locomo_dataset(args.dataset)
    report = {"created": datetime.now().isoformat(timespec="seconds"), "model": args.model,
              "method": args.method, "topic_threshold": args.topic_threshold,
              "max_compare": args.max_compare, "status_duplicate": args.status_duplicate, "samples": {}}
    total_new_calls = 0

    for s in args.samples:
        with open(os.path.join(args.cache_dir, f"memory_cache_sample_{s}.pkl"), "rb") as handle:
            notes = list(pickle.load(handle).values())

        # 1. State tagging
        state_prompt = STATE_EXTRACT_PROMPT if args.method == "v1" else STATE_EXTRACT_PROMPT_STRICT
        prompts = {str(i): state_prompt.format(
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

        # 3. Choose which steps to check
        day = lambda i: parse_timestamp(notes[i].timestamp).date()  # noqa: E731
        steps = []  # (timeline id, older note, newer note)
        for t_id, tl in enumerate(timelines):
            members = tl["notes"]
            if args.method == "v1":
                last_by_day = []
                for i in members:
                    if last_by_day and day(last_by_day[-1]) == day(i):
                        last_by_day[-1] = i  # keep the latest note of each day
                    else:
                        last_by_day.append(i)
                steps += [(t_id, a, b) for a, b in zip(last_by_day, last_by_day[1:])]
                continue
            # v2: keep one representative note per distinct status; compare each new
            # note with the representatives from earlier days.
            status_emb = {i: encoder.encode([states[i]["status"] or states[i]["topic"]],
                                            normalize_embeddings=True)[0] for i in members}
            reps = []
            for i in members:
                earlier = [r for r in reps if day(r) < day(i)][-args.max_compare:]
                steps += [(t_id, r, i) for r in earlier]
                same = [k for k, r in enumerate(reps)
                        if float(status_emb[r] @ status_emb[i]) >= args.status_duplicate]
                if same:
                    reps[same[0]] = i  # same status: keep the latest mention
                else:
                    reps.append(i)
        pair_prompts, pair_meta = {}, {}
        for t_id, a, b in steps:
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

        # Known cases: are both notes tagged, in the same timeline, compared, and labelled as expected?
        known = []
        find = lambda text: [i for i, n in enumerate(notes) if text.lower() in n.content.lower()]  # noqa: E731
        timeline_of = {i: t_id for t_id, tl in enumerate(timelines) for i in tl["notes"]}
        labelled = {(p["old"], p["new"]): p["label"] for p in pairs}
        for ks, old_text, new_text, ok_labels in KNOWN_CASES:
            if ks != s:
                continue
            olds, news = find(old_text), find(new_text)
            outcome = {"old_text": old_text, "new_text": new_text, "expected": sorted(ok_labels)}
            if not olds or not news:
                outcome["result"] = "text not found"
            else:
                a, b = olds[0], news[0]
                if not (states[a]["is_state"] and states[b]["is_state"]):
                    outcome["result"] = "not tagged as situation"
                elif timeline_of.get(a) != timeline_of.get(b):
                    outcome["result"] = "different topics"
                elif (a, b) in labelled:
                    label = labelled[(a, b)]
                    outcome["result"] = "found" if label in ok_labels else f"wrong label ({label})"
                else:
                    # The older note may have been replaced by a later mention of the same status.
                    status_a = encoder.encode([states[a]["status"] or states[a]["topic"]], normalize_embeddings=True)[0]
                    via = [(x, lab) for (x, y), lab in labelled.items() if y == b and float(
                        encoder.encode([states[x]["status"] or states[x]["topic"]], normalize_embeddings=True)[0]
                        @ status_a) >= args.status_duplicate]
                    if any(lab in ok_labels for _, lab in via):
                        outcome["result"] = "found (via a later note with the same status)"
                    elif via:
                        outcome["result"] = f"wrong label ({', '.join(lab for _, lab in via)})"
                    else:
                        outcome["result"] = "not compared"
                    outcome["compared_with_newer"] = [
                        {"older": notes[x].content[:80], "label": lab} for (x, y), lab in labelled.items() if y == b]
                outcome["topics"] = [states[a]["topic"], states[b]["topic"]]
            known.append(outcome)
            print(f"   known case: {old_text[:35]!r} -> {new_text[:35]!r}: {outcome['result']}")

        counts = collections.Counter(p["label"] for p in pairs)
        report["samples"][str(s)] = {
            "notes": len(notes),
            "state_notes": sum(st["is_state"] for st in states.values()),
            "timelines": len(timelines),
            "timeline_steps_checked": len(pairs),
            "labels": dict(counts),
            "timelines_with_conflict": len({p["timeline"] for p in pairs if p["label"] in CONFLICT_KINDS}),
            "questions_touching_conflict_notes": dict(collections.Counter(q["category"] for q in touched)),
            "known_cases": known,
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
