"""
Conflict handling for T-MEM (Module 3): state timelines.

Runs offline on a built memory bank, after consolidation. It never adds,
removes or reorders notes; it only sets the conflict-handling fields on raw
notes (see RobustMemoryNote):

  1. tag each raw note: is it a concrete, changeable fact about the speaker,
     and if so its topic and status (STATE_EXTRACT_PROMPT_STRICT)
  2. group each speaker's tagged notes into topics and sort them by time
     (one timeline per topic)
  3. compare each note with the earlier distinct statuses of its topic
     (CONFLICT_CHECK_PROMPT): SAME, PROGRESS, CHANGE, CONTRADICTION,
     COMPATIBLE or UNRELATED
  4. verify every CHANGE or CONTRADICTION with a stricter second prompt
     (CONFLICT_VERIFY_PROMPT) that must quote the newer note; unconfirmed
     ones become COMPATIBLE and change nothing
  5. apply: timeline fields on every tagged note; CHANGE marks the older note
     as replaced (valid_until, superseded_by); CONTRADICTION links both notes
     (conflicts_with) and replaces nothing

LLM answers are cached by prompt key, so reruns and step-0 caches cost nothing.
"""

from __future__ import annotations

import collections
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from scipy.cluster.hierarchy import fcluster, linkage

from llm_text_parsers import (
    CONFLICT_CHECK_PROMPT,
    CONFLICT_VERIFY_PROMPT,
    STATE_EXTRACT_PROMPT_STRICT,
    parse_conflict_label,
    parse_conflict_verify,
    parse_state_extract,
)
from memory_consolidation import happened_around, note_speaker, parse_timestamp
from memory_layer_robust import RobustAgenticMemorySystem

SPEAKER_PREFIX = re.compile(r"^Speaker\s+.+?says\s*:\s*")


@dataclass
class ConflictConfig:
    topic_threshold: float = 0.78    # topic names at least this similar share a timeline
    status_duplicate: float = 0.85   # statuses at least this similar count as the same status
    max_compare: Optional[int] = None  # earlier statuses compared per note (None = all)
    workers: int = 8


def day_label(timestamp: str) -> str:
    parsed = parse_timestamp(timestamp)
    return f"{parsed.day} {parsed.strftime('%B')} {parsed.year}" if parsed else timestamp


def note_body(content: str) -> str:
    return SPEAKER_PREFIX.sub("", content or "").strip()


def cached_calls(prompts: Dict[str, str], cache_path: str, llm, workers: int = 8) -> Tuple[Dict[str, str], int]:
    """Run prompts whose key is not yet cached; return ({key: response}, new calls)."""
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as handle:
            cache = json.load(handle)
    todo = {k: p for k, p in prompts.items() if k not in cache}
    if todo:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for key, answer in pool.map(lambda kp: (kp[0], llm.get_completion(kp[1], temperature=0.0)),
                                        todo.items()):
                cache[key] = answer
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(cache, handle, indent=1, ensure_ascii=False)
    return {k: cache[k] for k in prompts}, len(todo)


def topic_groups(topics: List[str], encoder, threshold: float) -> List[int]:
    """Cluster topic names by meaning (average linkage on cosine distance)."""
    if len(topics) == 1:
        return [1]
    emb = encoder.encode(topics, normalize_embeddings=True)
    tree = linkage(emb, method="average", metric="cosine")
    return list(fcluster(tree, t=1.0 - threshold, criterion="distance"))


def build_timelines(notes, states: Dict[int, dict], encoder, config: ConflictConfig) -> List[dict]:
    """Per speaker, group tagged notes by topic; keep topics spanning 2+ days."""
    by_speaker = collections.defaultdict(list)
    for i, st in states.items():
        if st["is_state"]:
            by_speaker[note_speaker(notes[i])].append(i)
    timelines = []
    for speaker in sorted(by_speaker, key=str):
        idxs = by_speaker[speaker]
        labels = topic_groups([states[i]["topic"] for i in idxs], encoder, config.topic_threshold)
        groups = collections.defaultdict(list)
        for i, lab in zip(idxs, labels):
            groups[lab].append(i)
        for lab in sorted(groups):
            members = sorted(groups[lab], key=lambda i: (parse_timestamp(notes[i].timestamp), i))
            if len({parse_timestamp(notes[i].timestamp).date() for i in members}) >= 2:
                name = collections.Counter(states[i]["topic"] for i in members).most_common(1)[0][0]
                timelines.append({"speaker": speaker, "topic": name, "notes": members})
    return timelines


def comparison_steps(notes, states, timelines, encoder, config: ConflictConfig) -> List[Tuple[int, int, int, bool]]:
    """(timeline id, older note, newer note, is_previous_status) pairs to check.

    Each note is compared with every earlier-day representative of a distinct
    status in its timeline (or the most recent ``max_compare`` of them). A
    repeated status replaces its representative with the newest mention.
    """
    day = lambda i: parse_timestamp(notes[i].timestamp).date()  # noqa: E731
    steps = []
    for t_id, tl in enumerate(timelines):
        members = tl["notes"]
        emb = {i: encoder.encode([states[i]["status"] or states[i]["topic"]], normalize_embeddings=True)[0]
               for i in members}
        reps: List[int] = []
        for i in members:
            earlier = [r for r in reps if day(r) < day(i)]
            if config.max_compare is not None:
                earlier = earlier[-config.max_compare:]
            for r in earlier:
                steps.append((t_id, r, i, r == (earlier[-1] if earlier else None)))
            same = [k for k, r in enumerate(reps) if float(emb[r] @ emb[i]) >= config.status_duplicate]
            if same:
                reps[same[0]] = i
            else:
                reps.append(i)
    return steps


