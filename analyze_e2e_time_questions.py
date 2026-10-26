"""
Why does T-MEM help time questions on some samples but not others?

No LLM calls. Uses the saved results, run logs and memory banks of an
end-to-end run folder (A-MEM vs T-MEM complete) and prints, per sample:
  1. time-question F1 change, split by whether the evidence turn is in a
     conflict-handling timeline and whether it uses a relative time
  2. what the real (logged) prompts contained: evidence found, notes,
     merged notes, timeline labels, OUTDATED labels
  3. retrieval with the question text as the query for A-MEM, V2, V2 + C and
     V2 + C + CH (demote), to see which module changes the evidence found

Example:
    .venv/bin/python analyze_e2e_time_questions.py --dir experiments/e2e_samples0-2_2026-10-26_13-10
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import json
import os
import pickle
import re
import statistics

import numpy as np

from analyze_consolidation_qa import parse_contexts
from evaluate_evidence_recall import context_indices, load_system, note_dia_ids, parse_evidence
from load_dataset import load_locomo_dataset

RELATIVE = re.compile(r"\b(ago|last (week|weekend|month|year|summer|friday|saturday|sunday)|yesterday|"
                      r"next (week|month)|years? old|since)\b", re.I)
LOG_LINE = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+ - INFO - ")


def raw_contexts(path):
    out, buf = [], None
    for line in open(path, encoding="utf-8", errors="replace"):
        if LOG_LINE.match(line):
            if buf is not None:
                out.append("".join(buf))
                buf = None
            body = LOG_LINE.sub("", line)
            if body.startswith("Raw Context: "):
                buf = [body]
        elif buf is not None:
            buf.append(line)
    if buf is not None:
        out.append("".join(buf))
    return out


def f1(row):
    metrics = row["metrics"] if isinstance(row["metrics"], dict) else eval(row["metrics"])  # noqa: S307
    return metrics["f1"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dir", required=True)
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--dataset", default="data/locomo10.json")
    args = parser.parse_args()
    d = args.dir
    ds = load_locomo_dataset(args.dataset)
    seeds = sorted(re.search(r"seed(\d+)", p).group(1) for p in glob.glob(f"{d}/results/amem_seed*.json"))
    A = [json.load(open(f"{d}/results/amem_seed{s}.json"))["individual_results"] for s in seeds]
    T = [json.load(open(f"{d}/results/tmem_complete_seed{s}.json"))["individual_results"] for s in seeds]
    log = lambda tag, s: glob.glob(f"{d}/logs/*_{tag}_s{s}_*.log")[0]  # noqa: E731
    qs = [(smp, qa) for smp in args.samples for qa in ds[smp].qa]
    report = {"seeds": seeds, "samples": {}}

    raw_dia, cons_dia, tl_dia, turn_text = {}, {}, {}, {}
    for smp in args.samples:
        base = list(pickle.load(open(f"{d}/cache/base/memory_cache_sample_{smp}.pkl", "rb")).values())
        for n, c in zip(base, note_dia_ids(ds[smp], base)):
            raw_dia[(smp, n.content)] = c
        conf = list(pickle.load(open(f"{d}/cache/conflict/memory_cache_sample_{smp}.pkl", "rb")).values())
        cov = note_dia_ids(ds[smp], conf)
        tl_dia[smp] = {next(iter(c)) for n, c in zip(conf, cov) if n.note_type == "raw" and n.timeline_id is not None}
        for n, c in zip(conf, cov):
            if n.note_type == "consolidated":
                cons_dia[(smp, n.content)] = c
        turn_text[smp] = {t.dia_id: t.text for s in ds[smp].conversation.sessions.values() for t in s.turns}

    ctx = {tag: [parse_contexts(log(tag, s)) for s in seeds] for tag in ("amem", "tmem_complete")}
    raw = {tag: [raw_contexts(log(tag, s)) for s in seeds] for tag in ("amem", "tmem_complete")}

    for smp in args.samples:
        idx = [i for i, (s2, qa) in enumerate(qs) if s2 == smp and int(qa.category) == 2]
        groups = {}
        prompt = {"A-MEM": {}, "T-MEM": {}}
        for i in idx:
            qa = qs[i][1]
            ev = set(parse_evidence(qa.evidence))
            delta = statistics.mean(f1(T[k][i]) - f1(A[k][i]) for k in range(len(seeds)))
            groups.setdefault("in a timeline" if ev & tl_dia[smp] else "not in a timeline", []).append(delta)
            rel = any(RELATIVE.search(turn_text[smp].get(e, "")) for e in ev)
            groups.setdefault("relative time" if rel else "no relative time", []).append(delta)
            for tag, name in (("amem", "A-MEM"), ("tmem_complete", "T-MEM")):
                for k in range(len(seeds)):
                    notes = ctx[tag][k][i][1]
                    found = set()
                    for c in notes:
                        found |= raw_dia.get((smp, c), set()) | cons_dia.get((smp, c), set())
                    p = prompt[name]
                    p.setdefault("evidence", []).append(len(ev & found) / len(ev) if ev else 0)
                    p.setdefault("notes", []).append(len(notes))
                    p.setdefault("merged", []).append(sum(not c.startswith("Speaker ") for c in notes))
                    p.setdefault("timeline_labels", []).append(raw[tag][k][i].count("memory timeline:"))
                    p.setdefault("outdated", []).append(raw[tag][k][i].count("OUTDATED since"))

        # Retrieval with the question text as query, module by module
        setups = [("A-MEM", "amem", "base", "off", None, "off"), ("V2", "tmem_v2", "base", "off", None, "off"),
                  ("V2 + C", "tmem_v2", "consolidated", "primary_expand", 1, "off"),
                  ("V2 + C + CH (demote)", "tmem_v2", "conflict", "primary_expand", 1, "demote")]
        retrieval = {}
        for label, name, cache, mode, cap, conflict in setups:
            system = load_system(name, f"{d}/cache/{cache}", smp, mode)
            if cap is not None:
                system.consolidated_top_k_cap = cap
            system.conflict_mode = conflict
            cov = note_dia_ids(ds[smp], list(system.memories.values()))
            rec, skipped = [], 0
            for i in idx:
                qa = qs[i][1]
                ev = set(parse_evidence(qa.evidence))
                system.current_question = qa.question
                _, order = context_indices(name, system, qa.question, 10, 2)
                rec.append(len(ev & set().union(*(cov[j] for j in order))) / len(ev) if ev else 0)
                if name == "tmem_v2":
                    view = system.raw_only_view() if mode == "off" else contextlib.nullcontext()
                    with view:
                        sc = system._semantic_scores(qa.question, list(system.memories.values()))
                    o = np.argsort(sc)[::-1]
                    skipped += bool(sc[o[0]] - sc[o[1]] >= system.temporal_config.semantic_margin_to_skip_temporal)
            retrieval[label] = {"evidence": statistics.mean(rec), "time_skipped": skipped}

        report["samples"][str(smp)] = {
            "time_questions": len(idx),
            "groups": {k: {"n": len(v), "mean_delta": statistics.mean(v)} for k, v in groups.items()},
            "prompts": {n: {k: statistics.mean(v) for k, v in p.items()} for n, p in prompt.items()},
            "retrieval_question_query": retrieval,
        }
        r = report["samples"][str(smp)]
        print(f"\n=== sample {smp}: {len(idx)} time questions")
        for k, g in r["groups"].items():
            print(f"   {k:20} n={g['n']:>2}  T-MEM minus A-MEM {g['mean_delta']:+.3f}")
        for n, p in r["prompts"].items():
            print(f"   prompts {n}: evidence {p['evidence']:.3f}, notes {p['notes']:.1f}, merged {p['merged']:.2f}, "
                  f"timeline labels {p['timeline_labels']:.1f}, OUTDATED {p['outdated']:.2f}")
        for label, v in retrieval.items():
            print(f"   retrieval {label:22} evidence {v['evidence']:.3f}, time skipped {v['time_skipped']}")

    out = os.path.join(d, "time_question_analysis.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
