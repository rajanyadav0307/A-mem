"""
Temporal-aware robust memory layer for benchmarking T-MEM against A-MEM.

This layer reuses the robust A-MEM note construction and memory evolution
pipeline unchanged, and swaps only the query-time retrieval ranking:

    A-MEM: score = cosine(query, memory)
    T-MEM: score = alpha * cosine + (1 - alpha) * normalized_temporal_relevance

The default temporal relevance matches the current thesis prototype:
decay-only scoring using note timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import math
from typing import List, Optional, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from memory_layer_robust import RobustAgenticMemorySystem, RobustMemoryNote

logger = logging.getLogger("tmem_robust")


_TIMESTAMP_FORMATS = (
    "%I:%M %p on %d %B, %Y",
    "%I:%M %p on %d %b, %Y",
    "%Y%m%d%H%M",
    "%Y-%m-%d %H:%M:%S",
)


def _parse_timestamp(value: str) -> datetime:
    """Parse timestamps used by LoCoMo and cached memory notes."""
    if not value:
        raise ValueError("empty timestamp")
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"unsupported timestamp format: {value!r}")


def _min_max_normalize(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    lo = float(np.min(values))
    hi = float(np.max(values))
    if hi - lo < 1e-12:
        return np.full_like(values, 0.5)
    return (values - lo) / (hi - lo)


@dataclass
class TemporalRetrievalConfig:
    """Temporal scoring configuration for T-MEM benchmark runs."""

    decay_lambda: float = 0.1
    blend_alpha: float = 0.9
    decay_age_unit: str = "months_equiv"
    use_decay_only_temporal: bool = True
    reinforce_beta: float = 0.5
    link_gamma: float = 0.3
    update_access_stats: bool = False
    candidate_pool_size: int = 20
    semantic_anchor_count: int = 2
    semantic_margin_to_skip_temporal: float = 0.05
    temporal_score_floor: float = 0.25
    temporal_categories: tuple[int, ...] = (2,)


class TemporalAwareRobustAgenticMemorySystem(RobustAgenticMemorySystem):
    """
    Robust A-MEM system with temporal-aware query-time retrieval.

    Note construction, metadata generation, and memory evolution still come
    from the base robust A-MEM implementation. This keeps benchmark conditions
    aligned with the original work and isolates the retrieval change.
    """

    def __init__(
        self,
        *args,
        temporal_config: Optional[TemporalRetrievalConfig] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.temporal_config = temporal_config or TemporalRetrievalConfig()

    def _should_apply_temporal(
        self,
        question_category: Optional[int] = None,
    ) -> bool:
        """Apply temporal reranking only to configured question categories."""
        if question_category is None:
            return False
        return int(question_category) in set(self.temporal_config.temporal_categories)

    def _current_query_time(self, memories: List[RobustMemoryNote]) -> datetime:
        """
        Use the latest memory timestamp as the query-time reference.

        LoCoMo evaluation loads the full dialogue history before QA, so using the
        end of the conversation is a stable benchmark-time approximation.
        """
        parsed: List[datetime] = []
        for memory in memories:
            try:
                parsed.append(_parse_timestamp(memory.timestamp))
            except ValueError as exc:
                logger.warning("Could not parse memory timestamp %r: %s", memory.timestamp, exc)
        return max(parsed) if parsed else datetime.now()

    def _temporal_relevance(
        self,
        memory: RobustMemoryNote,
        t_current: datetime,
        max_links: int,
    ) -> float:
        cfg = self.temporal_config
        try:
            t_i = _parse_timestamp(memory.timestamp)
        except ValueError:
            # Fall back to neutral temporal weight if the timestamp is malformed.
            return 1.0

        delta = t_current - t_i
        days = max(delta.total_seconds() / 86400.0, 0.0)
        age = days if cfg.decay_age_unit == "days" else days / 30.0

        decay = math.exp(-cfg.decay_lambda * age)
        if cfg.use_decay_only_temporal:
            return decay

        reinforce = 1.0 + cfg.reinforce_beta * math.log1p(max(memory.retrieval_count, 0))
        link_bonus = 1.0 + cfg.link_gamma * (len(memory.links) / max(max_links, 1))
        return decay * reinforce * link_bonus

    def _semantic_scores(self, query: str, all_memories: List[RobustMemoryNote]) -> np.ndarray:
        """Compute semantic retrieval scores for all memories."""
        if self.retriever.embeddings is None or len(self.retriever.embeddings) != len(all_memories):
            logger.info("Retriever embeddings missing or stale; rebuilding from memory state")
            self.retriever = self.retriever.load_from_local_memory(self.memories, "all-MiniLM-L6-v2")

        query_embedding = self.retriever.model.encode([query])[0]
        return cosine_similarity([query_embedding], self.retriever.embeddings)[0]

    def _rank_memories_temporally(
        self,
        query: str,
        k: int,
    ) -> Tuple[List[int], np.ndarray]:
        """Return top-k indices using semantic-first temporal reranking."""
        if not self.memories:
            return [], np.array([], dtype=np.float64)

        all_memories = list(self.memories.values())
        semantic_scores = self._semantic_scores(query, all_memories)
        semantic_ranked = np.argsort(semantic_scores)[::-1]
        top_k = min(k, len(all_memories))

        if len(semantic_ranked) <= top_k:
            return semantic_ranked[:top_k].tolist(), semantic_scores

        if len(semantic_ranked) > 1:
            semantic_margin = float(
                semantic_scores[semantic_ranked[0]] - semantic_scores[semantic_ranked[1]]
            )
            if semantic_margin >= self.temporal_config.semantic_margin_to_skip_temporal:
                return semantic_ranked[:top_k].tolist(), semantic_scores

        candidate_pool_size = max(top_k, self.temporal_config.candidate_pool_size)
        candidate_pool_size = min(candidate_pool_size, len(all_memories))
        candidate_indices = semantic_ranked[:candidate_pool_size]

        t_current = self._current_query_time(all_memories)
        max_links = max((len(m.links) for m in all_memories), default=1)
        temporal_raw = np.array(
            [self._temporal_relevance(all_memories[idx], t_current, max_links) for idx in candidate_indices],
            dtype=np.float64,
        )
        temporal_norm = _min_max_normalize(temporal_raw)
        temporal_norm = (
            self.temporal_config.temporal_score_floor +
            (1.0 - self.temporal_config.temporal_score_floor) * temporal_norm
        )
        candidate_semantic = semantic_scores[candidate_indices]
        semantic_norm = _min_max_normalize(candidate_semantic)

        alpha = self.temporal_config.blend_alpha
        blended = alpha * semantic_norm + (1.0 - alpha) * temporal_norm
        reranked_candidate_positions = np.argsort(blended)[::-1]
        reranked_candidates = candidate_indices[reranked_candidate_positions].tolist()

        anchor_count = min(self.temporal_config.semantic_anchor_count, top_k)
        anchored = semantic_ranked[:anchor_count].tolist()
        anchor_set = set(anchored)
        final_ranked = anchored + [idx for idx in reranked_candidates if idx not in anchor_set]
        ranked_indices = final_ranked[:top_k]

        if self.temporal_config.update_access_stats:
            stamp = t_current.strftime("%Y%m%d%H%M")
            for idx in ranked_indices:
                memory = all_memories[idx]
                memory.retrieval_count += 1
                memory.last_accessed = stamp

        return ranked_indices, semantic_scores

    def find_related_memories_raw(
        self,
        query: str,
        k: int = 5,
        question_category: Optional[int] = None,
    ) -> str:
        """Find related memories using temporal-aware retrieval plus A-MEM neighbor expansion."""
        if not self.memories:
            return ""

        if not self._should_apply_temporal(question_category):
            return super().find_related_memories_raw(query, k=k)

        indices, _ = self._rank_memories_temporally(query, k)
        all_memories = list(self.memories.values())
        memory_str = ""

        for i in indices:
            j = 0
            memory_str += (
                "talk start time:" + all_memories[i].timestamp +
                "memory content: " + all_memories[i].content +
                "memory context: " + all_memories[i].context +
                "memory keywords: " + str(all_memories[i].keywords) +
                "memory tags: " + str(all_memories[i].tags) + "\n"
            )
            neighborhood = all_memories[i].links
            for neighbor in neighborhood:
                if neighbor >= len(all_memories):
                    continue
                memory_str += (
                    "talk start time:" + all_memories[neighbor].timestamp +
                    "memory content: " + all_memories[neighbor].content +
                    "memory context: " + all_memories[neighbor].context +
                    "memory keywords: " + str(all_memories[neighbor].keywords) +
                    "memory tags: " + str(all_memories[neighbor].tags) + "\n"
                )
                if j >= k:
                    break
                j += 1

        return memory_str
