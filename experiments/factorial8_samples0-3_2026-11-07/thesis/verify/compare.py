"""Compare every table cell of the built chapters with independent recounts.

  python3 compare.py CHAPTERS.docx RECOMPUTED.json

Chapter IV results tables (16-18, 20-27) are compared with RECOMPUTED.json (verify/recompute.py, which
reads only the raw result files, not summary.json). Table 19 is compared with analysis/extra_recount.json
(the Stage 7 recount from the run logs). The Chapter III tables 3, 5-10 and Table 15 are compared with a
recount written here from the manifest, data/locomo10.json, the banks, the code and the check files,
without facts.py. Every row must have exactly as many cells as expected. Exit status 1 on any mismatch.
"""
import collections
import json
import math
import os
import pickle
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
os.chdir(REPO)
sys.path.insert(0, REPO)
E = "experiments/factorial8_samples0-3_2026-11-07"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def tables(path):
    body = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml")).find(W + "body")
    out, caption = {}, None
    for el in body:
        if el.tag == W + "p":
            m = re.match(r"^Table (\d+)", "".join(x.text or "" for x in el.iter(W + "t")))
            if m:
                caption = int(m.group(1))
        elif el.tag == W + "tbl":
            out[caption] = [["".join(x.text or "" for x in tc.iter(W + "t")) for tc in tr.iter(W + "tc")] for tr in el.iter(W + "tr")]
    return out


T = tables(sys.argv[1])
X = json.load(open(sys.argv[2]))
MAN = json.load(open(f"{E}/manifest.json"))
SET = list(MAN["setups"])
NAME = dict(zip(SET, ["A-MEM", "T", "C", "H", "T + C", "T + H", "C + H", "All three"]))
INV = {v: k for k, v in NAME.items()}


def rnd(x, d):
    v = math.floor(abs(x) * 10 ** d + 0.5 + 1e-9) / 10 ** d
    return f"{-v if x < 0 and v else v:.{d}f}"


f3 = lambda x: rnd(x, 3)  # noqa: E731
pv = lambda x: "1.000" if x >= 0.9995 else rnd(x, 3).lstrip("0")  # noqa: E731
pct = lambda x: rnd(100 * x, 1) + "%"  # noqa: E731


def sg(x):
    r = rnd(abs(x), 3)
    return "0.000" if r == "0.000" else ("−" if x < 0 else "+") + r


def bd(x):
    return ("−" if x < 0 else "+") + rnd(abs(x), 3)


ok = bad = 0


def chk(where, got, exp):
    global ok, bad
    if got == exp:
        ok += 1
    else:
        bad += 1
        print(f"MISMATCH {where}: doc={got!r} expected={exp!r}")


def row(where, cells, expected):
    if len(cells) != len(expected):
        chk(where + " cell count", len(cells), len(expected))
        return
    for i, (c, e) in enumerate(zip(cells, expected)):
        chk(f"{where} col {i}", c, e)


def rows_of(tn, n):
    r = T[tn][1:]
    chk(f"T{tn} row count", len(r), n)
    return r


# ---------------------------------------------------------------- Chapter IV vs recompute.py
st = X["setups"]
ms = lambda g, s, k: f"{f3(st[g][s][k][0])} ± {f3(st[g][s][k][1])}"  # noqa: E731
mp = lambda g, s, k: f"{pct(st[g][s][k][0])} ± {rnd(100 * st[g][s][k][1], 1)}"  # noqa: E731
vs = lambda g, s, m: next(t for t in X["vs"][g] if t["s"] == s and t["m"] == m)  # noqa: E731
fe = lambda g, e, m: next(t for t in X["fac"][g] if t["e"] == e and t["m"] == m)  # noqa: E731
MN = {"Temporal F1": "time", "Answerable F1": "ans"}
star = lambda t: "*" if t["ph"] < 0.05 else ""  # noqa: E731
ci = lambda t: f"[{bd(t['lo'])}, {bd(t['hi'])}]"  # noqa: E731
MAIN, OTHER = ["s2_t", "s3_c", "s4_h", "s8_tch"], ["s5_tc", "s6_th", "s7_ch"]
for tn, g in ((16, "A"), (24, "DEV")):
    for s, r in zip(SET, rows_of(tn, 8)):
        chk(f"T{tn} name", r[0], NAME[s])
        row(f"T{tn} {r[0]}", r[1:], [ms(g, s, "ans"), ms(g, s, "time"), mp(g, s, "ref"), ms(g, s, "paper"), ms(g, s, "cred")])
