"""Tests for the LLM-free consolidation core (memory_consolidation.py)."""

import os
import pickle
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memory_consolidation import (  # noqa: E402
    ConsolidationConfig,
    apply_consolidation,
    find_candidate_groups,
    missing_facts,
)
from memory_layer_robust import RobustAgenticMemorySystem, RobustMemoryNote  # noqa: E402


class FakeRetriever:
    """Stand-in for SimpleEmbeddingRetriever that appends one row per document."""

    def __init__(self, n_docs: int, dim: int = 4):
        self.corpus = [f"doc {i}" for i in range(n_docs)]
        self.embeddings = np.arange(n_docs * dim, dtype=np.float64).reshape(n_docs, dim)

    def add_documents(self, documents):
        self.corpus.extend(documents)
        new_rows = np.full((len(documents), self.embeddings.shape[1]), -1.0)
        self.embeddings = np.vstack([self.embeddings, new_rows])


def make_note(content, timestamp="1:00 pm on 1 May, 2023", links=None):
    return RobustMemoryNote(
        content=content,
        keywords=["k"],
        tags=["t"],
        context="ctx",
        category="c",
        timestamp=timestamp,
        links=list(links or []),
    )


def make_system(notes):
    system = RobustAgenticMemorySystem.__new__(RobustAgenticMemorySystem)
    system.memories = {note.id: note for note in notes}
    system.retriever = FakeRetriever(len(notes))
    return system


def unit(vectors):
    arr = np.asarray(vectors, dtype=np.float64)
    return arr / np.linalg.norm(arr, axis=1, keepdims=True)


# ---------------------------------------------------------------------------
# Note fields
# ---------------------------------------------------------------------------

def test_old_pickled_notes_get_default_fields():
    note = make_note("Speaker Annasays : hello")
    for name in ("note_type", "source_indices", "consolidated_into", "status", "first_seen", "last_seen"):
        note.__dict__.pop(name, None)
    restored = pickle.loads(pickle.dumps(note))
    assert restored.note_type == "raw"
    assert restored.status == "active"
    assert restored.consolidated_into is None
    assert restored.source_indices == ()


def test_setting_field_on_one_note_does_not_leak_to_others():
    a, b = make_note("a"), make_note("b")
    a.status = "archived"
    assert b.status == "active"
    assert RobustMemoryNote.status == "active"


# ---------------------------------------------------------------------------
# Candidate groups
# ---------------------------------------------------------------------------

def test_complete_linkage_does_not_chain():
    # a~b and b~c are similar, but a and c are not: only one pair may form.
    notes = [make_note(f"Speaker Annasays : n{i}") for i in range(3)]
    emb = unit([[1.0, 0.0], [0.8, 0.6], [0.28, 0.96]])
    groups = find_candidate_groups(notes, emb, ConsolidationConfig(similarity_threshold=0.75))
    assert len(groups) == 1
    assert len(groups[0].indices) == 2


def test_group_size_cap():
    notes = [make_note(f"Speaker Annasays : n{i}") for i in range(4)]
    emb = unit([[1.0, 0.0]] * 4)
    groups = find_candidate_groups(notes, emb, ConsolidationConfig(similarity_threshold=0.9, max_group_size=2))
    assert all(len(g.indices) <= 2 for g in groups)
    assert sum(len(g.indices) for g in groups) == 4


def test_same_speaker_required_by_default():
    notes = [make_note("Speaker Annasays : hi"), make_note("Speaker Bensays : hi")]
    emb = unit([[1.0, 0.0], [1.0, 0.0]])
    assert find_candidate_groups(notes, emb) == []
    loose = ConsolidationConfig(require_same_speaker=False)
    assert len(find_candidate_groups(notes, emb, loose)) == 1


def test_consolidated_and_consumed_notes_are_skipped():
    notes = [make_note(f"Speaker Annasays : n{i}") for i in range(3)]
    notes[0].consolidated_into = 5
    notes[1].note_type = "consolidated"
    emb = unit([[1.0, 0.0]] * 3)
    assert find_candidate_groups(notes, emb) == []


