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
SAMPLES = (0, 1, 2, 3)
SETUPS = ["s1_amem", "s2_t", "s3_c", "s4_h", "s5_tc", "s6_th", "s7_ch", "s8_tch"]
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


def date_dmy(text):
    """'1:56 pm on 8 May, 2023' -> '8 May 2023' (parsed, not retyped)."""
    for fmt in ("%I:%M %p on %d %B, %Y", "%I:%M %p on %d %b, %Y"):
        try:
            d = dt.datetime.strptime(text.strip(), fmt)
            return f"{d.day} {d.strftime('%B')} {d.year}"
        except ValueError:
            pass
    raise ValueError(text)


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
        put(f"d{s}_first_session", date_dmy(conv[f"session_{sess[0]}_date_time"]), src + f".session_{sess[0]}_date_time")
        put(f"d{s}_last_session", date_dmy(conv[f"session_{sess[-1]}_date_time"]), src + f".session_{sess[-1]}_date_time")
        tot["sessions"] += len(sess)
        tot["turns"] += turns
        tot["questions"] += len(x["qa"])
    for k, v in tot.items():
        put(f"d_total_{k}", v, f"{path}[0..3]: sum over samples 0-3")
    put("n_categories", len({int(q["category"]) for s in SAMPLES for q in data[s]["qa"]}), f"{path}[0..3]: distinct question categories")
    put("d_answerable", sum(tot[f"cat{c}"] for c in range(1, 5)), f"{path}[0..3]: categories 1-4")
    put("d_nontemporal", tot["questions"] - tot["cat2"], f"{path}[0..3]: all questions except category 2")
    put("d_temporal_share_pct", 100 * tot["cat2"] / tot["questions"], f"{path}[0..3]: category 2 / all questions")
    ev = {c: [len(q["evidence"]) for s in SAMPLES for q in data[s]["qa"] if int(q["category"]) == c] for c in (1, 4)}
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
        emb = np.load(f"{E}/cache/shared/retriever_cache_embeddings_sample_{s}.npy")
        if s == 0:
            put("embedding_dim", int(emb.shape[1]), f"{E}/cache/shared/retriever_cache_embeddings_sample_0.npy: columns")
        norms = np.linalg.norm(emb, axis=1)
        assert float(np.max(np.abs(norms - 1))) < 1e-4, "embeddings are normalized"


# ---------------------------------------------------------------- build logs
CONS = {0: "analysis/consolidation_log_sample_0_v3.json",
        1: "analysis/consolidation_log_sample_1_v3.json",
        2: "experiments/e2e_samples0-2_2026-10-26_13-10/build_logs/consolidation_log_sample_2_e2e.json",
        3: f"{E}/build_logs/sample3_consolidation_log.json"}
CONF = {0: "experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/build_logs/conflict/conflict_log_sample_0.json",
        1: "experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/build_logs/conflict/conflict_log_sample_1.json",
        2: "experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/build_logs/conflict/conflict_log_sample_2.json",
        3: f"{E}/build_logs/sample3_conflict_log.json"}


