import json, sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
OUT, FACTS = sys.argv[1], sys.argv[2]
import os
S = json.load(open(os.environ["SUMMARY"]))
F = {k: v["value"] for k, v in json.load(open(FACTS)).items()}   # labels with numbers come from the facts file
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#555555", "axes.linewidth": 0.6, "xtick.color": "#333333", "ytick.color": "#333333"})
INK, MARK, BAR, GRID = "#1a1a1a", "#1f4e79", "#c9d6e3", "#e6e6e6"

# ---- Figure 1: where each part acts
fig, ax = plt.subplots(figsize=(6.0, 4.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 9.4); ax.axis("off")
def box(x, y, w, h, text, tmem=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", lw=0.8,
                                ec=INK, fc="#d9d9d9" if tmem else "white"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.6, color=INK, wrap=True)
def arrow(x1, y1, x2, y2): ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", lw=0.8, color=INK))
ax.text(3.0, 9.0, "Built once, offline", ha="center", fontsize=9.5, fontweight="bold")
ax.text(9.0, 9.0, "For each question", ha="center", fontsize=9.5, fontweight="bold")
box(0.6, 7.3, 4.8, 1.1, "Conversation turns (LoCoMo)")
box(0.6, 5.5, 4.8, 1.2, "A-MEM: one note per turn,\nkeywords, context, tags, links")
box(0.6, 3.6, 4.8, 1.3, "Consolidation (C): verified merged\nnotes appended; sources kept", True)
box(0.6, 1.6, 4.8, 1.4, "Conflict handling (H): state timelines,\nchange labels, statement and\nevent dates", True)
box(1.6, 0.1, 2.8, 0.9, "One shared bank\nper sample")
for y1, y2 in [(7.3, 6.7), (5.5, 4.9), (3.6, 3.0), (1.6, 1.0)]: arrow(3.0, y1, 3.0, y2)
box(6.6, 7.3, 4.8, 1.1, "Question → search words\n(made once, shared by all setups)")
box(6.6, 5.2, 4.8, 1.5, f"Retrieve {F['t_k']} notes by similarity\n+ at most {F['cons_cap']} merged note (C)\n+ demotion of replaced notes (H)\n+ time ranking (T, category {', '.join(map(str, F['t_categories']))} only)", True)
box(6.6, 3.3, 4.8, 1.3, "Add linked notes; show timeline\nlabels with each note (H)", True)
box(6.6, 1.6, 4.8, 1.1, f"Answer model ({F['model']})")
box(7.6, 0.1, 2.8, 0.9, "Scored against\nthe reference")
for y1, y2 in [(7.3, 6.7), (5.2, 4.6), (3.3, 2.7), (1.6, 1.0)]: arrow(9.0, y1, 9.0, y2)
ax.plot([4.4, 6.05, 6.05], [0.55, 0.55, 5.95], color=INK, lw=0.8); arrow(6.05, 5.95, 6.6, 5.95)
fig.tight_layout(); fig.savefig(f"{OUT}/fig1_pipeline.png", dpi=300); plt.close(fig)

# ---- Figure 2: F1 of the 8 setups, each run a dot
ORDER = ["s1_amem", "s2_t", "s3_c", "s4_h", "s5_tc", "s6_th", "s7_ch", "s8_tch"]
LAB = ["A-MEM", "T", "C", "H", "T + C", "T + H", "C + H", "All three"]
fig, axes = plt.subplots(2, 2, figsize=(6.2, 5.2), sharex=True)
for col, (g, gt) in enumerate([("samples 0-3", "Samples 0–3"), ("sample 3 (clean test)", "Sample 3 (clean test)")]):
    for row, (m, mt) in enumerate([("time_f1", "Temporal F1"), ("answerable_f1", "Answerable F1")]):
        a = axes[row][col]
        means = [S["setups"][g][s][m]["mean"] for s in ORDER]
        a.hlines(means, [i - 0.3 for i in range(8)], [i + 0.3 for i in range(8)], color=INK, lw=1.6, zorder=2)
        for i, s in enumerate(ORDER):
            pr = S["setups"][g][s][m]["per_run"]
            xs = [i - 0.16 + 0.08 * j for j in range(len(pr))]
            a.scatter(xs, pr, s=9, color=MARK, zorder=3, linewidths=0)
        a.axhline(means[0], color="#777777", lw=0.7, ls="--", zorder=2)
        lo = min(min(S["setups"][g][s][m]["per_run"]) for s in ORDER); hi = max(max(S["setups"][g][s][m]["per_run"]) for s in ORDER)
        pad = (hi - lo) * 0.25; a.set_ylim(lo - pad, hi + pad)
        a.yaxis.grid(True, color=GRID, lw=0.5); a.set_axisbelow(True)
        if row == 0: a.set_title(gt, fontsize=9.5)
        if col == 0: a.set_ylabel(mt)
        a.set_xticks(range(8)); a.set_xticklabels(LAB, rotation=45, ha="right", fontsize=8.5)
fig.tight_layout(); fig.savefig(f"{OUT}/fig2_setups.png", dpi=300); plt.close(fig)

# ---- Figure 3: factorial effects with 95% intervals
EFF = ["T", "C", "H", "TxC", "TxH", "CxH", "TxCxH"]; EL = ["T", "C", "H", "T × C", "T × H", "C × H", "T × C × H"]
GROUPS = [("samples 0-3", "Samples 0–3"), ("samples 0-2 (development)", "Samples 0–2 (development)"), ("sample 3 (clean test)", "Sample 3 (clean test)")]
fig, axes = plt.subplots(2, 3, figsize=(6.4, 4.6), sharey=True)
for row, (m, mt) in enumerate([("time_f1", "Temporal F1"), ("answerable_f1", "Answerable F1")]):
    vals = [t for g, _ in GROUPS for t in S["factorial"][g] if t["measure"] == m]
    lim = max(max(abs(t["ci95"][0]), abs(t["ci95"][1])) for t in vals) * 1.1
    for col, (g, gt) in enumerate(GROUPS):
        a = axes[row][col]
        for i, e in enumerate(EFF):
            t = [x for x in S["factorial"][g] if x["effect"] == e and x["measure"] == m][0]
            y = len(EFF) - 1 - i
            a.plot(t["ci95"], [y, y], color=MARK, lw=1.2)
            a.scatter([t["value"]], [y], s=22, zorder=3, color=MARK if t["real"] else "white", edgecolors=MARK, linewidths=1.0)
        a.axvline(0, color="#777777", lw=0.7, ls="--"); a.set_xlim(-lim, lim)
        a.set_yticks(range(len(EFF))); a.set_yticklabels(EL[::-1], fontsize=8.5)
        a.tick_params(axis="x", labelsize=8)
        a.xaxis.grid(True, color=GRID, lw=0.5); a.set_axisbelow(True)
        if row == 0: a.set_title(gt, fontsize=9)
        if col == 1: a.set_xlabel(f"Effect on {mt[0].lower() + mt[1:]}", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/fig3_effects.png", dpi=300); plt.close(fig)
print("ok")
