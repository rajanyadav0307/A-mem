"""Stage 7 check: recount analysis/extra.json by a different route (offline, no AI calls).

extra_analysis.py rebuilds retrieval with the T-MEM classes. This script instead reads what the
runs actually showed the model (the Raw Context records in the run logs), takes merged notes from
the consolidation build logs instead of the memory bank, averages metrics per question instead of
reading aggregate_metrics, and computes the time-ranking margin with its own cosine arithmetic.
The 10 notes each run retrieved are read back from the logged context: each retrieved note is
followed by its linked notes (at most k + 1 of them), so the context can be walked note by note.

Usage (from the repository root):
  HF_HUB_OFFLINE=1 .venv/bin/python experiments/factorial8_samples0-3_2026-11-07/scripts/extra_recount.py EXTRA.json OUT.json
Exits with status 1 if any number differs.
"""
import collections
import json
import os
import pickle
import re
import sys

import numpy as np

E = "experiments/factorial8_samples0-3_2026-11-07"
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
os.chdir(REPO)
sys.path.insert(0, REPO)  # only so the bank pickles can be loaded; no retrieval code is called
os.environ.setdefault("HF_HUB_OFFLINE", "1")
SAMPLES, SEEDS = (0, 1, 2, 3), (42, 43, 44, 45, 46)
SETUPS = ["s1_amem", "s2_t", "s3_c", "s4_h", "s5_tc", "s6_th", "s7_ch", "s8_tch"]
STAMP = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d")


def contexts(setup, seed):
    """Raw Context records of one run log, read line by line (own parser)."""
    out, cur = [], None
    for line in open(f"{E}/logs/{setup}_seed{seed}.log", encoding="utf-8", errors="replace"):
        if STAMP.match(line):
            if cur is not None:
                out.append("".join(cur).rstrip("\n"))
                cur = None
            k = line.find(" - Raw Context: ")
            if k >= 0:
                cur = [line[k + len(" - Raw Context: "):]]
        elif cur is not None:
            cur.append(line)
    if cur is not None:
        out.append("".join(cur).rstrip("\n"))
    return out


def notes(ctx):
    """Split a context into its note blocks; each block starts with 'talk start time:'."""
    return [b for b in ctx.split("talk start time:") if b.strip()]


def render(n):
    return ("talk start time:" + n.timestamp + "memory content: " + n.content + "memory context: " + n.context +
            "memory keywords: " + str(n.keywords) + "memory tags: " + str(n.tags) + "\n")


def top_notes(ctx, raw, k=10):
    """Walk an A-MEM style context and return the render strings of its k retrieved notes."""
    by_text = collections.defaultdict(set)
    for idx, n in enumerate(raw):
        by_text[render(n)].add(idx)
    pos, tops = 0, []
    text = ctx + "\n"
    while pos < len(text.rstrip("\n")):
        cands = [r for r in by_text if text.startswith(r, pos)]
        assert len(cands) == 1, ("retrieved note not found or ambiguous", pos, len(cands))
        r = cands[0]
        nlinks = {len(raw[i].links) for i in by_text[r]}
        assert len(nlinks) == 1, "duplicate notes with different links"
        idx = min(by_text[r])
        tops.append(r)
        pos += len(r)
        for nb in raw[idx].links[: k + 1]:
            assert text.startswith(render(raw[nb]), pos), "linked note not where expected"
            pos += len(render(raw[nb]))
    assert len(tops) == k, ("expected k retrieved notes", len(tops))
    return tops


def note_content(block):
    a = block.find("memory content: ")
    b = block.find("memory context:", a)
    return block[a + len("memory content: "):b] if a >= 0 and b >= 0 else None


def is_now(q):
    """Present-tense rule written out word by word (not the regex in the A-MEM code)."""
    words = re.findall(r"[a-z0-9]+", q.lower())
    text = " " + " ".join(words) + " "
    now_single = {"now", "currently", "current", "still", "nowadays", "latest", "anymore"}
    now_multi = [" these days ", " at the moment ", " any more "]
    hist_single = {"when", "before", "first", "originally", "previously", "initially", "ago", "earlier"}
    hist_multi = [" used to "]
    year = any(words[i] == "in" and len(words[i + 1]) == 4 and words[i + 1][:2] in ("19", "20") and words[i + 1].isdigit()
               for i in range(len(words) - 1))
    now = bool(now_single & set(words)) or any(m in text for m in now_multi)
    hist = bool(hist_single & set(words)) or any(m in text for m in hist_multi) or year
    return now and not hist


