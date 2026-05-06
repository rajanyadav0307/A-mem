"""Memory note structure aligned with A-MEM paper Eq. 1 plus T-MEM fields.

Paper: m_i = {c_i, t_i, K_i, G_i, X_i, e_i, L_i}
Embedding (Eq. 1–3): e_i = f_enc(concat(c_i, K_i, G_i, X_i)) with SentenceTransformers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import numpy as np


@dataclass
class MemoryNote:
    """Single memory unit: A-MEM Eq. 1 fields + T-MEM temporal metadata."""

    # c_i — original interaction content
    content: str
    # t_i — creation timestamp (used in decay; wall-clock age)
    timestamp: datetime
    # K_i — keywords; G_i — tags; X_i — one-sentence contextual description
    keywords: List[str]
    tags: List[str]
    context: str
    # L_i — linked memory IDs (structural neighborhood)
    links: List[str] = field(default_factory=list)
    # Stable id for bookkeeping (not in paper symbol list; required for L_i)
    id: str = ""

    # e_i — dense embedding of concat(c_i, K_i, G_i, X_i); filled by encoder
    embedding: Optional[np.ndarray] = None

    # T-MEM extensions
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    # Cached product r_i = decay × reinforce × link_bonus (optional cache)
    relevance_score: float = 0.0

    def embedding_input_text(self) -> str:
        """Text fed to f_enc per A-MEM paper (concat of c_i, K_i, G_i, X_i)."""
        kw = " ".join(self.keywords) if self.keywords else ""
        tg = " ".join(self.tags) if self.tags else ""
        return " ".join(
            part for part in (self.content, kw, tg, self.context) if part
        ).strip()
