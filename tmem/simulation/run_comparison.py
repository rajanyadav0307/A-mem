"""Run A-MEM (α=1 cosine) vs T-MEM (blended) retrieval side-by-side."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from tmem.config import TMemConfig, merge_env_into_config
from tmem.encoder import load_encoder
from tmem.memory_note import MemoryNote
from tmem.retrieval import (
    amem_retrieve,
    best_target_rank,
    full_score_breakdown,
    tmem_retrieve,
)
from tmem.temporal_scoring import max_link_degree

from simulation.memory_bank import build_memory_bank
from simulation.queries import EvalQuery, all_eval_queries, categories_in_order


def _full_ranking_ids(
    query_emb: np.ndarray,
    notes: List[MemoryNote],
    *,
    mode: str,
    t_current,
    cfg: TMemConfig,
) -> List[str]:
    if mode == "amem":
        ranked = amem_retrieve(query_emb, notes, k=len(notes))
    else:
        ranked = tmem_retrieve(query_emb, notes, k=len(notes), t_current=t_current, cfg=cfg)
    return [n.id for n, _ in ranked]


def best_rank(ordered_ids: List[str], targets: List[str]) -> int:
    return best_target_rank(ordered_ids, targets)


def row_for_query(
    eq: EvalQuery,
    notes: List[MemoryNote],
    model,
    t_current,
    cfg_tmem: TMemConfig,
) -> Dict[str, Any]:
    """Build one CSV row plus console payload with score breakdown for ground-truth note."""
    q_emb = model.encode(eq.text, convert_to_numpy=True)
    q_emb = np.asarray(q_emb, dtype=np.float32)

    amem_ids = _full_ranking_ids(q_emb, notes, mode="amem", t_current=t_current, cfg=cfg_tmem)
    tmem_ids = _full_ranking_ids(q_emb, notes, mode="tmem", t_current=t_current, cfg=cfg_tmem)

    ra = best_rank(amem_ids, eq.correct_note_ids)
    rt = best_rank(tmem_ids, eq.correct_note_ids)
    delta = ra - rt  # positive => T-MEM improved (lower rank is better)

    if delta > 0:
        moved = "improved"
    elif delta < 0:
        moved = "worse"
    else:
        moved = "same"

    # Pick primary ground-truth id = best under T-MEM ranking among targets
    primary = eq.correct_note_ids[0]
    best_t = len(notes) + 1
    for tid in eq.correct_note_ids:
        pos = tmem_ids.index(tid) + 1 if tid in tmem_ids else len(notes) + 1
        if pos < best_t:
            best_t = pos
            primary = tid

    idx = next(i for i, n in enumerate(notes) if n.id == primary)
    ml = max_link_degree(notes)
    cos_arr, d_arr, rf_arr, lb_arr, r_raw, r_hat, blended = full_score_breakdown(
        q_emb, notes, t_current, cfg_tmem, max_links=ml
    )

    return {
        "query_id": eq.query_id,
        "query_text": eq.text,
        "category": eq.category,
        "ground_truth_ids": ";".join(eq.correct_note_ids),
        "primary_ground_truth_id": primary,
        "amem_rank": ra,
        "tmem_rank": rt,
        "rank_delta_amem_minus_tmem": delta,
        "movement_vs_amem": moved,
        "amem_top1_id": amem_ids[0] if amem_ids else "",
        "tmem_top1_id": tmem_ids[0] if tmem_ids else "",
        "gt_cosine_similarity": float(cos_arr[idx]),
        "gt_decay": float(d_arr[idx]),
        "gt_reinforce": float(rf_arr[idx]),
        "gt_link_bonus": float(lb_arr[idx]),
        "gt_r_raw": float(r_raw[idx]),
        "gt_r_hat": float(r_hat[idx]),
        "gt_tmem_blended_score": float(blended[idx]),
    }


def category_accuracy_stats(
    results: List[Dict[str, Any]],
) -> Tuple[Dict[str, Tuple[float, float, float, float]], Dict[str, int]]:
    """Per category: (amem_top1_acc, tmem_top1_acc, amem_top3_acc, tmem_top3_acc), counts."""
    from collections import defaultdict

    by_cat: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)

    stats = {}
    counts = {}
    for cat in categories_in_order():
        rows = by_cat.get(cat, [])
        counts[cat] = len(rows)
        if not rows:
            stats[cat] = (0.0, 0.0, 0.0, 0.0)
            continue

        def acc_at(k: int, key_rank: str) -> float:
            return sum(1 for x in rows if 0 < x[key_rank] <= k) / len(rows)

        a1 = acc_at(1, "amem_rank")
        t1 = acc_at(1, "tmem_rank")
        a3 = acc_at(3, "amem_rank")
        t3 = acc_at(3, "tmem_rank")
        stats[cat] = (a1, t1, a3, t3)
    return stats, counts


def run_full_comparison(
    results_dir: str,
    *,
    encoder_model: str | None = None,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]], TMemConfig, List[MemoryNote], Any, Any]:
    os.makedirs(results_dir, exist_ok=True)
    cfg = merge_env_into_config(TMemConfig(encoder_model=encoder_model or "all-MiniLM-L6-v2"))
    model = load_encoder(cfg.encoder_model, paper_aligned=cfg.paper_aligned_amem)
    notes, t_current = build_memory_bank(model, cfg)

    rows: List[Dict[str, Any]] = []
    for eq in all_eval_queries():
        rows.append(row_for_query(eq, notes, model, t_current, cfg))

    df = pd.DataFrame(rows)
    csv_path = os.path.join(results_dir, "comparison_table.csv")
    df.to_csv(csv_path, index=False)
    return df, rows, cfg, notes, t_current, model
