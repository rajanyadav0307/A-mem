"""Tests for conflict handling (memory_conflicts.py and the retrieval options)."""

import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memory_conflicts import ConflictConfig, detect_and_apply  # noqa: E402
from memory_layer_robust import RobustAgenticMemorySystem, RobustMemoryNote, is_now_question  # noqa: E402

WORDS = ("studio", "searching", "running", "opening", "adoption", "applied", "pets", "dog", "cat", "store")


class WordEncoder:
    """Embeds text as a normalized bag of a few keywords (stand-in for MiniLM)."""

    def encode(self, texts, normalize_embeddings=False):
        rows = []
        for text in texts:
            t = text.lower()
            v = np.array([1.0 if w in t else 0.0 for w in WORDS] + [0.05])
            rows.append(v / np.linalg.norm(v) if normalize_embeddings else v)
        return np.asarray(rows)


class FakeRetriever:
    def __init__(self, notes):
        self.model = WordEncoder()
        self.corpus = [n.content for n in notes]
        self.embeddings = self.model.encode(self.corpus)

    def add_documents(self, documents):
        self.corpus.extend(documents)
        self.embeddings = np.vstack([self.embeddings, self.model.encode(documents)])

    def search(self, query, k=5):
        q = self.model.encode([query])[0]
        sims = self.embeddings @ q / (np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(q))
        return np.argsort(sims)[-k:][::-1]


# State answers keyed by a phrase in the note; pair labels keyed by (older phrase, newer phrase).
STATES = {
    "searching for a studio": ("Jon's dance studio", "searching for a studio"),
    "running my own studio": ("Jon's dance studio", "running studio"),
    "still opening the studio": ("Jon's dance studio", "opening studio"),
    "I have a dog": ("Jon's pets", "owns a dog"),
    "got a cat": ("Jon's pets", "got a cat"),
}
LABELS = {
    ("searching for a studio", "running my own studio"): "PROGRESS",
    ("running my own studio", "still opening the studio"): "CONTRADICTION",
    ("searching for a studio", "still opening the studio"): "PROGRESS",
    ("I have a dog", "got a cat"): "COMPATIBLE",
}


class ScriptedLLM:
    def __init__(self, change_pair=None, reject_verify=False):
        self.change_pair = change_pair
        self.reject_verify = reject_verify
        self.calls = 0

    def get_completion(self, prompt, temperature=0.0):
        self.calls += 1
        if prompt.startswith("A person said this"):
            for phrase, (topic, status) in STATES.items():
                if phrase in prompt:
                    return f"STATE: YES\nTOPIC: {topic}\nSTATUS: {status}"
            return "STATE: NO\nTOPIC: NONE\nSTATUS: NONE"
        if prompt.startswith("Two things the same person said, in date order"):
            if self.reject_verify:
                return "ANSWER: NO\nQUOTE: NONE"
            new_text = prompt.split("NEWER (")[1].split("): ", 1)[1].split("\n")[0]
            return f"ANSWER: YES\nQUOTE: {new_text}"
        for (old, new), label in LABELS.items():
            if f"): {old}" in prompt and f"): {new}" in prompt:
                if self.change_pair == (old, new):
                    label = "CHANGE"
                return f"LABEL: {label}\nREASON: test"
        return "LABEL: UNRELATED\nREASON: test"


def make_note(text, date, links=None):
    return RobustMemoryNote(content=f"Speaker Jonsays : {text}", timestamp=f"1:00 pm on {date}",
                            keywords=["k"], tags=["t"], context="ctx", category="c", links=list(links or []))


def make_system():
    notes = [
        make_note("searching for a studio", "1 February, 2023"),
        make_note("thanks so much!", "1 February, 2023"),
        make_note("running my own studio", "8 February, 2023"),
        make_note("I have a dog", "8 February, 2023"),
        make_note("got a cat", "3 April, 2023"),
        make_note("still opening the studio", "19 June, 2023"),
    ]
    system = RobustAgenticMemorySystem.__new__(RobustAgenticMemorySystem)
    system.memories = {n.id: n for n in notes}
    system.retriever = FakeRetriever(notes)
    return system


def run_detection(tmp_path, llm=None):
    system = make_system()
    log = detect_and_apply(system, llm or ScriptedLLM(), WordEncoder(), str(tmp_path), 0,
                           ConflictConfig(topic_threshold=0.5, status_duplicate=0.99, workers=1))
    return system, list(system.memories.values()), log


# ---------------------------------------------------------------------------
# Question intent and note fields
# ---------------------------------------------------------------------------

def test_now_question_rules():
    assert is_now_question("What book is Jon currently reading?")
    assert is_now_question("Is Caroline still going to the support group?")
    assert not is_now_question("When did Jon start reading the book?")
    assert not is_now_question("What did Jon do before he opened the studio, and what is he doing now?")
    assert not is_now_question("What did Melanie paint?")
    assert not is_now_question(None)


