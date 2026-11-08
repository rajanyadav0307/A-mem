"""Facts for thesis Chapters III and IV, read from the source of truth (offline, no AI calls).

Every value the chapters print comes from this file's output, thesis/facts.json. Each entry has
  value  - the number or text
  src    - where it was read (file, and the field, line or command)
Nothing is typed in by hand: every value is read or computed from a file, the code or git.

Sources: the committed experiment folder (manifest, PLAN.md, checks, results, analysis, build logs),
its local logs and banks (cache/, logs/), data/locomo10.json, the code at the frozen commit, and git.

Usage (from the repository root):
  HF_HUB_OFFLINE=1 .venv/bin/python experiments/factorial8_samples0-3_2026-11-07/thesis/facts.py OUT.json
"""
import collections
import datetime as dt
import hashlib
import inspect
import json
import math
import os
import pickle
import re
import statistics
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
os.chdir(REPO)
sys.path.insert(0, REPO)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np  # noqa: E402

E = "experiments/factorial8_samples0-3_2026-11-07"
with open(os.path.join(E, "manifest.json")) as _f:
    _MAN = json.load(_f)
SAMPLES = tuple(_MAN["samples"])
SETUPS = list(_MAN["setups"])
SEEDS = tuple(_MAN["seeds"])
DEV = tuple(SAMPLES[:-1])          # PLAN.md section 1: the last sample (3) is the clean test, the others are development
CODE_FILES = ["memory_layer_robust.py", "memory_layer_tmem_robust.py", "memory_consolidation.py", "memory_conflicts.py",
              "shared_keywords.py", "test_advanced_robust.py", "test_tmem_advanced_robust.py", "utils.py",
              "analyze_consolidation_qa.py", "llm_text_parsers.py", "build_consolidated_cache.py", "build_conflict_bank.py"]
F = {}


def put(key, value, src):
    assert key not in F, f"duplicate fact {key}"
    if isinstance(value, float):
        assert math.isfinite(value), key
    F[key] = {"value": value, "src": src}


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def jload(path):
    with open(path) as f:
        return json.load(f)


def date_us(text):
    """'1:56 pm on 8 May, 2023' or '8 May 2023' -> 'May 8, 2023' (parsed, not retyped)."""
    for fmt in ("%I:%M %p on %d %B, %Y", "%I:%M %p on %d %b, %Y", "%d %B %Y"):
        try:
            d = dt.datetime.strptime(text.strip(), fmt)
            return f"{d.strftime('%B')} {d.day}, {d.year}"
        except ValueError:
            pass
    raise ValueError(text)


def iso_us(text):
    """'2026-11-07...' -> 'November 7, 2026'."""
    d = dt.date.fromisoformat(text[:10])
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def speech(content):
    """Drop the evaluation code's 'Speaker Xsays : ' prefix from a note's text."""
    return re.sub(r"^Speaker\s+.+?says\s*:\s*", "", content)


# ---------------------------------------------------------------- dataset
def dataset():
    path = "data/locomo10.json"
    raw = open(path, "rb").read()
    put("data_file", path, "repository file")
    put("data_sha256_prefix", hashlib.sha256(raw).hexdigest()[:16], f"sha256 of {path}")
    data = json.loads(raw)
    put("data_conversations", len(data), f"{path}: number of conversations")
    tot = collections.Counter()
    for s in SAMPLES:
        x = data[s]
        conv = x["conversation"]
        sess = sorted((int(k.split("_")[1]) for k in conv if re.fullmatch(r"session_\d+", k) and conv[k]))
        turns = sum(len(conv[f"session_{i}"]) for i in sess)
        cats = collections.Counter(int(q["category"]) for q in x["qa"])
        src = f"{path}[{s}]"
        put(f"d{s}_speakers", f"{conv['speaker_a']} & {conv['speaker_b']}", src + ".conversation speaker_a, speaker_b")
        put(f"d{s}_sessions", len(sess), src + ".conversation: non-empty session_N lists")
        put(f"d{s}_turns", turns, src + ".conversation: dialogue turns in all sessions")
        put(f"d{s}_questions", len(x["qa"]), src + ".qa")
        for c in range(1, 6):
            put(f"d{s}_cat{c}", cats[c], src + f".qa with category {c}")
            tot[f"cat{c}"] += cats[c]
        put(f"d{s}_first_session", date_us(conv[f"session_{sess[0]}_date_time"]), src + f".session_{sess[0]}_date_time")
        put(f"d{s}_last_session", date_us(conv[f"session_{sess[-1]}_date_time"]), src + f".session_{sess[-1]}_date_time")
        tot["sessions"] += len(sess)
        tot["turns"] += turns
        tot["questions"] += len(x["qa"])
    for k, v in tot.items():
        put(f"d_total_{k}", v, f"{path}[0..3]: sum over samples 0-3")
    put("n_categories", len({int(q["category"]) for s in SAMPLES for q in data[s]["qa"]}), f"{path}[0..3]: distinct question categories")
    put("d_answerable", sum(tot[f"cat{c}"] for c in range(1, 5)), f"{path}[0..3]: categories 1-4")
    put("d_nontemporal", tot["questions"] - tot["cat2"], f"{path}[0..3]: all questions except category 2")
    put("d_temporal_share_pct", 100 * tot["cat2"] / tot["questions"], f"{path}[0..3]: category 2 / all questions")
    turns_of = lambda q: sum(len([t for t in e.split(";") if t.strip()]) for e in q["evidence"])  # an entry may hold several turns, e.g. 'D8:6; D9:17'
    ev = {c: [turns_of(q) for s in SAMPLES for q in data[s]["qa"] if int(q["category"]) == c] for c in (1, 4)}
    put("ev_cat1_two_plus_pct", 100 * sum(n >= 2 for n in ev[1]) / len(ev[1]), f"{path}[0..3].qa category 1: share with 2+ evidence turns")
    put("ev_cat1_mean", statistics.mean(ev[1]), f"{path}[0..3].qa category 1: mean evidence turns")
    put("ev_cat4_two_plus_pct", 100 * sum(n >= 2 for n in ev[4]) / len(ev[4]), f"{path}[0..3].qa category 4: share with 2+ evidence turns")
    put("ev_cat4_mean", statistics.mean(ev[4]), f"{path}[0..3].qa category 4: mean evidence turns")
    q0 = data[0]["qa"][0]
    assert int(q0["category"]) == 2
    put("example_temporal_question", q0["question"], f"{path}[0].qa[0] (category 2)")
    return data


