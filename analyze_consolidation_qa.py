"""
Analyze the repeated QA runs with and without consolidation.

No LLM calls. Reads the result JSONs and the run logs (for the retrieved
context of every question) and reports:
  1. category-5 answer types: "Not mentioned" vs the trap answer
  2. F1 on answerable questions only (categories 1-4), per seed
  3. what the answer prompts contained (notes, unique notes, merged notes)
  4. F1 change split by whether a merged note was in the prompt

Category 5 note: the pipeline scores category 5 against LoCoMo's
``adversarial_answer``, the trap answer, so choosing it raises F1. In most
of these questions the trap answer belongs to the other speaker, so
"Not mentioned in the conversation" is the truthful answer.

Example:
    .venv/bin/python analyze_consolidation_qa.py
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import statistics

from compare_qa_runs import load, per_question_f1

SETUPS = {
    "A-MEM": ("amem_off", "amem_off"),
    "A-MEM + C": ("amem_consolidated", "amem_cons"),
    "T-MEM V2": ("tmem_v2_off", "tmem_off"),
    "T-MEM V2 + C": ("tmem_v2_consolidated", "tmem_cons"),
}
PAIRS = (("A-MEM + C", "A-MEM"), ("T-MEM V2 + C", "T-MEM V2"), ("T-MEM V2", "A-MEM"))
SEEDS = (("42", "", ""), ("43", "_seed43", "_s43"), ("44", "_seed44", "_s44"))
LOG_LINE = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+ - INFO - ")


def classify_cat5(prediction: str, trap: str) -> str:
    text = prediction.lower()
    not_mentioned = "not mentioned" in text
    words = [w for w in re.findall(r"[a-z0-9+']+", trap.lower()) if len(w) > 2]
    trap_hit = bool(words) and sum(w in text for w in words) / len(words) >= 0.5
    if not_mentioned and trap_hit:
        return "both"
    if not_mentioned:
        return "not_mentioned"
    return "trap" if trap_hit else "other"


def parse_contexts(path: str):
    """(category, [note contents]) for every question in a run log."""
    out, buf, category, in_ctx = [], [], None, False

    def flush():
        notes = [n for n in "".join(buf).split("talk start time:") if n.strip()]
        contents = [n.split("memory content: ", 1)[1].split("memory context: ", 1)[0]
                    if "memory content: " in n else n for n in notes]
        out.append((category, contents))

    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if LOG_LINE.match(line):
                if in_ctx:
                    flush()
                    in_ctx, buf = False, []
                body = LOG_LINE.sub("", line)
                if body.startswith("Category: "):
                    category = int(body.split(":")[1])
                elif body.startswith("Raw Context: "):
                    in_ctx, buf = True, [body[len("Raw Context: "):]]
            elif in_ctx:
                buf.append(line)
    if in_ctx:
        flush()
    return out


def find_log(log_dir: str, tag: str) -> str:
    matches = glob.glob(os.path.join(log_dir, f"*ratio0.2_{tag}_2*.log"))
    if len(matches) != 1:
        raise SystemExit(f"expected one log for {tag}, found {matches}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--results_dir", default="experiments/consolidation_qa_samples0-1_gpt-4o-mini/results")
    parser.add_argument("--log_dir", default="logs")
    parser.add_argument("--output", default="experiments/consolidation_qa_samples0-1_gpt-4o-mini/analysis.json")
    args = parser.parse_args()

    results = {lab: [load(os.path.join(args.results_dir, f"{prefix}{suffix}.json"))
                     for _, suffix, _ in SEEDS] for lab, (prefix, _) in SETUPS.items()}
    f1 = {lab: [list(per_question_f1(r).values()) for r in runs] for lab, runs in results.items()}
    contexts = {lab: [parse_contexts(find_log(args.log_dir, f"{tag}{tsuffix}")) for _, _, tsuffix in SEEDS]
                for lab, (_, tag) in SETUPS.items()}
    report = {}

    print("1. Category-5 answer types (mean over 3 seeds, 71 questions)")
    print(f"   {'setup':<14} {'not mentioned':>14} {'trap':>6} {'both':>6} {'other':>6}")
    report["cat5_answer_types"] = {}
    for lab, runs in results.items():
        counts = []
        for run in runs:
            c = collections.Counter(classify_cat5(r["prediction"], r["reference"])
                                    for r in run["individual_results"] if str(r["category"]) == "5")
            counts.append(c)
        avg = {k: statistics.mean(c[k] for c in counts) for k in ("not_mentioned", "trap", "both", "other")}
        report["cat5_answer_types"][lab] = avg
        print(f"   {lab:<14} {avg['not_mentioned']:>14.1f} {avg['trap']:>6.1f} {avg['both']:>6.1f} {avg['other']:>6.1f}")

    print("\n2. F1 on answerable questions (categories 1-4, 233 questions)")
    report["f1_cats_1_4"] = {}
    for lab, runs in f1.items():
        vals = [statistics.mean(x[1] for x in run if x[2] != 5) for run in runs]
        report["f1_cats_1_4"][lab] = vals
        print(f"   {lab:<14} {statistics.mean(vals):.4f} ± {statistics.stdev(vals):.4f}   seeds: "
              + ", ".join(f"{v:.4f}" for v in vals))
    for b, a in PAIRS:
        deltas = [y - x for x, y in zip(report["f1_cats_1_4"][a], report["f1_cats_1_4"][b])]
        print(f"   {b} − {a}: mean {statistics.mean(deltas):+.4f}, seeds "
              + ", ".join(f"{d:+.4f}" for d in deltas) + f" ({sum(d > 0 for d in deltas)}/3 positive)")

    print("\n3. Answer prompts (mean per question, 3 seeds)")
    report["prompts"] = {}
    for lab, runs in contexts.items():
        rows = [row for run in runs for row in run]
        stats = {
            "notes": statistics.mean(len(c) for _, c in rows),
            "unique_notes": statistics.mean(len(set(c)) for _, c in rows),
            "merged_notes": statistics.mean(sum(not n.startswith("Speaker ") for n in c) for _, c in rows),
            "share_with_merged_note": statistics.mean(any(not n.startswith("Speaker ") for n in c) for _, c in rows),
        }
        report["prompts"][lab] = stats
        print(f"   {lab:<14} notes {stats['notes']:5.1f}  unique {stats['unique_notes']:5.1f}  "
              f"merged {stats['merged_notes']:4.2f}  questions with a merged note {stats['share_with_merged_note']:.0%}")

    print("\n4. F1 change by whether a merged note was in the prompt (3 seeds pooled)")
    report["by_merged_note"] = {}
    for b, a in PAIRS[:2]:
        groups = collections.defaultdict(list)
        for seed in range(3):
            for i, ((q_a, f_a, c_a), (q_b, f_b, _)) in enumerate(zip(f1[a][seed], f1[b][seed])):
                cat_ctx, notes = contexts[b][seed][i]
                if q_a != q_b or cat_ctx != c_a:
                    raise SystemExit(f"order mismatch at {b} seed {seed} question {i}")
                merged = any(not n.startswith("Speaker ") for n in notes)
                key = f"{'cat 5' if c_a == 5 else 'cats 1-4'} | {'merged note' if merged else 'no merged note'}"
                groups[key].append(f_b - f_a)
        report["by_merged_note"][f"{b} vs {a}"] = {
            k: {"n": len(v), "mean_delta": statistics.mean(v),
                "better": sum(d > 1e-9 for d in v), "worse": sum(d < -1e-9 for d in v)}
            for k, v in groups.items()}
        print(f"   {b} vs {a}")
        for k in sorted(groups):
            g = report["by_merged_note"][f"{b} vs {a}"][k]
            print(f"      {k:<26} n={g['n']:>4}  mean ΔF1 {g['mean_delta']:+.4f}  better {g['better']:>3}  worse {g['worse']:>3}")

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
