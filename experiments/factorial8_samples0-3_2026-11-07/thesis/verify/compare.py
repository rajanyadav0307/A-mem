"""Compare every table cell of the built chapters with independent recounts.

  python3 compare.py CHAPTERS.docx RECOMPUTED.json

Chapter IV tables 16-18 and 20-26 are compared with RECOMPUTED.json (verify/recompute.py, which
reads only the raw result files). Table 19 is compared with analysis/extra_recount.json (the Stage 7
recount from the run logs). Tables 5, 6, 8 and 9 of Chapter III are compared with a recount written
here from data/locomo10.json, the banks and the build logs, without facts.py. Table 15 is compared
with the check files. Exit status 1 on any mismatch.
"""
import collections
import json
import math
import os
import pickle
import re
import statistics
import sys
import zipfile
import xml.etree.ElementTree as ET

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
os.chdir(REPO)
sys.path.insert(0, REPO)
E = "experiments/factorial8_samples0-3_2026-11-07"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def tables(path):
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    body = root.find(W + "body")
    out, caption = {}, None
    for el in body:
        if el.tag == W + "p":
            t = "".join(x.text or "" for x in el.iter(W + "t"))
            m = re.match(r"^Table (\d+)", t)
            if m:
                caption = int(m.group(1))
        elif el.tag == W + "tbl":
            rows = [["".join(x.text or "" for x in tc.iter(W + "t")) for tc in tr.iter(W + "tc")] for tr in el.iter(W + "tr")]
            out[caption] = rows
    return out


T = tables(sys.argv[1])
X = json.load(open(sys.argv[2]))
SET = ["s1_amem", "s2_t", "s3_c", "s4_h", "s5_tc", "s6_th", "s7_ch", "s8_tch"]
NAME = dict(zip(SET, ["A-MEM", "T", "C", "H", "T + C", "T + H", "C + H", "All three"]))
INV = {v: k for k, v in NAME.items()}


def rnd(x, d):
    v = math.floor(abs(x) * 10 ** d + 0.5 + 1e-9) / 10 ** d
    return f"{-v if x < 0 and v else v:.{d}f}"


f3 = lambda x: rnd(x, 3)  # noqa: E731


def sg(x):
    r = rnd(abs(x), 3)
    return "0.000" if r == "0.000" else ("−" if x < 0 else "+") + r


pv = lambda x: "1.000" if x >= 0.9995 else rnd(x, 3).lstrip("0")  # noqa: E731
pct = lambda x: rnd(100 * x, 1) + "%"  # noqa: E731
ok = bad = 0


def chk(where, got, exp):
    global ok, bad
    if got == exp:
        ok += 1
    else:
        bad += 1
        print(f"MISMATCH {where}: doc={got!r} expected={exp!r}")


# ---------------------------------------------------------------- Chapter IV vs recompute.py
st = X["setups"]
ms = lambda g, s, k: f"{f3(st[g][s][k][0])} ± {f3(st[g][s][k][1])}"  # noqa: E731
vs = lambda g, s, m: next(t for t in X["vs"][g] if t["s"] == s and t["m"] == m)  # noqa: E731
fe = lambda g, e, m: next(t for t in X["fac"][g] if t["e"] == e and t["m"] == m)  # noqa: E731
MN = {"Temporal F1": "time", "Answerable F1": "ans"}
star = lambda t: "*" if t["ph"] < 0.05 else ""  # noqa: E731
ci = lambda t: f"[{sg(t['lo'])}, {sg(t['hi'])}]"  # noqa: E731
for r in T[16][1:]:
    s = INV[r[0]]
    for c, e in zip(r[1:], [ms("A", s, "ans"), ms("A", s, "time"), pct(st["A"][s]["ref"][0]), f3(st["A"][s]["paper"][0]), f3(st["A"][s]["cred"][0])]):
        chk(f"T16 {r[0]}", c, e)
for tn in (17, 22):
    for r in T[tn][1:]:
        t = vs("A", INV[r[0]], MN[r[1]])
        exp = [sg(t["diff"]), ci(t), pv(t["ph"]), "Yes" if t["ph"] < .05 else "No", f"{t['rb']} of 5"]
        if tn == 17:
            exp.append(f"{t['qb']} / {t['qw']}")
        for c, e in zip(r[2:], exp):
            chk(f"T{tn} {r[0]} {r[1]}", c, e)
GL = {"Samples 0–3": "A", "Samples 0–2": "DEV", "Sample 3": "S3"}
EN = {"T × C": "TxC", "T × H": "TxH", "C × H": "CxH", "T × C × H": "TxCxH"}
for tn in (18, 21):
    g = None
    for r in T[tn][1:]:
        if r[0]:
            g = GL[r[0]]
        e = EN.get(r[1], r[1])
        a, b = fe(g, e, "time"), fe(g, e, "ans")
        exp = [sg(a["v"]) + star(a), ci(a), pv(a["ph"]), sg(b["v"]) + star(b), ci(b), pv(b["ph"])]
        for c, x in zip(r[2:], exp):
            chk(f"T{tn} {g} {r[1]}", c, x)
