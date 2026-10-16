"""
Offline memory consolidation for T-MEM (Module 2).

Consolidation runs after the A-MEM memory bank is built. It finds groups of
near-duplicate notes, and for each verified group appends one consolidated
note and marks the source notes. It never deletes or reorders notes, because
A-MEM links and retriever embedding rows are positions into
``list(memories.values())``.

This module holds candidate grouping, the information-loss guard, the
append-only apply step, and ``consolidate_bank`` which runs the LLM verify and
merge steps. Prompts and parsers live in ``llm_text_parsers.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from llm_text_parsers import (
    CONSOLIDATION_MERGE_FEEDBACK,
    CONSOLIDATION_MERGE_PROMPT,
    CONSOLIDATION_VERIFY_PROMPT,
    format_consolidation_notes,
    parse_consolidation_merge,
    parse_consolidation_verdict,
)
from memory_layer_robust import RobustAgenticMemorySystem, RobustMemoryNote


_SPEAKER_PATTERN = re.compile(r"^Speaker\s+(.+?)says\s*:")

_TIMESTAMP_FORMATS = (
    "%I:%M %p on %d %B, %Y",
    "%I:%M %p on %d %b, %Y",
    "%Y%m%d%H%M",
    "%Y-%m-%d %H:%M:%S",
)


@dataclass
class ConsolidationConfig:
    """Settings for finding candidate groups."""

    similarity_threshold: float = 0.80
    max_group_size: int = 5
    require_same_speaker: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"


@dataclass
class CandidateGroup:
    """A set of notes that may describe the same fact or small talk."""

    indices: List[int]
    min_similarity: float
    mean_similarity: float

    def to_dict(self) -> dict:
        return {
            "indices": list(self.indices),
            "min_similarity": self.min_similarity,
            "mean_similarity": self.mean_similarity,
        }


@dataclass
class ConsolidationResult:
    """Outcome of appending one consolidated note."""

    consolidated_index: int
    source_indices: List[int]
    note_id: str
    extra: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def note_speaker(note: RobustMemoryNote) -> Optional[str]:
    """Speaker name parsed from LoCoMo-style content ("Speaker Xsays : ...")."""
    match = _SPEAKER_PATTERN.match(note.content or "")
    return match.group(1).strip() if match else None


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def content_embeddings(notes: Sequence[RobustMemoryNote], model) -> np.ndarray:
    """L2-normalized embeddings of note content only (no keywords/tags/context).

    The A-MEM retriever embeds content plus metadata, which makes unrelated
    notes with similar tags look alike, so grouping uses content alone.
    """
    embeddings = model.encode([note.content for note in notes])
    embeddings = np.asarray(embeddings, dtype=np.float64)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return embeddings / norms


# ---------------------------------------------------------------------------
# Candidate grouping
# ---------------------------------------------------------------------------

def find_candidate_groups(
    notes: Sequence[RobustMemoryNote],
    embeddings: np.ndarray,
    config: Optional[ConsolidationConfig] = None,
) -> List[CandidateGroup]:
    """Group notes by complete-linkage similarity.

    Pairs are visited from most to least similar. Two groups merge only when
    every cross pair is at or above the threshold (complete linkage, so no
    chaining), the merged group stays within ``max_group_size``, and, if
    required, all notes share a speaker. Raw notes only: notes that are
    already consolidated or already consumed are skipped.
    """
    cfg = config or ConsolidationConfig()
    n = len(notes)
    if n < 2:
        return []

    eligible = [
        i for i, note in enumerate(notes)
        if note.note_type == "raw" and note.consolidated_into is None
    ]
    if len(eligible) < 2:
        return []

    sims = embeddings @ embeddings.T
    speakers = [note_speaker(note) for note in notes]

    eligible_arr = np.array(eligible)
    sub = sims[np.ix_(eligible_arr, eligible_arr)]
    rows, cols = np.where(np.triu(sub >= cfg.similarity_threshold, k=1))
    pairs = sorted(
        ((float(sub[r, c]), int(eligible_arr[r]), int(eligible_arr[c])) for r, c in zip(rows, cols)),
        key=lambda item: (-item[0], item[1], item[2]),
    )

    group_of: Dict[int, int] = {}
    members: Dict[int, List[int]] = {}

    def _group(idx: int) -> List[int]:
        gid = group_of.get(idx)
        return members[gid] if gid is not None else [idx]

    next_gid = 0
    for _, i, j in pairs:
        gi, gj = group_of.get(i), group_of.get(j)
        if gi is not None and gi == gj:
            continue
        left, right = _group(i), _group(j)
        merged = left + right
        if len(merged) > cfg.max_group_size:
            continue
        if cfg.require_same_speaker and len({speakers[m] for m in merged}) > 1:
            continue
        if float(sims[np.ix_(left, right)].min()) < cfg.similarity_threshold:
            continue

        for gid in (gi, gj):
            if gid is not None:
                members.pop(gid, None)
        members[next_gid] = merged
        for m in merged:
            group_of[m] = next_gid
        next_gid += 1

    groups: List[CandidateGroup] = []
    for idxs in members.values():
        idxs = sorted(idxs)
        block = sims[np.ix_(idxs, idxs)]
        upper = block[np.triu_indices(len(idxs), k=1)]
        groups.append(CandidateGroup(
            indices=idxs,
            min_similarity=float(upper.min()),
            mean_similarity=float(upper.mean()),
        ))
    groups.sort(key=lambda g: g.indices[0])
    return groups


# ---------------------------------------------------------------------------
# Information-loss guard
# ---------------------------------------------------------------------------

_NUMBER_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_CAPITALIZED_PATTERN = re.compile(r"\b[A-Z][a-zA-Z'’-]+\b")
_IGNORED_CAPITALIZED = {
    "Speaker", "I", "I'm", "I’m", "I've", "I’ve", "I'll", "I’ll", "I'd", "I’d",
    "Image", "Wow", "Yes", "Yeah", "No", "Oh", "Hey", "Hi", "Thanks", "Thank",
    "The", "This", "That", "It", "It's", "It’s", "My", "We", "You", "They",
    "What", "How", "Why", "When", "Where", "Who", "And", "But", "So", "Just",
    "Sounds", "Glad", "Great", "Awesome", "Cool", "Nice", "Love", "Sure",
}


def _source_date_strings(timestamp: Optional[str]) -> List[str]:
    """Accepted spellings of a source note's date in the merged text."""
    parsed = parse_timestamp(timestamp)
    if parsed is None:
        return []
    return [
        f"{parsed.day} {parsed.strftime('%B')} {parsed.year}",
        f"{parsed.day} {parsed.strftime('%B')}, {parsed.year}",
        f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}",
        parsed.strftime("%Y-%m-%d"),
    ]


