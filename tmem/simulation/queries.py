"""Evaluation queries mapped to LoCoMo-style categories (A-MEM paper Sec. 4.1).

Each query lists ``correct_note_ids`` (acceptable ground-truth memories).
Ranking metrics use the best (minimum) rank among those ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EvalQuery:
    """Single test query with category label and ground-truth note ids."""

    query_id: str
    text: str
    category: str  # temporal | multi_hop | adversarial | single_hop | open_domain
    correct_note_ids: List[str]
    description: str


def all_eval_queries() -> List[EvalQuery]:
    return [
        EvalQuery(
            query_id="q_temporal_work",
            text="Where does Alice currently work?",
            category="temporal",
            correct_note_ids=["s08_n1"],
            description="Recent Meta employment should outrank older Google memories.",
        ),
        EvalQuery(
            query_id="q_temporal_home",
            text="Where does Alice live now?",
            category="temporal",
            correct_note_ids=["s09_n1", "s10_n1"],
            description="Seattle / recent relocation should outrank Brooklyn NYC note.",
        ),
        EvalQuery(
            query_id="q_multi_hop_hobby",
            text="What hobby did Alice pick up after she moved to Seattle?",
            category="multi_hop",
            correct_note_ids=["s10_n2", "s09_n2"],
            description="Connect relocation (Seattle) with post-move hobby continuation.",
        ),
        EvalQuery(
            query_id="q_adv_google",
            text="Does Alice still work at Google?",
            category="adversarial",
            correct_note_ids=["s08_n1"],
            description="Outdated Google memories should rank below Meta resignation note.",
        ),
        EvalQuery(
            query_id="q_adv_nyc",
            text="Is Alice still living in NYC?",
            category="adversarial",
            correct_note_ids=["s09_n1", "s09_n3"],
            description="Old NYC housing memory should be deprioritized vs Seattle move evidence.",
        ),
        EvalQuery(
            query_id="q_single_camera",
            text="What camera does Alice use?",
            category="single_hop",
            correct_note_ids=["s03_n1", "s10_n2", "s09_n2"],
            description="Sony A7IV appears in gear and usage memories.",
        ),
        EvalQuery(
            query_id="q_open_japan",
            text="What did Alice and Bob plan to do in Japan?",
            category="open_domain",
            correct_note_ids=["s06_n1", "s07_n1", "s06_n3"],
            description="Trip planning spread across linked session 6–7 notes.",
        ),
    ]


def categories_in_order() -> List[str]:
    return ["temporal", "multi_hop", "adversarial", "single_hop", "open_domain"]