for r in T[20][1:]:
    s = INV[r[0]]
    for c, k in zip(r[1:], ["cat1", "cat2", "cat3", "cat4", "cat5"]):
        chk(f"T20 {r[0]} {k}", c, f3(st["A"][s][k][0]))
for r in T[23][1:]:
    s = INV[r[0]]
    chk("T23 ans " + r[0], r[1], ms("S3", s, "ans"))
    chk("T23 time " + r[0], r[2], ms("S3", s, "time"))
    if s == "s1_amem":
        continue
    a, b = vs("S3", s, "time"), vs("S3", s, "ans")
    for c, e in zip(r[3:], [f"{sg(a['diff'])}{star(a)} {ci(a)}", pv(a["ph"]), f"{sg(b['diff'])}{star(b)} {ci(b)}", pv(b["ph"])]):
        chk("T23 " + r[0], c, e)
for r in T[24][1:]:
    s, m = INV[r[0]], MN[r[1]]
    a, b = vs("DEV", s, m), vs("S3", s, m)
    for c, e in zip(r[2:], [f"{sg(a['diff'])}{star(a)} {ci(a)}", pv(a["ph"]), f"{sg(b['diff'])}{star(b)} {ci(b)}", pv(b["ph"])]):
        chk(f"T24 {r[0]} {r[1]}", c, e)
for r in T[25][1:]:
    s = INV[r[0]]
    exp = [pct(st["A"][s]["ref"][0]), f3(st["A"][s]["paper"][0]), f3(st["A"][s]["cred"][0]), pct(st["S3"][s]["ref"][0]), f3(st["S3"][s]["paper"][0]), f3(st["S3"][s]["cred"][0])]
    for c, e in zip(r[1:], exp):
        chk("T25 " + r[0], c, e)
for r in T[26][1:]:
    s = INV[r[0]]
    for c, k in zip(r[1:], ["f1", "exact_match", "rougeL_f", "bleu1", "meteor", "bert_f1", "sbert_similarity"]):
        chk(f"T26 {r[0]} {k}", c, f3(X["met"][s][k]))
n4 = ok + bad

# ---------------------------------------------------------------- Table 19 vs the Stage 7 recount
R = json.load(open(f"{E}/analysis/extra_recount.json"))
M, G = R["mechanism"], R["merged_ctx"]
smp = ["0", "1", "2", "3"]
tot = lambda o, k: sum(o[s][k] for s in smp)  # noqa: E731
get = lambda o, k, i: tot(o, k) if i == "all" else o[i][k]  # noqa: E731
share = lambda a, b: f"{a:,} ({rnd(100 * a / b, 1)}%)"  # noqa: E731
rows19 = [
    lambda i: f"{get(M, 'time_q', i):,}",
    lambda i: share(get(M, "t_same_set", i), get(M, "time_q", i)),
    lambda i: share(get(M, "t_margin_skip", i), get(M, "time_q", i)),
    lambda i: rnd(get(M, "t_notes_swapped", i) / get(M, "time_q", i), 2),
    lambda i: share(get(M, "h_time_ctx_with_timeline", i), get(M, "time_q", i)),
    lambda i: share(get(M, "h_time_ctx_with_happened", i), get(M, "time_q", i)),
    lambda i: share(get(M, "h_ctx_with_outdated", i), get(M, "all_q", i)),
    lambda i: f"{get(M, 'now_q', i) // 5:,}",
    lambda i: share(get(G, "tm", i), get(G, "tq", i)),
    lambda i: share(get(G, "m", i), get(G, "all", i)),
]
for r, fn in zip(T[19][1:], rows19):
    for c, i in zip(r[1:], smp + ["all"]):
        chk(f"T19 {r[0][:40]} {i}", c, fn(i))
n19 = ok + bad - n4

# ---------------------------------------------------------------- Chapter III tables, recounted here
data = json.load(open("data/locomo10.json"))
for r in T[5][1:]:
    if r[0] == "Total":
        rows = data[:4]
    else:
        rows = [data[int(r[0])]]
    sess = turns = 0
    cats = collections.Counter()
    for x in rows:
        c = x["conversation"]
        keys = [k for k in c if k.startswith("session_") and not k.endswith("date_time") and isinstance(c[k], list) and c[k]]
        sess += len(keys)
        turns += sum(len(c[k]) for k in keys)
        cats.update(q["category"] for q in x["qa"])
    exp = [f"{sess:,}", f"{turns:,}", f"{sum(cats.values()):,}"] + [f"{cats[k]:,}" for k in (1, 2, 3, 4, 5)]
    if r[0] != "Total":
        chk(f"T5 {r[0]} speakers", r[1], f"{rows[0]['conversation']['speaker_a']} & {rows[0]['conversation']['speaker_b']}")
    for c, e in zip(r[2:10], exp):
        chk(f"T5 {r[0]}", c, e)
