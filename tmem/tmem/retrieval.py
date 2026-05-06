"""A-MEM vs T-MEM retrieval.

A-MEM Eq. 9 (cosine only): rank by s_{q,i} = cos(e_q, e_i).
T-MEM (default) uses temporal decay only for r_i: r_i = decay(m_i); then
    score(q, m_i) = α × cos(e_q, e_i) + (1 - α) × r̂_i
where r̂_i is min-max normalized r_i over all memories in M.
With ``use_decay_only_temporal=False``, r_i = decay × reinforce × link_bonus instead.

When α = 1.0, this is identical to A-MEM.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from tmem.config import TMemConfig
from tmem.memory_note import MemoryNote
from tmem.temporal_scoring import compute_relevance, max_link_degree, min_max_normalize


def cosine_similarities(query_emb: np.ndarray, note_embs: np.ndarray) -> np.ndarray:
    """Cos(e_q, e_i) for each row in note_embs (Eq. 9 in paper)."""
    q = np.asarray(query_emb, dtype=np.float64).ravel()
    m = np.asarray(note_embs, dtype=np.float64)
    qn = np.linalg.norm(q) + 1e-12
    mn = np.linalg.norm(m, axis=1, keepdims=True) + 1e-12
    return (m @ q) / (mn.ravel() * qn)


@dataclass
class RetrievalHit:
    """One ranked memory with diagnostic scores."""

    note_id: str
    rank: int
    cosine: float
    decay: float
    reinforce: float
    link_bonus: float
    r_raw: float
    r_hat: float
    amem_score: float
    tmem_score: float


def _note_index_map(notes: List[MemoryNote]) -> Dict[str, int]:
    return {n.id: i for i, n in enumerate(notes)}


def amem_retrieve(
    query_embedding: np.ndarray,
    notes: List[MemoryNote],
    k: int,
) -> List[Tuple[MemoryNote, float]]:
    """Pure cosine ranking (A-MEM Eq. 9). Returns (note, cosine) descending."""
    if not notes:
        return []
    embs = np.stack([n.embedding for n in notes], axis=0)
    sims = cosine_similarities(query_embedding, embs)
    order = np.argsort(-sims)
    out: List[Tuple[MemoryNote, float]] = []
    for idx in order[:k]:
        i = int(idx)
        out.append((notes[i], float(sims[i])))
    return out


def tmem_retrieve(
    query_embedding: np.ndarray,
    notes: List[MemoryNote],
    k: int,
    t_current: datetime,
    cfg: TMemConfig,
    max_links: Optional[int] = None,
) -> List[Tuple[MemoryNote, float]]:
    """Blended ranking: α cos + (1-α) r̂ (modified Eq. 9)."""
    if not notes:
        return []
    ml = max_links if max_links is not None else max_link_degree(notes)
    embs = np.stack([n.embedding for n in notes], axis=0)
    cos = cosine_similarities(query_embedding, embs)

    r_raw = np.zeros(len(notes), dtype=np.float64)
    for i, n in enumerate(notes):
        r_raw[i], _, _, _ = compute_relevance(
            n,
            t_current,
            cfg.decay_lambda,
            cfg.reinforce_beta,
            cfg.link_gamma,
            ml,
            decay_age_unit=cfg.decay_age_unit,
            decay_only=cfg.use_decay_only_temporal,
        )
    r_hat = min_max_normalize(r_raw)

    alpha = cfg.blend_alpha
    blended = alpha * cos + (1.0 - alpha) * r_hat
    order = np.argsort(-blended)
    out: List[Tuple[MemoryNote, float]] = []
    for idx in order[:k]:
        i = int(idx)
        out.append((notes[i], float(blended[i])))
    return out


def apply_access_updates(
    notes: List[MemoryNote],
    retrieved_ids: List[str],
    t_access: datetime,
    id_getter: Callable[[MemoryNote], str] = lambda n: n.id,
) -> None:
    """Increment access_count and last_accessed for each id in retrieved_ids."""
    by_id = {id_getter(n): n for n in notes}
    for rid in retrieved_ids:
        n = by_id.get(rid)
        if n is None:
            continue
        n.access_count += 1
        n.last_accessed = t_access


def retrieve_with_access_tracking(
    query_embedding: np.ndarray,
    notes: List[MemoryNote],
    k: int,
    t_current: datetime,
    cfg: TMemConfig,
    *,
    use_tmem: bool,
    update_access: bool = True,
) -> List[Tuple[MemoryNote, float]]:
    """Retrieve with optional T-MEM scoring and top-k access bookkeeping."""
    if use_tmem:
        ranked = tmem_retrieve(query_embedding, notes, k, t_current, cfg)
    else:
        ranked = amem_retrieve(query_embedding, notes, k)
    if update_access:
        apply_access_updates(notes, [n.id for n, _ in ranked], t_current)
    return ranked


def full_score_breakdown(
    query_embedding: np.ndarray,
    notes: List[MemoryNote],
    t_current: datetime,
    cfg: TMemConfig,
    max_links: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Arrays aligned with ``notes``: cos, decay, reinforce, link_bonus, r_raw, r_hat, tmem_blended."""
    ml = max_links if max_links is not None else max_link_degree(notes)
    embs = np.stack([n.embedding for n in notes], axis=0)
    cos = cosine_similarities(query_embedding, embs)
    d = np.zeros(len(notes))
    rf = np.zeros(len(notes))
    lb = np.zeros(len(notes))
    r_raw = np.zeros(len(notes))
    for i, n in enumerate(notes):
        r_raw[i], d[i], rf[i], lb[i] = compute_relevance(
            n,
            t_current,
            cfg.decay_lambda,
            cfg.reinforce_beta,
            cfg.link_gamma,
            ml,
            decay_age_unit=cfg.decay_age_unit,
            decay_only=cfg.use_decay_only_temporal,
        )
    r_hat = min_max_normalize(r_raw)
    alpha = cfg.blend_alpha
    blended = alpha * cos + (1.0 - alpha) * r_hat
    return cos, d, rf, lb, r_raw, r_hat, blended


def rank_of_target(
    ordered_ids: List[str],
    target_ids: List[str],
) -> int:
    """1-based rank of first target id in list; 0 if absent."""
    pos = {nid: i + 1 for i, nid in enumerate(ordered_ids)}
    for tid in target_ids:
        if tid in pos:
            return pos[tid]
    return 0


def best_target_rank(ordered_ids: List[str], target_ids: List[str]) -> int:
    """Best (minimum) 1-based rank among all targets; 0 if none appear."""
    pos = {nid: i + 1 for i, nid in enumerate(ordered_ids)}
    ranks = [pos[t] for t in target_ids if t in pos]
    return min(ranks) if ranks else 0