for tn, setups in ((17, MAIN), (22, OTHER)):
    exp_rows = [(s, m) for s in setups for m in ("time", "ans")]
    for (s, m), r in zip(exp_rows, rows_of(tn, len(exp_rows))):
        t = vs("A", s, m)
        e = [NAME[s], {"time": "Temporal F1", "ans": "Answerable F1"}[m], sg(t["diff"]), ci(t), pv(t["ph"]), "Yes" if t["ph"] < .05 else "No", f"{t['rb']} of 5"]
        if tn == 17:
            e.append(f"{t['qb']} / {t['qw']}")
        row(f"T{tn} {s} {m}", r, e)
GL = [("A", "Samples 0–3"), ("DEV", "Samples 0–2"), ("S3", "Sample 3")]
EN = {"TxC": "T × C", "TxH": "T × H", "CxH": "C × H", "TxCxH": "T × C × H"}
for tn, effs in ((18, ["T", "C", "H"]), (21, ["TxC", "TxH", "CxH", "TxCxH"])):
    exp_rows = [(g, gl, e) for g, gl in GL for e in effs]
    for (g, gl, e), r in zip(exp_rows, rows_of(tn, len(exp_rows))):
        a, b = fe(g, e, "time"), fe(g, e, "ans")
        row(f"T{tn} {g} {e}", r, [gl if e == effs[0] else "", EN.get(e, e), sg(a["v"]) + star(a), ci(a), pv(a["ph"]), sg(b["v"]) + star(b), ci(b), pv(b["ph"])])
for s, r in zip(SET, rows_of(20, 8)):
    row(f"T20 {s}", r, [NAME[s]] + [f3(st["A"][s][k][0]) for k in ["cat1", "cat2", "cat3", "cat4", "cat5"]])
for s, r in zip(SET, rows_of(23, 8)):
    if s == "s1_amem":
        row("T23 A-MEM", r, [NAME[s], ms("S3", s, "ans"), ms("S3", s, "time"), "—", "—", "—", "—"])
        continue
    a, b = vs("S3", s, "time"), vs("S3", s, "ans")
    row(f"T23 {s}", r, [NAME[s], ms("S3", s, "ans"), ms("S3", s, "time"), f"{sg(a['diff'])}{star(a)} {ci(a)}", pv(a["ph"]), f"{sg(b['diff'])}{star(b)} {ci(b)}", pv(b["ph"])])
exp_rows = [(s, m) for s in MAIN + OTHER for m in ("time", "ans")]
for (s, m), r in zip(exp_rows, rows_of(25, len(exp_rows))):
    a, b = vs("DEV", s, m), vs("S3", s, m)
    row(f"T25 {s} {m}", r, [NAME[s], {"time": "Temporal F1", "ans": "Answerable F1"}[m], f"{sg(a['diff'])}{star(a)} {ci(a)}", pv(a["ph"]), f"{sg(b['diff'])}{star(b)} {ci(b)}", pv(b["ph"])])
for s, r in zip(SET, rows_of(26, 8)):
    row(f"T26 {s}", r, [NAME[s], mp("A", s, "ref"), ms("A", s, "paper"), ms("A", s, "cred"), mp("S3", s, "ref"), ms("S3", s, "paper"), ms("S3", s, "cred")])
for s, r in zip(SET, rows_of(27, 8)):
    row(f"T27 {s}", r, [NAME[s]] + [f3(X["met"][s][k]) for k in ["f1", "exact_match", "rougeL_f", "bleu1", "meteor", "bert_f1", "sbert_similarity"]])
n4 = ok + bad

# ---------------------------------------------------------------- Table 19 vs the Stage 7 recount
R = json.load(open(f"{E}/analysis/extra_recount.json"))
M, G = R["mechanism"], R["merged_ctx"]
smp = [str(s) for s in MAN["samples"]]
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
    lambda i: f"{get(M, 'now_q', i) // len(MAN['seeds']):,}",
    lambda i: share(get(G, "tm", i), get(G, "tq", i)),
    lambda i: share(get(G, "m", i), get(G, "all", i)),
]
for r, fn in zip(rows_of(19, len(rows19)), rows19):
    row(f"T19 {r[0][:40]}", r[1:], [fn(i) for i in smp + ["all"]])
