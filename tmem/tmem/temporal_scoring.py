"""Temporal relevance for retrieval on top of A-MEM (cosine).

**Decay-only mode** (default in config): ``r_i = decay(m_i)`` with
``decay = exp(-λ × age)`` — the minimal temporal addition to the original work.

**Full mode** (optional): ``r_i = decay × reinforce × link_bonus`` when
``use_decay_only_temporal`` is False in ``TMemConfig``.

- decay: uses ``note.timestamp`` as ``t_i`` (memory creation time), not ``last_accessed``.
- age: see ``decay()`` — ``days`` or ``months_equiv`` per ``decay_age_unit``.

These feed the modified retrieval score (see retrieval.py) together with
cosine similarity from A-MEM Eq. 9.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING, Iterable, List, Tuple

import numpy as np

from tmem.memory_note import MemoryNote

if TYPE_CHECKING:
    from tmem.config import TMemConfig


def decay(
    note: MemoryNote,
    t_current: datetime,
    decay_lambda: float,
    age_unit: str = "months_equiv",
) -> float:
    """Exponential decay: exp(-λ × age).

    Uses creation time ``note.timestamp`` as ``t_i``. If ``t_current < t_i``,
    age is clamped to 0 so decay(·)=1 (no "future" penalty).

    ``age_unit``:
    - ``"days"`` — age = (t_current − t_i) in **full days** (86400-second buckets).
    - ``"months_equiv"`` — age = elapsed days / 30 (any other value falls back here).

    A-MEM (Xu et al.) does not define this; it is the temporal extension only.
    """
    delta = t_current - note.timestamp
    days = max(delta.total_seconds() / 86400.0, 0.0)
    if age_unit == "days":
        age = days
    else:
        age = days / 30.0
    return math.exp(-decay_lambda * age)


def reinforce(note: MemoryNote, beta: float) -> float:
    """Access-based boost: 1 + β × log(1 + access_count_i)."""
    return 1.0 + beta * math.log1p(max(note.access_count, 0))


def link_bonus(note: MemoryNote, gamma: float, max_links: int) -> float:
    """Structural boost from graph degree: 1 + γ × (|L_i| / max_links).

    ``max_links`` is max |L_j| over the memory bank (≥ 1 to avoid division by zero).
    """
    denom = max(max_links, 1)
    return 1.0 + gamma * (len(note.links) / denom)


def compute_relevance(
    note: MemoryNote,
    t_current: datetime,
    decay_lambda: float,
    beta: float,
    gamma: float,
    max_links: int,
    decay_age_unit: str = "months_equiv",
    decay_only: bool = False,
) -> Tuple[float, float, float, float]:
    """Return (r_i, decay_i, reinforce_i, link_bonus_i) for diagnostics.

    When ``decay_only`` is True, ``r_i = decay_i`` and reinforce/link factors
    are reported as 1.0 (they do not affect ``r_i`` or retrieval).
    """
    d = decay(note, t_current, decay_lambda, age_unit=decay_age_unit)
    if decay_only:
        return d, d, 1.0, 1.0
    rf = reinforce(note, beta)
    lb = link_bonus(note, gamma, max_links)
    r = d * rf * lb
    return r, d, rf, lb


def max_link_degree(notes: Iterable[MemoryNote]) -> int:
    """max_j |L_j| over the collection (for link_bonus normalization)."""
    return max((len(n.links) for n in notes), default=1)


def min_max_normalize(values: np.ndarray) -> np.ndarray:
    """Min-max normalize vector to [0, 1]; flat maps to 0.5."""
    v = np.asarray(values, dtype=np.float64)
    lo, hi = float(np.min(v)), float(np.max(v))
    if hi - lo < 1e-12:
        return np.full_like(v, 0.5)
    return (v - lo) / (hi - lo)


def relevance_vector(
    notes: List[MemoryNote],
    t_current: datetime,
    cfg: "TMemConfig",
    max_links: int | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute r_i and factor arrays for all notes (same order as ``notes``).

    Returns (r, decay, reinforce, link_bonus) as parallel vectors.
    """
    ml = max_links if max_links is not None else max_link_degree(notes)
    r_list: List[float] = []
    d_list: List[float] = []
    rf_list: List[float] = []
    lb_list: List[float] = []
    for n in notes:
        r, d, rf, lb = compute_relevance(
            n,
            t_current,
            cfg.decay_lambda,
            cfg.reinforce_beta,
            cfg.link_gamma,
            ml,
            decay_age_unit=cfg.decay_age_unit,
            decay_only=cfg.use_decay_only_temporal,
        )
        r_list.append(r)
        d_list.append(d)
        rf_list.append(rf)
        lb_list.append(lb)
    return (
        np.array(r_list, dtype=np.float64),
        np.array(d_list, dtype=np.float64),
        np.array(rf_list, dtype=np.float64),
        np.array(lb_list, dtype=np.float64),
    )