# ---------------------------------------------------------------- banks
def banks():
    import memory_layer_robust  # noqa: F401  (classes needed to load the pickles)
    man = jload(f"{E}/manifest.json")
    for s in SAMPLES:
        p = f"{E}/cache/shared/memory_cache_sample_{s}.pkl"
        assert hashlib.sha256(open(p, "rb").read()).hexdigest() == man["banks"][p]["sha256"], "bank fingerprint"
        mem = list(pickle.load(open(p, "rb")).values())
        raw = [n for n in mem if n.note_type != "consolidated"]
        merged = [n for n in mem if n.note_type == "consolidated"]
        assert raw == mem[:len(raw)], "raw notes first"
        src = f"{p} (fingerprint = manifest)"
        put(f"b{s}_notes", len(mem), src + ": all notes")
        put(f"b{s}_raw", len(raw), src + ": raw notes")
        put(f"b{s}_merged", len(merged), src + ": consolidated notes")
        put(f"b{s}_with_links", sum(1 for n in raw if n.links), src + ": raw notes with links")
        put(f"b{s}_mean_links", statistics.mean(len(n.links) for n in raw), src + ": mean links per raw note")
        put(f"b{s}_mean_keywords", statistics.mean(len(n.keywords) for n in raw), src + ": mean keywords per raw note")
        put(f"b{s}_mean_tags", statistics.mean(len(n.tags) for n in raw), src + ": mean tags per raw note")
        put(f"b{s}_timeline_notes", sum(1 for n in raw if getattr(n, "timeline_id", None) is not None), src + ": raw notes with a timeline")
        put(f"b{s}_event_dates", sum(1 for n in raw if getattr(n, "event_time", None)), src + ": raw notes with an event date")
        put(f"b{s}_replaced", sum(1 for n in raw if getattr(n, "valid_until", None)), src + ": raw notes marked replaced")
        assert all(n.timeline_id is not None for n in raw if n.event_time), "event dates only on timeline notes"
        put(f"b{s}_timelines", len({n.timeline_id for n in raw if n.timeline_id is not None}), src + ": distinct timeline_id")
        put(f"b{s}_contradictions", sum(1 for n in raw if n.conflicts_with), src + ": raw notes with conflicts_with")
        put(f"b{s}_archived", sum(1 for n in raw if n.status == "archived"), src + ": raw notes archived as sources")
        put(f"b{s}_mean_sources", statistics.mean(len(n.source_indices) for n in merged), src + ": mean source_indices per merged note")
        assert sum(len(n.source_indices) for n in merged) == F[f"b{s}_archived"]["value"], "each source archived once"
        assert all(raw[i].status == "archived" for n in merged for i in n.source_indices)
        emb = np.load(f"{E}/cache/shared/retriever_cache_embeddings_sample_{s}.npy")
        if s == 0:
            put("embedding_dim", int(emb.shape[1]), f"{E}/cache/shared/retriever_cache_embeddings_sample_0.npy: columns")
        norms = np.linalg.norm(emb, axis=1)
        assert float(np.max(np.abs(norms - 1))) < 1e-4, "embeddings are normalized"


# ---------------------------------------------------------------- the sample 3 build (part of this experiment)
CONS3 = f"{E}/build_logs/sample3_consolidation_log.json"
CONF3 = f"{E}/build_logs/sample3_conflict_log.json"