# ---------------------------------------------------------------------------
# Information-loss guard
# ---------------------------------------------------------------------------

def test_missing_facts_flags_numbers_names_and_dates():
    sources = [
        make_note("Speaker Annasays : I ran 5 miles with Ben", "2:31 pm on 17 July, 2023"),
        make_note("Speaker Annasays : Ran with Ben again", "1:33 pm on 25 August, 2023"),
    ]
    merged = "Anna ran with Ben on 17 July 2023."
    missing = missing_facts(sources, merged)
    assert "5" in missing
    assert "25 August 2023" in missing
    assert "Ben" not in missing and "Anna" not in missing


def test_missing_facts_empty_when_everything_kept():
    sources = [
        make_note("Speaker Annasays : I ran 5 miles with Ben", "2:31 pm on 17 July, 2023"),
        make_note("Speaker Annasays : Ran with Ben again", "1:33 pm on 25 August, 2023"),
    ]
    merged = "Anna ran 5 miles with Ben on 17 July 2023 and again on 25 August 2023."
    assert missing_facts(sources, merged) == []


# ---------------------------------------------------------------------------
# Append-only apply step
# ---------------------------------------------------------------------------

def test_apply_consolidation_is_append_only():
    notes = [
        make_note("Speaker Annasays : art show next month", "2:31 pm on 17 July, 2023", links=[2]),
        make_note("Speaker Bensays : nice", "3:00 pm on 18 July, 2023", links=[0]),
        make_note("Speaker Annasays : art show next month!", "1:33 pm on 25 August, 2023", links=[1]),
    ]
    system = make_system(notes)
    ids_before = list(system.memories.keys())
    links_before = [list(n.links) for n in system.memories.values()]
    rows_before = system.retriever.embeddings.copy()

    result = apply_consolidation(system, [2, 0], "Anna planned an art show (merged).")

    all_notes = list(system.memories.values())
    assert list(system.memories.keys())[:3] == ids_before
    assert [list(n.links) for n in all_notes[:3]] == links_before
    np.testing.assert_array_equal(system.retriever.embeddings[:3], rows_before)
    assert system.retriever.embeddings.shape[0] == 4

    assert result.consolidated_index == 3
    merged = all_notes[3]
    assert merged.note_type == "consolidated"
    assert merged.links == [0, 2]
    assert merged.source_indices == (0, 2)
    assert merged.first_seen == "2:31 pm on 17 July, 2023"
    assert merged.last_seen == "1:33 pm on 25 August, 2023"
    assert merged.timestamp == merged.last_seen

    assert all_notes[0].consolidated_into == 3 and all_notes[0].status == "archived"
    assert all_notes[2].consolidated_into == 3 and all_notes[2].status == "archived"
    assert all_notes[1].consolidated_into is None and all_notes[1].status == "active"


def test_apply_consolidation_can_keep_sources_active():
    notes = [make_note("Speaker Annasays : a"), make_note("Speaker Annasays : b")]
    system = make_system(notes)
    apply_consolidation(system, [0, 1], "merged", archive_sources=False)
    assert all(n.status == "active" for n in notes)
    assert all(n.consolidated_into == 2 for n in notes)


def test_apply_consolidation_rejects_bad_input():
    notes = [make_note("Speaker Annasays : a"), make_note("Speaker Annasays : b"), make_note("Speaker Annasays : c")]
    system = make_system(notes)
    with pytest.raises(ValueError):
        apply_consolidation(system, [0], "one source")
    with pytest.raises(IndexError):
        apply_consolidation(system, [0, 9], "out of range")
    apply_consolidation(system, [0, 1], "merged")
    with pytest.raises(ValueError):
        apply_consolidation(system, [1, 2], "note 1 already consolidated")


# ---------------------------------------------------------------------------
# Prompts, parsers and the full offline pass (fake LLM)
# ---------------------------------------------------------------------------

from llm_text_parsers import parse_consolidation_merge, parse_consolidation_verdict  # noqa: E402
from memory_consolidation import consolidate_bank  # noqa: E402


