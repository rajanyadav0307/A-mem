"""SentenceTransformer loader (A-MEM paper Sec. 4.2) with optional offline fallbacks.

Paper baseline uses ``all-MiniLM-L6-v2`` and does **not** use a hash encoder.
Set ``TMEM_PAPER_ALIGNED_AMEM=1`` (or ``TMemConfig.paper_aligned_amem=True``) to
require SentenceTransformer only — same embedding method as the original paper.

Environment variables
---------------------
``TMEM_PAPER_ALIGNED_AMEM=1``
    Paper-aligned A-MEM: load ``all-MiniLM-L6-v2`` (or ``TMEM_LOCAL_MODEL_PATH``) only;
    **no** hash fallback. Fails if weights are unavailable.

``TMEM_ALLOW_HASH_ENCODER=1``
    Force the hash encoder (ignored when paper-aligned mode is on).

``TMEM_LOCAL_MODEL_PATH=/path/to/all-MiniLM-L6-v2``
    Offline directory with model files (after a one-time download elsewhere).

``TMEM_STRICT=1``
    When not in paper-aligned mode: do not auto-fall back to hash on hub errors.

``HF_HOME`` / ``TRANSFORMERS_CACHE`` / ``SENTENCE_TRANSFORMERS_HOME``
    Hugging Face caches; with a populated cache, ``HF_HUB_OFFLINE=1`` can work without network.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from typing import List, Sequence, Union

import numpy as np


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


class HashTextEncoder:
    """384-D bag-of-character-ngram embeddings; L2-normalized (not in A-MEM paper)."""

    dim = 384

    def __init__(self, dim: int = 384, ngram: int = 3, seed: int = 42):
        self.dim = dim
        self.ngram = ngram
        rng = np.random.default_rng(seed)
        self._proj = rng.standard_normal((dim, 256)).astype(np.float32)

    def _vector(self, text: str) -> np.ndarray:
        t = re.sub(r"\s+", " ", text.lower()).strip()
        counts = np.zeros(256, dtype=np.float32)
        if len(t) < self.ngram:
            h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % 256
            counts[h] = 1.0
        else:
            for i in range(len(t) - self.ngram + 1):
                ng = t[i : i + self.ngram]
                h = int(hashlib.md5(ng.encode("utf-8")).hexdigest(), 16) % 256
                counts[h] += 1.0 + 0.25 * len(ng)
        v = self._proj @ counts
        n = np.linalg.norm(v) + 1e-12
        return (v / n).astype(np.float32)

    def encode(
        self,
        sentences: Union[str, Sequence[str]],
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
        **kwargs,
    ) -> np.ndarray:
        if isinstance(sentences, str):
            sentences = [sentences]
        rows = [self._vector(s) for s in sentences]
        return np.stack(rows, axis=0)


def _warn_hash_fallback(model_name: str, err: BaseException) -> None:
    msg = (
        "\n"
        "======================================================================\n"
        "T-MEM: Could not load SentenceTransformer model.\n"
        f"  Requested: {model_name!r}\n"
        f"  Reason: {type(err).__name__}: {err}\n"
        "\n"
        "  Using the built-in HASH encoder for this run (pipeline only; not for\n"
        "  paper-reported embedding similarity).\n"
        "\n"
        "  For A-MEM–aligned runs (original paper methods), set:\n"
        "        export TMEM_PAPER_ALIGNED_AMEM=1\n"
        "    and ensure all-MiniLM-L6-v2 is cached or set TMEM_LOCAL_MODEL_PATH.\n"
        "\n"
        "  To force the hash encoder:  export TMEM_ALLOW_HASH_ENCODER=1\n"
        "  To fail fast:                export TMEM_STRICT=1\n"
        "======================================================================\n"
    )
    print(msg, file=sys.stderr)


def load_encoder(model_name: str, *, paper_aligned: bool = False):
    """Return an object with ``.encode(texts) -> ndarray`` (SentenceTransformer API).

    ``paper_aligned``: if True, only ``SentenceTransformer`` is allowed (A-MEM paper Sec. 4.2).
    """
    paper = paper_aligned or _env_truthy("TMEM_PAPER_ALIGNED_AMEM")

    if paper and _env_truthy("TMEM_ALLOW_HASH_ENCODER"):
        print(
            "T-MEM: TMEM_PAPER_ALIGNED_AMEM is set — ignoring TMEM_ALLOW_HASH_ENCODER "
            "(paper methods require SentenceTransformer).",
            file=sys.stderr,
        )

    if not paper and _env_truthy("TMEM_ALLOW_HASH_ENCODER"):
        return HashTextEncoder()

    from sentence_transformers import SentenceTransformer

    local = os.environ.get("TMEM_LOCAL_MODEL_PATH", "").strip()
    candidates: list[str] = []
    if local:
        candidates.append(local)
    candidates.append(model_name)

    last_err: BaseException | None = None
    for path in candidates:
        try:
            return SentenceTransformer(path)
        except BaseException as e:
            last_err = e
            continue

    if last_err is None:
        last_err = RuntimeError("No model path candidates")

    if paper:
        raise RuntimeError(
            "Paper-aligned A-MEM mode requires SentenceTransformer('all-MiniLM-L6-v2') "
            "or TMEM_LOCAL_MODEL_PATH to a local copy. Hash encoder is disabled.\n"
            f"Last error: {last_err}"
        ) from last_err

    if _env_truthy("TMEM_STRICT"):
        raise last_err

    _warn_hash_fallback(model_name, last_err)
    return HashTextEncoder()
