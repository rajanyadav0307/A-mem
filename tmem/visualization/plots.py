"""Presentation-ready charts for T-MEM vs A-MEM simulation."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from simulation.queries import categories_in_order


def _set_academic_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "legend.fontsize": 9,
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def plot_retrieval_accuracy(
    stats: Dict[str, Tuple[float, float, float, float]],
    out_path: str,
) -> None:
    """Grouped bars: A-MEM vs T-MEM top-1 and top-3 accuracy per category."""
    _set_academic_style()
    cats = categories_in_order()
    x = np.arange(len(cats))
    width = 0.18
    am1 = [stats[c][0] for c in cats]
    tm1 = [stats[c][1] for c in cats]
    am3 = [stats[c][2] for c in cats]
    tm3 = [stats[c][3] for c in cats]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(x - 1.5 * width, am1, width, label="A-MEM @1", color="#4C72B0")
    ax.bar(x - 0.5 * width, tm1, width, label="T-MEM @1", color="#55A868")
    ax.bar(x + 0.5 * width, am3, width, label="A-MEM @3", color="#8172B2")
    ax.bar(x + 1.5 * width, tm3, width, label="T-MEM @3", color="#CCB974")

    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", " ").title() for c in cats])
    ax.set_ylabel("Accuracy")
    ax.set_title("Retrieval accuracy by LoCoMo-style category (simulation)")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_decay_curves(out_path: str, *, decay_lambda: float = 0.1, beta: float = 0.5, gamma: float = 0.3) -> None:
    """Four scenarios for r_i vs days since note creation (conceptual curves)."""
    _set_academic_style()
    # Age axis in month-equivalent units (matches temporal_scoring.decay).
    months = np.linspace(0, 6, 200)
    decay_v = np.exp(-decay_lambda * months)

    # Scenario curves (r = decay * reinforce * link_bonus)
    old_never = decay_v * 1.0 * 1.0
    reinforce_hi = 1.0 + beta * np.log1p(25)
    old_frequent = decay_v * reinforce_hi * 1.0
    max_links_norm = 1.0  # assume |L|/max_links = 1
    link_part = 1.0 + gamma * max_links_norm
    old_linked = decay_v * 1.0 * link_part
    # Recent: same formula but interpreted as low age on shared x-axis — plot as reference at low days
    recent = decay_v * (1.0 + beta * np.log1p(3)) * 1.0

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(months, old_never, label="Old, never accessed (decay only)", color="#4C72B0", linewidth=2)
    ax.plot(months, old_frequent, label="Old, frequently accessed (+ reinforce)", color="#55A868", linewidth=2)
    ax.plot(months, old_linked, label="Old, well-connected (+ link bonus)", color="#C44E52", linewidth=2)
    ax.plot(months, recent, label="Typical usage + decay (moderate access)", color="#8172B2", linewidth=2, linestyle="--")

    ax.set_xlabel("Age (month-equivalent units, days/30)")
    ax.set_ylabel("Relevance score component product (r_i)")
    ax.set_title("Temporal relevance: decay offset by reinforcement and links")
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_score_breakdown_work_query(
    note_labels: List[str],
    cos: np.ndarray,
    r_hat: np.ndarray,
    alpha: float,
    amem_scores: np.ndarray,
    out_path: str,
) -> None:
    """Stacked cosine vs temporal contribution for T-MEM; A-MEM cosine-only bars."""
    _set_academic_style()
    x = np.arange(len(note_labels))
    width = 0.36
    cos_part = alpha * cos
    temp_part = (1.0 - alpha) * r_hat

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, amem_scores, width, label="A-MEM (cosine only)", color="#4C72B0")
    ax.bar(x + width / 2, cos_part, width, label=r"T-MEM: $\alpha$·cosine", color="#55A868")
    ax.bar(x + width / 2, temp_part, width, bottom=cos_part, label=r"T-MEM: $(1-\alpha)$·$\hat{r}$", color="#CCB974")

    ax.set_xticks(x)
    ax.set_xticklabels(note_labels, rotation=22, ha="right")
    ax.set_ylabel("Score")
    ax.set_title('Score components for "Where does Alice currently work?" (top-5 union)')
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def build_work_query_breakdown_data(
    notes: List[Any],
    model: Any,
    t_current: Any,
    cfg: Any,
) -> Tuple[List[str], np.ndarray, np.ndarray, float, np.ndarray]:
    """Prepare arrays for the temporal work query figure (union of A-MEM and T-MEM top-5)."""
    from tmem.retrieval import amem_retrieve, full_score_breakdown, tmem_retrieve
    from tmem.temporal_scoring import max_link_degree

    query = "Where does Alice currently work?"
    q_emb = model.encode(query, convert_to_numpy=True)
    q_emb = np.asarray(q_emb, dtype=np.float32)
    ml = max_link_degree(notes)
    cos, _, _, _, _, r_hat, blended = full_score_breakdown(q_emb, notes, t_current, cfg, max_links=ml)

    amem_ranked = amem_retrieve(q_emb, notes, k=5)
    tmem_ranked = tmem_retrieve(q_emb, notes, k=5, t_current=t_current, cfg=cfg)
    ids = list(dict.fromkeys([n.id for n, _ in amem_ranked] + [n.id for n, _ in tmem_ranked]))
    id_to_i = {n.id: i for i, n in enumerate(notes)}

    labels: List[str] = []
    cos_sel: List[float] = []
    rhat_sel: List[float] = []
    amem_sel: List[float] = []
    for nid in ids[:7]:
        i = id_to_i[nid]
        labels.append(nid.replace("_", " "))
        cos_sel.append(float(cos[i]))
        rhat_sel.append(float(r_hat[i]))
        amem_sel.append(float(cos[i]))

    return (
        labels,
        np.array(cos_sel),
        np.array(rhat_sel),
        float(cfg.blend_alpha),
        np.array(amem_sel),
    )


def write_summary_stats(
    rows: List[Dict[str, Any]],
    stats: Dict[str, Tuple[float, float, float, float]],
    counts: Dict[str, int],
    out_path: str,
) -> None:
    improved = sum(1 for r in rows if r["movement_vs_amem"] == "improved")
    same = sum(1 for r in rows if r["movement_vs_amem"] == "same")
    worse = sum(1 for r in rows if r["movement_vs_amem"] == "worse")
    deltas = [r["rank_delta_amem_minus_tmem"] for r in rows if r["amem_rank"] > 0 and r["tmem_rank"] > 0]
    avg_imp = float(np.mean(deltas)) if deltas else 0.0

    lines = [
        "T-MEM vs A-MEM simulation summary",
        "================================",
        f"Queries where T-MEM improved correct-answer rank: {improved}",
        f"Queries where rank stayed the same: {same}",
        f"Queries where rank got worse: {worse}",
        f"Average rank delta (A-MEM rank minus T-MEM rank; positive is better for T-MEM): {avg_imp:.3f}",
        "",
        "Per-category retrieval accuracy (from grouped bar chart data)",
        "-------------------------------------------------------------",
    ]
    for cat in categories_in_order():
        a1, t1, a3, t3 = stats.get(cat, (0.0, 0.0, 0.0, 0.0))
        n = counts.get(cat, 0)
        lines.append(
            f"{cat}: n={n} | A-MEM@1={a1:.2f} T-MEM@1={t1:.2f} | A-MEM@3={a3:.2f} T-MEM@3={t3:.2f}"
        )
    lines.append("")
    lines.append("Note: ranks use the best rank among acceptable ground-truth note ids.")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def generate_all_plots(
    results_dir: str,
    stats: Dict[str, Tuple[float, float, float, float]],
    counts: Dict[str, int],
    rows: List[Dict[str, Any]],
    notes: List[Any],
    model: Any,
    t_current: Any,
    cfg: Any,
) -> None:
    plot_retrieval_accuracy(stats, os.path.join(results_dir, "retrieval_accuracy.png"))
    plot_decay_curves(os.path.join(results_dir, "decay_curves.png"), decay_lambda=cfg.decay_lambda, beta=cfg.reinforce_beta, gamma=cfg.link_gamma)
    labels, cos_a, r_hat_a, alpha, amem_s = build_work_query_breakdown_data(notes, model, t_current, cfg)
    plot_score_breakdown_work_query(labels, cos_a, r_hat_a, alpha, amem_s, os.path.join(results_dir, "score_breakdown.png"))
    write_summary_stats(rows, stats, counts, os.path.join(results_dir, "summary_stats.txt"))