def test_old_pickles_get_conflict_defaults():
    note = make_note("x", "1 May, 2023")
    for name in ("timeline_id", "superseded_by", "conflicts_with", "valid_until"):
        note.__dict__.pop(name, None)
    restored = pickle.loads(pickle.dumps(note))
    assert restored.timeline_id is None and restored.superseded_by is None
    assert restored.conflicts_with == () and restored.valid_until is None


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def test_timelines_progress_contradiction_and_compatible(tmp_path):
    system, notes, log = run_detection(tmp_path)
    assert len(notes) == 6  # nothing added or removed
    studio = {notes[i].timeline_id for i in (0, 2, 5)}
    assert len(studio) == 1 and None not in studio
    assert notes[1].timeline_id is None  # small talk is not a situation
    assert notes[2].transition == "PROGRESS"
    # Contradiction links both notes and replaces nothing
    assert notes[2].conflicts_with == (5,) and notes[5].conflicts_with == (2,)
    assert all(n.superseded_by is None for n in notes)
    # Two-dogs case: compatible additions keep both notes active
    assert notes[3].timeline_id == notes[4].timeline_id
    assert notes[4].transition == "COMPATIBLE"
    assert log["labels"]["CONTRADICTION"] == 1


def test_change_marks_older_note_as_replaced(tmp_path):
    llm = ScriptedLLM(change_pair=("running my own studio", "still opening the studio"))
    _, notes, log = run_detection(tmp_path, llm)
    assert notes[2].superseded_by == 5
    assert notes[2].valid_until == "19 June 2023"
    assert notes[5].superseded_by is None
    assert len(log["replaced"]) == 1


def test_detection_uses_cache(tmp_path):
    run_detection(tmp_path)
    llm = ScriptedLLM()
    run_detection(tmp_path, llm)
    assert llm.calls == 0


def test_consolidated_notes_are_not_tagged(tmp_path):
    system = make_system()
    from memory_consolidation import apply_consolidation
    apply_consolidation(system, [0, 2], "Jon was searching for a studio and later running my own studio")
    detect_and_apply(system, ScriptedLLM(), WordEncoder(), str(tmp_path), 0,
                     ConflictConfig(topic_threshold=0.5, status_duplicate=0.99, workers=1))
    merged = list(system.memories.values())[-1]
    assert merged.note_type == "consolidated" and merged.timeline_id is None


# ---------------------------------------------------------------------------
# Retrieval options
# ---------------------------------------------------------------------------

def test_off_mode_leaves_prompt_unchanged(tmp_path):
    system, _, _ = run_detection(tmp_path)
    plain = make_system()
    assert system.find_related_memories_raw("studio", k=3) == plain.find_related_memories_raw("studio", k=3)
    assert "memory timeline:" not in system.find_related_memories_raw("studio", k=3)


def test_annotate_adds_timeline_and_conflict_labels(tmp_path):
    system, notes, _ = run_detection(tmp_path)
    system.conflict_mode = "annotate"
    text = system.render_notes([2, 5])
    assert "memory timeline: Jon's dance studio, step 2 of 3" in text
    assert "before: searching for a studio (1 February 2023)" in text
    assert "CONFLICTS with what was said on 19 June 2023" in text


def test_annotate_marks_outdated_notes(tmp_path):
    llm = ScriptedLLM(change_pair=("running my own studio", "still opening the studio"))
    system, _, _ = run_detection(tmp_path, llm)
    system.conflict_mode = "annotate"
    assert 'OUTDATED since 19 June 2023: replaced by "opening studio"' in system.render_notes([2])


def test_demote_only_for_now_questions(tmp_path):
    llm = ScriptedLLM(change_pair=("running my own studio", "still opening the studio"))
    system, _, _ = run_detection(tmp_path, llm)
    system.conflict_mode = "annotate_demote"
    system.current_question = "Is Jon currently running a studio?"
    penalties = system.conflict_penalties()
    assert penalties[2] == system.demote_penalty and penalties.sum() == system.demote_penalty
    system.current_question = "When did Jon open the studio?"
    assert system.conflict_penalties().sum() == 0
    system.conflict_mode = "annotate"
    system.current_question = "Is Jon currently running a studio?"
    assert system.conflict_penalties().sum() == 0


def test_demote_hits_older_side_of_contradiction(tmp_path):
    system, _, _ = run_detection(tmp_path)
    system.conflict_mode = "demote"
    system.current_question = "Is Jon still opening the studio?"
    penalties = system.conflict_penalties()
    assert penalties[2] > 0 and penalties[5] == 0