n19 = ok + bad - n4

# ---------------------------------------------------------------- Chapter III tables, recounted here
short = ["A-MEM", "T", "C", "H", "T + C", "T + H", "C + H", "All three"]
for s, nm, r in zip(SET, short, rows_of(3, 8)):
    f = MAN["setups"][s]
    oo = lambda b: "On" if b else "Off"  # noqa: E731
    row(f"T3 {s}", r, [s.split("_")[0], nm, oo(f["time_ranking"]), oo(f["consolidation"]), oo(f["conflict"]), "T-MEM" if f["time_ranking"] else "A-MEM"])
data = json.load(open("data/locomo10.json"))
for idx, r in enumerate(rows_of(5, 5)):
    rows = data[:4] if idx == 4 else [data[idx]]
    sess = turns = 0
    cats = collections.Counter()
    for x in rows:
        c = x["conversation"]
        keys = [k for k in c if k.startswith("session_") and not k.endswith("date_time") and isinstance(c[k], list) and c[k]]
        sess += len(keys)
        turns += sum(len(c[k]) for k in keys)
        cats.update(q["category"] for q in x["qa"])
    spk = "" if idx == 4 else f"{rows[0]['conversation']['speaker_a']} & {rows[0]['conversation']['speaker_b']}"
    row(f"T5 {r[0]}", r, ["Total" if idx == 4 else str(idx), spk, f"{sess:,}", f"{turns:,}", f"{sum(cats.values()):,}"] + [f"{cats[k]:,}" for k in (1, 2, 3, 4, 5)]
        + ["" if idx == 4 else ("Test" if idx == 3 else "Dev.")])
import memory_layer_robust  # noqa: E402,F401
bank = {s: list(pickle.load(open(f"{E}/cache/shared/memory_cache_sample_{s}.pkl", "rb")).values()) for s in range(4)}
raw = {s: [n for n in bank[s] if n.note_type == "raw"] for s in range(4)}
mer = {s: [n for n in bank[s] if n.note_type == "consolidated"] for s in range(4)}
for s, r in zip(range(4), rows_of(6, 4)):
    ns = raw[s]
    row(f"T6 {s}", r, [str(s), f"{len(ns):,}", f"{sum(bool(n.links) for n in ns):,}", rnd(sum(len(n.links) for n in ns) / len(ns), 2),
                       rnd(sum(len(n.keywords) for n in ns) / len(ns), 2), rnd(sum(len(n.tags) for n in ns) / len(ns), 2)])
from memory_layer_tmem_robust import TemporalRetrievalConfig  # noqa: E402
c = TemporalRetrievalConfig()
t7 = {r[0]: r[1] for r in rows_of(7, 7)}
chk("T7 lambda", t7["Decay rate λ (per 30 days)"], f"{c.decay_lambda:.1f}")
chk("T7 alpha", t7["Weight on similarity α"], f"{c.blend_alpha:.1f}")
chk("T7 pool", t7["Notes reranked"], f"Top {c.candidate_pool_size} by similarity")
chk("T7 anchor", t7["Notes fixed in place"], f"Top {c.semantic_anchor_count} by similarity")
chk("T7 margin", t7["Skip when the best note leads by"], f"{c.semantic_margin_to_skip_temporal:.2f} or more")
chk("T7 floor", t7["Recency floor after normalization"], f"{c.temporal_score_floor:.2f}")
chk("T7 cats", t7["Questions affected"], f"Category {', '.join(map(str, c.temporal_categories))} only")
t8 = rows_of(8, 4)
exp8 = [[f"{len(mer[s])}" for s in range(4)],
        [f"{sum(n.status == 'archived' for n in raw[s])}" for s in range(4)],
        [rnd(sum(len(n.source_indices) for n in mer[s]) / len(mer[s]), 2) for s in range(4)],
        [f"{len(raw[s]):,} → {len(bank[s]):,}" for s in range(4)]]
for r, e in zip(t8, exp8):
    row(f"T8 {r[0]}", r[1:], e)
