"""Stage 7: extra descriptive analyses for the thesis (offline, no AI calls).

Writes analysis/extra.json with three parts:
  mechanism  - how often each module changed what the model saw. Retrieval is rebuilt
               exactly as the evaluators did it (shared banks, shared search words).
  merged_ctx - how many s3_c contexts (from the run logs) contain a merged note.
  metrics    - mean over the five runs of every overall metric in each result file.

Usage (from the repository root):
  HF_HUB_OFFLINE=1 .venv/bin/python experiments/factorial8_samples0-3_2026-11-07/scripts/extra_analysis.py OUT.json
"""
import collections
import contextlib
import io
import json
import os
import pickle
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks  # noqa: E402  (sets cwd to the repository and HF offline)
import common  # noqa: E402
from memory_layer import SimpleEmbeddingRetriever  # noqa: E402
from memory_layer_robust import RobustAgenticMemorySystem, is_now_question  # noqa: E402
from memory_layer_tmem_robust import TemporalAwareRobustAgenticMemorySystem, TemporalRetrievalConfig  # noqa: E402

E = "experiments/factorial8_samples0-3_2026-11-07"
SETUPS = ["s1_amem", "s2_t", "s3_c", "s4_h", "s5_tc", "s6_th", "s7_ch", "s8_tch"]


def mechanism(ds):
    model = SimpleEmbeddingRetriever("all-MiniLM-L6-v2").model

    def system(s, t, c, h):
        cls = TemporalAwareRobustAgenticMemorySystem if t else RobustAgenticMemorySystem
        x = cls.__new__(cls)
        x.memories = pickle.load(open(common.bank_files(s)[0], "rb"))
        r = SimpleEmbeddingRetriever.__new__(SimpleEmbeddingRetriever)
        r.model, r.corpus, r.embeddings, r.document_ids = model, [], None, {}
        with contextlib.redirect_stdout(io.StringIO()):
            x.retriever = r.load(common.bank_files(s)[1], common.bank_files(s)[2])
        if t:
            x.temporal_config = TemporalRetrievalConfig()
        x.consolidation_mode = "primary_expand" if c else "off"
        x.consolidated_top_k_cap = 1 if c else None
        x.consolidated_score_penalty = 0.0
        x.conflict_mode = "annotate_demote" if h else "off"
        x.demote_penalty = 0.10
        x.timeline_date_style = "two_dates"
        return x

    out = {}
    for s in common.SAMPLES:
        a, tt, hh = system(s, 0, 0, 0), system(s, 1, 0, 0), system(s, 0, 0, 1)
        st = collections.Counter()
        for seed in common.SEEDS:
            kw = json.load(open(common.keywords_file(seed)))["keywords"]
            for i, qa in enumerate(ds[s].qa):
                words = kw[f"{s}:{i}"]
                cat = int(qa.category)
                if cat == 2:
                    st["time_q"] += 1
                    with a.raw_only_view():
                        base = a.retriever.search(words, 10)
                    with tt.raw_only_view():
                        tr, sc = tt._rank_memories_temporally(words, 10)
                    base, tr = list(map(int, base)), list(map(int, tr))
                    st["t_same_set"] += set(base) == set(tr)
                    st["t_same_order"] += base == tr
                    st["t_notes_swapped"] += len(set(base) - set(tr))
                    o = sorted(sc[:len(a.memories)], reverse=True)
                    st["t_margin_skip"] += (o[0] - o[1]) >= 0.05
                    hh.current_question = qa.question
                    ctx = hh.find_related_memories_raw(words, k=10)
                    st["h_time_ctx_with_timeline"] += "memory timeline:" in ctx
                    st["h_time_ctx_with_happened"] += "happened:" in ctx
                if is_now_question(qa.question):
                    st["now_q"] += 1
                if cat != 5:
                    st["answerable_q"] += 1
                hh.current_question = qa.question
                ctx = hh.find_related_memories_raw(words, k=10)
                st["h_ctx_with_timeline"] += "memory timeline:" in ctx
                st["h_ctx_with_outdated"] += "OUTDATED" in ctx
                st["all_q"] += 1
        out[str(s)] = {k: int(v) for k, v in sorted(st.items())}
    return out


def merged_ctx():
    r = json.load(open(f"{E}/results/s1_amem_seed42.json"))["individual_results"]
    sid = [int(x["sample_id"]) for x in r]
    cat = [int(x["category"]) for x in r]
    merged = {s: [n.content for n in pickle.load(open(f"{E}/cache/shared/memory_cache_sample_{s}.pkl", "rb")).values()
                  if n.note_type == "consolidated"] for s in common.SAMPLES}
    c = collections.Counter()
    for seed in common.SEEDS:
        ctx = checks.log_fields(f"{E}/logs/s3_c_seed{seed}.log", "Raw Context")
        assert len(ctx) == len(r), (seed, len(ctx))
        for i in range(len(r)):
            s = sid[i]
            has = any(("memory content: " + m) in ctx[i] for m in merged[s])
            c[(s, "all")] += 1
            c[(s, "m")] += has
            if cat[i] == 2:
                c[(s, "tq")] += 1
                c[(s, "tm")] += has
    return {str(s): {k: c[(s, k)] for k in ["all", "m", "tq", "tm"]} for s in common.SAMPLES}


def metrics():
    out = {}
    for s in SETUPS:
        v = {}
        for seed in common.SEEDS:
            agg = json.load(open(f"{E}/results/{s}_seed{seed}.json"))["aggregate_metrics"]["overall"]
            for k, x in agg.items():
                v.setdefault(k, []).append(x["mean"])
        assert all(len(x) == len(common.SEEDS) for x in v.values())
        out[s] = {k: statistics.mean(x) for k, x in sorted(v.items())}
    return out


def main():
    ds = checks.dataset()
    res = {"mechanism": mechanism(ds), "merged_ctx": merged_ctx(), "metrics": metrics()}
    with open(sys.argv[1], "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", sys.argv[1])


if __name__ == "__main__":
    main()