def build_logs():
    s = SAMPLES[-1]
    x = jload(CONS3)
    groups = x["groups"]
    lab = collections.Counter(g["label"] for g in groups)
    out = collections.Counter(g["outcome"] for g in groups)
    merged = [g for g in groups if g["outcome"] == "merged"]
    assert len(merged) == x["counts"]["merged"] == F[f"b{s}_merged"]["value"], "merges in the log = merged notes in the bank"
    put("c3_groups", len(groups), CONS3 + ": groups")
    for l in ("SAME_FACT", "SMALL_TALK", "DIFFERENT"):
        put(f"c3_{l}", lab[l], CONS3 + f": groups labeled {l}")
    put("c3_merged", out["merged"], CONS3 + ": groups with outcome merged")
    put("c3_merged_small_talk", sum(1 for g in merged if g["label"] == "SMALL_TALK"), CONS3 + ": merged groups labeled SMALL_TALK")
    put("c3_rejected", out["rejected"], CONS3 + ": groups with outcome rejected")
    put("c3_llm_calls", x["counts"]["llm_calls"], CONS3 + ": counts.llm_calls")
    assert x["counts"]["llm_calls"] == sum(1 + len(g.get("attempts", [])) for g in groups), "one label call plus one call per merge attempt"
    put("c3_max_attempts", max(len(g.get("attempts", [])) for g in groups), CONS3 + ": most merge attempts in one group")
    longer = 0
    for g in merged:
        used = [a for a in g["attempts"] if a["content"] == g["consolidated_content"]]
        assert used, "the merged note is one of the attempts"
        longer += bool(used[0]["too_long"])
    put("c3_merged_longer", longer, CONS3 + ": merged notes whose accepted attempt was flagged too_long")
    cfg = x["config"]
    put("cons_threshold", cfg["similarity_threshold"], CONS3 + ": config.similarity_threshold")
    put("cons_max_group", cfg["max_group_size"], CONS3 + ": config.max_group_size")
    assert cfg["require_same_speaker"] is True
    put("embedding_model", cfg["embedding_model"], CONS3 + ": config.embedding_model")

    # worked examples, found by a phrase in the log and printed from the log
    ex = [g for g in merged if "creamy, rich, dairy-free" in g["consolidated_content"]]
    assert len(ex) == 1
    g = ex[0]
    put("ex_merge_n_sources", len(g["sources"]), CONS3 + f": group {g['indices']}")
    for i, srcn in enumerate(g["sources"], 1):
        put(f"ex_merge_src{i}_date", date_us(srcn["timestamp"]), CONS3 + f": group {g['indices']} source {i} timestamp")
        put(f"ex_merge_src{i}_text", speech(srcn["content"]), CONS3 + f": group {g['indices']} source {i} content")
    put("ex_merge_result", g["consolidated_content"], CONS3 + f": group {g['indices']} consolidated_content")
    put("ex_merge_speaker", re.match(r"^Speaker\s+(.+?)says", g["sources"][0]["content"]).group(1), CONS3 + ": source speaker")
    dif = [g for g in groups if g["label"] == "DIFFERENT" and any("first video game tournament" in t["content"] for t in g["sources"])
           and any("international tournament" in t["content"] for t in g["sources"])]
    assert len(dif) == 1
    put("ex_different_speaker", re.match(r"^Speaker\s+(.+?)says", dif[0]["sources"][0]["content"]).group(1), CONS3 + f": DIFFERENT group {dif[0]['indices']}")
    put("ex_different_n", len(dif[0]["sources"]), CONS3 + f": DIFFERENT group {dif[0]['indices']}")

    x = jload(CONF3)
    lab = collections.Counter(p["label"] for p in x["pairs"])
    assert lab == collections.Counter(x["labels"]), "pair labels = label counts"
    put("h3_tagged", x["state_notes"], CONF3 + ": state_notes")
    for l in ("PROGRESS", "COMPATIBLE", "SAME", "CHANGE", "CONTRADICTION", "UNRELATED"):
        put(f"h3_{l}", lab[l], CONF3 + f": comparisons labeled {l}")
    put("h3_comparisons", sum(lab.values()), CONF3 + ": comparisons")
    put("h3_verified", x["verification"]["checked"], CONF3 + ": verification.checked")
    put("h3_new_calls", x["new_llm_calls"], CONF3 + ": new_llm_calls")
    assert len(x["timelines"]) == F[f"b{s}_timelines"]["value"] and len(x["replaced"]) == F[f"b{s}_replaced"]["value"]
    assert sum(len(t["notes"]) for t in x["timelines"]) == F[f"b{s}_timeline_notes"]["value"]
    cfg = x["config"]
    put("conf_topic_threshold", cfg["topic_threshold"], CONF3 + ": config.topic_threshold")
    put("conf_status_duplicate", cfg["status_duplicate"], CONF3 + ": config.status_duplicate")
    put("b_dev_replaced", sum(F[f"b{d}_replaced"]["value"] for d in DEV), "banks of the development samples: replaced notes")
    put("b_total_contradictions", sum(F[f"b{d}_contradictions"]["value"] for d in SAMPLES), "all banks: notes with conflicts_with")
    tl = {t["topic"]: t for t in x["timelines"]}
    for key, topic in (("script", "Joanna's movie script"), ("tourn", "Nate's video game tournament")):
        t = tl[topic]
        put(f"ex_tl_{key}_topic", topic, CONF3 + ": timelines[].topic")
        put(f"ex_tl_{key}_n", len(t["notes"]), CONF3 + f": timeline '{topic}' notes")
        put(f"ex_tl_{key}_first", date_us(t["dates"][0]), CONF3 + f": timeline '{topic}' dates[0]")
        put(f"ex_tl_{key}_last", date_us(t["dates"][-1]), CONF3 + f": timeline '{topic}' dates[-1]")