def missing_facts(
    sources: Sequence[RobustMemoryNote],
    merged_text: str,
) -> List[str]:
    """Facts from the sources that do not appear in the merged text.

    Checks every number, every capitalized name (minus common sentence
    starters), and every source date. Returns an empty list when nothing is
    missing. This is a conservative screen, not a proof of faithfulness.
    """
    merged_lower = merged_text.lower()
    missing: List[str] = []
    seen: set = set()

    def _flag(token: str) -> None:
        if token not in seen:
            seen.add(token)
            missing.append(token)

    for note in sources:
        body = _SPEAKER_PATTERN.sub("", note.content or "")
        for number in _NUMBER_PATTERN.findall(body):
            if number not in merged_text:
                _flag(number)
        for word in _CAPITALIZED_PATTERN.findall(body):
            if word in _IGNORED_CAPITALIZED:
                continue
            if word.lower() not in merged_lower:
                _flag(word)
        speaker = note_speaker(note)
        if speaker and speaker.lower() not in merged_lower:
            _flag(speaker)
        dates = _source_date_strings(note.timestamp)
        if dates and not any(d.lower() in merged_lower for d in dates):
            _flag(dates[0])
    return missing


# ---------------------------------------------------------------------------
# Append-only apply step
# ---------------------------------------------------------------------------

def _sorted_timestamps(notes: Iterable[RobustMemoryNote]) -> List[str]:
    stamps = [note.timestamp for note in notes]
    return sorted(stamps, key=lambda s: (parse_timestamp(s) or datetime.min, s))


