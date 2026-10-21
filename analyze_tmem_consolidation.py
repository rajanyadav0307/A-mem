"""
Analyze how consolidation interacts with T-MEM V2 (samples 0-1, 3 seeds).

No LLM calls. Uses the result JSONs and run logs of
experiments/consolidation_qa_samples0-1_gpt-4o-mini and the v3 consolidated
cache. Prints:
  1. a 2x2 table (A-MEM / T-MEM V2, each with and without consolidation)
     with the consolidation effect, the V2 effect, and their interaction
  2. category-2 F1 change (V2 + C vs V2) by the role of merged notes in the
     prompt, plus the questions that changed most
  3. V2's reranking with merged notes, using the question text as the query
  4. category-2 evidence found in the real logged prompts of all four setups

Example:
    .venv/bin/python analyze_tmem_consolidation.py
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pickle
import statistics

import numpy as np

from analyze_consolidation_qa import classify_cat5, find_log, parse_contexts
from compare_qa_runs import load, per_question_f1
from evaluate_evidence_recall import load_system, note_dia_ids, parse_evidence
from load_dataset import load_locomo_dataset
from memory_layer_tmem_robust import _parse_timestamp

SETUPS = {  # key: (result prefix, log tag)
    "A": ("amem_off", "amem_off"),
    "AC": ("amem_consolidated", "amem_cons"),
    "V": ("tmem_v2_off", "tmem_off"),
    "VC": ("tmem_v2_consolidated", "tmem_cons"),
}
SEEDS = (("", ""), ("_seed43", "_s43"), ("_seed44", "_s44"))
SPLITS = ("overall", "cats 1-4", "cat 1", "cat 2", "cat 3", "cat 4", "cat 5 F1", "cat 5 refusal")


def split_score(f1_rows, raw_rows, split):
    if split == "cat 5 refusal":
        return statistics.mean(classify_cat5(r["prediction"], r["reference"]) == "not_mentioned"
                               for r in raw_rows if str(r["category"]) == "5")
    keep = {"overall": lambda c: True, "cats 1-4": lambda c: c != 5, "cat 1": lambda c: c == 1,
            "cat 2": lambda c: c == 2, "cat 3": lambda c: c == 3, "cat 4": lambda c: c == 4,
            "cat 5 F1": lambda c: c == 5}[split]
    return statistics.mean(f1 for _, f1, c in f1_rows if keep(c))


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--results_dir", default="experiments/consolidation_qa_samples0-1_gpt-4o-mini/results")
    parser.add_argument("--log_dir", default="logs")
    parser.add_argument("--base_cache", default="cached_memories_robust_openai_gpt-4o-mini")
    parser.add_argument("--cons_cache", default="cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80_v3")
    parser.add_argument("--dataset", default="data/locomo10.json")
    parser.add_argument("--output", default="experiments/consolidation_qa_samples0-1_gpt-4o-mini/analysis_tmem_v2.json")
    args = parser.parse_args()

    raw = {k: [load(os.path.join(args.results_dir, p + s + ".json"))["individual_results"] for s, _ in SEEDS]
           for k, (p, _) in SETUPS.items()}
    f1 = {k: [list(per_question_f1({"individual_results": r}).values()) for r in runs] for k, runs in raw.items()}
    ctx = {k: [parse_contexts(find_log(args.log_dir, tag + t)) for _, t in SEEDS] for k, (_, tag) in SETUPS.items()}
    ds = load_locomo_dataset(args.dataset)
    questions = [(smp, qa) for smp in (0, 1) for qa in ds[smp].qa]
    report = {}

    # 1. 2x2 table and interaction
    print("1. 2x2: mean over 3 seeds. Interaction = (V2+C - A-MEM+C) - (V2 - A-MEM)")
    print(f"   {'split':<14}{'A-MEM':>8}{'V2':>8}{'A-MEM+C':>9}{'V2+C':>8} | {'C on A':>8}{'C on V2':>8}"
          f"{'V2 eff':>8}{'V2|C':>8}{'interact':>9}  per seed")
    report["two_by_two"] = {}
    for split in SPLITS:
        per = {k: [split_score(f1[k][s], raw[k][s], split) for s in range(3)] for k in SETUPS}
        m = {k: statistics.mean(v) for k, v in per.items()}
        inter = [(per["VC"][s] - per["AC"][s]) - (per["V"][s] - per["A"][s]) for s in range(3)]
        report["two_by_two"][split] = {"means": m, "interaction_per_seed": inter}
        print(f"   {split:<14}{m['A']:>8.4f}{m['V']:>8.4f}{m['AC']:>9.4f}{m['VC']:>8.4f} | "
              f"{m['AC'] - m['A']:>+8.4f}{m['VC'] - m['V']:>+8.4f}{m['V'] - m['A']:>+8.4f}{m['VC'] - m['AC']:>+8.4f}"
              f"{statistics.mean(inter):>+9.4f}  " + ", ".join(f"{x:+.3f}" for x in inter))

    # Map note content -> dia_ids, for raw and consolidated notes.
    raw_dia, cons_dia = {}, {}
    for smp in (0, 1):
        base = list(load_system("amem", args.base_cache, smp, "off").memories.values())
        for note, cov in zip(base, note_dia_ids(ds[smp], base)):
            raw_dia[(smp, note.content)] = cov
        with open(os.path.join(args.cons_cache, f"memory_cache_sample_{smp}.pkl"), "rb") as handle:
            cons = list(pickle.load(handle).values())
        for note, cov in zip(cons, note_dia_ids(ds[smp], cons)):
            if note.note_type == "consolidated":
                cons_dia[(smp, note.content)] = cov

    # 2. Category-2 change by merged-note role
    print("\n2. Category 2, V2 + C vs V2, by merged notes in the V2 + C prompt (3 seeds pooled)")
    groups, per_q = collections.defaultdict(list), collections.defaultdict(list)
    for s in range(3):
        for i, (smp, qa) in enumerate(questions):
            if int(qa.category) != 2:
                continue
            cat, notes = ctx["VC"][s][i]
            assert cat == 2 and f1["VC"][s][i][0] == f1["V"][s][i][0] == qa.question
            merged = [n for n in notes if not n.startswith("Speaker ")]
            evidence = set(parse_evidence(qa.evidence))
            holds = any(cons_dia.get((smp, m), set()) & evidence for m in merged)
            key = ("merged note holds evidence" if holds
                   else "merged note, not evidence" if merged else "no merged note")
            delta = f1["VC"][s][i][1] - f1["V"][s][i][1]
            groups[key].append(delta)
            per_q[i].append((delta, raw["V"][s][i]["prediction"], raw["VC"][s][i]["prediction"]))
    report["cat2_by_merged_note"] = {}
    for key, vals in sorted(groups.items()):
        g = {"n": len(vals), "mean_delta": statistics.mean(vals),
             "better": sum(d > 1e-9 for d in vals), "worse": sum(d < -1e-9 for d in vals)}
        report["cat2_by_merged_note"][key] = g
        print(f"   {key:<28} n={g['n']:>3}  mean dF1 {g['mean_delta']:+.4f}  better {g['better']:>2}  worse {g['worse']:>2}")
    ranked = sorted((statistics.mean(d for d, _, _ in v), i) for i, v in per_q.items())
    report["cat2_extremes"] = []
    for label, chosen in (("worse", ranked[:5]), ("better", ranked[::-1][:5])):
        for mean_delta, i in chosen:
            qa = questions[i][1]
            item = {"direction": label, "mean_delta": mean_delta, "question": qa.question, "reference": qa.final_answer,
                    "v2": [p for _, p, _ in per_q[i]], "v2_c": [p for _, _, p in per_q[i]]}
            report["cat2_extremes"].append(item)
            print(f"   [{label}] {mean_delta:+.2f} {qa.question} | ref: {qa.final_answer}\n"
                  f"        V2  : {[p[:40] for p in item['v2']]}\n        V2+C: {[p[:40] for p in item['v2_c']]}")

    # 3. V2 reranking mechanics with merged notes (question text as query)
    print("\n3. V2 reranking with merged notes (category 2, question text as query)")
    mech = collections.Counter()
    for smp in (0, 1):
        system = load_system("tmem_v2", args.cons_cache, smp, "primary_expand")
        system.consolidated_top_k_cap = 1
        notes = list(system.memories.values())
        for qa in ds[smp].qa:
            if int(qa.category) != 2:
                continue
            mech["questions"] += 1
            scores = system._semantic_scores(qa.question, notes)
            order = np.argsort(scores)[::-1]
            if scores[order[0]] - scores[order[1]] >= system.temporal_config.semantic_margin_to_skip_temporal:
                mech["time skipped (clear semantic winner)"] += 1
                continue
            mech["time applied"] += 1
            pool = [int(i) for i in order[:system.temporal_config.candidate_pool_size] if np.isfinite(scores[i])]
            merged = [i for i in pool if notes[i].note_type == "consolidated"]
            mech["merged note in top-20 pool"] += bool(merged)
            seeds, _ = system._rank_memories_temporally(qa.question, 10)
            semantic_top = [int(i) for i in order[:10]]
            for m in merged:
                mech["merged note in final top-10"] += m in seeds
                mech["merged note moved INTO top-10 by time"] += (m in seeds) and (m not in semantic_top)
                mech["merged note moved OUT of top-10 by time"] += (m not in seeds) and (m in semantic_top)
    ages = []
    for smp in (0, 1):
        notes = list(load_system("tmem_v2", args.cons_cache, smp, "off").memories.values())
        t_end = max(_parse_timestamp(n.timestamp) for n in notes)
        for n in notes:
            if n.note_type == "consolidated":
                ages.append(((t_end - _parse_timestamp(n.first_seen)).days / 30.0,
                             (t_end - _parse_timestamp(n.last_seen)).days / 30.0))
    decay = lambda months: float(np.exp(-0.1 * months))  # noqa: E731 - thesis default lambda
    mech_report = dict(mech)
    mech_report.update({
        "merged_notes": len(ages),
        "mean_age_months_earliest_source": statistics.mean(a for a, _ in ages),
        "mean_age_months_merged_note": statistics.mean(b for _, b in ages),
        "mean_decay_earliest_source": statistics.mean(decay(a) for a, _ in ages),
        "mean_decay_merged_note": statistics.mean(decay(b) for _, b in ages),
    })
    report["v2_mechanics"] = mech_report
    for key, value in mech_report.items():
        print(f"   {key}: {value:.3f}" if isinstance(value, float) else f"   {key}: {value}")

    # 4. Category-2 evidence in the real logged prompts
    print("\n4. Category-2 evidence found in the real prompts (mean over 63 questions x 3 seeds)")
    names = {"A": "A-MEM", "AC": "A-MEM + C", "V": "T-MEM V2", "VC": "T-MEM V2 + C"}
    report["cat2_evidence_in_prompt"] = {}
    for key in SETUPS:
        rates = []
        for s in range(3):
            for i, (smp, qa) in enumerate(questions):
                if int(qa.category) != 2:
                    continue
                evidence = set(parse_evidence(qa.evidence))
                found = set()
                for content in ctx[key][s][i][1]:
                    found |= raw_dia.get((smp, content), set()) | cons_dia.get((smp, content), set())
                if evidence:
                    rates.append(len(evidence & found) / len(evidence))
        report["cat2_evidence_in_prompt"][names[key]] = statistics.mean(rates)
        print(f"   {names[key]:<14} {statistics.mean(rates):.3f}")

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