def event_example():
    """The writing-gig label exactly as the model saw it in an s4_h run log, and its source note."""
    import memory_layer_robust  # noqa: F401
    mem = list(pickle.load(open(f"{E}/cache/shared/memory_cache_sample_3.pkl", "rb")).values())
    x = jload(CONF3)
    t = [t for t in x["timelines"] if t["topic"] == "Joanna's writing gig"][0]
    n = mem[t["notes"][0]]
    m = re.search(r"\byesterday\b", n.content)
    assert m
    put("ex_event_speaker", re.match(r"^Speaker\s+(.+?)says", n.content).group(1), f"{E}/cache/shared/memory_cache_sample_3.pkl note {t['notes'][0]} content")
    put("ex_event_note_date", date_us(n.timestamp), f"{E}/cache/shared/memory_cache_sample_3.pkl note {t['notes'][0]} timestamp")
    phrase = re.search(r"[^.!?]*\byesterday\b[^.!?]*", speech(n.content)).group(0).strip()
    put("ex_event_note_phrase", phrase, f"{E}/cache/shared/memory_cache_sample_3.pkl note {t['notes'][0]} content")
    pat = re.compile(r"memory timeline: (Joanna's writing gig, step 1 of [^\n]*?)(?=memory |\n|$)")
    found = set()
    with open(f"{E}/logs/s4_h_seed42.log", encoding="utf-8", errors="replace") as f:
        for line in f:
            for mm in pat.finditer(line):
                found.add(mm.group(1).strip())
    assert len(found) == 1, found
    put("ex_event_label", found.pop(), f"{E}/logs/s4_h_seed42.log: 'memory timeline:' field of that note")
    # every event date stored in the sample 3 bank, with the phrase it came from
    from memory_consolidation import _RELATIVE_TIME_PATTERN, happened_around
    from memory_conflicts import note_body
    rows = []
    for i, n in enumerate(mem):
        if n.note_type == "consolidated" or not n.event_time:
            continue
        body = note_body(n.content)
        m = _RELATIVE_TIME_PATTERN.search(body)
        assert m and happened_around(body, n.timestamp) == n.event_time, f"note {i}: event date reproduces from its first phrase"
        rows.append([date_us(n.timestamp), m.group(0), n.event_time])
    assert len(rows) == F["b3_event_dates"]["value"]
    put("event_rows", rows, f"{E}/cache/shared/memory_cache_sample_3.pkl: raw notes with event_time (said on, first relative phrase, event date); each re-derived by happened_around")


# ---------------------------------------------------------------- code
def code():
    man = jload(f"{E}/manifest.json")
    diff = subprocess.run(["git", "diff", "--quiet", man["code_commit"], "--", *CODE_FILES])
    assert diff.returncode == 0, "code in the working tree differs from the frozen commit"
    from memory_layer_tmem_robust import TemporalRetrievalConfig
    from memory_consolidation import ConsolidationConfig, consolidate_bank, happened_around
    from memory_conflicts import ConflictConfig
    import memory_layer_robust as mlr
    import test_advanced_robust as tar

    c = TemporalRetrievalConfig()
    assert c.decay_age_unit == "months_equiv" and c.use_decay_only_temporal is True, "Equation 1 assumptions"
    src = "memory_layer_tmem_robust.py: TemporalRetrievalConfig"
    put("t_lambda", c.decay_lambda, src + ".decay_lambda")
    put("t_alpha", c.blend_alpha, src + ".blend_alpha")
    put("t_pool", c.candidate_pool_size, src + ".candidate_pool_size")
    put("t_anchor", c.semantic_anchor_count, src + ".semantic_anchor_count")
    put("t_margin", c.semantic_margin_to_skip_temporal, src + ".semantic_margin_to_skip_temporal")
    put("t_floor", c.temporal_score_floor, src + ".temporal_score_floor")
    put("t_categories", list(c.temporal_categories), src + ".temporal_categories")
    put("t_floor_slope", 1.0 - c.temporal_score_floor, "1 - temporal_score_floor (memory_layer_tmem_robust.py, _rank_memories_temporally)")
    tsrc = inspect.getsource(sys.modules["memory_layer_tmem_robust"])
    m = re.search(r"days / ([0-9.]+)", tsrc)
    assert m, "age unit"
    put("t_age_days", float(m.group(1)), "memory_layer_tmem_robust.py: age in days / this value (months_equiv)")
    ks = {c[c.index("--retrieve_k") + 1] for c in jload(f"{E}/manifest.json")["commands"].values()}
    assert len(ks) == 1
    put("t_k", int(ks.pop()), f"{E}/manifest.json: commands --retrieve_k")

    cc = ConsolidationConfig()
    assert cc.similarity_threshold == F["cons_threshold"]["value"] and cc.max_group_size == F["cons_max_group"]["value"]
    sig = inspect.signature(consolidate_bank)
    put("cons_temperature", sig.parameters["temperature"].default, "memory_consolidation.py: consolidate_bank(temperature=...); build_consolidated_cache.py passes none")
    bsrc = open("build_consolidated_cache.py").read()
    assert "temperature=" not in bsrc.split("consolidate_bank(", 1)[1].split(")", 1)[0]
    r = int(re.search(r'"--merge_retries", type=int, default=(\d+)', bsrc).group(1))
    assert "--merge_retries" not in open(f"{E}/scripts/build_sample3.sh").read(), "the sample 3 build used the default"
    put("cons_retries", r, "build_consolidated_cache.py: --merge_retries default, used by scripts/build_sample3.sh")
    assert F["c3_max_attempts"]["value"] <= 1 + r
    import memory_consolidation as mc
    probs = re.findall(r'"(\w+)": ', inspect.getsource(mc._merge_problems).split("return", 1)[1])
    put("n_merge_checks", len(set(probs)), "memory_consolidation.py: distinct keys returned by _merge_problems")
    put("merge_hard_checks", len(set(probs)) - 1, "memory_consolidation.py: consolidate_bank hard_ok uses all keys except too_long")
    assert "too_long" in probs and 'hard_ok = not (problems["missing"] or problems["relative_times"] or problems["dropped_times"])' in inspect.getsource(consolidate_bank)

    cf = ConflictConfig()
    assert cf.topic_threshold == F["conf_topic_threshold"]["value"] and cf.status_duplicate == F["conf_status_duplicate"]["value"]
    csrc = inspect.getsource(sys.modules["memory_conflicts"].cached_calls)
    put("conf_temperature", float(re.search(r"get_completion\(kp\[1\], temperature=([0-9.]+)\)", csrc).group(1)), "memory_conflicts.py: cached_calls, get_completion(temperature=...)")

    put("now_words", mlr.NOW_WORDS.pattern, "memory_layer_robust.py: NOW_WORDS")
    put("history_words", mlr.HISTORY_WORDS.pattern, "memory_layer_robust.py: HISTORY_WORDS")

    asrc = inspect.getsource(tar.RobustAdvancedMemAgent.answer_question)
    put("ans_temp", float(re.findall(r"temperature = (0\.\d+)", asrc)[0]), "test_advanced_robust.py: answer_question, categories 1-4")
    tsrc_all = open("test_advanced_robust.py").read()
    put("ans_temp_c5", float(re.search(r'"--temperature_c5", type=float, default=([0-9.]+)', tsrc_all).group(1)),
        "test_advanced_robust.py: --temperature_c5 default")
    assert "--temperature_c5" not in " ".join(sum(jload(f"{E}/manifest.json")["commands"].values(), [])), "default used"
    put("kw_temp", inspect.signature(mlr.RobustOpenAIController.get_completion).parameters["temperature"].default,
        "memory_layer_robust.py: RobustOpenAIController.get_completion default temperature (search words call passes none)")
    assert re.search(r"self\.retriever_llm\.llm\.get_completion\(prompt\)\n", tsrc_all), "search-word call uses the default"
    put("prompt_c2", re.search(r"(Use DATE of CONVERSATION to answer with an approximate date\.)", asrc).group(1), "test_advanced_robust.py: category 2 prompt")
    put("prompt_c5_option", re.search(r"'(Not mentioned in the conversation)'", asrc).group(1), "test_advanced_robust.py: category 5 option")



