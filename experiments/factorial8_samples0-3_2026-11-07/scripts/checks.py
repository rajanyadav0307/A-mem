"""Automatic checks for the 8-setup test (PLAN.md section 7). No AI calls.

    checks.py build              B1-B5, sample 3 banks
    checks.py keywords           K1-K3, all keyword files
    checks.py inputs --seed N    before a wave
    checks.py results --seed N   R1-R11 after a wave (writes checks/checks_seedN.json)
    checks.py all                every seed, plus cross-run checks (writes checks/checks_all.json)

Exit code 0 only when every check passes.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import re
import shutil
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

sys.path.insert(0, common.REPO)
os.chdir(common.REPO)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

LINE = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+ - (INFO|WARNING|ERROR|DEBUG) - ")
CORE = ("id", "content", "keywords", "tags", "context", "links", "timestamp")
BAD_STDOUT = ("Traceback", "answer_question failed", "failed after", " - ERROR - ", "Error code:", "RateLimitError",
              "Could not load SentenceTransformer")


class Report:
    def __init__(self, name):
        self.name, self.items = name, []

    def check(self, cid, ok, detail=""):
        self.items.append({"check": cid, "ok": bool(ok), "detail": detail})
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid}: {detail}")
        return ok

    @property
    def ok(self):
        return all(i["ok"] for i in self.items)


def dataset():
    from load_dataset import load_locomo_dataset
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        return load_locomo_dataset("data/locomo10.json")


def log_fields(path, name):
    """Multi-line values of 'name: ...' log records, in order."""
    out, buf = [], None
    for line in open(path, encoding="utf-8", errors="replace"):
        if LINE.match(line):
            if buf is not None:
                out.append("".join(buf).rstrip("\n"))
                buf = None
            body = LINE.sub("", line)
            if body.startswith(name + ": "):
                buf = [body[len(name) + 2:]]
        elif buf is not None:
            buf.append(line)
    if buf is not None:
        out.append("".join(buf).rstrip("\n"))
    return out


def first_line(words):
    """The log keeps the first line of the search words on the 'Search words (shared)' line."""
    return words.strip().splitlines()[0].strip() if words.strip() else ""


def load_bank(path):
    with open(path, "rb") as handle:
        return list(pickle.load(handle).values())


# ---------------------------------------------------------------- build (B1-B5)

def check_build(rep):
    ds = dataset()
    b = common.SAMPLE3_BUILD
    paths = {k: os.path.join(b, k, "memory_cache_sample_3.pkl") for k in ("base", "consolidated", "conflict")}
    if not rep.check("B0 files", all(os.path.exists(p) for p in paths.values()), str(paths)):
        return
    base, cons, conf = (load_bank(paths[k]) for k in ("base", "consolidated", "conflict"))
    turns = ["Speaker " + t.speaker + "says : " + t.text for s in ds[3].conversation.sessions.values() for t in s.turns]
    rep.check("B1 629 notes in turn order", len(base) == len(turns) == 629 and [n.content for n in base] == turns,
              f"{len(base)} notes, {len(turns)} turns")
    import numpy as np
    n = len(base)
    same = all(getattr(x, f) == getattr(y, f) for bank in (cons, conf) for x, y in zip(base, bank[:n]) for f in CORE)
    raw_first = all(x.note_type == "raw" for bank in (cons, conf) for x in bank[:n])
    emb = [np.load(os.path.join(b, k, "retriever_cache_embeddings_sample_3.npy")) for k in ("base", "consolidated", "conflict")]
    rep.check("B2 A-MEM notes identical in all 3 banks", same and raw_first and all(np.array_equal(emb[0], e[:n]) for e in emb[1:]),
              f"base {n}, consolidated {len(cons)}, conflict {len(conf)}")
    report = json.load(open(os.path.join(b, "base", "build_report.json")))
    rep.check("B3 0 build warnings or errors", report["3"]["warnings_or_errors"] == 0, json.dumps(report["3"])[:200])
    clog = json.load(open(os.path.join(b, "logs", "consolidation_log_sample_3_f8.json")))
    flog = json.load(open(os.path.join(b, "logs", "conflict", "conflict_log_sample_3.json")))
    rep.check("B4 merged notes and timelines logged", len(cons) - n == clog["counts"]["merged"] and len(flog["timelines"]) > 0,
              f"merged {clog['counts']['merged']}, timelines {len(flog['timelines'])}, replaced {len(flog['replaced'])}")
    from memory_consolidation import happened_around
    from memory_conflicts import note_body
    tl = [x for x in conf if x.timeline_id is not None]
    expected = [happened_around(note_body(x.content), x.timestamp) for x in tl]
    rep.check("B5 'happened' dates filled from relative times", [x.event_time for x in tl] == expected,
              f"{sum(e is not None for e in expected)} of {len(tl)} timeline notes have a 'happened' date")


# ---------------------------------------------------------------- keywords (K1-K3)

def check_keywords(rep, seeds=common.SEEDS):
    m = common.load_manifest()
    for seed in seeds:
        path = common.keywords_file(seed)
        if not rep.check(f"K0 seed {seed} file", os.path.exists(path), path):
            continue
        data = json.load(open(path))
        table = data["keywords"]
        keys = {f"{s}:{i}" for s in common.SAMPLES for i in range(common.QUESTIONS[s])}
        rep.check(f"K1 seed {seed} all 757 questions", set(table) == keys and data.get("seed") == seed,
                  f"{len(table)} entries")
        rep.check(f"K2 seed {seed} no empty words", all(isinstance(v, str) and v.strip() for v in table.values()), "")
        rep.check(f"K3 seed {seed} fingerprint in manifest",
                  m.get("keywords", {}).get(str(seed), {}).get("sha256") == common.sha256(path), "")


# ---------------------------------------------------------------- inputs (before a wave)

def check_inputs(rep, seed):
    m = common.load_manifest()
    for s in common.SAMPLES:
        for f in common.bank_files(s):
            ok = os.path.exists(f) and m["banks"].get(f, {}).get("sha256") == common.sha256(f)
            rep.check(f"I1 bank {os.path.basename(f)}", ok, "" if os.path.exists(f) else "missing")
    kw = common.keywords_file(seed)
    rep.check("I2 keywords fingerprint", os.path.exists(kw) and m["keywords"].get(str(seed), {}).get("sha256") == common.sha256(kw),
              kw if os.path.exists(kw) else f"{kw} missing")
    if os.path.exists(kw):
        table = json.load(open(kw)).get("keywords", {})
        keys = {f"{s}:{i}" for s in common.SAMPLES for i in range(common.QUESTIONS[s])}
        rep.check("I2b search words for all 757 questions, none empty",
                  set(table) == keys and all(isinstance(v, str) and v.strip() for v in table.values()), f"{len(table)} entries")
    import subprocess
    same = subprocess.run(["git", "diff", "--quiet", m["code_commit"], "HEAD", "--", "*.py", "*.sh"],
                          cwd=common.REPO).returncode == 0
    rep.check("I3 code unchanged since the frozen commit", same and not common.python_files_dirty(),
              f"frozen {m['code_commit'][:10]}, HEAD {common.git_commit()[:10]}")
    env = open(os.path.join(common.REPO, ".env")).read() if os.path.exists(os.path.join(common.REPO, ".env")) else ""
    rep.check("I4 API key present", "OPENAI_API_KEY=" in env or bool(os.environ.get("OPENAI_API_KEY")), "")
    free = shutil.disk_usage(common.REPO).free / 1e9
    rep.check("I5 free disk >= 15 GB", free >= 15, f"{free:.0f} GB")
    import subprocess
    batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    rep.check("I6 on mains power", "AC Power" in batt, batt.splitlines()[0] if batt else "")
    existing = [common.result_file(s, seed) for s in common.SETUPS if os.path.exists(common.result_file(s, seed))]
    rep.check("I7 no result files for this seed yet", not existing, ", ".join(existing))


# ---------------------------------------------------------------- results (R1-R11)

def replay_contexts(setup, seed, ds):
    """R11: the context each question should get, from the shared bank and keywords, offline."""
    from memory_layer import SimpleEmbeddingRetriever
    from memory_layer_robust import RobustAgenticMemorySystem
    from memory_layer_tmem_robust import TemporalAwareRobustAgenticMemorySystem, TemporalRetrievalConfig
    t, c, h = common.SETUPS[setup]
    table = json.load(open(common.keywords_file(seed)))["keywords"]
    global _MODEL
    if "_MODEL" not in globals():
        _MODEL = SimpleEmbeddingRetriever("all-MiniLM-L6-v2").model
    out = []
    for s in common.SAMPLES:
        cls = TemporalAwareRobustAgenticMemorySystem if t else RobustAgenticMemorySystem
        system = cls.__new__(cls)
        system.memories = pickle.load(open(common.bank_files(s)[0], "rb"))
        r = SimpleEmbeddingRetriever.__new__(SimpleEmbeddingRetriever)
        r.model, r.corpus, r.embeddings, r.document_ids = _MODEL, [], None, {}
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            system.retriever = r.load(common.bank_files(s)[1], common.bank_files(s)[2])
        if t:
            system.temporal_config = TemporalRetrievalConfig()
        system.consolidation_mode = "primary_expand" if c else "off"
        system.consolidated_top_k_cap = 1 if c else None
        system.consolidated_score_penalty = 0.0
        system.conflict_mode = "annotate_demote" if h else "off"
        system.demote_penalty = 0.10
        system.timeline_date_style = "two_dates"
        for i, qa in enumerate(ds[s].qa):
            system.current_question = qa.question
            words = table[f"{s}:{i}"]
            x = (system.find_related_memories_raw(words, k=10, question_category=int(qa.category)) if t
                 else system.find_related_memories_raw(words, k=10))
            out.append(x.rstrip("\n"))
    return out


def check_results(rep, seed, ds, replay=True):
    m = common.load_manifest()
    order = [(s, qa.question, int(qa.category)) for s in common.SAMPLES for qa in ds[s].qa]
    kw = json.load(open(common.keywords_file(seed)))["keywords"]
    kw_keys = [f"{s}:{i}" for s in common.SAMPLES for i in range(common.QUESTIONS[s])]
    merged = set()
    for s in common.SAMPLES:
        for n in load_bank(common.bank_files(s)[0]):
            if n.note_type == "consolidated":
                merged.add("memory content: " + n.content + "memory context: ")
    contexts, traps = {}, {}
    for setup, (t, c, h) in common.SETUPS.items():
        name = f"{setup} seed {seed}"
        rf, lf = common.result_file(setup, seed), common.log_file(setup, seed)
        sf = lf[:-4] + ".stdout"
        if not rep.check(f"R0 {name} files", all(os.path.exists(p) for p in (rf, lf, sf)), rf):
            continue
        d = json.load(open(rf))
        rows = d["individual_results"]
        got = [(int(r["sample_id"]), r["question"], int(r["category"])) for r in rows]
        rep.check(f"R1 {name} 757 questions in dataset order", d.get("total_questions") == common.TOTAL_QUESTIONS and got == order,
                  f"{len(rows)} rows")
        rep.check(f"R2 {name} no empty answers", all(str(r["prediction"]).strip() for r in rows),
                  f"{sum(not str(r['prediction']).strip() for r in rows)} empty")
        expect = {"model": common.MODEL, "seed": seed, "memories_dir": common.SHARED_BANK,
                  "keywords_file": common.keywords_file(seed), "keywords_sha256": m["keywords"][str(seed)]["sha256"],
                  "consolidation_mode": "primary_expand" if c else "off", "consolidated_top_k_cap": 1 if c else None,
                  "consolidated_score_penalty": 0.0, "memory_layer": "tmem_robust" if t else "robust",
                  "trap_order": "per_question"}
        if h:
            expect.update({"conflict_mode": "annotate_demote", "demote_penalty": 0.1, "timeline_date_style": "two_dates"})
        bad = {k: (d.get(k), v) for k, v in expect.items() if d.get(k) != v}
        if not h and "conflict_mode" in d:
            bad["conflict_mode"] = (d["conflict_mode"], "absent")
        if t and d.get("temporal_config") != common.TEMPORAL_DEFAULTS:
            bad["temporal_config"] = (d.get("temporal_config"), "thesis V2 defaults")
        if not t and "temporal_config" in d:
            bad["temporal_config"] = ("present", "absent")
        rep.check(f"R3 {name} settings match the setup", not bad, json.dumps(bad)[:300] if bad else "")
        f1s = [r["metrics"]["f1"] for r in rows]
        rep.check(f"R4 {name} saved F1 = mean of question F1",
                  abs(d["aggregate_metrics"]["overall"]["f1"]["mean"] - statistics.mean(f1s)) < 1e-12, "")
        log = open(lf, encoding="utf-8", errors="replace").read()
        out = open(sf, encoding="utf-8", errors="replace").read()
        loaded = [int(x) for x in re.findall(r"Successfully loaded (\d+) memories", log)]
        want = [m["banks"][common.bank_files(s)[0]]["notes"] for s in common.SAMPLES]
        rebuild = ("No cached memories found", "Creating new memories", "stale; rebuilding")
        rep.check(f"R5 {name} right memory, no rebuild", loaded == want and not any(x in log + out for x in rebuild),
                  f"loaded {loaded}, expected {want}")
        bad_lines = [ln for ln in (log + out).splitlines()
                     if any(p in ln for p in BAD_STDOUT) and "retrying in" not in ln]
        retries = (log + out).count("retrying in")
        rep.check(f"R6 {name} no errors or failed answers", not bad_lines,
                  f"{len(bad_lines)} bad lines, {retries} retries" + (f"; e.g. {bad_lines[0][:150]}" if bad_lines else ""))
        shared = re.findall(r"Search words \(shared\) (\d+:\d+): (.*)", log)
        rep.check(f"R7 {name} shared search words used for every question",
                  [k for k, _ in shared] == kw_keys and all(v.strip() == first_line(kw[k]) for k, v in shared),
                  f"{len(shared)} questions")
        ctx = log_fields(lf, "Raw Context")
        prompts = log_fields(lf, "User Prompt")
        contexts[setup] = ctx
        traps[setup] = [re.search(r"Select the correct answer: (.*?)  Short answer:", p, re.S).group(1)
                        for p in prompts if "Select the correct answer:" in p]
        has_tl = sum("memory timeline:" in x for x in ctx)
        has_hap = sum("happened:" in x for x in ctx)
        has_merged = sum(any(mm in x for mm in merged) for x in ctx)
        ok8 = (has_tl > 0 and has_hap > 0) if h else (has_tl == 0 and has_hap == 0)
        ok8 = ok8 and ((has_merged > 0) if c else (has_merged == 0))
        rep.check(f"R8 {name} labels and merged notes only where switched on", ok8 and len(ctx) == common.TOTAL_QUESTIONS,
                  f"timeline {has_tl}, happened {has_hap}, merged {has_merged} of {len(ctx)} contexts")
        if replay:
            want_ctx = replay_contexts(setup, seed, ds)
            diff = [i for i, (a, b) in enumerate(zip(ctx, want_ctx)) if a != b]
            rep.check(f"R11 {name} replay: logged notes = offline notes", len(ctx) == len(want_ctx) and not diff,
                      f"{len(diff)} differ" + (f", first at question {diff[0]}" if diff else ""))
    if len(traps) == len(common.SETUPS):
        from shared_keywords import trap_draw
        nm = "Not mentioned in the conversation"
        expected = []
        for s in common.SAMPLES:
            for i, qa in enumerate(ds[s].qa):
                if int(qa.category) == 5:
                    a = qa.final_answer
                    expected.append(f"{nm} or {a}" if trap_draw(seed, s, i) < 0.5 else f"{a} or {nm}")
        wrong = {k: sum(x != y for x, y in zip(v, expected)) + abs(len(v) - len(expected)) for k, v in traps.items()}
        rep.check(f"R9 seed {seed} trap answer order = the fixed per-question order, in all 8 setups",
                  all(n == 0 for n in wrong.values()), f"{len(expected)} trap questions; mismatches {wrong}")
    if len(contexts) == len(common.SETUPS):
        non_time = [i for i, o in enumerate(order) if o[2] != 2]
        for on, off in (("s2_t", "s1_amem"), ("s5_tc", "s3_c"), ("s6_th", "s4_h"), ("s8_tch", "s7_ch")):
            diff = sum(contexts[on][i] != contexts[off][i] for i in non_time)
            rep.check(f"R10 seed {seed} non-time questions: {on} = {off}", diff == 0, f"{diff} of {len(non_time)} differ")


def check_trial(rep, ds):
    """Stage 3: the trial run (s1_amem, sample 0, seed 42) in trial/."""
    d0 = os.path.join(common.EXP, "trial")
    rf, lf, sf = (os.path.join(d0, "s1_amem_seed42_sample0" + x) for x in (".json", ".log", ".stdout"))
    if not rep.check("T0 trial files", all(os.path.exists(p) for p in (rf, lf, sf)), d0):
        return
    d = json.load(open(rf))
    rows = d["individual_results"]
    order = [(0, qa.question, int(qa.category)) for qa in ds[0].qa]
    rep.check("T1 199 questions in dataset order", [(int(r["sample_id"]), r["question"], int(r["category"])) for r in rows] == order, "")
    rep.check("T2 no empty answers", all(str(r["prediction"]).strip() for r in rows), "")
    rep.check("T3 settings", d.get("model") == common.MODEL and d.get("seed") == 42 and d.get("memories_dir") == common.SHARED_BANK
              and d.get("keywords_file") == common.keywords_file(42) and d.get("consolidation_mode") == "off"
              and "conflict_mode" not in d and d.get("memory_layer") == "robust", "")
    log, out = open(lf, errors="replace").read(), open(sf, errors="replace").read()
    kw = json.load(open(common.keywords_file(42)))["keywords"]
    shared = re.findall(r"Search words \(shared\) (\d+:\d+): (.*)", log)
    rep.check("T4 shared words used", [k for k, _ in shared] == [f"0:{i}" for i in range(199)]
              and all(v.strip() == first_line(kw[k]) for k, v in shared), f"{len(shared)} questions")
    bad = [ln for ln in (log + out).splitlines() if any(p in ln for p in BAD_STDOUT) and "retrying in" not in ln]
    rep.check("T5 no errors or failed answers", not bad, bad[0][:150] if bad else "")
    ctx = log_fields(lf, "Raw Context")
    want = replay_contexts("s1_amem", 42, ds)[:199]
    rep.check("T6 replay: logged notes = offline notes", ctx == want, f"{sum(a != b for a, b in zip(ctx, want))} differ")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("what", choices=["build", "keywords", "inputs", "trial", "results", "all"])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(common.SEEDS))
    parser.add_argument("--no_replay", action="store_true")
    args = parser.parse_args()
    os.makedirs(common.CHECKS_DIR, exist_ok=True)
    rep = Report(args.what)
    if args.what == "build":
        check_build(rep)
        out = os.path.join(common.CHECKS_DIR, "build_sample3.json")
    elif args.what == "keywords":
        check_keywords(rep, args.seeds)
        out = os.path.join(common.CHECKS_DIR, "keywords.json")
    elif args.what == "trial":
        check_trial(rep, dataset())
        out = os.path.join(common.CHECKS_DIR, "trial.json")
    elif args.what == "inputs":
        check_inputs(rep, args.seed)
        out = os.path.join(common.CHECKS_DIR, f"inputs_seed{args.seed}.json")
    elif args.what == "results":
        check_results(rep, args.seed, dataset(), replay=not args.no_replay)
        out = os.path.join(common.CHECKS_DIR, f"checks_seed{args.seed}.json")
    else:
        ds = dataset()
        for seed in common.SEEDS:
            check_results(rep, seed, ds, replay=not args.no_replay)
        found = sorted(os.path.basename(p) for p in glob.glob(os.path.join(common.RESULTS_DIR, "*.json")))
        want = sorted(os.path.basename(common.result_file(s, seed)) for s in common.SETUPS for seed in common.SEEDS)
        rep.check("A1 exactly the 40 planned result files", found == want, f"{len(found)} files")
        out = os.path.join(common.CHECKS_DIR, "checks_all.json")
    import datetime
    record = {"what": args.what, "seed": args.seed, "ok": rep.ok, "items": rep.items,
              "when": datetime.datetime.now().isoformat(timespec="seconds"), "code_commit": common.git_commit()}
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=1)
    os.replace(tmp, out)
    with open(os.path.join(common.CHECKS_DIR, "history.jsonl"), "a", encoding="utf-8") as handle:  # never rewritten
        handle.write(json.dumps({k: record[k] for k in ("when", "what", "seed", "ok", "code_commit")} |
                                {"failed": [i["check"] for i in rep.items if not i["ok"]], "file": out}) + "\n")
    print(f"{'ALL PASS' if rep.ok else 'FAILED'} ({sum(i['ok'] for i in rep.items)}/{len(rep.items)}) -> {out}")
    sys.exit(0 if rep.ok else 1)


if __name__ == "__main__":
    main()