def main():
    extra = json.load(open(sys.argv[1]))
    res = {s: json.load(open(f"{E}/results/s1_amem_seed{s}.json"))["individual_results"] for s in SEEDS}
    base = res[42]
    sid = [int(x["sample_id"]) for x in base]
    cat = [int(x["category"]) for x in base]
    qs = [x["question"] for x in base]
    for s in SEEDS:  # every run has the same questions in the same order
        assert [(int(x["sample_id"]), x["question"]) for x in res[s]] == list(zip(sid, qs))

    # merged notes: the rendered blocks of the banks' consolidated notes, matched block by block
    # (extra_analysis.py instead searches each context for the merged note's text)
    merged = {}
    for s in SAMPLES:
        mem = pickle.load(open(f"{E}/cache/shared/memory_cache_sample_{s}.pkl", "rb"))
        merged[s] = {render(n) for n in mem.values() if n.note_type == "consolidated"}

    # time-ranking margin: own cosine over the raw notes of each shared bank
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    raw_emb, raw_notes = {}, {}
    for s in SAMPLES:
        mem = pickle.load(open(f"{E}/cache/shared/memory_cache_sample_{s}.pkl", "rb"))
        n_raw = sum(1 for n in mem.values() if n.note_type != "consolidated")
        emb = np.load(f"{E}/cache/shared/retriever_cache_embeddings_sample_{s}.npy")[:n_raw]
        raw_emb[s] = emb / np.linalg.norm(emb, axis=1, keepdims=True)
        raw_notes[s] = [n for n in mem.values() if n.note_type != "consolidated"]
        assert len(raw_notes[s]) == n_raw

    m = {s: collections.Counter() for s in SAMPLES}
    mc = {s: collections.Counter() for s in SAMPLES}
    for seed in SEEDS:
        kw = json.load(open(f"{E}/keywords/keywords_seed{seed}.json"))["keywords"]
        c1, c2, c3, c4 = (contexts(x, seed) for x in ("s1_amem", "s2_t", "s3_c", "s4_h"))
        assert len(c1) == len(c2) == len(c3) == len(c4) == len(base)
        qi = collections.Counter()
        for i in range(len(base)):
            s = sid[i]
            j = qi[s]
            qi[s] += 1
            words = kw[f"{s}:{j}"]
            m[s]["all_q"] += 1
            m[s]["answerable_q"] += cat[i] != 5
            m[s]["now_q"] += is_now(qs[i])
            m[s]["h_ctx_with_timeline"] += "memory timeline:" in c4[i]
            m[s]["h_ctx_with_outdated"] += "OUTDATED" in c4[i]
            has = any(("talk start time:" + b + ("" if b.endswith("\n") else "\n")) in merged[s] for b in notes(c3[i] + "\n"))
            mc[s]["all"] += 1
            mc[s]["m"] += has
            if cat[i] == 2:
                a, b = top_notes(c1[i], raw_notes[s]), top_notes(c2[i], raw_notes[s])
                m[s]["time_q"] += 1
                m[s]["t_same_set"] += collections.Counter(a) == collections.Counter(b)
                m[s]["t_same_order"] += a == b
                m[s]["t_notes_swapped"] += sum((collections.Counter(a) - collections.Counter(b)).values())
                q = model.encode([words])[0]
                sc = np.sort(raw_emb[s] @ (q / np.linalg.norm(q)))[::-1]
                m[s]["t_margin_skip"] += bool(sc[0] - sc[1] >= 0.05)
                m[s]["h_time_ctx_with_timeline"] += "memory timeline:" in c4[i]
                m[s]["h_time_ctx_with_happened"] += "happened:" in c4[i]
                mc[s]["tq"] += 1
                mc[s]["tm"] += has

    met = {}
    for st in SETUPS:
        per_run = collections.defaultdict(list)
        for seed in SEEDS:
            rows = json.load(open(f"{E}/results/{st}_seed{seed}.json"))["individual_results"]
            keys = rows[0]["metrics"].keys()
            for k in keys:
                per_run[k].append(sum(r["metrics"][k] for r in rows) / len(rows))
        met[st] = {k: sum(v) / len(v) for k, v in sorted(per_run.items())}

    out = {"mechanism": {str(s): dict(sorted(m[s].items())) for s in SAMPLES},
           "merged_ctx": {str(s): {k: mc[s][k] for k in ["all", "m", "tq", "tm"]} for s in SAMPLES},
           "metrics": met}
    with open(sys.argv[2], "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")

    bad = 0
    for part in ("mechanism", "merged_ctx"):
        for s in map(str, SAMPLES):
            for k, v in extra[part][s].items():
                if out[part][s].get(k) != v:
                    bad += 1
                    print(f"DIFF {part} sample {s} {k}: extra={v} recount={out[part][s].get(k)}")
    for st in SETUPS:
        for k, v in extra["metrics"][st].items():
            r = out["metrics"][st].get(k)
            if r is None or abs(r - v) > 1e-9:
                bad += 1
                print(f"DIFF metrics {st} {k}: extra={v} recount={r}")
    n = sum(len(extra[p][s]) for p in ("mechanism", "merged_ctx") for s in extra[p]) + sum(len(v) for v in extra["metrics"].values())
    print(f"compared {n} numbers, differences: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