# ---------------------------------------------------------------- git, plan, manifest, checks
def history():
    plan = f"{E}/PLAN.md"
    first = git("log", "--diff-filter=A", "--format=%h|%ci", "--", plan).splitlines()[-1].split("|")
    put("plan_commit", first[0], f"git log --diff-filter=A {plan}")
    t = dt.datetime.strptime(first[1][:19], "%Y-%m-%d %H:%M:%S")
    put("plan_time", t.strftime("%H:%M"), f"git log {plan}: commit time")
    put("plan_date", f"{t.strftime('%B')} {t.day}, {t.year}", f"git log {plan}: commit date")
    # analysis section and script unchanged since then
    sec = lambda c: re.search(r"## 8\. Analysis.*?(?=\n## 9\.)", git("show", f"{c}:{plan}"), re.S).group(0)
    assert sec(first[0]) == sec("HEAD"), "plan section 8 changed"
    assert git("log", "--format=%h", f"{first[0]}..HEAD", "--", f"{E}/scripts/analyze.py") == "", "analyze.py changed"
    rc = git("log", "-1", "--format=%h|%an|%ad", "--date=format:%B %-d, %Y", "0c8039f2").split("|")
    put("robust_commit", rc[0], "git log 0c8039f2")
    put("robust_author", rc[1], "git log 0c8039f2: author")
    put("robust_date", rc[2], "git log 0c8039f2: date")
    man = jload(f"{E}/manifest.json")
    put("code_commit", man["code_commit"][:8], f"{E}/manifest.json: code_commit")
    for c, key in ((first[0], "tests_stage0"), (man["code_commit"][:8], "tests_after_fix")):
        msg = git("log", "-1", "--format=%B", c)
        put(key, int(re.search(r"(\d+) pass", msg).group(1)), f"git commit message of {c} (pytest tests/ re-run gives the same count)")
    put("tests_added", F["tests_after_fix"]["value"] - F["tests_stage0"]["value"], "difference of the two counts")
    txt = open(plan).read()
    m = re.search(r"reached the ([\d,]+) limit", txt)
    put("tpm_limit", int(m.group(1).replace(",", "")), f"{plan}: section 9, token limit")
    m = re.search(r"4 side by side, about ([\d,]+) tokens per minute", txt)
    put("tpm_planned", int(m.group(1).replace(",", "")), f"{plan}: section 9, 4 side by side")


