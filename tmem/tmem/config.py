"""Hyperparameters for T-MEM temporal relevance (thesis Module 1).

Defaults match the specification: λ, β, γ for r_i components; α blends
cosine similarity (A-MEM Eq. 9) with normalized temporal relevance.
When α = 1.0, retrieval reduces exactly to A-MEM's pure cosine ranking.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


@dataclass
class TMemConfig:
    """T-MEM hyperparameters (decay, reinforcement, link density, blend)."""

    # When True (or env TMEM_PAPER_ALIGNED_AMEM=1): require A-MEM paper encoder only
    # (all-MiniLM-L6-v2, Sec. 4.2); no hash fallback — matches original embedding pipeline.
    paper_aligned_amem: bool = False

    # λ: decay rate in exp(-λ × age) — age unit set by decay_age_unit (T-MEM extension; not in A-MEM)
    decay_lambda: float = 0.1
    # "months_equiv" = (t_now−t_i) in days / 30 (stable for long banks). "days" = literal day count.
    decay_age_unit: str = "months_equiv"
    # If True: r_i = decay only (reinforce and link_bonus fixed at 1). Matches "temporal decay only"
    # on top of A-MEM; set False for full r_i = decay × reinforce × link_bonus.
    use_decay_only_temporal: bool = True
    # β: weight on log access reinforcement (spacing / usage boost); ignored when use_decay_only_temporal
    reinforce_beta: float = 0.5
    # γ: weight on normalized link count in link_bonus; ignored when use_decay_only_temporal
    link_gamma: float = 0.3
    # α: weight on cosine similarity vs (1-α) on normalized r_i (modified Eq. 9)
    blend_alpha: float = 0.7

    # SentenceTransformer model name (A-MEM paper Sec. 4.2)
    encoder_model: str = "all-MiniLM-L6-v2"

    # Auto-link threshold when simulating LLM link generation (cosine on embeddings)
    auto_link_cosine_threshold: float = 0.5

    # Default k for "top-k" access tracking updates
    default_top_k: int = 10


def merge_env_into_config(cfg: TMemConfig) -> TMemConfig:
    """Apply TMEM_PAPER_ALIGNED_AMEM=1 when set (OR with cfg.paper_aligned_amem)."""
    from dataclasses import replace

    paper = cfg.paper_aligned_amem or _env_truthy("TMEM_PAPER_ALIGNED_AMEM")
    return replace(cfg, paper_aligned_amem=paper)