def apply_consolidation(
    system: RobustAgenticMemorySystem,
    source_indices: Sequence[int],
    merged_content: str,
    keywords: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    context: Optional[str] = None,
    archive_sources: bool = True,
    extra: Optional[Dict] = None,
) -> ConsolidationResult:
    """Append one consolidated note and mark its sources.

    The new note goes at the end of ``system.memories`` and its embedding is
    appended to the retriever, so every existing position, link, and
    embedding row stays valid. The new note links to its sources so A-MEM's
    neighbor expansion can bring them back into context.
    """
    all_notes = list(system.memories.values())
    sources_idx = sorted({int(i) for i in source_indices})
    if len(sources_idx) < 2:
        raise ValueError("consolidation needs at least two source notes")
    for idx in sources_idx:
        if idx < 0 or idx >= len(all_notes):
            raise IndexError(f"source index {idx} out of range")
        if all_notes[idx].consolidated_into is not None:
            raise ValueError(f"note {idx} is already consolidated")

    sources = [all_notes[i] for i in sources_idx]
    stamps = _sorted_timestamps(sources)

    note = RobustMemoryNote(
        content=merged_content,
        keywords=list(keywords or []),
        tags=list(tags or []),
        context=context or "Consolidated memory",
        links=list(sources_idx),
        timestamp=stamps[-1],
        last_accessed=stamps[-1],
        category="Consolidated",
    )
    note.note_type = "consolidated"
    note.source_indices = tuple(sources_idx)
    note.source_timestamps = tuple(all_notes[i].timestamp for i in sources_idx)
    note.first_seen = stamps[0]
    note.last_seen = stamps[-1]

    new_index = len(all_notes)
    system.memories[note.id] = note
    system.retriever.add_documents([
        "content:" + note.content +
        " context:" + note.context +
        " keywords: " + ", ".join(note.keywords) +
        " tags: " + ", ".join(note.tags)
    ])

    for source in sources:
        source.consolidated_into = new_index
        if archive_sources:
            source.status = "archived"

    return ConsolidationResult(
        consolidated_index=new_index,
        source_indices=sources_idx,
        note_id=note.id,
        extra=dict(extra or {}),
    )


# ---------------------------------------------------------------------------
# Full offline pass (LLM verify + merge)
# ---------------------------------------------------------------------------

def _unique(items: Iterable[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for item in items:
        key = str(item).strip()
        if key and key.lower() not in seen:
            seen.add(key.lower())
            out.append(key)
    return out


def consolidate_bank(
    system: RobustAgenticMemorySystem,
    llm,
    embeddings: np.ndarray,
    config: Optional[ConsolidationConfig] = None,
    temperature: float = 0.0,
    merge_retries: int = 1,
) -> Dict:
    """Find, verify, merge, check, and append consolidated notes.

    ``llm`` is any object with ``get_completion(prompt, temperature=...)``.
    ``embeddings`` are content-only embeddings of the notes currently in
    ``system`` (see ``content_embeddings``). Returns a log with one entry per
    candidate group and summary counts.
    """
    cfg = config or ConsolidationConfig()
    notes = list(system.memories.values())
    groups = find_candidate_groups(notes, embeddings, cfg)
    entries: List[Dict] = []
    counts = {"groups": len(groups), "merged": 0, "different": 0, "rejected": 0, "llm_calls": 0}

    for group in groups:
        sources = [notes[i] for i in group.indices]
        note_list = format_consolidation_notes(sources)
        entry: Dict = {
            **group.to_dict(),
            "sources": [{"index": i, "timestamp": notes[i].timestamp, "content": notes[i].content}
                        for i in group.indices],
        }

        verdict_raw = llm.get_completion(
            CONSOLIDATION_VERIFY_PROMPT.format(notes=note_list), temperature=temperature
        )
        counts["llm_calls"] += 1
        verdict = parse_consolidation_verdict(verdict_raw)
        entry["label"] = verdict["label"]
        entry["label_reason"] = verdict["reason"]

        if verdict["label"] == "DIFFERENT":
            entry["outcome"] = "kept_separate"
            counts["different"] += 1
            entries.append(entry)
            continue

        feedback = ""
        attempts: List[Dict] = []
        merged: Optional[Dict[str, str]] = None
        for _ in range(1 + max(merge_retries, 0)):
            merge_raw = llm.get_completion(
                CONSOLIDATION_MERGE_PROMPT.format(notes=note_list, feedback=feedback),
                temperature=temperature,
            )
            counts["llm_calls"] += 1
            parsed = parse_consolidation_merge(merge_raw)
            missing = missing_facts(sources, parsed["content"]) if parsed["content"] else ["<empty>"]
            attempts.append({"content": parsed["content"], "context": parsed["context"], "missing": missing})
            if not missing:
                merged = parsed
                break
            feedback = CONSOLIDATION_MERGE_FEEDBACK.format(missing=", ".join(missing))
        entry["attempts"] = attempts

        if merged is None:
            entry["outcome"] = "rejected_missing_facts"
            counts["rejected"] += 1
            entries.append(entry)
            continue

        result = apply_consolidation(
            system,
            group.indices,
            merged["content"],
            keywords=_unique(k for note in sources for k in note.keywords),
            tags=_unique(t for note in sources for t in note.tags),
            context=merged["context"] or None,
            extra={"label": verdict["label"]},
        )
        entry["outcome"] = "merged"
        entry["consolidated_index"] = result.consolidated_index
        entry["consolidated_content"] = merged["content"]
        counts["merged"] += 1
        entries.append(entry)

    return {"config": cfg.__dict__, "counts": counts, "groups": entries}