import memory_layer_robust  # noqa: E402,F401
for r in T[6][1:]:
    notes = [n for n in pickle.load(open(f"{E}/cache/shared/memory_cache_sample_{r[0]}.pkl", "rb")).values() if n.note_type == "raw"]
    exp = [f"{len(notes):,}", f"{sum(bool(n.links) for n in notes):,}", rnd(sum(map(len, (n.links for n in notes))) / len(notes), 2),
           rnd(sum(len(n.keywords) for n in notes) / len(notes), 2), rnd(sum(len(n.tags) for n in notes) / len(notes), 2)]
    for c, e in zip(r[1:], exp):
        chk(f"T6 {r[0]}", c, e)
CONS = {0: "analysis/consolidation_log_sample_0_v3.json", 1: "analysis/consolidation_log_sample_1_v3.json",
        2: "experiments/e2e_samples0-2_2026-10-26_13-10/build_logs/consolidation_log_sample_2_e2e.json",
        3: f"{E}/build_logs/sample3_consolidation_log.json"}
CONF = {s: f"experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/build_logs/conflict/conflict_log_sample_{s}.json" for s in (0, 1, 2)}
CONF[3] = f"{E}/build_logs/sample3_conflict_log.json"
c8 = {}
for s in range(4):
    g = json.load(open(CONS[s]))["groups"]
    out = collections.Counter(x["outcome"] for x in g)
    lab = collections.Counter(x["label"] for x in g)
    merged = [x for x in g if x["outcome"] == "merged"]
    calls = sum(1 + len(x.get("attempts", [])) for x in g)
    bank = list(pickle.load(open(f"{E}/cache/shared/memory_cache_sample_{s}.pkl", "rb")).values())
    raw = sum(n.note_type == "raw" for n in bank)
    c8[s] = [f"{len(g):,}", f"{lab['SAME_FACT']}", f"{lab['SMALL_TALK']}", f"{lab['DIFFERENT']}", f"{out['merged']}", f"{out['rejected']}",
             rnd(sum(len(x["sources"]) for x in merged) / len(merged), 2), f"{calls}", f"{raw:,} → {len(bank):,}"]
for i, r in enumerate(T[8][1:]):
    for s, c in enumerate(r[1:]):
        chk(f"T8 {r[0]} s{s}", c, c8[s][i])
c9 = {}
for s in range(4):
    x = json.load(open(CONF[s]))
    lab = collections.Counter(p["label"] for p in x["pairs"])
    bank = [n for n in pickle.load(open(f"{E}/cache/shared/memory_cache_sample_{s}.pkl", "rb")).values() if n.note_type == "raw"]
    c9[s] = [f"{len(bank):,}", f"{x['state_notes']}", f"{len(x['timelines'])}", f"{sum(len(t['notes']) for t in x['timelines'])}",
             f"{lab['PROGRESS']}", f"{lab['COMPATIBLE']}", f"{lab['SAME']}", f"{x['verification']['checked']}", f"{x['verification']['confirmed']}",
             f"{sum(1 for n in bank if n.valid_until)}", f"{sum(1 for n in bank if n.event_time)}"]
for i, r in enumerate(T[9][1:]):
    for s, c in enumerate(r[1:]):
        chk(f"T9 {r[0][:30]} s{s}", c, c9[s][i])
n3 = ok + bad - n4 - n19

# ---------------------------------------------------------------- Table 15 vs the check files
a = json.load(open(f"{E}/checks/checks_all.json"))["items"]
waves = [json.load(open(f"{E}/checks/checks_seed{s}.json")) for s in (42, 43, 44, 45, 46)]
per = {len(w["items"]) for w in waves}
assert len(per) == 1 and all(w["ok"] for w in waves)
nper = per.pop()
r15 = {r[0]: r[1] for r in T[15][1:]}
chk("T15 runs", r15["Runs (8 setups × 5 seeds)"], f"{len(os.listdir(f'{E}/results'))} of 40 finished")
chk("T15 answers", r15["Answers (40 runs × 757 questions)"], f"{sum(int(i['detail'].split()[0]) for i in a if i['check'].startswith('R1 ')):,}, none empty")
chk("T15 per wave", r15["Checks per wave (R0–R11)"], f"{nper} of {nper} passed in each of the five waves")
chk("T15 final", r15["Final checks across all 40 files"], f"{len(a)} of {len(a)} passed")
n15 = ok + bad - n4 - n19 - n3
print(f"Chapter IV tables vs recompute.py: {n4} cells; Table 19 vs extra_recount.json: {n19}; Chapter III tables 5, 6, 8, 9: {n3}; Table 15: {n15}")
print(f"cells checked: {ok + bad}, mismatches: {bad}")
sys.exit(1 if bad else 0)