def detect_and_apply(
    system: RobustAgenticMemorySystem,
    llm,
    encoder,
    cache_dir: str,
    sample_idx: int,
    config: Optional[ConflictConfig] = None,
) -> Dict:
    """Tag, build timelines, check steps, and set conflict fields on the notes.

    Only raw notes are tagged; merged (consolidated) notes are left alone.
    Returns a log of timelines, labels, replacements and contradictions.
    """
    cfg = config or ConflictConfig()
    os.makedirs(cache_dir, exist_ok=True)
    notes = list(system.memories.values())
    raw = [i for i, n in enumerate(notes) if n.note_type == "raw"]

    prompts = {str(i): STATE_EXTRACT_PROMPT_STRICT.format(
        date=day_label(notes[i].timestamp), speaker=note_speaker(notes[i]) or "Speaker",
        text=note_body(notes[i].content)) for i in raw}
    answers, new_state_calls = cached_calls(
        prompts, os.path.join(cache_dir, f"state_cache_sample_{sample_idx}.json"), llm, cfg.workers)
    states = {int(k): parse_state_extract(v) for k, v in answers.items()}

    timelines = build_timelines(notes, states, encoder, cfg)
    steps = comparison_steps(notes, states, timelines, encoder, cfg)
    pair_prompts = {f"{a}-{b}": CONFLICT_CHECK_PROMPT.format(
        old_date=day_label(notes[a].timestamp), old_text=note_body(notes[a].content),
        new_date=day_label(notes[b].timestamp), new_text=note_body(notes[b].content)) for _, a, b, _ in steps}
    answers, new_pair_calls = cached_calls(
        pair_prompts, os.path.join(cache_dir, f"pair_cache_sample_{sample_idx}.json"), llm, cfg.workers)

    pairs = []
    for t_id, a, b, is_prev in steps:
        parsed = parse_conflict_label(answers[f"{a}-{b}"])
        pairs.append({"timeline": t_id, "old": a, "new": b, "previous_status": is_prev, **parsed})

    # Verify the labels that would change a note (CHANGE, CONTRADICTION)
    risky = [p for p in pairs if p["label"] in ("CHANGE", "CONTRADICTION")]
    verify_prompts = {f"{p['old']}-{p['new']}": CONFLICT_VERIFY_PROMPT.format(
        old_date=day_label(notes[p["old"]].timestamp), old_text=note_body(notes[p["old"]].content),
        new_date=day_label(notes[p["new"]].timestamp), new_text=note_body(notes[p["new"]].content)) for p in risky}
    verify_answers, new_verify_calls = cached_calls(
        verify_prompts, os.path.join(cache_dir, f"verify_cache_sample_{sample_idx}.json"), llm, cfg.workers)
    for p in risky:
        check = parse_conflict_verify(verify_answers[f"{p['old']}-{p['new']}"], note_body(notes[p["new"]].content))
        p["first_label"], p["verified"], p["quote"] = p["label"], check["confirmed"], check["quote"]
        if not check["confirmed"]:
            p["label"] = "COMPATIBLE"

    # Apply: timeline fields
    for t_id, tl in enumerate(timelines):
        for i in tl["notes"]:
            notes[i].timeline_id = t_id
            notes[i].timeline_topic = tl["topic"]
            notes[i].timeline_status = states[i]["status"] or states[i]["topic"]
            notes[i].event_time = happened_around(note_body(notes[i].content), notes[i].timestamp)
    # Transition label of each note vs the previous distinct status
    for p in pairs:
        if p["previous_status"]:
            notes[p["new"]].transition = p["label"]
    # CHANGE: the older note is replaced from the newer note's date (earliest replacement wins)
    replaced, contradictions = [], []
    for p in sorted(pairs, key=lambda q: (parse_timestamp(notes[q["new"]].timestamp), q["new"])):
        older, newer = notes[p["old"]], notes[p["new"]]
        if p["label"] == "CHANGE" and older.superseded_by is None:
            older.superseded_by = p["new"]
            older.valid_until = day_label(newer.timestamp)
            replaced.append((p["old"], p["new"]))
        elif p["label"] == "CONTRADICTION":
            older.conflicts_with = tuple(sorted(set(older.conflicts_with) | {p["new"]}))
            newer.conflicts_with = tuple(sorted(set(newer.conflicts_with) | {p["old"]}))
            contradictions.append((p["old"], p["new"]))

    return {
        "config": cfg.__dict__,
        "raw_notes": len(raw),
        "state_notes": sum(st["is_state"] for st in states.values()),
        "timelines": [{**tl, "dates": [day_label(notes[i].timestamp) for i in tl["notes"]],
                       "statuses": [states[i]["status"] for i in tl["notes"]]} for tl in timelines],
        "labels": dict(collections.Counter(p["label"] for p in pairs)),
        "replaced": [{"older": a, "newer": b, "older_text": notes[a].content, "newer_text": notes[b].content,
                      "valid_until": notes[a].valid_until} for a, b in replaced],
        "contradictions": [{"older": a, "newer": b, "older_text": notes[a].content,
                            "newer_text": notes[b].content} for a, b in contradictions],
        "pairs": pairs,
        "verification": {"checked": len(risky), "confirmed": sum(p["verified"] for p in risky)},
        "new_llm_calls": new_state_calls + new_pair_calls + new_verify_calls,
    }