def manifest():
    man = jload(f"{E}/manifest.json")
    src = f"{E}/manifest.json"
    put("model", man["model"], src + ": model")
    assert man["served_model"]["served"] == man["model"]
    put("served_check_date", iso_us(man["served_model"]["checked"]), src + ": served_model.checked")
    put("seeds", man["seeds"], src + ": seeds")
    put("n_seeds", len(man["seeds"]), src + ": seeds")
    put("n_setups", len(man["setups"]), src + ": setups")
    put("n_runs", len(man["commands"]), src + ": commands")
    assert all(c[c.index("--trap_order") + 1] == "per_question" for c in man["commands"].values())
    pen = {c[c.index("--demote_penalty") + 1] for c in man["commands"].values() if "--demote_penalty" in c}
    assert len(pen) == 1
    put("demote_penalty", float(pen.pop()), src + ": commands --demote_penalty")
    cap = {c[c.index("--consolidated_top_k_cap") + 1] for c in man["commands"].values() if "--consolidated_top_k_cap" in c}
    assert cap == {"1"}
    put("cons_cap", 1, src + ": commands --consolidated_top_k_cap")
    put("evaluator_amem", sorted({c[1] for k, c in man["commands"].items() if not man["setups"][k.rsplit("_seed", 1)[0]]["time_ranking"]}), src + ": commands, setups with T off")
    put("evaluator_tmem", sorted({c[1] for k, c in man["commands"].items() if man["setups"][k.rsplit("_seed", 1)[0]]["time_ranking"]}), src + ": commands, setups with T on")
    put("cpu", man["computer"]["cpu"], src + ": computer.cpu")
    put("memory_gb", man["computer"]["memory_gb"], src + ": computer.memory_gb")
    put("kw_files", len(man["keywords"]), src + ": keywords")
    put("kw_entries", sum(v["questions"] for v in man["keywords"].values()), src + ": keywords[].questions summed (one entry per question and run)")
    att = man["attempts"]
    trial = [a for a in att if a["stage"] == "trial"][0]
    put("trial_start", trial["started"][11:16], src + ": attempts trial.started")
    bad = [a for a in att if a.get("invalidated")][0]
    first = [a for a in att if a["stage"] == "wave" and a.get("seed") == 42 and "halves" not in a and not a.get("invalidated")][0]
    put("bad_started", first["started"][11:16], src + ": attempts, first wave 42")
    put("bad_finished", first["finished"][11:16], src + ": attempts, first wave 42")
    put("bad_minutes", first["minutes"], src + ": attempts, first wave 42 minutes")
    put("bad_moved", bad["when"][11:16], src + ": attempts, invalidated.when")
    waves = [a for a in att if a["stage"] == "wave" and "halves" in a]
    assert sorted(a["seed"] for a in waves) == man["seeds"]
    put("waves_start", min(a["started"] for a in waves)[11:16], src + ": attempts, valid waves started")
    ends = [h["finished"] for a in waves for h in a["halves"]]
    put("runs_end", max(ends)[11:16], src + ": attempts, valid waves, last half finished")
    put("waves_end", max(a["finished"] for a in waves)[11:16], src + ": attempts, valid waves finished (after their checks)")
    mins = [h["minutes"] for a in waves for h in a["halves"]]
    put("half_min", min(mins), src + ": attempts, halves minutes")
    put("half_max", max(mins), src + ": attempts, halves minutes")
    put("n_halves", len([k for k in man["halves"] if k != "order"]), src + ": halves A and B")
    put("half_A", man["halves"]["A"], src + ": halves.A")
    put("half_B", man["halves"]["B"], src + ": halves.B")
    put("s3_build_stages", len(man["sample3_build"]), src + ": sample3_build (one fingerprint per build stage)")
    tc = trial["command"]
    put("trial_seed", int(tc[tc.index("--seed") + 1]), src + ": attempts trial command --seed")
    put("trial_ratio", float(tc[tc.index("--ratio") + 1]), src + ": attempts trial command --ratio")
    tr = jload(tc[tc.index("--output") + 1])["individual_results"]
    put("trial_samples", len({int(r["sample_id"]) for r in tr}), "trial output file: distinct sample_id")
    put("trial_sample", min(int(r["sample_id"]) for r in tr), "trial output file: sample_id")
    put("half_size", len(man["halves"]["A"]), src + ": halves.A")
    wd = {a["started"][:10] for a in waves}
    assert len(wd) == 1
    put("waves_date", iso_us(wd.pop()), src + ": attempts, date of valid waves")
    b0 = jload(f"{E}/build_logs/sample3_base_build_report.json")["3"]
    put("s3_base_seconds", b0["seconds"], f"{E}/build_logs/sample3_base_build_report.json: seconds")
    put("s3_base_warnings", b0["warnings_or_errors"], f"{E}/build_logs/sample3_base_build_report.json: warnings_or_errors")
    st = dt.datetime.strptime(open(f"{E}/build_logs/sample3_started_at.txt").read().strip(), "%Y-%m-%dT%H:%M:%SZ")
    en = dt.datetime.strptime(open(f"{E}/build_logs/sample3_finished_at.txt").read().strip(), "%Y-%m-%dT%H:%M:%SZ")
    put("s3_build_minutes", (en - st).total_seconds() / 60, f"{E}/build_logs/sample3_started_at.txt and sample3_finished_at.txt")
    bs = jload(f"{E}/build_logs/sample3_conflict_build_summary.json")
    put("s3_build_date", iso_us(bs["created"]), f"{E}/build_logs/sample3_conflict_build_summary.json: created")
    put("s3_base_date", iso_us(b0["finished"]), f"{E}/build_logs/sample3_base_build_report.json: finished")
    put("s3_build_model", bs["model"], f"{E}/build_logs/sample3_conflict_build_summary.json: model")
    bc = jload(f"{E}/checks/build_sample3.json")
    assert bc["ok"]
    put("build_checks", sum(1 for i in bc["items"] if re.match(r"B[1-9]", i["check"])), f"{E}/checks/build_sample3.json: B1-B5")