def test_verdict_parser_defaults_to_different():
    assert parse_consolidation_verdict("LABEL: same fact\nREASON: x")["label"] == "SAME_FACT"
    assert parse_consolidation_verdict("LABEL: Small talk.")["label"] == "SMALL_TALK"
    assert parse_consolidation_verdict("no idea")["label"] == "DIFFERENT"
    assert parse_consolidation_verdict("")["label"] == "DIFFERENT"
    assert parse_consolidation_verdict('{"label": "SAME_FACT", "reason": "r"}')["label"] == "SAME_FACT"


def test_merge_parser_joins_lines():
    parsed = parse_consolidation_merge("CONTENT: Anna said hi\n on 1 May 2023.\nCONTEXT: greeting")
    assert parsed == {"content": "Anna said hi on 1 May 2023.", "context": "greeting"}
    assert parse_consolidation_merge("nothing useful")["content"] == ""


class ScriptedLLM:
    """Returns a label for verify prompts and queued answers for merge prompts."""

    def __init__(self, label, merges):
        self.label = label
        self.merges = list(merges)
        self.prompts = []

    def get_completion(self, prompt, temperature=0.7):
        self.prompts.append(prompt)
        if prompt.startswith("You are checking"):
            return f"LABEL: {self.label}\nREASON: test"
        return self.merges.pop(0)


def _two_similar_notes():
    notes = [
        make_note("Speaker Annasays : Wow, I ran 5 miles with Ben along the river trail and it was so tough!",
                  "2:31 pm on 17 July, 2023"),
        make_note("Speaker Annasays : Yay, ran 5 miles with Ben again on the river trail, getting easier now!",
                  "1:33 pm on 25 August, 2023"),
    ]
    return notes, unit([[1.0, 0.0], [1.0, 0.0]])


GOOD = "CONTENT: Anna ran 5 miles with Ben on 17 July 2023 and 25 August 2023.\nCONTEXT: running"


def test_consolidate_bank_merges_after_retry():
    notes, emb = _two_similar_notes()
    system = make_system(notes)
    llm = ScriptedLLM("SAME_FACT", ["CONTENT: Anna ran with Ben.\nCONTEXT: running", GOOD])
    log = consolidate_bank(system, llm, emb)
    assert log["counts"] == {"groups": 1, "merged": 1, "different": 0, "rejected": 0, "llm_calls": 3}
    assert "missing and must appear" in llm.prompts[-1]
    merged = list(system.memories.values())[2]
    assert merged.note_type == "consolidated"
    assert merged.context == "running"
    assert log["groups"][0]["outcome"] == "merged"
    assert log["groups"][0]["compression_ratio"] < 1.0


def test_consolidate_bank_rejects_when_facts_stay_missing():
    notes, emb = _two_similar_notes()
    system = make_system(notes)
    bad = "CONTENT: Anna ran with Ben.\nCONTEXT: running"
    log = consolidate_bank(system, ScriptedLLM("SAME_FACT", [bad, bad, bad]), emb)
    assert log["counts"]["rejected"] == 1
    assert len(system.memories) == 2
    assert all(n.consolidated_into is None for n in notes)


def test_consolidate_bank_rejects_unresolved_relative_times():
    notes, emb = _two_similar_notes()
    system = make_system(notes)
    vague = ("CONTENT: Anna ran 5 miles with Ben on 17 July 2023 and 25 August 2023, "
             "and plans to run next month.\nCONTEXT: running")
    llm = ScriptedLLM("SAME_FACT", [vague, vague, vague])
    log = consolidate_bank(system, llm, emb)
    assert log["counts"]["rejected"] == 1
    assert "next month" in llm.prompts[-1]


def test_consolidate_bank_falls_back_to_complete_but_long_merge():
    notes, emb = _two_similar_notes()
    system = make_system(notes)
    long_text = "CONTENT: " + " ".join(n.content for n in notes) + " Anna on 17 July 2023 and 25 August 2023.\nCONTEXT: r"
    log = consolidate_bank(system, ScriptedLLM("SAME_FACT", [long_text, long_text, long_text]), emb)
    assert log["counts"]["merged"] == 1
    assert log["groups"][0]["compression_ratio"] > 1.0
    assert len(log["groups"][0]["attempts"]) == 3


