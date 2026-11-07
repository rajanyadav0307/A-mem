"""Tests for the optional shared search words (--keywords_file)."""

import json
import os
import sys

import pytest

os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared_keywords import keyword_key, load_keywords_file, lookup_keywords  # noqa: E402


class _LLM:
    def __init__(self):
        self.prompts = []

    def get_completion(self, prompt, temperature=0.7):
        self.prompts.append(prompt)
        return "answer"


class _Controller:
    def __init__(self):
        self.llm = _LLM()


class _Memory:
    def __init__(self):
        self.queries = []
        self.llm_controller = _Controller()
        self.current_question = None

    def find_related_memories_raw(self, query, k=5, question_category=None):
        self.queries.append(query)
        return "context"


def _agent(module_name, class_name):
    module = __import__(module_name)
    cls = getattr(module, class_name)
    agent = cls.__new__(cls)
    agent.memory_system = _Memory()
    agent.retrieve_k = 10
    agent.temperature_c5 = 0.5
    agent.generated = []

    def fake_generate(question):
        agent.generated.append(question)
        return "generated words"

    agent.generate_query_llm = fake_generate
    return agent


AGENTS = [("test_advanced_robust", "RobustAdvancedMemAgent"), ("test_tmem_advanced_robust", "TMemAdvancedMemAgent")]


@pytest.mark.parametrize("module_name,class_name", AGENTS)
def test_without_file_the_agent_makes_its_own_words(module_name, class_name):
    agent = _agent(module_name, class_name)
    agent.answer_question("When did Jon open his studio?", 2, "x")
    assert agent.generated == ["When did Jon open his studio?"]
    assert agent.memory_system.queries == ["generated words"]


@pytest.mark.parametrize("module_name,class_name", AGENTS)
def test_shared_words_reach_the_lookup_and_no_words_are_generated(module_name, class_name):
    agent = _agent(module_name, class_name)
    agent.answer_question("When did Jon open his studio?", 2, "x", keywords="Jon, studio, opening")
    assert agent.generated == []
    assert agent.memory_system.queries == ["Jon, studio, opening"]
    assert agent.memory_system.current_question == "When did Jon open his studio?"


def _write(tmp_path, table):
    path = tmp_path / "kw.json"
    path.write_text(json.dumps({"seed": 42, "keywords": table}))
    return str(path)


def test_load_and_lookup(tmp_path):
    shared = load_keywords_file(_write(tmp_path, {"0:0": "a, b", "3:259": "c"}))
    assert lookup_keywords(shared, 0, 0) == "a, b"
    assert lookup_keywords(shared, 3, 259) == "c"
    assert len(shared["sha256"]) == 64
    assert keyword_key(3, 259) == "3:259"


def test_missing_entry_stops_the_run(tmp_path):
    shared = load_keywords_file(_write(tmp_path, {"0:0": "a"}))
    with pytest.raises(KeyError, match="0:1"):
        lookup_keywords(shared, 0, 1)


def test_empty_entries_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        load_keywords_file(_write(tmp_path, {"0:0": "a", "0:1": "  "}))


def test_no_file_means_no_shared_words():
    assert load_keywords_file(None) is None
