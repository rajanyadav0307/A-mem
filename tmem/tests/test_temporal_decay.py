"""Unit checks for temporal decay (extension on A-MEM cosine retrieval)."""

from __future__ import annotations

import math
import unittest
from datetime import datetime, timedelta

from tmem.config import TMemConfig
from tmem.memory_note import MemoryNote
from tmem.temporal_scoring import compute_relevance, decay


def _note(ts: datetime) -> MemoryNote:
    return MemoryNote(
        id="n1",
        content="c",
        timestamp=ts,
        keywords=["k"],
        tags=["t"],
        context="ctx",
        links=[],
        access_count=99,
    )


class TestDecay(unittest.TestCase):
    def test_future_note_no_penalty(self) -> None:
        t_i = datetime(2025, 6, 1)
        t_now = datetime(2025, 1, 1)
        n = _note(t_i)
        self.assertEqual(decay(n, t_now, 1.0, "days"), 1.0)

    def test_monotone_in_age(self) -> None:
        t0 = datetime(2025, 1, 1)
        lam = 0.1
        d0 = decay(_note(t0), t0, lam, "days")
        self.assertAlmostEqual(d0, 1.0, places=6)
        d30 = decay(_note(t0), t0 + timedelta(days=30), lam, "days")
        self.assertLess(d30, d0)
        d60 = decay(_note(t0), t0 + timedelta(days=60), lam, "days")
        self.assertLess(d60, d30)

    def test_exp_law_days(self) -> None:
        t0 = datetime(2025, 1, 1)
        n = _note(t0)
        tq = t0 + timedelta(days=10)
        lam = 0.2
        self.assertAlmostEqual(decay(n, tq, lam, "days"), math.exp(-lam * 10.0), places=9)

    def test_months_equiv_scale(self) -> None:
        t0 = datetime(2025, 1, 1)
        n = _note(t0)
        tq = t0 + timedelta(days=30)
        lam = 0.1
        d_month = decay(n, tq, lam, "months_equiv")
        d_day = decay(n, tq, lam, "days")
        self.assertAlmostEqual(d_month, math.exp(-0.1 * 1.0), places=6)
        self.assertNotAlmostEqual(d_month, d_day, places=2)

    def test_decay_only_neutralizes_access_and_links(self) -> None:
        t0 = datetime(2025, 1, 1)
        n = _note(t0)
        n.links = ["a", "b", "c"]
        tq = t0 + timedelta(days=5)
        r, d, rf, lb = compute_relevance(n, tq, 0.1, 0.5, 0.3, max_links=3, decay_age_unit="days", decay_only=True)
        self.assertEqual(rf, 1.0)
        self.assertEqual(lb, 1.0)
        self.assertEqual(r, d)

    def test_full_mode_uses_access_and_links(self) -> None:
        t0 = datetime(2025, 1, 1)
        n = _note(t0)
        n.links = ["a"]
        tq = t0 + timedelta(days=5)
        r, d, rf, lb = compute_relevance(n, tq, 0.1, 0.5, 0.3, max_links=2, decay_age_unit="days", decay_only=False)
        self.assertGreater(rf, 1.0)
        self.assertGreater(lb, 1.0)
        self.assertAlmostEqual(r, d * rf * lb, places=9)

    def test_config_decay_only_flag(self) -> None:
        cfg = TMemConfig(use_decay_only_temporal=True)
        n = _note(datetime(2025, 1, 1))
        tq = datetime(2025, 1, 20)
        r, d, rf, lb = compute_relevance(
            n,
            tq,
            cfg.decay_lambda,
            cfg.reinforce_beta,
            cfg.link_gamma,
            1,
            decay_age_unit=cfg.decay_age_unit,
            decay_only=cfg.use_decay_only_temporal,
        )
        self.assertEqual(r, d)
        self.assertEqual(rf, 1.0)


if __name__ == "__main__":
    unittest.main()