def test_consolidate_bank_keeps_different_notes_apart():
    notes, emb = _two_similar_notes()
    system = make_system(notes)
    llm = ScriptedLLM("DIFFERENT", [])
    log = consolidate_bank(system, llm, emb)
    assert log["counts"]["different"] == 1 and log["counts"]["llm_calls"] == 1
    assert len(system.memories) == 2


def test_fact_words_skip_interjections_but_keep_names():
    from memory_consolidation import fact_words
    words = fact_words("Yay! Next month I'm having an LGBTQ art show. Super stoked, Mel. We went to Paris.")
    assert words == ["LGBTQ", "Mel", "Paris"]


def test_relative_times_detected():
    from memory_consolidation import relative_times
    assert relative_times("Next month, two weeks ago, last night") == ["next month", "two weeks ago", "last night"]
    assert relative_times("in August 2023") == []


def test_dropped_relative_time_blocks_merge():
    from memory_consolidation import dropped_relative_times, expected_resolution
    assert expected_resolution("next month", "2:31 pm on 17 July, 2023") == ["August 2023"]
    assert expected_resolution("next month", "1:00 pm on 20 December, 2023") == ["January 2024"]
    assert expected_resolution("last year", "1:00 pm on 1 May, 2023") == ["2022"]
    notes = [
        make_note("Speaker Annasays : Next month I have an art show with my paintings, so excited!",
                  "2:31 pm on 17 July, 2023"),
        make_note("Speaker Annasays : Putting together my art show of paintings next month, super stoked!",
                  "1:33 pm on 25 August, 2023"),
    ]
    silent = "Anna is preparing an art show of her paintings, mentioned on 17 July 2023 and 25 August 2023."
    assert len(dropped_relative_times(notes, silent)) == 2
    resolved = ("Anna is preparing an art show of her paintings: on 17 July 2023 she said August 2023, "
                "on 25 August 2023 she said September 2023.")
    assert dropped_relative_times(notes, resolved) == []

    system = make_system(notes)
    llm = ScriptedLLM("SAME_FACT", [f"CONTENT: {silent}\nCONTEXT: art"] + [f"CONTENT: {resolved}\nCONTEXT: art"] * 2)
    log = consolidate_bank(system, llm, unit([[1.0, 0.0], [1.0, 0.0]]))
    assert log["counts"]["merged"] == 1
    assert "do not drop them" in llm.prompts[2]
    assert log["groups"][0]["consolidated_content"] == resolved


# ---------------------------------------------------------------------------
# Retrieval modes
# ---------------------------------------------------------------------------

class KeywordModel:
    """Embeds text as a 3-d vector by keyword, so search results are predictable."""

    AXES = ("art", "dog", "chat")

    def encode(self, texts):
        rows = []
        for text in texts:
            text = text.lower()
            rows.append([1.0 if axis in text else 0.01 for axis in self.AXES])
        return np.asarray(rows, dtype=np.float64)


class ModelRetriever:
    def __init__(self, docs):
        self.model = KeywordModel()
        self.corpus = list(docs)
        self.embeddings = self.model.encode(docs)

    def add_documents(self, documents):
        self.corpus.extend(documents)
        self.embeddings = np.vstack([self.embeddings, self.model.encode(documents)])

    def search(self, query, k=5):
        q = self.model.encode([query])[0]
        e = self.embeddings
        sims = e @ q / (np.linalg.norm(e, axis=1) * np.linalg.norm(q))
        return np.argsort(sims)[-k:][::-1]


def mode_system():
    notes = [
        make_note("Speaker Annasays : art show in August", links=[3]),   # 0, source
        make_note("Speaker Bensays : my dog is sick", links=[]),         # 1
        make_note("Speaker Annasays : art show is coming", links=[]),    # 2, source
        make_note("Speaker Bensays : nice chat", links=[0]),              # 3, links to a source
    ]
    system = RobustAgenticMemorySystem.__new__(RobustAgenticMemorySystem)
    system.memories = {n.id: n for n in notes}
    system.retriever = ModelRetriever([n.content for n in notes])
    apply_consolidation(system, [0, 2], "Anna has an art show in August")  # becomes note 4
    return system