def build_logs():
    for s in SAMPLES:
        x = jload(CONS[s])
        groups = x["groups"]
        lab = collections.Counter(g["label"] for g in groups)
        merged = [g for g in groups if g.get("outcome") == "merged"]
        assert len(merged) == x["counts"]["merged"] == F[f"b{s}_merged"]["value"], "merges = bank"
        src = CONS[s]
        put(f"c{s}_groups", x["counts"]["groups"], src + ": counts.groups")
        for l in ("SAME_FACT", "SMALL_TALK", "DIFFERENT"):
            put(f"c{s}_{l}", lab[l], src + f": groups labelled {l}")
        put(f"c{s}_merged", x["counts"]["merged"], src + ": counts.merged")
        put(f"c{s}_merged_small_talk", sum(1 for g in merged if g["label"] == "SMALL_TALK"), src + ": merged groups labelled SMALL_TALK")
        put(f"c{s}_rejected", x["counts"]["rejected"], src + ": counts.rejected")
        put(f"c{s}_llm_calls", x["counts"]["llm_calls"], src + ": counts.llm_calls")
        put(f"c{s}_mean_sources", statistics.mean(len(g["indices"]) for g in merged), src + ": mean source notes per merged group")
        cfg = x["config"]
        if s == 0:
            put("cons_threshold", cfg["similarity_threshold"], src + ": config.similarity_threshold")
            put("cons_max_group", cfg["max_group_size"], src + ": config.max_group_size")
        else:
            assert cfg == jload(CONS[0])["config"], "same consolidation settings in every bank"
    put("c_total_merged", sum(F[f"c{s}_merged"]["value"] for s in SAMPLES), "sum of counts.merged over the four consolidation logs")
    put("c_total_merged_small_talk", sum(F[f"c{s}_merged_small_talk"]["value"] for s in SAMPLES), "sum over the four consolidation logs")

    # worked examples from sample 3, found by a word in the log and printed from the log
    x = jload(CONS[3])
    ex = [g for g in x["groups"] if g.get("outcome") == "merged" and "creamy, rich, dairy-free" in g["consolidated_content"]]
    assert len(ex) == 1
    g = ex[0]
    for i, srcn in enumerate(g["sources"], 1):
        put(f"ex_merge_src{i}_date", date_dmy(srcn["timestamp"]), CONS[3] + f": group {g['indices']} source {i} timestamp")
        put(f"ex_merge_src{i}_text", speech(srcn["content"]), CONS[3] + f": group {g['indices']} source {i} content")
    put("ex_merge_n_sources", len(g["sources"]), CONS[3] + f": group {g['indices']}")
    put("ex_merge_result", g["consolidated_content"], CONS[3] + f": group {g['indices']} consolidated_content")
    put("ex_merge_speaker", re.match(r"^Speaker\s+(.+?)says", g["sources"][0]["content"]).group(1), CONS[3] + ": source speaker")
    dif = [g for g in x["groups"] if g["label"] == "DIFFERENT" and any("first video game tournament" in s["content"] for s in g["sources"]) and any("international tournament" in s["content"] for s in g["sources"])]
    assert len(dif) == 1
    put("ex_different_speaker", re.match(r"^Speaker\s+(.+?)says", dif[0]["sources"][0]["content"]).group(1), CONS[3] + f": DIFFERENT group {dif[0]['indices']}")
    put("ex_different_n", len(dif[0]["sources"]), CONS[3] + f": DIFFERENT group {dif[0]['indices']}")

    for s in SAMPLES:
        x = jload(CONF[s])
        lab = collections.Counter(p["label"] for p in x["pairs"])
        assert lab == collections.Counter(x["labels"]), "pair labels = label counts"
        src = CONF[s]
        put(f"h{s}_tagged", x["state_notes"], src + ": state_notes")
        put(f"h{s}_timelines", len(x["timelines"]), src + ": timelines")
        put(f"h{s}_timeline_notes", sum(len(t["notes"]) for t in x["timelines"]), src + ": notes in timelines")
        for l in ("PROGRESS", "COMPATIBLE", "SAME", "CHANGE", "CONTRADICTION"):
            put(f"h{s}_{l}", lab[l], src + f": pairs labelled {l}")
        put(f"h{s}_verified", x["verification"]["checked"], src + ": verification.checked")
        put(f"h{s}_confirmed", x["verification"]["confirmed"], src + ": verification.confirmed")
        put(f"h{s}_replaced", len(x["replaced"]), src + ": replaced")
        put(f"h{s}_contradictions", len(x["contradictions"]), src + ": contradictions")
        put(f"h{s}_new_calls", x["new_llm_calls"], src + ": new_llm_calls")
        assert F[f"h{s}_replaced"]["value"] == F[f"b{s}_replaced"]["value"], "replaced = bank"
        assert F[f"h{s}_timeline_notes"]["value"] == F[f"b{s}_timeline_notes"]["value"], "timeline notes = bank"
        cfg = x["config"]
        if s == 0:
            put("conf_topic_threshold", cfg["topic_threshold"], src + ": config.topic_threshold")
            put("conf_status_duplicate", cfg["status_duplicate"], src + ": config.status_duplicate")
        else:
            assert cfg == jload(CONF[0])["config"], "same conflict settings in every bank"
    put("h_dev_confirmed", sum(F[f"h{s}_confirmed"]["value"] for s in (0, 1, 2)), "sum of verification.confirmed, samples 0-2")
    put("h_dev_replaced", sum(F[f"h{s}_replaced"]["value"] for s in (0, 1, 2)), "sum of replaced, samples 0-2")
    put("h_total_contradictions", sum(F[f"h{s}_CONTRADICTION"]["value"] for s in SAMPLES), "sum over the four conflict logs")

    x = jload(CONF[3])
    tl = {t["topic"]: t for t in x["timelines"]}
    for key, topic in (("script", "Joanna's movie script"), ("tourn", "Nate's video game tournament")):
        t = tl[topic]
        put(f"ex_tl_{key}_topic", topic, CONF[3] + ": timelines[].topic")
        put(f"ex_tl_{key}_n", len(t["notes"]), CONF[3] + f": timeline '{topic}' notes")
        put(f"ex_tl_{key}_first", t["dates"][0], CONF[3] + f": timeline '{topic}' dates[0]")
        put(f"ex_tl_{key}_last", t["dates"][-1], CONF[3] + f": timeline '{topic}' dates[-1]")


