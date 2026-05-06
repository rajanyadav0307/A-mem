#!/usr/bin/env python3
"""T-MEM thesis demo: LoCoMo-style simulation, A-MEM vs T-MEM retrieval, figures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from simulation.queries import all_eval_queries
from simulation.run_comparison import (
    _full_ranking_ids,
    category_accuracy_stats,
    run_full_comparison,
)
from tmem.encoder import HashTextEncoder
from tmem.retrieval import amem_retrieve, full_score_breakdown, tmem_retrieve
from tmem.temporal_scoring import max_link_degree
from visualization.plots import generate_all_plots


def _print_query_details(notes, model, t_current, cfg) -> None:
    """Rich terminal output: top-5, components for ground-truth note."""
    ml = max_link_degree(notes)
    for eq in all_eval_queries():
        q_emb = np.asarray(model.encode(eq.text, convert_to_numpy=True), dtype=np.float32)
        amem_ids = _full_ranking_ids(q_emb, notes, mode="amem", t_current=t_current, cfg=cfg)
        tmem_ids = _full_ranking_ids(q_emb, notes, mode="tmem", t_current=t_current, cfg=cfg)
        ra = min((amem_ids.index(t) + 1 for t in eq.correct_note_ids if t in amem_ids), default=0)
        rt = min((tmem_ids.index(t) + 1 for t in eq.correct_note_ids if t in tmem_ids), default=0)
        delta = ra - rt
        move = "improved" if delta > 0 else ("worse" if delta < 0 else "same")

        print("\n" + "=" * 88)
        print(f"[{eq.category.upper()}] {eq.text}")
        print(f"Ground-truth ids: {eq.correct_note_ids}")
        print(f"A-MEM best rank: {ra}  |  T-MEM best rank: {rt}  |  Δ (A−T): {delta}  ({move})")
        print("-" * 88)
        print("A-MEM top-5 (cosine):")
        for i, (n, sc) in enumerate(amem_retrieve(q_emb, notes, k=5), 1):
            mark = "*" if n.id in eq.correct_note_ids else " "
            print(f"  {mark}{i}. {n.id:8s}  cos={sc:.4f}  | {n.content[:72]}...")
        print("T-MEM top-5 (blended):")
        cos, d, rf, lb, r_raw, r_hat, blended = full_score_breakdown(q_emb, notes, t_current, cfg, max_links=ml)
        id_to_i = {n.id: j for j, n in enumerate(notes)}
        for i, (n, sc) in enumerate(tmem_retrieve(q_emb, notes, 5, t_current, cfg), 1):
            j = id_to_i[n.id]
            mark = "*" if n.id in eq.correct_note_ids else " "
            print(
                f"  {mark}{i}. {n.id:8s}  blend={sc:.4f}  "
                f"(cos={cos[j]:.3f}, decay={d[j]:.3f}, reinforce={rf[j]:.3f}, "
                f"link_b={lb[j]:.3f}, r_hat={r_hat[j]:.3f})"
            )
        print("Score breakdown for each ground-truth note:")
        for tid in eq.correct_note_ids:
            if tid not in id_to_i:
                continue
            j = id_to_i[tid]
            print(
                f"  {tid}: cos={cos[j]:.4f}  decay={d[j]:.4f}  reinforce={rf[j]:.4f}  "
                f"link_bonus={lb[j]:.4f}  r_raw={r_raw[j]:.4f}  r_hat={r_hat[j]:.4f}  "
                f"blend={blended[j]:.4f}"
            )


def main() -> None:
    results_dir = str(ROOT / "results")
    print("T-MEM simulation — loading encoder and building memory bank...")
    df, rows, cfg, notes, t_current, model = run_full_comparison(results_dir)
    enc = "SentenceTransformer (paper: all-MiniLM-L6-v2)" if not isinstance(model, HashTextEncoder) else "HashTextEncoder (dev/offline only)"
    print(
        f"Config: paper_aligned_amem={cfg.paper_aligned_amem}  |  "
        f"use_decay_only_temporal={cfg.use_decay_only_temporal}  |  "
        f"decay_age_unit={cfg.decay_age_unit!r}  |  encoder={enc}"
    )
    stats, counts = category_accuracy_stats(rows)

    _print_query_details(notes, model, t_current, cfg)

    print("\n" + "=" * 88)
    print("SUMMARY TABLE (see results/comparison_table.csv)")
    print(df.to_string(index=False))
    generate_all_plots(results_dir, stats, counts, rows, notes, model, t_current, cfg)
    print("\nArtifacts written to:", results_dir)
    print("  - comparison_table.csv")
    print("  - retrieval_accuracy.png")
    print("  - decay_curves.png")
    print("  - score_breakdown.png")
    print("  - summary_stats.txt")


if __name__ == "__main__":
    main()