def context_order(system, query, k=2):
    rendered = system.find_related_memories_raw(query, k=k)
    contents = [n.content for n in system.memories.values()]
    lines = [line.split("memory content: ")[1].split("memory context: ")[0] for line in rendered.splitlines()]
    return [contents.index(line) for line in lines]


def test_off_mode_ignores_consolidated_notes_and_restores_state():
    system = mode_system()
    system.consolidation_mode = "off"
    order = context_order(system, "art", k=2)
    assert 4 not in order and order[0] in (0, 2)
    assert len(system.memories) == 5 and system.retriever.embeddings.shape[0] == 5


def test_add_only_lets_everything_compete():
    system = mode_system()
    system.consolidation_mode = "add_only"
    assert system.retrievable_indices() == [0, 1, 2, 3, 4]


def test_primary_hides_sources_and_redirects_links():
    system = mode_system()
    system.consolidation_mode = "primary"
    assert system.retrievable_indices() == [1, 3, 4]
    assert system.search_retrievable("art", 1) == [4]
    assert system.context_neighbors(4) == []       # its sources are archived: not expanded
    assert system.context_neighbors(3) == [4]      # link to source 0 now points to note 4
    assert 0 not in context_order(system, "art chat", k=3)
    assert 2 not in context_order(system, "art chat", k=3)


def test_primary_expand_brings_sources_with_consolidated_note():
    system = mode_system()
    system.consolidation_mode = "primary_expand"
    assert system.search_retrievable("art", 1) == [4]
    assert context_order(system, "art", k=1)[:3] == [4, 0, 2]


def test_unknown_mode_raises():
    system = mode_system()
    system.consolidation_mode = "bogus"
    with pytest.raises(ValueError):
        system.find_related_memories_raw("art", k=1)


# ---------------------------------------------------------------------------
# Fixes for consolidated notes crowding the top-k
# ---------------------------------------------------------------------------

def test_small_talk_summaries_can_be_hidden():
    system = mode_system()
    system.consolidation_mode = "primary_expand"
    list(system.memories.values())[4].consolidation_label = "SMALL_TALK"
    assert 4 in system.retrievable_indices()
    system.hide_small_talk_summaries = True
    assert 4 not in system.retrievable_indices()


def test_cap_limits_consolidated_notes_in_top_k():
    system = mode_system()
    system.consolidation_mode = "add_only"
    assert 4 in system.search_retrievable("art", 5)
    system.consolidated_top_k_cap = 0
    assert 4 not in system.search_retrievable("art", 5)
    system.consolidated_top_k_cap = 1
    assert 4 in system.search_retrievable("art", 5)


def test_penalty_moves_consolidated_note_down():
    system = mode_system()
    system.consolidation_mode = "add_only"
    first = system.search_retrievable("art", 5)
    system.consolidated_score_penalty = 5.0
    assert system.search_retrievable("art", 5)[-1] == 4
    assert first != system.search_retrievable("art", 5)


def test_defaults_leave_search_unchanged():
    system = mode_system()
    system.consolidation_mode = "add_only"
    before = system.search_retrievable("art chat", 5)
    system.consolidated_score_penalty = 0.0
    system.consolidated_top_k_cap = None
    assert system.search_retrievable("art chat", 5) == before


def test_reembed_and_labels():
    from memory_consolidation import attach_labels_from_log, consolidated_embedding_text, reembed_consolidated_notes
    system = mode_system()
    raw_rows = system.retriever.embeddings[:4].copy()
    note = list(system.memories.values())[4]
    assert consolidated_embedding_text(note, "content") == note.content
    assert reembed_consolidated_notes(system, "content") == 1
    np.testing.assert_array_equal(system.retriever.embeddings[:4], raw_rows)
    assert system.retriever.corpus[4] == note.content
    log = {"groups": [{"outcome": "merged", "consolidated_index": 4, "label": "SAME_FACT"},
                      {"outcome": "kept_separate", "label": "DIFFERENT"}]}
    assert attach_labels_from_log(system, log) == 1
    assert note.consolidation_label == "SAME_FACT"