def event_example():
    """The writing-gig label exactly as the model saw it in an s4_h run log, and its source note."""
    import memory_layer_robust  # noqa: F401
    mem = list(pickle.load(open(f"{E}/cache/shared/memory_cache_sample_3.pkl", "rb")).values())
    x = jload(CONF[3])
    t = [t for t in x["timelines"] if t["topic"] == "Joanna's writing gig"][0]
    n = mem[t["notes"][0]]
    m = re.search(r"\byesterday\b", n.content)
    assert m
    put("ex_event_note_date", date_dmy(n.timestamp), f"{E}/cache/shared/memory_cache_sample_3.pkl note {t['notes'][0]} timestamp")
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


# ---------------------------------------------------------------- code
def code():
    from memory_layer_tmem_robust import TemporalRetrievalConfig
    from memory_consolidation import ConsolidationConfig, consolidate_bank, happened_around
    from memory_conflicts import ConflictConfig
    import memory_layer_robust as mlr
    import test_advanced_robust as tar

    c = TemporalRetrievalConfig()
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
    ex = [1, 6]
    put("t_recency_periods", ex, "periods used in the worked recency example")
    put("t_recency_1", math.exp(-c.decay_lambda * ex[0]), "exp(-decay_lambda * periods[0])")
    put("t_recency_6", math.exp(-c.decay_lambda * ex[1]), "exp(-decay_lambda * periods[1])")
    ks = {c[c.index("--retrieve_k") + 1] for c in jload(f"{E}/manifest.json")["commands"].values()}
    assert len(ks) == 1
    put("t_k", int(ks.pop()), f"{E}/manifest.json: commands --retrieve_k")

    cc = ConsolidationConfig()
    assert cc.similarity_threshold == F["cons_threshold"]["value"] and cc.max_group_size == F["cons_max_group"]["value"]
    sig = inspect.signature(consolidate_bank)
    put("cons_temperature", sig.parameters["temperature"].default, "memory_consolidation.py: consolidate_bank(temperature=...)")
    put("cons_retries", sig.parameters["merge_retries"].default, "memory_consolidation.py: consolidate_bank(merge_retries=...)")
    put("cons_attempts", 1 + sig.parameters["merge_retries"].default, "memory_consolidation.py: 1 + merge_retries attempts")

    cf = ConflictConfig()
    assert cf.topic_threshold == F["conf_topic_threshold"]["value"] and cf.status_duplicate == F["conf_status_duplicate"]["value"]
    csrc = inspect.getsource(sys.modules["memory_conflicts"])
    assert "temperature=0.0" in csrc
    put("conf_temperature", 0.0, "memory_conflicts.py: llm.get_completion(..., temperature=0.0)")

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

    # event-date rules: run the function on each expression, said on 9 June 2023
    said = "1:00 pm on 9 June, 2023"
    put("event_anchor", date_dmy(said), "anchor date used for the rule table")
    rules = ["yesterday", "last night", "tomorrow", "tonight", "last week", "next week", "last Friday",
             "next month", "last month", "next year", "last year", "last summer", "three days ago",
             "two months ago", "a year ago", "10 years ago", "a few weeks ago"]
    put("event_rules", rules, "expressions run through happened_around (inputs of the rule table)")
    for r in rules:
        out = happened_around(f"I did it {r}.", said)
        assert out, r
        put("event_" + re.sub(r"\W+", "_", r), out, f"memory_consolidation.py: happened_around('I did it {r}.', '{said}')")


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
    m = re.search(r"checked on (\d+) of (\d+) questions", txt)
    put("offmode_agree", int(m.group(1)), f"{plan}: 'checked on N of M questions'")
    put("offmode_total", int(m.group(2)), f"{plan}: 'checked on N of M questions'")
    m = re.search(r"reached the ([\d,]+) limit", txt)
    put("tpm_limit", int(m.group(1).replace(",", "")), f"{plan}: section 9, token limit")
    m = re.search(r"4 side by side, about ([\d,]+) tokens per minute", txt)
    put("tpm_planned", int(m.group(1).replace(",", "")), f"{plan}: section 9, 4 side by side")