def checks():
    per_wave = []
    for s in jload(f"{E}/manifest.json")["seeds"]:
        x = jload(f"{E}/checks/checks_seed{s}.json")
        assert x["ok"] and all(i["ok"] for i in x["items"])
        per_wave.append(len(x["items"]))
    assert len(set(per_wave)) == 1
    put("checks_per_wave", per_wave[0], f"{E}/checks/checks_seed42..46.json: items, all ok")
    x = jload(f"{E}/checks/checks_seed42.json")
    kinds = collections.Counter(i["check"].split()[0] for i in x["items"])
    per_file = [k for k, v in kinds.items() if v == len(SETUPS)]
    put("checks_per_file", len(per_file), f"{E}/checks/checks_seed42.json: check kinds run once per result file")
    put("checks_r10_pairs", kinds["R10"], f"{E}/checks/checks_seed42.json: R10 items")
    a = jload(f"{E}/checks/checks_all.json")
    assert a["ok"] and all(i["ok"] for i in a["items"])
    put("checks_final", len(a["items"]), f"{E}/checks/checks_all.json: items, all ok")
    put("checks_final_extra", sum(1 for i in a["items"] if not i["check"].startswith("R")), f"{E}/checks/checks_all.json: checks other than R0-R11 (A1)")
    put("checks_r9_per_wave", sum(1 for i in jload(f"{E}/checks/checks_seed42.json")["items"] if i["check"].startswith("R9")), f"{E}/checks/checks_seed42.json: R9 items")
    r10 = {re.search(r"0 of (\d+) differ", i["detail"]).group(1) for i in a["items"] if i["check"].startswith("R10")}
    assert len(r10) == 1
    put("r10_questions", int(r10.pop()), f"{E}/checks/checks_all.json: R10 details")
    r9 = {re.match(r"(\d+) trap", i["detail"]).group(1) for i in a["items"] if i["check"].startswith("R9")}
    assert len(r9) == 1
    put("r9_questions", int(r9.pop()), f"{E}/checks/checks_all.json: R9 details")
    assert all(i["detail"].startswith("0 differ") for i in a["items"] if i["check"].startswith("R11"))
    assert all(i["detail"].startswith("0 bad lines, 0 retries") for i in a["items"] if i["check"].startswith("R6"))
    assert all(i["detail"] == "0 empty" for i in a["items"] if i["check"].startswith("R2"))
    tot = lambda pref, pat: sum(sum(int(x) for x in re.findall(pat, i["detail"])) for i in a["items"] if i["check"].startswith(pref))
    put("r2_empty_total", tot("R2 ", r"^(\d+) empty"), f"{E}/checks/checks_all.json: R2 details summed")
    put("r6_bad_total", tot("R6 ", r"^(\d+) bad lines"), f"{E}/checks/checks_all.json: R6 bad lines summed")
    put("r6_retries_total", tot("R6 ", r"(\d+) retries"), f"{E}/checks/checks_all.json: R6 retries summed")
    put("r11_differ_total", tot("R11 ", r"^(\d+) differ"), f"{E}/checks/checks_all.json: R11 details summed")
    put("r10_differ_total", tot("R10 ", r"^(\d+) of"), f"{E}/checks/checks_all.json: R10 details summed")
    put("r9_mismatch_total", tot("R9 ", r"'s\d_\w+': (\d+)"), f"{E}/checks/checks_all.json: R9 mismatches summed")
    rows = [i for i in a["items"] if i["check"].startswith("R1 ")]
    put("answers_total", sum(int(i["detail"].split()[0]) for i in rows), f"{E}/checks/checks_all.json: R1 rows summed")
    empt = 0
    for st in SETUPS:
        txt = open(f"{E}/invalid/{st}_seed42_attempt1/reason.txt").read()
        empt += int(re.search(rf"R2 {st} seed 42 no empty answers: (\d+) empty", txt).group(1))
    put("bad_empty", empt, f"{E}/invalid/*_seed42_attempt1/reason.txt: R2 lines summed")


