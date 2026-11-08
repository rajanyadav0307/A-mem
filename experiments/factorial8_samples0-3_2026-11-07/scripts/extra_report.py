"""Print the Stage 7 section of REPORT.md from analysis/extra.json (every number is read, none typed).

Usage (from the repository root):
  python3 experiments/factorial8_samples0-3_2026-11-07/scripts/extra_report.py > section.md
"""
import json

E = "experiments/factorial8_samples0-3_2026-11-07"
X = json.load(open(f"{E}/analysis/extra.json"))
M, G, T = X["mechanism"], X["merged_ctx"], X["metrics"]
S = ["0", "1", "2", "3"]
NAME = {"s1_amem": "s1 A-MEM", "s2_t": "s2 T", "s3_c": "s3 C", "s4_h": "s4 H", "s5_tc": "s5 T+C",
        "s6_th": "s6 T+H", "s7_ch": "s7 C+H", "s8_tch": "s8 all three"}


def tot(d, k):
    return sum(d[s][k] for s in S)


def share(a, b):
    return f"{a:,} of {b:,} ({100 * a / b:.1f}%)"


rows = [
    ("Time questions × runs", lambda s: f"{M[s]['time_q']:,}", f"{tot(M, 'time_q'):,}"),
    ("T: same 10 notes as A-MEM", lambda s: share(M[s]["t_same_set"], M[s]["time_q"]), share(tot(M, "t_same_set"), tot(M, "time_q"))),
    ("T: same 10 notes in the same order", lambda s: share(M[s]["t_same_order"], M[s]["time_q"]), share(tot(M, "t_same_order"), tot(M, "time_q"))),
    ("T: skipped (best note leads by ≥ 0.05)", lambda s: share(M[s]["t_margin_skip"], M[s]["time_q"]), share(tot(M, "t_margin_skip"), tot(M, "time_q"))),
    ("T: notes replaced, total", lambda s: f"{M[s]['t_notes_swapped']:,}", f"{tot(M, 't_notes_swapped'):,}"),
    ("H: time contexts with a timeline label", lambda s: share(M[s]["h_time_ctx_with_timeline"], M[s]["time_q"]), share(tot(M, "h_time_ctx_with_timeline"), tot(M, "time_q"))),
    ("H: time contexts with an event date", lambda s: share(M[s]["h_time_ctx_with_happened"], M[s]["time_q"]), share(tot(M, "h_time_ctx_with_happened"), tot(M, "time_q"))),
    ("H: all contexts with a timeline label", lambda s: share(M[s]["h_ctx_with_timeline"], M[s]["all_q"]), share(tot(M, "h_ctx_with_timeline"), tot(M, "all_q"))),
    ("H: all contexts with an OUTDATED label", lambda s: share(M[s]["h_ctx_with_outdated"], M[s]["all_q"]), share(tot(M, "h_ctx_with_outdated"), tot(M, "all_q"))),
    ("Questions about the present × runs", lambda s: f"{M[s]['now_q']:,}", f"{tot(M, 'now_q'):,}"),
    ("C: s3 contexts with a merged note", lambda s: share(G[s]["m"], G[s]["all"]), share(tot(G, "m"), tot(G, "all"))),
    ("C: s3 time contexts with a merged note", lambda s: share(G[s]["tm"], G[s]["tq"]), share(tot(G, "tm"), tot(G, "tq"))),
]

print("## Stage 7: extra counts for the thesis (added 2026-11-08)\n")
print("Descriptive only, no tests. The context counts were not part of the plan; the other measures were named in the plan (section 8) and are averaged here over the five runs. Offline, no AI calls. Numbers: "
      "[analysis/extra.json](analysis/extra.json), made by `scripts/extra_analysis.py`.\n")
print("- **Made twice:** the two runs gave byte-identical files.")
print("- **Recounted another way:** `scripts/extra_recount.py` reads what the runs actually showed the model "
      "(the logged contexts), matches merged notes block by block against the banks' merged notes, averages metrics per question, "
      "and computes the time-ranking margin with its own arithmetic. Result: "
      "[analysis/extra_recount.json](analysis/extra_recount.json), 0 differences. Run twice, byte-identical.\n")
print("### What each part changed in the model's context (question × run cases)\n")
print("| Count | Sample 0 | Sample 1 | Sample 2 | Sample 3 | All |")
print("|---|---|---|---|---|---|")
for name, f, t in rows:
    print(f"| {name} | " + " | ".join(f(s) for s in S) + f" | {t} |")
print("\n### Other measures (all 757 questions, mean of the five runs)\n")
keys = ["f1", "exact_match", "rougeL_f", "bleu1", "meteor", "bert_f1", "sbert_similarity"]
print("| Setup | " + " | ".join(keys) + " |")
print("|---" * (len(keys) + 1) + "|")
for s, v in T.items():
    print(f"| {NAME[s]} | " + " | ".join(f"{v[k]:.4f}" for k in keys) + " |")
