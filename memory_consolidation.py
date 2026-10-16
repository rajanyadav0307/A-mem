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
    CONSOLIDATION_LABEL_RULES,
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


_SENTENCE_BREAK = re.compile(r"[.!?:;\]\[(\"“]")
_ACRONYM_PATTERN = re.compile(r"^[A-Z0-9+&]{2,}$")


def fact_words(text: str) -> List[str]:
    """Capitalized words that look like names, places, or other proper nouns.

    A capitalized word at the start of a sentence (or clause) is usually just
    an interjection ("Wow", "Yay", "Super"), so it only counts when it is an
    acronym like "LGBTQ". Capitalized words inside a sentence count.
    """
    words: List[str] = []
    for match in _CAPITALIZED_PATTERN.finditer(text):
        word = match.group(0)
        if word in _IGNORED_CAPITALIZED:
            continue
        before = text[:match.start()].rstrip()
        at_start = not before or _SENTENCE_BREAK.search(before[-1] + " ") is not None
        if at_start and not _ACRONYM_PATTERN.match(word):
            continue
        words.append(word)
    return words


def missing_facts(
    sources: Sequence[RobustMemoryNote],
    merged_text: str,
) -> List[str]:
    """Facts from the sources that do not appear in the merged text.

    Checks every number, every proper noun (see ``fact_words``), every
    speaker, and every source date. Returns an empty list when nothing is
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
        for word in fact_words(body):
            if word.lower() not in merged_lower:
                _flag(word)
        speaker = note_speaker(note)
        if speaker and speaker.lower() not in merged_lower:
            _flag(speaker)
        dates = _source_date_strings(note.timestamp)
        if dates and not any(d.lower() in merged_lower for d in dates):
            _flag(dates[0])
    return missing


_WEEKDAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"
_RELATIVE_TIME_PATTERN = re.compile(
    r"\b(?:next|last|this|coming|past)\s+(?:week|weekend|month|year|summer|winter|spring|fall|autumn|"
    + _WEEKDAYS + r")\b"
    r"|\b(?:yesterday|tomorrow|tonight|last night)\b"
    r"|\b(?:a few|few|a couple of|couple of|a|one|two|three|four|five|six|\d+)\s+"
    r"(?:days?|weeks?|months?|years?)\s+ago\b",
    re.IGNORECASE,
)


def relative_times(text: str) -> List[str]:
    """Relative time phrases such as "next month" or "two weeks ago"."""
    return [m.group(0).lower() for m in _RELATIVE_TIME_PATTERN.finditer(text or "")]


def unresolved_relative_times(merged_text: str) -> List[str]:
    """Relative time phrases left in a merged note.

    Every source note has its own date, so a merged note should state an
    absolute time ("August 2023") instead of "next month", which would be
    ambiguous once notes from different dates are combined.
    """
    found: List[str] = []
    for phrase in relative_times(merged_text):
        if phrase not in found:
            found.append(phrase)
    return found


_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")
_NUMBER_WORDS = {"a": 1, "one": 1, "a couple of": 2, "couple of": 2, "two": 2, "three": 3,
                 "four": 4, "five": 5, "six": 6, "a few": None, "few": None}


def _shift_month(year: int, month: int, delta: int) -> tuple:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def expected_resolution(phrase: str, said_at: Optional[str]) -> Optional[List[str]]:
    """Strings, any one of which shows ``phrase`` was resolved in a merged note.

    "next month" said on 17 July 2023 needs "August 2023"; "last year" said in
    2023 needs "2022". Week, weekend, weekday, and day phrases need their unit
    word ("week", "friday", "day"), as in "the week after 20 April 2022".
    Returns None when the phrase cannot be resolved from the date.
    """
    when = parse_timestamp(said_at)
    if when is None:
        return None
    phrase = phrase.lower()
    month_shift = {"next month": 1, "last month": -1, "this month": 0, "coming month": 1, "past month": -1}
    if phrase in month_shift:
        year, month = _shift_month(when.year, when.month, month_shift[phrase])
        return [f"{_MONTHS[month - 1]} {year}"]
    year_shift = {"next year": 1, "last year": -1, "this year": 0, "coming year": 1, "past year": -1}
    if phrase in year_shift:
        return [str(when.year + year_shift[phrase])]
    match = re.match(r"(.+?)\s+(day|week|month|year)s?\s+ago$", phrase)
    if match:
        count = _NUMBER_WORDS.get(match.group(1), None)
        if match.group(1).isdigit():
            count = int(match.group(1))
        unit = match.group(2)
        if unit == "month" and count:
            year, month = _shift_month(when.year, when.month, -count)
            return [f"{_MONTHS[month - 1]} {year}"]
        if unit == "year" and count:
            return [str(when.year - count)]
        return [unit]
    for unit in ("weekend", "week", "summer", "winter", "spring", "fall", "autumn") + tuple(_WEEKDAYS.split("|")):
        if phrase.endswith(unit):
            return [unit]
    if phrase in ("yesterday", "tomorrow", "tonight", "last night"):
        return ["day", "night", "evening"] if phrase in ("tonight", "last night") else ["day"]
    return None


def _mentions(text_lower: str, expected: str) -> bool:
    """True if ``expected`` appears in the text on its own.

    A month like "August 2023" must not count when it is only part of a day
    date such as "25 August 2023", which is the note's own date, not the
    resolved time.
    """
    pattern = re.escape(expected.lower())
    if expected.split()[0] in _MONTHS:
        pattern = r"(?<!\d\s)(?<!\d)" + pattern
    return re.search(r"\b" + pattern + r"\b", text_lower) is not None


def dropped_relative_times(sources: Sequence[RobustMemoryNote], merged_text: str) -> List[str]:
    """Relative times in the sources whose resolved form is missing from the merge.

    Catches merges that silence "next month" by deleting it instead of
    turning it into "August 2023".
    """
    merged_lower = merged_text.lower()
    dropped: List[str] = []
    for note in sources:
        for phrase in relative_times(note.content):
            expected = expected_resolution(phrase, note.timestamp)
            if expected and not any(_mentions(merged_lower, e) for e in expected):
                label = f"{phrase} (said {expected_date_label(note.timestamp)} -> {expected[0]})"
                if label not in dropped:
                    dropped.append(label)
    return dropped


def expected_date_label(timestamp: Optional[str]) -> str:
    parsed = parse_timestamp(timestamp)
    return f"{parsed.day} {parsed.strftime('%B')} {parsed.year}" if parsed else str(timestamp)


def compression_ratio(sources: Sequence[RobustMemoryNote], merged_text: str) -> float:
    """Merged length divided by the total length of the source note bodies."""
    total = sum(len(_SPEAKER_PATTERN.sub("", note.content or "").strip()) for note in sources)
    return len(merged_text) / total if total else 0.0


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


def _merge_problems(sources, parsed: Dict[str, str]) -> Dict[str, List[str]]:
    """Hard problems block a merge; "too_long" only triggers a retry."""
    content = parsed["content"]
    if not content:
        return {"missing": ["<empty>"], "relative_times": [], "dropped_times": [], "too_long": []}
    ratio = compression_ratio(sources, content)
    return {
        "missing": missing_facts(sources, content),
        "relative_times": unresolved_relative_times(content),
        "dropped_times": dropped_relative_times(sources, content),
        "too_long": [f"{ratio:.2f}x the length of the notes"] if ratio > 1.0 else [],
    }


def _feedback_lines(problems: Dict[str, List[str]]) -> str:
    lines = []
    if problems["missing"]:
        lines.append("- These items are missing and must appear: " + ", ".join(problems["missing"]))
    if problems["relative_times"]:
        lines.append(
            "- Replace these relative times with absolute dates: " + ", ".join(problems["relative_times"])
        )
    if problems["dropped_times"]:
        lines.append(
            "- State these times as absolute dates (do not drop them): " + "; ".join(problems["dropped_times"])
        )
    if problems["too_long"]:
        lines.append("- The note is too long (" + problems["too_long"][0] + "). Summarize; do not copy.")
    return "\n".join(lines)


def consolidate_bank(
    system: RobustAgenticMemorySystem,
    llm,
    embeddings: np.ndarray,
    config: Optional[ConsolidationConfig] = None,
    temperature: float = 0.0,
    merge_retries: int = 2,
) -> Dict:
    """Find, verify, merge, check, and append consolidated notes.

    ``llm`` is any object with ``get_completion(prompt, temperature=...)``.
    ``embeddings`` are content-only embeddings of the notes currently in
    ``system`` (see ``content_embeddings``). A merge is accepted only when no
    source fact is missing and no relative time is left. If it is merely
    longer than its sources, it is retried, and the first fact-complete
    attempt is used when retries run out. Returns a log with one entry per
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
        accepted: Optional[Dict] = None
        fallback: Optional[Dict] = None
        for _ in range(1 + max(merge_retries, 0)):
            merge_raw = llm.get_completion(
                CONSOLIDATION_MERGE_PROMPT.format(
                    notes=note_list,
                    label_rules=CONSOLIDATION_LABEL_RULES[verdict["label"]],
                    feedback=feedback,
                ),
                temperature=temperature,
            )
            counts["llm_calls"] += 1
            parsed = parse_consolidation_merge(merge_raw)
            problems = _merge_problems(sources, parsed)
            attempt = {
                "content": parsed["content"],
                "context": parsed["context"],
                "compression_ratio": compression_ratio(sources, parsed["content"]),
                **problems,
            }
            attempts.append(attempt)
            hard_ok = not (problems["missing"] or problems["relative_times"] or problems["dropped_times"])
            if hard_ok and not problems["too_long"]:
                accepted = attempt
                break
            if hard_ok and fallback is None:
                fallback = attempt
            feedback = CONSOLIDATION_MERGE_FEEDBACK.format(problems=_feedback_lines(problems))
        entry["attempts"] = attempts
        if accepted is None:
            accepted = fallback

        if accepted is None:
            entry["outcome"] = "rejected"
            counts["rejected"] += 1
            entries.append(entry)
            continue

        result = apply_consolidation(
            system,
            group.indices,
            accepted["content"],
            keywords=_unique(k for note in sources for k in note.keywords),
            tags=_unique(t for note in sources for t in note.tags),
            context=accepted["context"] or None,
            extra={"label": verdict["label"]},
        )
        entry["outcome"] = "merged"
        entry["consolidated_index"] = result.consolidated_index
        entry["consolidated_content"] = accepted["content"]
        entry["compression_ratio"] = accepted["compression_ratio"]
        counts["merged"] += 1
        entries.append(entry)

    return {"config": cfg.__dict__, "counts": counts, "groups": entries}
