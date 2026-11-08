# Copied unchanged from the 2026-11-07 verification (independent of analyze.py and summary.json).
"""Independent recomputation of every Chapter IV results table from the raw result files.
Does not read analysis/summary.json and does not import analyze.py."""
import json, random, statistics, sys
sys.path.insert(0, "."); from analyze_consolidation_qa import classify_cat5
E = "experiments/factorial8_samples0-3_2026-11-07"; SEEDS = [42, 43, 44, 45, 46]
SET = ["s1_amem", "s2_t", "s3_c", "s4_h", "s5_tc", "s6_th", "s7_ch", "s8_tch"]
NAME = dict(zip(SET, ["A-MEM", "T", "C", "H", "T + C", "T + H", "C + H", "All three"]))
GR = {"A": {0, 1, 2, 3}, "S3": {3}, "DEV": {0, 1, 2}}
R = {s: [json.load(open(f"{E}/results/{s}_seed{sd}.json"))["individual_results"] for sd in SEEDS] for s in SET}
SID = [int(r["sample_id"]) for r in R["s1_amem"][0]]; CAT = [int(r["category"]) for r in R["s1_amem"][0]]
for s in SET:
    for run in R[s]: assert [int(r["sample_id"]) for r in run] == SID and [int(r["category"]) for r in run] == CAT
f1 = lambda r: r["metrics"]["f1"]
def refusal(r): return classify_cat5(r["prediction"], r["reference"]) == "not_mentioned"
def run_score(run, g, kind):
    idx = [i for i in range(757) if SID[i] in GR[g]]
    if kind == "ans": v = [f1(run[i]) for i in idx if CAT[i] != 5]
    elif kind == "time": v = [f1(run[i]) for i in idx if CAT[i] == 2]
    elif kind == "ref": v = [refusal(run[i]) for i in idx if CAT[i] == 5]
    elif kind == "paper": v = [f1(run[i]) for i in idx]
    elif kind == "cred": v = [f1(run[i]) if CAT[i] != 5 else float(refusal(run[i])) for i in idx]
    elif kind.startswith("cat"): v = [f1(run[i]) for i in idx if CAT[i] == int(kind[3])]
    return statistics.mean(v)
def ms(s, g, k): xs = [run_score(r, g, k) for r in R[s]]; return statistics.mean(xs), statistics.stdev(xs), xs
Q = {s: [statistics.mean(f1(r[i]) for r in R[s]) for i in range(757)] for s in SET}
def boot(vals_by_sample):
    allv = [x for v in vals_by_sample.values() for x in v]; m = statistics.mean(allv)
    rng = random.Random(7); st = []
    for _ in range(10000):
        tot = n = 0
        for v in vals_by_sample.values():
            L = len(v)
            for _ in range(L): tot += v[rng.randrange(L)]; n += 1
        st.append(tot / n)
    st.sort(); a = sum(x > 0 for x in st) / 1e4; b = sum(x < 0 for x in st) / 1e4
    return m, st[250], st[9749], min(1.0, 2 * min(a, b) + 1e-4)
def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0] * len(ps); run = 0
    for k, i in enumerate(o): run = max(run, min(1, (len(ps) - k) * ps[i])); adj[i] = run
    return adj
MEAS = {"time": {2}, "ans": {1, 2, 3, 4}}
def byS(g, cats, fn):
    d = {}
    for i in range(757):
        if SID[i] in GR[g] and CAT[i] in cats: d.setdefault(SID[i], []).append(fn(i))
    return d
def contrast(i, e):
    s1, s2, s3, s4, s5, s6, s7, s8 = (Q[s][i] for s in SET)
    return {"T": (s2-s1+s5-s3+s6-s4+s8-s7)/4, "C": (s3-s1+s5-s2+s7-s4+s8-s6)/4, "H": (s4-s1+s6-s2+s7-s3+s8-s5)/4,
            "TxC": ((s5-s3)-(s2-s1)+(s8-s7)-(s6-s4))/2, "TxH": ((s6-s4)-(s2-s1)+(s8-s7)-(s5-s3))/2,
            "CxH": ((s7-s4)-(s3-s1)+(s8-s6)-(s5-s2))/2, "TxCxH": ((s8-s7)-(s6-s4))-((s5-s3)-(s2-s1))}[e]
OUT = {"setups": {}, "vs": {}, "fac": {}}
for g in GR:
    OUT["setups"][g] = {s: {k: ms(s, g, k)[:2] for k in ["ans", "time", "ref", "paper", "cred", "cat1", "cat2", "cat3", "cat4", "cat5"]} for s in SET}
    OUT["setups"][g]["_runs"] = {s: {k: ms(s, g, k)[2] for k in ["ans", "time"]} for s in SET}
    tests = []
    for s in SET[1:]:
        for m, cats in MEAS.items():
            d = byS(g, cats, lambda i: Q[s][i] - Q["s1_amem"][i]); mm, lo, hi, p = boot(d)
            keys = [i for i in range(757) if SID[i] in GR[g] and CAT[i] in cats]
            rb = sum(run_score(R[s][k], g, m) > run_score(R["s1_amem"][k], g, m) for k in range(5))
            tests.append(dict(s=s, m=m, diff=mm, lo=lo, hi=hi, p=p, rb=rb, qb=sum(Q[s][i] > Q["s1_amem"][i] + 1e-12 for i in keys),
                              qw=sum(Q[s][i] < Q["s1_amem"][i] - 1e-12 for i in keys), prim=s in ("s2_t", "s3_c", "s4_h", "s8_tch")))
    for fam in (True, False):
        ts = [t for t in tests if t["prim"] == fam]
        for t, a in zip(ts, holm([t["p"] for t in ts])): t["ph"] = a
    OUT["vs"][g] = tests
    fac = []
    for m, cats in MEAS.items():
        for e in ["T", "C", "H", "TxC", "TxH", "CxH", "TxCxH"]:
            mm, lo, hi, p = boot(byS(g, cats, lambda i: contrast(i, e))); fac.append(dict(e=e, m=m, v=mm, lo=lo, hi=hi, p=p))
    for t, a in zip(fac, holm([t["p"] for t in fac])): t["ph"] = a
    OUT["fac"][g] = fac
    print("done", g, flush=True)
met = {}
for s in SET:
    v = {}
    for sd in SEEDS:
        for k, x in json.load(open(f"{E}/results/{s}_seed{sd}.json"))["aggregate_metrics"]["overall"].items(): v.setdefault(k, []).append(x["mean"])
    met[s] = {k: statistics.mean(x) for k, x in v.items()}
OUT["met"] = met
json.dump(OUT, open(sys.argv[1], "w"))