def extra_and_summary():
    x = jload(f"{E}/analysis/extra.json")
    for s in SAMPLES:
        now = x["mechanism"][str(s)]["now_q"]
        assert now % len(SEEDS) == 0
        put(f"now_q{s}", now // len(SEEDS), f"{E}/analysis/extra.json: mechanism.{s}.now_q / runs")
    put("now_q_total", sum(F[f"now_q{s}"]["value"] for s in SAMPLES), "sum of the four")
    from memory_layer_robust import is_now_question
    data = jload("data/locomo10.json")
    nowt = sum(1 for s in SAMPLES for q in data[s]["qa"] if is_now_question(q["question"]) and int(q["category"]) == 2)
    put("now_q_temporal", nowt, "data/locomo10.json samples 0-3: category 2 questions matching is_now_question")
    sm = jload(f"{E}/analysis/summary.json")
    put("boot_reps", sm["method"]["reps"], f"{E}/analysis/summary.json: method.reps")
    put("boot_seed", sm["method"]["rng_seed"], f"{E}/analysis/summary.json: method.rng_seed")
    put("fam_factorial", len(sm["factorial"]["samples 0-3"]), f"{E}/analysis/summary.json: factorial['samples 0-3'] rows")
    main = [r for r in sm["vs_amem"]["samples 0-3"] if r["primary"]]
    other = [r for r in sm["vs_amem"]["samples 0-3"] if not r["primary"]]
    put("fam_main", len(main), f"{E}/analysis/summary.json: vs_amem rows for s2, s3, s4, s8")
    put("fam_other", len(other), f"{E}/analysis/summary.json: vs_amem rows for s5, s6, s7")
    put("n_groups", len(sm["setups"]), f"{E}/analysis/summary.json: sample groups")
    fams = {("vs", bool(r["primary"])) for r in sm["vs_amem"]["samples 0-3"]} | {("factorial", None)}
    put("n_families", len(fams), f"{E}/analysis/summary.json: main tests, other setups (primary flag) and factorial effects")


def analysis_rules():
    """Constants of the fixed analysis, read from scripts/analyze.py and the refusal rule it imports."""
    src = open(f"{E}/scripts/analyze.py").read()
    m = re.search(r'stats\[int\(([0-9.]+) \* REPS\)\], stats\[int\(([0-9.]+) \* REPS\) - 1\]', src)
    put("ci_lo_pct", 100 * float(m.group(1)), f"{E}/scripts/analyze.py: bootstrap lower percentile")
    put("ci_hi_pct", 100 * float(m.group(2)), f"{E}/scripts/analyze.py: bootstrap upper percentile")
    put("ci_level_pct", 100 * (float(m.group(2)) - float(m.group(1))), f"{E}/scripts/analyze.py: interval level")
    al = set(re.findall(r't\["real"\] = a < ([0-9.]+)', src))
    assert len(al) == 1
    put("alpha", float(al.pop()), f"{E}/scripts/analyze.py: t['real'] = a < alpha (Holm-adjusted p)")
    put("alpha_pct", 100 * F["alpha"]["value"], "alpha as a percentage")
    q = open("analyze_consolidation_qa.py").read()
    put("refusal_phrase", re.search(r'"(not mentioned)" in text', q).group(1), "analyze_consolidation_qa.py: classify_cat5")
    put("refusal_min_chars", int(re.search(r"if len\(w\) > (\d+)", q).group(1)) + 1, "analyze_consolidation_qa.py: classify_cat5, words longer than 2 characters")
    put("refusal_share", float(re.search(r"/ len\(words\) >= ([0-9.]+)", q).group(1)), "analyze_consolidation_qa.py: classify_cat5, share of trap words")


def structure():
    """Counts that describe the design and the code paths (read, not typed)."""
    man = jload(f"{E}/manifest.json")
    flags = {k for v in man["setups"].values() for k in v}
    put("n_modules", len(flags), f"{E}/manifest.json: on/off switches per setup")
    put("n_levels", len({b for v in man["setups"].values() for b in v.values()}), f"{E}/manifest.json: values each switch takes")
    put("n_samples", len(man["samples"]), f"{E}/manifest.json: samples")
    put("n_dev_samples", len(man["samples"]) - 1, f"{E}/PLAN.md section 1: samples 0-2 development, sample 3 clean test")
    import memory_layer_robust as mlr
    src = inspect.getsource(mlr.RobustAgenticMemorySystem.process_memory)
    put("evolution_k", int(re.search(r"find_related_memories\(note\.content, k=(\d+)\)", src).group(1)), "memory_layer_robust.py: process_memory, find_related_memories(k=...)")
    put("evolution_calls", src.count("llm.get_completion("), "memory_layer_robust.py: process_memory, language-model calls")
    import llm_text_parsers
    names = list(llm_text_parsers.CONFLICT_LABELS)
    put("conflict_labels", names, "llm_text_parsers.py: CONFLICT_LABELS")
    put("n_conflict_labels", len(names), "memory_conflicts.py: number of labels")
    rw = open(f"{E}/scripts/run_wave.py").read()
    put("poll_seconds", int(re.search(r"time\.sleep\((\d+)\)", rw).group(1)), f"{E}/scripts/run_wave.py: time.sleep")
    x = jload(f"{E}/checks/checks_seed42.json")
    kinds = sorted({i["check"].split()[0] for i in x["items"]}, key=lambda k: int(k[1:]))
    put("check_kinds", len(kinds), f"{E}/checks/checks_seed42.json: kinds of check")
    put("checks_across_files", len(kinds) - F["checks_per_file"]["value"], f"{E}/checks/checks_seed42.json: kinds not run per file (R9, R10)")
    put("check_first", kinds[0], f"{E}/checks/checks_seed42.json")
    put("check_last", kinds[-1], f"{E}/checks/checks_seed42.json")
    plan = open(f"{E}/PLAN.md").read()
    sec6 = re.search(r"## 6\..*?(?=\n## 7\.)", plan, re.S).group(0)
    put("plan_stages", len(re.findall(r"^\| \*\*\d+\*\* \|", sec6, re.M)), f"{E}/PLAN.md section 6: rows of the stage table")


def main():
    dataset()
    banks()
    build_logs()
    event_example()
    code()
    history()
    manifest()
    checks()
    extra_and_summary()
    analysis_rules()
    structure()
    with open(sys.argv[1], "w") as f:
        json.dump(F, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print("wrote", sys.argv[1], len(F), "facts")


if __name__ == "__main__":
    main()
