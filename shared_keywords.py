"""Shared search words for the evaluators (optional ``--keywords_file``).

A-MEM turns each question into search words with one LLM call
(``generate_query_llm``). When several setups are compared on the same input,
that call is made once per question per run and saved, and every setup reads
the same words from the file. Without a file, the evaluators behave exactly as
before.

File format::

    {"seed": 42, "model": "...", "made_with": "<git commit>",
     "keywords": {"<sample index>:<question index>": "<search words>"}}

The question index is the position of the question in ``sample.qa``.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Dict, Optional


def keyword_key(sample_idx: int, question_idx: int) -> str:
    return f"{int(sample_idx)}:{int(question_idx)}"


def load_keywords_file(path: Optional[str]) -> Optional[Dict]:
    """Load and validate a keywords file. Returns None when no path is given."""
    if not path:
        return None
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    table = data.get("keywords")
    if not isinstance(table, dict) or not table:
        raise ValueError(f"keywords file {path} has no 'keywords' table")
    empty = [k for k, v in table.items() if not isinstance(v, str) or not v.strip()]
    if empty:
        raise ValueError(f"keywords file {path} has {len(empty)} empty entries, e.g. {empty[:3]}")
    with open(path, "rb") as handle:
        data["sha256"] = hashlib.sha256(handle.read()).hexdigest()
    data["path"] = path
    return data


def trap_draw(seed: int, sample_idx: int, question_idx: int) -> float:
    """Number in [0, 1) that fixes the answer order of one trap (category 5) question.

    Used with --trap_order per_question: the order depends only on the seed and
    the question, so API retries (whose jitter draws from Python's shared random
    generator) cannot shift it, and every setup sees the same order. Below 0.5
    puts "Not mentioned in the conversation" first, as in the evaluators.
    """
    return random.Random(f"{int(seed)}:{int(sample_idx)}:{int(question_idx)}").random()


def lookup_keywords(shared: Dict, sample_idx: int, question_idx: int) -> str:
    """Search words for one question; a missing entry stops the run."""
    key = keyword_key(sample_idx, question_idx)
    try:
        return shared["keywords"][key]
    except KeyError:
        raise KeyError(f"no search words for question {key} in {shared.get('path')}") from None