def test_demote_changes_search_order(tmp_path):
    llm = ScriptedLLM(change_pair=("running my own studio", "still opening the studio"))
    system, _, _ = run_detection(tmp_path, llm)
    system.conflict_mode = "demote"
    system.demote_penalty = 10.0
    system.current_question = "Is Jon currently running a studio?"
    with system.raw_only_view():
        order = system.search_retrievable("running studio", 6)
    assert order[-1] == 2


def test_unverified_change_replaces_nothing(tmp_path):
    llm = ScriptedLLM(change_pair=("running my own studio", "still opening the studio"), reject_verify=True)
    _, notes, log = run_detection(tmp_path, llm)
    assert all(n.superseded_by is None for n in notes)
    assert all(n.conflicts_with == () for n in notes)
    assert log["verification"]["checked"] >= 1 and log["verification"]["confirmed"] == 0


def test_verify_parser_needs_a_real_quote():
    from llm_text_parsers import parse_conflict_verify
    newer = "Still working on opening a dance studio."
    assert parse_conflict_verify('ANSWER: YES\nQUOTE: "Still working on opening"', newer)["confirmed"]
    assert not parse_conflict_verify("ANSWER: YES\nQUOTE: I closed the studio", newer)["confirmed"]
    assert not parse_conflict_verify("ANSWER: NO\nQUOTE: Still working on opening", newer)["confirmed"]
    assert not parse_conflict_verify("garbage", newer)["confirmed"]


def test_timeline_only_style_has_no_outdated_or_conflict_labels(tmp_path):
    llm = ScriptedLLM(change_pair=("running my own studio", "still opening the studio"))
    system, _, _ = run_detection(tmp_path, llm)
    system.conflict_mode = "timeline_only"
    text = system.render_notes([2])
    assert "memory timeline: Jon's dance studio, step 2 of 3" in text
    assert "OUTDATED" not in text and "CONFLICTS" not in text
    system.current_question = "Is Jon currently running a studio?"
    assert system.conflict_penalties().sum() == 0


def test_date_range_style(tmp_path):
    llm = ScriptedLLM(change_pair=("running my own studio", "still opening the studio"))
    system, _, _ = run_detection(tmp_path, llm)
    system.conflict_mode = "date_range"
    assert "memory timeline: valid 8 February 2023 - 19 June 2023" in system.render_notes([2])
    assert "memory timeline: valid 19 June 2023 - present" in system.render_notes([5])
    assert "memory timeline" not in system.render_notes([1])  # not in a timeline
    system.current_question = "Is Jon currently running a studio?"
    assert system.conflict_penalties().sum() == 0


# ---------------------------------------------------------------------------
# Two dates per timeline step: said on, and happened
# ---------------------------------------------------------------------------

def test_happened_around_resolves_relative_times():
    from memory_consolidation import happened_around
    said = "2:31 pm on 3 August, 2023"
    assert happened_around("I started volunteering here about a year ago", said) == "around August 2022"
    assert happened_around("I got Coco two weeks ago", said) == "two weeks before 3 August 2023"
    assert happened_around("Last week I graduated", said) == "the week before 3 August 2023"
    assert happened_around("Yesterday was great", said) == "2 August 2023"
    assert happened_around("I ran a race last Saturday", said) == "the Saturday before 3 August 2023"
    assert happened_around("Next month I have a show", said) == "September 2023"
    assert happened_around("I got Max 10 years ago", said) == "2013"
    assert happened_around("We went camping last summer", said) == "summer 2022"
    assert happened_around("I signed up for a class", said) is None
    assert happened_around("Last week", None) is None


def test_detection_sets_event_time(tmp_path):
    system = make_system()
    list(system.memories.values())[2].content = "Speaker Jonsays : running my own studio since last week"
    detect_and_apply(system, ScriptedLLM(), WordEncoder(), str(tmp_path), 0,
                     ConflictConfig(topic_threshold=0.5, status_duplicate=0.99, workers=1))
    notes = list(system.memories.values())
    assert notes[2].event_time == "the week before 8 February 2023"
    assert notes[0].event_time is None


def test_two_dates_style_in_labels(tmp_path):
    system = make_system()
    list(system.memories.values())[0].content = "Speaker Jonsays : searching for a studio since last week"
    detect_and_apply(system, ScriptedLLM(), WordEncoder(), str(tmp_path), 0,
                     ConflictConfig(topic_threshold=0.5, status_duplicate=0.99, workers=1))
    system.conflict_mode = "annotate"
    single = system.render_notes([2])
    assert "before: searching for a studio (1 February 2023)" in single
    system.timeline_date_style = "two_dates"
    two = system.render_notes([2])
    assert "step 2 of 3 (said on 8 February 2023)" in two
    assert "before: searching for a studio (said on 1 February 2023; happened: the week before 1 February 2023)" in two