def manifest():
    man = jload(f"{E}/manifest.json")
    src = f"{E}/manifest.json"
    put("model", man["model"], src + ": model")
    assert man["served_model"]["served"] == man["model"]
    put("served_check_date", man["served_model"]["checked"][:10], src + ": served_model.checked")
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
    put("kw_calls", sum(v["questions"] for v in man["keywords"].values()), src + ": keywords[].questions summed")
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
    put("trial_samples", max(1, int(float(tc[tc.index("--ratio") + 1]) * F["data_conversations"]["value"])), "test_advanced_robust.py: max(1, int(conversations x --ratio)), first samples")
    put("half_size", len(man["halves"]["A"]), src + ": halves.A")
    wd = {a["started"][:10] for a in waves}
    assert len(wd) == 1
    d = dt.date.fromisoformat(wd.pop())
    put("waves_date", f"{d.strftime('%B')} {d.day}, {d.year}", src + ": attempts, date of valid waves")
    b0 = jload(f"{E}/build_logs/sample3_base_build_report.json")["3"]
    put("s3_base_seconds", b0["seconds"], f"{E}/build_logs/sample3_base_build_report.json: seconds")
    put("s3_base_warnings", b0["warnings_or_errors"], f"{E}/build_logs/sample3_base_build_report.json: warnings_or_errors")
    st = dt.datetime.strptime(open(f"{E}/build_logs/sample3_started_at.txt").read().strip(), "%Y-%m-%dT%H:%M:%SZ")
    en = dt.datetime.strptime(open(f"{E}/build_logs/sample3_finished_at.txt").read().strip(), "%Y-%m-%dT%H:%M:%SZ")
    put("s3_build_minutes", (en - st).total_seconds() / 60, f"{E}/build_logs/sample3_started_at.txt and sample3_finished_at.txt")
    bs = jload(f"{E}/build_logs/sample3_conflict_build_summary.json")
    put("s3_build_date", bs["created"][:10], f"{E}/build_logs/sample3_conflict_build_summary.json: created")
    d02 = jload("experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/build_logs/conflict/build_summary.json")
    put("dev_banks_date", d02["created"][:10], "experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/build_logs/conflict/build_summary.json: created")
    put("dev_banks_model", d02["model"], "same file: model")
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
        assert now % 5 == 0
        put(f"now_q{s}", now // 5, f"{E}/analysis/extra.json: mechanism.{s}.now_q / 5 runs")
    put("now_q_total", sum(F[f"now_q{s}"]["value"] for s in SAMPLES), "sum of the four")
    from memory_layer_robust import is_now_question
    data = jload("data/locomo10.json")
    nowt = sum(1 for s in SAMPLES for q in data[s]["qa"] if is_now_question(q["question"]) and int(q["category"]) == 2)
    put("now_q_temporal", nowt, "data/locomo10.json samples 0-3: category 2 questions matching is_now_question")
    sm = jload(f"{E}/analysis/summary.json")
    put("boot_reps", sm["method"]["reps"], f"{E}/analysis/summary.json: method.reps")
    put("boot_seed", sm["method"]["rng_seed"], f"{E}/analysis/summary.json: method.rng_seed")
    fam = collections.Counter()
    for g, rows in sm["vs_amem"].items():
        fam["vs_" + g] = len(rows)
    put("fam_factorial", len(sm["factorial"]["samples 0-3"]), f"{E}/analysis/summary.json: factorial['samples 0-3'] rows")
    main = [r for r in sm["vs_amem"]["samples 0-3"] if r["setup"] in ("s2_t", "s3_c", "s4_h", "s8_tch")]
    other = [r for r in sm["vs_amem"]["samples 0-3"] if r["setup"] in ("s5_tc", "s6_th", "s7_ch")]
    put("fam_main", len(main), f"{E}/analysis/summary.json: vs_amem rows for s2, s3, s4, s8")
    put("fam_other", len(other), f"{E}/analysis/summary.json: vs_amem rows for s5, s6, s7")
    put("n_groups", len(sm["setups"]), f"{E}/analysis/summary.json: sample groups")


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
    doc = sys.modules["memory_conflicts"].__doc__ if "memory_conflicts" in sys.modules else __import__("memory_conflicts").__doc__
    labs = re.search(r"\(CONFLICT_CHECK_PROMPT\): ([A-Z, \n]+?) or ([A-Z]+)", doc)
    names = [x.strip() for x in labs.group(1).replace("\n", " ").split(",") if x.strip()] + [labs.group(2)]
    put("conflict_labels", names, "memory_conflicts.py: module docstring, CONFLICT_CHECK_PROMPT labels")
    put("n_conflict_labels", len(names), "memory_conflicts.py: number of labels")
    rw = open(f"{E}/scripts/run_wave.py").read()
    put("poll_seconds", int(re.search(r"time\.sleep\((\d+)\)", rw).group(1)), f"{E}/scripts/run_wave.py: time.sleep")
    x = jload(f"{E}/checks/checks_seed42.json")
    kinds = sorted({i["check"].split()[0] for i in x["items"]}, key=lambda k: int(k[1:]))
    put("check_kinds", len(kinds), f"{E}/checks/checks_seed42.json: kinds of check")
    put("checks_across_files", len(kinds) - F["checks_per_file"]["value"], f"{E}/checks/checks_seed42.json: kinds not run per file (R9, R10)")
    put("check_first", kinds[0], f"{E}/checks/checks_seed42.json")
    put("check_last", kinds[-1], f"{E}/checks/checks_seed42.json")


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