t9 = rows_of(9, 6)
exp9 = [[f"{len(raw[s])}" for s in range(4)],
        [f"{len({n.timeline_id for n in raw[s] if n.timeline_id is not None})}" for s in range(4)],
        [f"{sum(n.timeline_id is not None for n in raw[s])}" for s in range(4)],
        [f"{sum(bool(n.valid_until) for n in raw[s])}" for s in range(4)],
        [f"{sum(bool(n.conflicts_with) for n in raw[s])}" for s in range(4)],
        [f"{sum(bool(n.event_time) for n in raw[s])}" for s in range(4)]]
for r, e in zip(t9, exp9):
    row(f"T9 {r[0]}", r[1:], [f"{int(x):,}" for x in e])
import datetime as dt  # noqa: E402
ev = [n for n in raw[3] if n.event_time]
for n, r in zip(ev, rows_of(10, len(ev))):
    d = dt.datetime.strptime(n.timestamp, "%I:%M %p on %d %B, %Y")
    chk("T10 date", r[0], f"{d.strftime('%B')} {d.day}, {d.year}")
    chk("T10 phrase in note", r[1].lower() in n.content.lower(), True)
    chk("T10 event date", r[2], n.event_time)
n3 = ok + bad - n4 - n19

# ---------------------------------------------------------------- Table 15 vs the check files
a = json.load(open(f"{E}/checks/checks_all.json"))["items"]
waves = [json.load(open(f"{E}/checks/checks_seed{s}.json")) for s in MAN["seeds"]]
per = {len(w["items"]) for w in waves}
assert len(per) == 1 and all(w["ok"] for w in waves)
nper = per.pop()
r15 = {r[0]: r[1] for r in rows_of(15, 8)}
z = lambda pre, pat: sum(int(x) for i in a if i["check"].startswith(pre) for x in re.findall(pat, i["detail"]))  # noqa: E731
chk("T15 runs", r15["Runs (8 setups × 5 seeds)"], f"{len(os.listdir(f'{E}/results'))} of 40 finished")
P_ROWS, P_BAD, P_RETRY, P_DIFF, P_OF, P_MIS = r"^(\d+) rows", r"^(\d+) bad", r"(\d+) retries", r"^(\d+) differ", r"^(\d+) of", r": (\d+)[,}]"
answers = z("R1 ", P_ROWS)
assert answers > 0
chk("T15 answers", r15["Answers (40 runs × 757 questions)"], f"{answers:,}, none empty")
chk("T15 per wave", r15["Checks per wave (R0–R11)"], f"{nper} of {nper} passed in each of the five waves")
chk("T15 final", r15["Final checks across all 40 files"], f"{len(a)} of {len(a)} passed")
assert all(re.search(P_BAD, i["detail"]) and re.search(P_RETRY, i["detail"]) for i in a if i["check"].startswith("R6 "))
chk("T15 R6", r15["Errors, failed answers, and logged retries (R6)"], f"{z('R6 ', P_BAD)} errors or failed answers and {z('R6 ', P_RETRY)} retries in all runs")
assert all(re.search(P_DIFF, i["detail"]) for i in a if i["check"].startswith("R11 "))
chk("T15 R11", r15["Contexts replayed offline (R11)"], f"{answers:,}; {z('R11 ', P_DIFF)} differ from the log")
n10 = {re.search(r"of (\d+) differ", i["detail"]).group(1) for i in a if i["check"].startswith("R10")}
chk("T15 R10", r15["Non-temporal questions, time ranking on vs. off (R10)"], f"{z('R10 ', P_OF)} of {n10.pop()} differ, in every pair and every run")
n9 = {re.match(r"(\d+) trap", i["detail"]).group(1) for i in a if i["check"].startswith("R9")}
assert all(len(re.findall(P_MIS, i["detail"])) == 8 for i in a if i["check"].startswith("R9"))
chk("T15 R9", r15["Adversarial option order (R9)"], f"{z('R9 ', P_MIS)} mismatches in {n9.pop()} questions, all setups and runs")
n15 = ok + bad - n4 - n19 - n3
print(f"Chapter IV tables vs recompute.py: {n4} cells; Table 19 vs extra_recount.json: {n19}; Chapter III tables 3, 5-10: {n3}; Table 15: {n15}")
print(f"cells checked: {ok + bad}, mismatches: {bad}")
sys.exit(1 if bad else 0)
