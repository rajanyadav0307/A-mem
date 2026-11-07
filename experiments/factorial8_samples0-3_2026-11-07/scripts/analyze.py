"""Stage 6: the analysis fixed in PLAN.md section 8 (written before any results).

    .venv/bin/python <exp>/scripts/analyze.py            -> analysis/summary.json, analysis/tables.md

Scores per question follow the thesis scripts:
  answerable F1 = categories 1-4; time F1 = category 2; trap refusal = category 5
  answered "not mentioned"; overall F1 (paper) = all categories; overall with
  refusals credited = category 5 scored 1 for a refusal, else 0.
Tests: paired bootstrap over questions (each question averaged over the 5 runs),
stratified by sample, 10,000 resamples, random seed 7; two-sided p from the
bootstrap; Holm correction within each family.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

sys.path.insert(0, common.REPO)
os.chdir(common.REPO)
from analyze_consolidation_qa import classify_cat5  # noqa: E402

REPS, RNG_SEED = 10000, 7
MEASURES = {"answerable_f1": {1, 2, 3, 4}, "time_f1": {2}}
GROUPS = {"samples 0-3": (0, 1, 2, 3), "sample 3 (clean test)": (3,), "samples 0-2 (development)": (0, 1, 2)}
PRIMARY = ["s2_t", "s3_c", "s4_h", "s8_tch"]           # each part alone, and all three, against A-MEM
S = list(common.SETUPS)


def load(path):
    d = json.load(open(path))
    pos, rows = collections.Counter(), {}
    for r in d["individual_results"]:
        s = int(r["sample_id"])
        key = (s, pos[s])
        pos[s] += 1
        c = int(r["category"])
        refusal = classify_cat5(r["prediction"], r["reference"]) == "not_mentioned" if c == 5 else None
        rows[key] = {"cat": c, "f1": r["metrics"]["f1"], "refusal": refusal,
                     "score": r["metrics"]["f1"] if c != 5 else float(refusal)}
    return rows


def run_scores(rows, samples):
    rs = [v for k, v in rows.items() if k[0] in samples]
    mean = lambda xs: statistics.mean(xs) if xs else float("nan")  # noqa: E731
    out = {"answerable_f1": mean([r["f1"] for r in rs if r["cat"] != 5]),
           "time_f1": mean([r["f1"] for r in rs if r["cat"] == 2]),
           "trap_refusal": mean([r["refusal"] for r in rs if r["cat"] == 5]),
           "overall_f1_paper": mean([r["f1"] for r in rs]),
           "overall_refusal_credited": mean([r["score"] for r in rs])}
    for c in (1, 2, 3, 4, 5):
        out[f"cat{c}_f1"] = mean([r["f1"] for r in rs if r["cat"] == c])
    return out


def per_question(runs, key="f1"):
    keys = next(iter(runs.values())).keys()
    return {k: statistics.mean(r[k][key] for r in runs.values()) for k in keys}


def bootstrap(diffs_by_sample):
    """diffs_by_sample: {sample: [per-question differences]} -> (mean, lo, hi, p two-sided)."""
    allv = [x for v in diffs_by_sample.values() for x in v]
    mean = statistics.mean(allv)
    rng = random.Random(RNG_SEED)
    stats = []
    for _ in range(REPS):
        tot = n = 0
        for v in diffs_by_sample.values():
            for _ in range(len(v)):
                tot += v[rng.randrange(len(v))]
                n += 1
        stats.append(tot / n)
    stats.sort()
    above = sum(x > 0 for x in stats) / REPS
    below = sum(x < 0 for x in stats) / REPS
    p = min(1.0, 2 * min(above, below) + 1 / REPS)
    return mean, stats[int(0.025 * REPS)], stats[int(0.975 * REPS) - 1], p


def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running = [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def contrast_values(q, kind):
    """Per-question value of a factorial contrast from the 8 setup means q[setup]."""
    s1, s2, s3, s4, s5, s6, s7, s8 = (q[s] for s in S)
    if kind == "T": return (s2 - s1 + s5 - s3 + s6 - s4 + s8 - s7) / 4  # noqa: E701
    if kind == "C": return (s3 - s1 + s5 - s2 + s7 - s4 + s8 - s6) / 4  # noqa: E701
    if kind == "H": return (s4 - s1 + s6 - s2 + s7 - s3 + s8 - s5) / 4  # noqa: E701
    if kind == "TxC": return ((s5 - s3) - (s2 - s1) + (s8 - s7) - (s6 - s4)) / 2  # noqa: E701
    if kind == "TxH": return ((s6 - s4) - (s2 - s1) + (s8 - s7) - (s5 - s3)) / 2  # noqa: E701
    if kind == "CxH": return ((s7 - s4) - (s3 - s1) + (s8 - s6) - (s5 - s2)) / 2  # noqa: E701
    if kind == "TxCxH": return ((s8 - s7) - (s6 - s4)) - ((s5 - s3) - (s2 - s1))  # noqa: E701
    raise ValueError(kind)


CONTRASTS = ["T", "C", "H", "TxC", "TxH", "CxH", "TxCxH"]


def analyse(results_dir):
    res = {s: {seed: load(os.path.join(results_dir, f"{s}_seed{seed}.json")) for seed in common.SEEDS} for s in S}
    first = res["s1_amem"][common.SEEDS[0]]
    out = {"setups": {}, "vs_amem": {}, "factorial": {}, "method": {"reps": REPS, "rng_seed": RNG_SEED, "runs": len(common.SEEDS)}}
    for g, samples in GROUPS.items():
        out["setups"][g] = {}
        for s in S:
            per = [run_scores(res[s][seed], samples) for seed in common.SEEDS]
            out["setups"][g][s] = {k: {"mean": statistics.mean(p[k] for p in per),
                                       "sd": statistics.stdev(p[k] for p in per), "per_run": [p[k] for p in per]}
                                   for k in per[0]}
        q = {s: per_question(res[s]) for s in S}
        tests = []
        for s in S[1:]:
            for meas, cats in MEASURES.items():
                keys = [k for k in first if k[0] in samples and first[k]["cat"] in cats]
                by = collections.defaultdict(list)
                for k in keys:
                    by[k[0]].append(q[s][k] - q["s1_amem"][k])
                m, lo, hi, p = bootstrap(by)
                better = sum(q[s][k] > q["s1_amem"][k] + 1e-12 for k in keys)
                worse = sum(q[s][k] < q["s1_amem"][k] - 1e-12 for k in keys)
                seeds_better = sum(run_scores(res[s][sd], samples)[meas] > run_scores(res["s1_amem"][sd], samples)[meas]
                                   for sd in common.SEEDS)
                tests.append({"setup": s, "measure": meas, "diff": m, "ci95": [lo, hi], "p": p, "questions": len(keys),
                              "questions_better": better, "questions_worse": worse, "runs_better": seeds_better,
                              "primary": s in PRIMARY})
        prim = [t for t in tests if t["primary"]]
        for t, a in zip(prim, holm([t["p"] for t in prim])):
            t["p_holm"] = a
            t["real"] = a < 0.05
        rest = [t for t in tests if not t["primary"]]
        for t, a in zip(rest, holm([t["p"] for t in rest])):
            t["p_holm"] = a
            t["real"] = a < 0.05
        out["vs_amem"][g] = tests
        fac = []
        for meas, cats in MEASURES.items():
            keys = [k for k in first if k[0] in samples and first[k]["cat"] in cats]
            for kind in CONTRASTS:
                by = collections.defaultdict(list)
                for k in keys:
                    by[k[0]].append(contrast_values({s: q[s][k] for s in S}, kind))
                m, lo, hi, p = bootstrap(by)
                fac.append({"effect": kind, "measure": meas, "value": m, "ci95": [lo, hi], "p": p})
        for t, a in zip(fac, holm([t["p"] for t in fac])):
            t["p_holm"] = a
            t["real"] = a < 0.05
        out["factorial"][g] = fac
    return out


def tables(out):
    names = {"s1_amem": "A-MEM", "s2_t": "Time ranking", "s3_c": "Consolidation", "s4_h": "Conflict handling",
             "s5_tc": "Time + Consolidation", "s6_th": "Time + Conflict", "s7_ch": "Consolidation + Conflict",
             "s8_tch": "All three"}
    lines = ["# Results tables (generated by scripts/analyze.py)", ""]
    for g in GROUPS:
        lines += [f"## {g}", "", "| Setup | Answerable F1 | Time F1 | Traps refused | Overall F1 (paper) | Overall (refusals credited) |",
                  "|---|---|---|---|---|---|"]
        for s in S:
            v = out["setups"][g][s]
            lines.append(f"| {names[s]} | {v['answerable_f1']['mean']:.3f} ± {v['answerable_f1']['sd']:.3f} | "
                         f"{v['time_f1']['mean']:.3f} ± {v['time_f1']['sd']:.3f} | {v['trap_refusal']['mean']:.1%} | "
                         f"{v['overall_f1_paper']['mean']:.3f} | {v['overall_refusal_credited']['mean']:.3f} |")
        lines += ["", "| Setup vs A-MEM | Measure | Difference | 95% range | Holm p | Real? | Runs better |", "|---|---|---|---|---|---|---|"]
        for t in out["vs_amem"][g]:
            lines.append(f"| {names[t['setup']]}{' (main test)' if t['primary'] else ''} | {t['measure']} | {t['diff']:+.3f} | "
                         f"{t['ci95'][0]:+.3f} to {t['ci95'][1]:+.3f} | {t['p_holm']:.3f} | {'yes' if t['real'] else 'no'} | "
                         f"{t['runs_better']} of {len(common.SEEDS)} |")
        lines += ["", "| Effect | Measure | Value | 95% range | Holm p | Real? |", "|---|---|---|---|---|---|"]
        for t in out["factorial"][g]:
            lines.append(f"| {t['effect']} | {t['measure']} | {t['value']:+.3f} | {t['ci95'][0]:+.3f} to {t['ci95'][1]:+.3f} | "
                         f"{t['p_holm']:.3f} | {'yes' if t['real'] else 'no'} |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results_dir", default=common.RESULTS_DIR)
    parser.add_argument("--out_dir", default=os.path.join(common.EXP, "analysis"))
    args = parser.parse_args()
    out = analyse(args.results_dir)
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "summary.json"), "w") as handle:
        json.dump(out, handle, indent=1)
    with open(os.path.join(args.out_dir, "tables.md"), "w") as handle:
        handle.write(tables(out))
    print(f"wrote {args.out_dir}/summary.json and tables.md")


if __name__ == "__main__":
    main()
