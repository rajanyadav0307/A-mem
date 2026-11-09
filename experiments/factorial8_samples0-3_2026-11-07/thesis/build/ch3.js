// Chapter III. Every number and quoted value enters through N, W, D, P, X or V (lib.js), which read
// thesis/facts.json and the experiment manifest. Each paragraph's "src" comment names where its claims
// can be checked. Only the November 7, 2026 experiment is the source of truth.
const fs = require("fs");
const { chapter, h1, h2, p, item, eq, table, figure, fact, rnd, asCount, cap, N, W, Wc, D, P, X, V, REFS, nextFigure } = require("./lib");
const FIG = process.env.FIGDIR;
const M = JSON.parse(fs.readFileSync(process.env.MANIFEST));
const T = { setups: 3, rqs: 4, locomo: 5, banks: 6, time: 7, cons: 8, conf: 9, event: 10, settings: 11, stages: 12, checks: 13, families: 14 };
const out = [];
const add = (...xs) => xs.forEach((x) => (Array.isArray(x) ? out.push(...x) : out.push(x)));
function tbl(key, ...args) { const [els, n] = table(...args); if (n !== T[key]) throw new Error(`table ${key} is ${n}, expected ${T[key]}`); add(els); }
const must = (cond, msg) => { if (!cond) throw new Error("source does not support the sentence: " + msg); return ""; };
const SMP = M.samples;                                   // sample numbers, from the manifest
const S4 = SMP;
const DEVS = SMP.slice(0, -1), TEST = SMP[SMP.length - 1]; // PLAN.md section 1: samples 0-2 development, sample 3 clean test
const sid = (s) => V(String(s), "manifest samples");
const sname = (s) => `Sample ${sid(s)}`;
const devRange = () => `${sid(DEVS[0])}–${sid(DEVS[DEVS.length - 1])}`;
const allRange = () => `${sid(SMP[0])}–${sid(SMP[SMP.length - 1])}`;
const lv = () => Array(fact("n_modules")).fill(null).map(() => V(String(fact("n_levels")), "n_levels")).join(" × ");
const list = (xs) => (xs.length === 2 ? `${xs[0]} and ${xs[1]}` : `${xs.slice(0, -1).join(", ")}, and ${xs[xs.length - 1]}`);
const alt = (k, w) => { must(new RegExp(`[(|]${w}[|)]`).test(fact(k)), `${w} in ${k}`); return V(w, k); };
REFS.consTable = T.cons;
REFS.setupsTable = T.setups;
must(fact("n_seeds") === M.seeds.length && fact("n_samples") === SMP.length, "manifest");

add(chapter("III", "METHODOLOGY"));
// src: structure of this chapter
add(p("This chapter describes how the study was carried out: the research design and research questions, the benchmark data, the baseline system, the T-MEM modules, the memory banks, the procedure for running the experiment, the checks applied to every run, and the measures and statistical procedures. Every setting reported here was read from the source code at the commit named in the text, from the experiment's plan and manifest, or from the logs and files written during the experiment."));
// src: GHTC 2026 presentation (external to this experiment; not drawn from the manifest or plan)
const ghtcRange = () => `${sid(SMP[0])}–${sid(SMP[1])}`;
add(p(`An earlier, narrower evaluation of the time-ranking module alone, on samples ${ghtcRange()}, was presented at GHTC 2026, in Boulder, Colorado, on October 8, 2026 (Yadav & Kumar, 2026); that paper has not been published. This chapter and the next report a full, end-to-end evaluation of all ${W("n_modules")} T-MEM modules (time ranking, consolidation, and conflict handling), run on samples ${allRange()}.`));

// ------------------------------------------------------------------ design
add(h1("Research Design and Rationale"));
// src: manifest.json setups (three switches, on/off); test_advanced_robust.py with every switch off is A-MEM
add(p(`The study used a full ${lv()} factorial design. Each of the ${W("n_modules")} T-MEM modules (time ranking, T; consolidation, C; and conflict handling, H) was a factor with ${W("n_levels")} levels, off and on, and all ${W("n_setups")} combinations were run. The combination with every module off is A-MEM itself (W. Xu et al., 2025), run with its own code and settings. Table ${T.setups} lists the ${W("n_setups")} setups and the names used for them in the rest of the thesis.`));
// src: design rationale (Montgomery, 2017)
add(p("A factorial design was chosen over adding the modules one at a time. When modules are added in a fixed order, the measured effect of a later module depends on which modules are already present, and the effect of a module on its own is never observed. A factorial design gives three kinds of answer from the same runs: the effect of each module alone against A-MEM, the average effect of each module over all settings of the other modules, and the interactions, which show whether the effect of one module depends on whether another is on (Montgomery, 2017)."));
{
  const ids = Object.keys(M.setups);
  const short = { s1_amem: "A-MEM", s2_t: "T", s3_c: "C", s4_h: "H", s5_tc: "T + C", s6_th: "T + H", s7_ch: "C + H", s8_tch: "All three" };
  must(JSON.stringify(ids) === JSON.stringify(Object.keys(short)), "setup ids");
  const onoff = (b) => (b ? "On" : "Off");
  const amem = fact("evaluator_amem"), tmem = fact("evaluator_tmem");
  must(amem.length === 1 && tmem.length === 1, "one evaluation script per group");
  tbl("setups", `The ${V(cap(asCount(fact("n_setups"))), "n_setups")} Setups of the Factorial Design`,
    ["Setup", "Short name", "Time ranking (T)", "Consolidation (C)", "Conflict handling (H)", "Evaluation script"],
    ids.map((s) => [V(s.split("_")[0], "manifest setups"), short[s], onoff(M.setups[s].time_ranking), onoff(M.setups[s].consolidation), onoff(M.setups[s].conflict),
      M.setups[s].time_ranking ? "T-MEM" : "A-MEM"]),
    [800, 1300, 1500, 1600, 1700, 1300],
    `"A-MEM" in the last column is A-MEM's own evaluation script, ${V(amem[0], "evaluator_amem")}; "T-MEM" is ${V(tmem[0], "evaluator_tmem")}, which uses a memory class that adds the time-ranking step. Consolidation and conflict handling are optional modes of the memory system, switched on by command-line options in either script. Source: the experiment manifest.`);
}
// src: manifest commands (--memories_dir, --keywords_file, --trap_order per_question, --seed, --run_tag); git diff 0c8039f2..b84b89cc of the evaluation scripts
add(p("Every setup received the same input, so that a difference between two setups could come only from the modules that separate them. Four controls kept the input the same. All setups read one shared memory bank per sample. The search words that A-MEM generates from each question were generated once per question and run, and every setup read them. The order of the two answer options in adversarial questions was fixed per question and run. Finally, A-MEM's memory, retrieval, and answering code paths, its prompts, and its answer temperatures were left unchanged. The evaluation scripts gained optional switches, off by default, for the shared search words, the fixed option order, the T-MEM modules, the bank folder, the seed, and the log name, and every setup used the switches for the shared search words and the fixed option order. With every module off, retrieval follows A-MEM's code path. Each control is described later in this chapter."));
// src: PLAN.md section 2 (settings frozen); manifest sample3_build (bank built fresh for this experiment)
add(p(`The LoCoMo conversations used are called samples ${allRange()}. The settings of the modules were frozen in the plan before the runs, and the bank of sample ${sid(TEST)} was built fresh for this experiment, as described under Memory Banks Used in the Experiment. Results are reported for samples ${allRange()} together.`));
// src: manifest seeds; shared_keywords.trap_draw; make_keywords.py (one search-word file per seed)
add(p(`Each setup was run ${W("n_seeds")} times, once with each of the seeds ${list(fact("seeds").map((s) => V(String(s), "seeds")))}, giving ${N("n_runs")} runs. The seed selects the run's shared search words and fixes the order of the answer options in adversarial questions; it does not control the language model's sampling. Several runs were needed because the answering model samples at a non-zero temperature, so the same setup gives slightly different answers from one run to the next (Reimers & Gurevych, 2017).`));
// src: git log PLAN.md (first commit c1fcece5); manifest attempts trial.started; trial output; plan section 8 and analyze.py unchanged since (asserted in facts.py)
must(fact("trial_samples") === 1, "trial on one sample");
add(p(`The analysis was fixed before any results existed. The experiment plan, including the measures, the test families, the correction for multiple tests, and the decision rule, was committed to the project repository at ${X("plan_time")} on ${X("plan_date")} (commit ${X("plan_commit")}), together with the analysis script. The first question-answering run, a trial on ${W("trial_samples")} sample, began at ${X("trial_start")} the same day. The analysis section of the plan and the analysis script were not changed afterwards. Every test, interval, and p-value in Chapter IV is the output of that script; the descriptive analyses added afterwards are labeled as such.`));

// ------------------------------------------------------------------ RQs
add(h1("Research Questions and Hypotheses"));
const RQS = [
  ["RQ1. Each module alone.", "When added alone to A-MEM, does time ranking, consolidation, or conflict handling change answerable F1 or temporal F1?",
   "H1~0~: For each module, the setup with only that module switched on has the same mean answerable F1 and the same mean temporal F1 as A-MEM, and the average effect of each module over the settings of the other modules is zero."],
  ["RQ2. All modules together.", "Does T-MEM with every module switched on differ from A-MEM?",
   "H2~0~: The setup with every module on has the same mean answerable F1 and the same mean temporal F1 as A-MEM."],
  ["RQ3. How the modules combine.", "Does the effect of one module depend on whether another module is switched on?",
   "H3~0~: Every interaction effect (T × C, T × H, C × H, and T × C × H) is zero on both measures."],
  ["RQ4. Adversarial questions and scoring.", "Do the setups differ in how often they decline adversarial questions, and does the way those questions are scored change the comparison between setups?",
   "RQ4 is descriptive. It is answered with the refusal rate and two overall scores, reported for every setup without significance tests."],
];
// src: PLAN.md section 1 and section 8; Measures section of this chapter
add(p(`The experiment addressed ${V(asCount(RQS.length), "count of RQS")} research questions. Answerable F1 and temporal F1, the two main measures, are defined under Measures. The hypotheses are stated as null hypotheses of no difference and are tested two-sided; the tests in Chapter IV either reject them or fail to reject them.`));
RQS.forEach(([a, q, h]) => { add(p(`**${a}** ${q}`)); add(p(h)); });
add(p(`Table ${T.rqs} links each research question to the comparisons and measures that answer it.`));
tbl("rqs", "Research Questions, Comparisons, and Measures",
  ["Research question", "Comparison", "Main measures", "Test family"],
  [["RQ1 Each module alone", "T, C, and H against A-MEM; average effect of each module", "Answerable F1, temporal F1", "Main tests; factorial effects"],
   ["RQ2 All modules together", "All three against A-MEM", "Answerable F1, temporal F1", "Main tests"],
   ["RQ3 How the modules combine", "Interaction effects; T + C, T + H, and C + H against A-MEM", "Answerable F1, temporal F1", "Factorial effects; other setups"],
   ["RQ4 Adversarial questions", "All setups", "Refusal rate; two overall scores", "Descriptive, no tests"]],
  [2000, 3000, 1800, 1800],
  "The test families are defined under Data Analysis Plan and Statistical Procedures.");

// ------------------------------------------------------------------ data
add(h1("Data Source: The LoCoMo Benchmark"));
// src: data/locomo10.json
add(p(`The data came from LoCoMo, a benchmark built to test memory over very long conversations (Maharana et al., 2024). The released file, ${X("data_file")}, contains ${N("data_conversations")} conversations between pairs of speakers. Each conversation runs over many dated sessions and comes with question–answer pairs that refer back to specific turns. The file used in every run has a SHA-256 fingerprint beginning ${X("data_sha256_prefix")}. Table ${T.locomo} describes the ${W("n_samples")} conversations used, samples ${allRange()}. Together they contain ${N("d_total_turns")} dialogue turns and ${N("d_total_questions")} questions.`));
tbl("locomo", "The LoCoMo Conversations Used in This Study",
  ["Sample", "Speakers", "Sessions", "Turns", "Questions", "Cat. 1", "Cat. 2", "Cat. 3", "Cat. 4", "Cat. 5"],
  [...S4.map((s) => [sid(s), X(`d${s}_speakers`), N(`d${s}_sessions`), N(`d${s}_turns`), N(`d${s}_questions`),
      N(`d${s}_cat1`), N(`d${s}_cat2`), N(`d${s}_cat3`), N(`d${s}_cat4`), N(`d${s}_cat5`)]),
   ["Total", "", N("d_total_sessions"), N("d_total_turns"), N("d_total_questions"), N("d_total_cat1"), N("d_total_cat2"), N("d_total_cat3"), N("d_total_cat4"), N("d_total_cat5")]],
  [800, 1800, 900, 700, 900, 600, 600, 600, 600, 600],
  `Counted from ${X("data_file")}. Cat. = question category (see text). The sessions of sample ${sid(TEST)} run from ${X("d3_first_session")}, to ${X("d3_last_session")}.`);
// src: data/locomo10.json qa[0]; test_advanced_robust.py answer_question (category 2 and 5 prompts)
add(p(`The questions fall into ${W("n_categories")} categories, identified by a number in the data file. Category 2 holds temporal questions, which ask when something happened, for example "${X("example_temporal_question")}" Category 5 holds adversarial questions, which Maharana et al. (2024) describe as designed to trick the agent into giving a wrong answer. In these questions the stored reference answer is the plausible but wrong answer that the question invites. The A-MEM evaluation code treats these two categories separately. For category 2 it adds an instruction to use the date of the conversation. For category 5 it asks the model to choose between the stored answer and "${X("prompt_c5_option")}."`));
// src: data/locomo10.json evidence lists (an entry may hold several turns separated by ';')
must(fact("n_categories") === 5, "categories 1-5");
add(p(`The data file labels the other categories only by number. Maharana et al. (2024) describe three types: single-hop questions, answered from one session; multi-hop questions, which need several sessions; and open-domain questions, which combine what a speaker said with outside knowledge. The numbers were matched to these types by the structure of the questions in samples ${allRange()}. In category 1, ${P("ev_cat1_two_plus_pct", 0)} of the questions cite two or more evidence turns (mean ${D("ev_cat1_mean", 2)}), which fits multi-hop. Of the category 4 questions, ${P("ev_cat4_two_plus_pct", 0)} cite more than one turn (mean ${D("ev_cat4_mean", 2)}), which fits single-hop. Category 3 questions ask for inference beyond what was said, which fits open-domain.`));
// src: data/locomo10.json counts
must(fact("d1_cat3") === 0, "sample 1 has no category 3 question");
add(p(`Two properties of the data matter when reading the results. First, temporal questions are a minority: ${N("d_total_cat2")} of the ${N("d_total_questions")} questions (${P("d_temporal_share_pct", 1)}). A module that helps only temporal questions can therefore move answerable F1 only a little. Second, the ${W("n_samples")} samples contain only ${N("d_total_cat3")} open-domain questions, and sample 1 contains ${V("none", "d1_cat3")}, so results for category 3 rest on very few items.`));

// ------------------------------------------------------------------ A-MEM
add(h1("Baseline System: A-MEM"));
// src: git log 0c8039f2 (author WujiangXu = W. Xu, first author of A-MEM); manifest model, served_model; sample 3 build summary (model); embeddings .npy shape; sample 3 consolidation log config
must(fact("s3_build_model") === fact("model") && fact("served_check_date") === fact("waves_date"), "model version and check date");
add(p(`A-MEM is an agentic memory system in which a language model writes, links, and revises memory notes as a conversation proceeds (W. Xu et al., 2025). This study used the "robust" implementation that the first author of A-MEM added to the project repository on ${X("robust_date")} (commit ${X("robust_commit")}). It asks the language model for plain text rather than structured JSON (JavaScript Object Notation) and reads the answer with section markers. The language model was gpt-4o-mini (OpenAI, 2024). All question answering, all search words, and the sample ${sid(TEST)} bank used the exact version ${X("model")}, and a test call to the OpenAI application programming interface (API) on the day of the runs confirmed that it served that version. The embedding model was ${X("embedding_model")}, a Sentence-BERT model (Reimers & Gurevych, 2019) built on MiniLM (W. Wang et al., 2020), which maps text to a normalized ${N("embedding_dim")}-dimensional vector.`));
add(h2("Note Construction"));
// src: test_advanced_robust.py note text ("Speaker Xsays : "); banks: raw notes = turns (B1)
must(S4.every((s) => fact(`b${s}_raw`) === fact(`d${s}_turns`)), "raw notes = turns");
add(p("Every dialogue turn became one memory note. The note's text is the turn in the form written by the evaluation code, for example \"Speaker Natesays : …\" (the code joins the name and \"says\" without a space), and its timestamp is the date and time of the session the turn belongs to. For each note the language model produced keywords, a one-sentence context, and tags. The retriever embedded a string made of the content, context, keywords, and tags. Because notes are created turn by turn, the number of raw notes in each bank equals the number of turns."));
add(h2("Memory Evolution and Links"));
// src: memory_layer_robust.py process_memory (k=5; decision, strengthen, update calls)
must(fact("evolution_calls") === 3, "three evolution calls described");
add(p(`When a note was added, A-MEM retrieved the ${W("evolution_k")} most similar existing notes and asked the language model, in up to ${W("evolution_calls")} calls, whether the memory should evolve. The first call returned a decision. If the decision included strengthening, a second call returned links from the new note to its neighbors and revised tags. If it included updating neighbors, a third call rewrote their context and tags. Table ${T.banks} describes the raw notes of the ${W("n_samples")} banks; almost every note carries links.`));
tbl("banks", "Raw A-MEM Notes in the Memory Banks",
  ["Sample", "Notes", "Notes with links", "Mean links per note", "Mean keywords per note", "Mean tags per note"],
  S4.map((s) => [sid(s), N(`b${s}_raw`), N(`b${s}_with_links`), D(`b${s}_mean_links`, 2), D(`b${s}_mean_keywords`, 2), D(`b${s}_mean_tags`, 2)]),
  [1000, 1100, 1500, 1600, 1700, 1500],
  `Counted from the raw notes of the shared banks used in the experiment. The A-MEM notes of sample ${sid(TEST)} were built on ${X("s3_base_date")}, by A-MEM's unchanged memory code called from the project's build script, in ${N("s3_base_seconds")} seconds, with ${must(fact("s3_base_warnings") === 0, "warnings")}${V("no", "s3_base_warnings")} warnings or errors.`);
add(h2("Retrieval and Answer Generation"));
// src: test_advanced_robust.py generate_query_llm + answer_question; memory_layer_robust.py _find_related_memories_raw_amem; manifest --retrieve_k
add(p(`In A-MEM, answering a question takes two language-model calls. The first turns the question into a short list of search words. The second produces the answer. Between them, the retriever compares the search words with every note by cosine similarity and takes the ${N("t_k")} best notes (*k* = ${N("t_k")}). For each of those notes, A-MEM then appends the notes it links to. The context passed to the answering model therefore holds the ${N("t_k")} retrieved notes and their linked neighbors, each shown with its session time, content, context, keywords, and tags.`));
// src: test_advanced_robust.py answer_question; --temperature_c5 default
add(p(`The answer prompt depends on the question category. All prompts ask for a short answer. The category 2 prompt adds "${X("prompt_c2")}" The category 5 prompt asks the model to select the correct answer from two options, the stored adversarial answer and "${X("prompt_c5_option")}." Answers are generated at temperature ${D("ans_temp", 1)}, except in category 5, which uses ${D("ans_temp_c5", 1)}. These temperatures are A-MEM's own and were not changed.`));

// ------------------------------------------------------------------ modules
add(h1("The T-MEM Modules"));
// src: build_consolidated_cache.py, build_conflict_bank.py (offline); memory_layer_robust.py retrievable_indices, conflict_penalties; memory_layer_tmem_robust.py
const fig1 = nextFigure();
add(p(`T-MEM adds ${W("n_modules")} modules to A-MEM. Consolidation and conflict handling do most of their work once, offline, after A-MEM has built its memory bank; at question time they decide which notes may be retrieved and what is shown with each note. Time ranking acts only at question time. Figure ${fig1} shows where each module acts.`));
{ const [els] = figure(`${FIG}/fig1_pipeline.png`, 5.6, 4.29, "Where each T-MEM module acts. Shaded boxes are the steps added or changed by a T-MEM module. Each module is switched on or off independently, and with every module off the system is A-MEM."); add(els); }

add(h2("Time Ranking (T)"));
// src: memory_layer_tmem_robust.py TemporalRetrievalConfig, _temporal_relevance (age = days / 30), _rank_memories_temporally; Yadav & Kumar (2026)
add(p("A-MEM stores a timestamp on every note but does not use it when ranking. Time ranking lets recency act, but only among notes that already match the question closely. It is the semantic-first reranking of the pilot study (Yadav & Kumar, 2026). Recency is an exponential decay of a note's age:"));
const [eqR, nR] = eq(`r(m) = exp(−λ · a(m)),   a(m) = (t~ref~ − t~m~) / ${N("t_age_days")} days`); add(eqR);
const [eqB, nB] = eq(`s(q, m) = α · ŝ(q, m) + (1 − α) · r̃(m),   α = ${D("t_alpha", 1)}`);
add(p(`where t~m~ is the note's session time, t~ref~ is the latest session time in the conversation, and λ = ${D("t_lambda", 1)} per ${N("t_age_days")}-day period. For a question with search words q, the steps are:`));
add(item(1, "Score every note by cosine similarity with q and sort."));
add(item(2, `If the best note leads the second-best by at least ${D("t_margin", 2)}, return the top ${N("t_k")} by similarity unchanged.`));
add(item(3, `Otherwise take the ${N("t_pool")} most similar notes as a candidate pool.`));
add(item(4, `Within the pool, min–max normalize the similarity scores to ŝ and the recency scores of Equation ${nR} to r̂, and raise the recency floor so that r̃ = ${D("t_floor", 2)} + ${D("t_floor_slope", 2)} · r̂.`));
add(item(5, `Rank the pool by the blend in Equation ${nB}.`));
add(item(6, `Keep the ${W("t_anchor")} most similar notes in the first places, and fill the remaining ${V(asCount(fact("t_k") - fact("t_anchor")), "t_k - t_anchor")} places from the blended ranking.`));
add(eqB);
// src: TemporalRetrievalConfig.temporal_categories; test_tmem_advanced_robust.py uses the stored category
add(p(`Time ranking is applied only to temporal questions. The router uses the category label stored in the benchmark: for a category ${V(fact("t_categories").join(", "), "t_categories")} question, time ranking orders the notes; for every other question, retrieval is the same as with time ranking off. This is an oracle router. A deployed system would have to infer from the question text whether it is temporal, so the results show the effect of time ranking when routing is perfect. Table ${T.time} lists the settings.`));
tbl("time", "Time-Ranking Settings",
  ["Setting", "Value"],
  [[`Decay rate λ (per ${N("t_age_days")} days)`, D("t_lambda", 1)], ["Weight on similarity α", D("t_alpha", 1)], ["Notes reranked", `Top ${N("t_pool")} by similarity`],
   ["Notes fixed in place", `Top ${N("t_anchor")} by similarity`], ["Skip when the best note leads by", `${D("t_margin", 2)} or more`],
   ["Recency floor after normalization", D("t_floor", 2)], ["Questions affected", `Category ${V(fact("t_categories").join(", "), "t_categories")} only`]],
  [4800, 3000],
  `Defaults of TemporalRetrievalConfig in memory_layer_tmem_robust.py at commit ${X("code_commit")}.`);

add(h2("Consolidation (C)"));
// src: memory_consolidation.py module docstring and consolidate_bank (hard_ok excludes too_long)
add(p(`Long conversations repeat themselves, and each repetition becomes a separate note that competes for the same ${N("t_k")} retrieval slots. Consolidation merges such repetitions offline, after the base bank is built and before any question is asked. Its rule is that no checked fact or date may be lost: the original notes are kept, a merged note must contain every checked fact and date from its sources, and a merge that fails the fact and date checks is discarded.`));
// src: memory_consolidation.py ConsolidationConfig, find_candidate_groups; sample 3 consolidation log config
add(p(`**Finding candidate groups.** The content of each raw note is embedded, and every pair is compared. Pairs with cosine similarity of at least ${D("cons_threshold", 2)} are visited from most to least similar, and groups are grown by complete linkage: two groups are joined only if every note in one is at least ${D("cons_threshold", 2)} similar to every note in the other. A group holds at most ${W("cons_max_group")} notes, all from the same speaker.`));
// src: memory_consolidation.py CONSOLIDATION_VERIFY_PROMPT, CONSOLIDATION_MERGE_PROMPT, consolidate_bank(temperature=0.0)
add(p(`**Verifying and merging.** Each candidate group is shown to the language model with the date of every note, and the model chooses one label. SAME_FACT means the notes state the same fact, plan, or event. SMALL_TALK means they are greetings, thanks, praise, or encouragement with no distinct facts. DIFFERENT means they describe different things despite sounding alike; the prompt tells the model to choose DIFFERENT when unsure. DIFFERENT groups are left alone. For the other two labels, a second prompt asks for one short merged note that names the speaker, writes every date in absolute form, and keeps every name, place, and number. Both calls use temperature ${D("cons_temperature", 1)}.`));
// src: memory_consolidation.py fact_words/missing_facts, unresolved_relative_times, dropped_relative_times, _merge_problems, consolidate_bank loop
must(fact("n_merge_checks") === 4 && fact("merge_hard_checks") === 3, "four checks, three hard");
add(p(`**Checks.** Every merged note passes ${W("n_merge_checks")} rule-based checks before it is accepted. The first lists every number, every capitalized name-like word inside a sentence, every speaker name, and every source date in the sources, and flags any of these that is missing from the merged note. The second flags relative time expressions left in the merged note, such as "next month," because the same phrase means different things when its sources were said on different dates. The third flags relative times in a source whose resolution is missing from the merged note: the resolved month or year for phrases such as "next month" or "last year," and the unit itself, such as "week" or "summer," for other phrases. The last flags a merged note that is longer than its sources. When any check fails, the merge prompt is repeated with a list of the problems, up to ${W("cons_retries")} more times. A group is rejected only if no attempt passes the first ${W("merge_hard_checks")} checks; if the only problem left is length, the first attempt that passed those ${W("merge_hard_checks")} checks is kept.`));
// src: build_logs/sample3_consolidation_log.json (found by facts.py)
must(fact("ex_merge_n_sources") === 2, "example has two sources");
add(p(`An example from sample ${sid(TEST)} shows the result. ${X("ex_merge_speaker")} said on ${X("ex_merge_src1_date")}, "${X("ex_merge_src1_text")}" and on ${X("ex_merge_src2_date")}, "${X("ex_merge_src2_text")}" The merged note reads: "${X("ex_merge_result")}" By contrast, ${W("ex_different_n")} of ${X("ex_different_speaker")}'s statements, about winning a first video game tournament and later an international tournament, were labeled DIFFERENT and kept apart.`));
// src: memory_consolidation.py apply_consolidation; memory_layer_robust.py retrievable_indices (primary_expand), consolidated_top_k_cap; manifest --consolidated_top_k_cap
add(p(`**Storage and retrieval.** Accepted merges are appended to the end of the bank, and nothing is deleted or reordered, because A-MEM's links and the retriever's rows refer to notes by position. Each merged note takes the latest timestamp of its sources, the union of their keywords and tags, and links to every source; its sources are marked as archived. At question time the primary-expand mode is used. Archived sources cannot be retrieved directly, but a retrieved merged note brings its sources back into the context through A-MEM's ordinary link expansion. At most ${W("cons_cap")} merged note may enter the ${N("t_k")} retrieved notes. Table ${T.cons} describes the merged notes in the ${W("n_samples")} banks.`));
tbl("cons", "Merged Notes in the Memory Banks",
  ["Measure", ...S4.map(sname)],
  [["Merged notes", ...S4.map((s) => N(`b${s}_merged`))],
   ["Source notes archived", ...S4.map((s) => N(`b${s}_archived`))],
   ["Mean source notes per merged note", ...S4.map((s) => D(`b${s}_mean_sources`, 2))],
   ["Notes before → after", ...S4.map((s) => `${N(`b${s}_raw`)} → ${N(`b${s}_notes`)}`)]],
  [3400, 1100, 1100, 1100, 1100],
  "Counted in the shared banks used in the experiment, whose fingerprints are recorded in the experiment manifest.");
// src: build_logs/sample3_consolidation_log.json counts, groups, attempts
must(fact("c3_rejected") === 0, "sample 3 none rejected");
add(p(`The build log of sample ${sid(TEST)} shows each step. The model labeled the ${N("c3_groups")} candidate groups SAME_FACT (${N("c3_SAME_FACT")}), SMALL_TALK (${N("c3_SMALL_TALK")}), or DIFFERENT (${W("c3_DIFFERENT")}). Of the ${N("c3_merged")} groups merged, ${N("c3_merged_small_talk")} were small talk; ${V("no", "c3_rejected")} group was rejected, and the build made ${N("c3_llm_calls")} language-model calls. Under the length rule, ${N("c3_merged_longer")} of the ${N("c3_merged")} merged notes are longer than their sources.`));

add(h2("Conflict Handling (H)"));
// src: memory_conflicts.py module docstring; detect_and_apply sets fields only
add(p("Facts about a person change during a long conversation: a plan moves forward, a job is replaced, or a later statement contradicts an earlier one. A-MEM stores every statement as an equal note and keeps no record of which one is current. Conflict handling builds, offline, an ordered timeline for each changeable fact and labels how each statement relates to the earlier ones. It never adds, removes, or reorders notes; it only sets fields on existing raw notes. Merged notes are not tagged."));
// src: memory_conflicts.py STATE_PROMPT (tagging)
add(p("**Tagging concrete facts.** Each raw note is shown to the language model with its date and speaker, and the model decides whether it states a concrete, checkable fact about the speaker's own life that could change later, such as a job and its status, a move, a relationship status, a step in a specific plan, starting or stopping an activity, or something bought or lost. Feelings, thanks, praise, wishes, opinions, questions, and facts about other people do not count. For notes tagged as facts, the model also returns a short topic in the form \"speaker's thing\" and the status at that time."));
// src: memory_conflicts.py topic_groups (average linkage, cosine), build_timelines (single-day clusters dropped), ConflictConfig.topic_threshold
add(p(`**Building timelines.** For each speaker, the tagged topics are clustered by meaning with average-linkage clustering on the cosine distance between topic embeddings, at a similarity threshold of ${D("conf_topic_threshold", 2)}. Each cluster becomes a timeline with its notes in time order. Clusters whose notes all come from a single day are dropped.`));
// src: memory_conflicts.py comparison_steps (status_duplicate), CONFLICT_CHECK_PROMPT, verification prompt, detect_and_apply (earliest replacement wins), cached_calls; llm_text_parsers.CONFLICT_LABELS
{
  const DESC = { SAME: "SAME", PROGRESS: "PROGRESS (the same plan moved forward)", CHANGE: "CHANGE (the old fact was replaced)",
    CONTRADICTION: "CONTRADICTION (both cannot be true, and it is not a natural change)", COMPATIBLE: "COMPATIBLE (both are true at once)", UNRELATED: "UNRELATED" };
  const labs = fact("conflict_labels");
  must(JSON.stringify(labs) === JSON.stringify(Object.keys(DESC)), "conflict labels");
  must(fact("b_total_contradictions") === 0, "no contradictions in the banks");
  const named = labs.map((l) => DESC[l]);
  add(p(`**Labeling and verifying changes.** Within a timeline, each note is compared with each distinct earlier status. Each status is represented by its most recent mention, provided that mention comes from an earlier day. Two statuses count as the same when their embeddings have similarity of at least ${D("conf_status_duplicate", 2)}. For each comparison the language model chooses one of ${W("n_conflict_labels")} labels: ${named.slice(0, -1).join(", ")}, or ${named[named.length - 1]}; the prompt tells the model to choose COMPATIBLE when unsure. CHANGE and CONTRADICTION labels are checked a second time with a stricter prompt that asks whether the older statement is no longer true and requires a quotation from the newer statement. A label is confirmed only if the answer is yes and the quotation is found in the newer note; otherwise it becomes COMPATIBLE. A confirmed CHANGE marks the older note as replaced from the newer note's date; if two confirmed changes point at the same older note, the earliest one is kept. A confirmed CONTRADICTION links the two notes without replacing either; ${V("no", "b_total_contradictions")} note in the ${W("n_samples")} banks carries such a link. The calls use temperature ${D("conf_temperature", 1)}, and their answers are cached so that a rebuild makes no new calls. Table ${T.conf} describes the timelines in the ${W("n_samples")} banks.`));
}
tbl("conf", "Timelines in the Memory Banks",
  ["Measure", ...S4.map(sname)],
  [["Raw notes", ...S4.map((s) => N(`b${s}_raw`))], ["Timelines", ...S4.map((s) => N(`b${s}_timelines`))],
   ["Notes in timelines", ...S4.map((s) => N(`b${s}_timeline_notes`))], ["Replaced notes", ...S4.map((s) => N(`b${s}_replaced`))],
   ["Notes linked by a contradiction", ...S4.map((s) => N(`b${s}_contradictions`))], ["Timeline notes with an event date", ...S4.map((s) => N(`b${s}_event_dates`))]],
  [3800, 1000, 1000, 1000, 1000],
  "Counted in the shared banks used in the experiment. Every note with an event date belongs to a timeline.");
// src: banks (replaced); build_logs/sample3_conflict_log.json (labels, verification, new calls, timelines)
must(fact("h3_CHANGE") === 0 && fact("h3_CONTRADICTION") === 0 && fact("h3_SAME") === 0 && fact("h3_UNRELATED") === 0 && fact("h3_verified") === 0 && fact("h3_PROGRESS") + fact("h3_COMPATIBLE") === fact("h3_comparisons") && fact("b3_replaced") === 0, "sample 3 labels");
add(p(`The banks differ in a way that matters for Chapter IV. The banks of samples ${devRange()} mark ${N("b_dev_replaced")} notes as replaced, and the bank of sample ${sid(TEST)} marks ${V("none", "b3_replaced")}. The build log of sample ${sid(TEST)} shows why: of its ${N("h3_tagged")} notes tagged as concrete facts, every comparison was labeled PROGRESS (${N("h3_PROGRESS")}) or COMPATIBLE (${W("h3_COMPATIBLE")}), so no label went to the verifier; the build made ${N("h3_new_calls")} new language-model calls. The timelines of sample ${sid(TEST)} include, for example, ${X("ex_tl_script_topic")} (${N("ex_tl_script_n")} notes from ${X("ex_tl_script_first")}, to ${X("ex_tl_script_last")}) and ${X("ex_tl_tourn_topic")} (${N("ex_tl_tourn_n")} notes).`));
// src: memory_layer_robust.py timeline annotation (OUTDATED, CONFLICTS), conflict_penalties, is_now_question, NOW_WORDS, HISTORY_WORDS; manifest --demote_penalty; extra.json now_q
must(fact("now_q_temporal") === 1 && fact("b3_replaced") === 0 && fact("b3_contradictions") === 0, "present-tense counts; sample 3 has nothing to demote");
add(p(`**Showing timelines to the model.** Two mechanisms use the timeline fields at question time. The first is annotation. Every note in the context that belongs to a timeline carries one extra field. The field names the topic, the note's step number and its own dates, and the status and dates of the steps immediately before and after it. A replaced note also carries the label "OUTDATED since date: replaced by …," and a note on either side of a confirmed contradiction would carry a CONFLICTS label. The second is demotion. For questions about the present, replaced notes and the older side of any contradiction lose ${D("demote_penalty", 2)} from their similarity score. A question counts as being about the present if it contains a word such as "${alt("now_words", "now")}," "${alt("now_words", "currently")}," or "${alt("now_words", "still")}" and none of the history words, such as "${alt("history_words", "when")}," "${alt("history_words", "before")}," "${alt("history_words", "first")}," "${alt("history_words", "used to")}," "${alt("history_words", "previously")}," or "${alt("history_words", "ago")}." ${Wc("now_q0")} questions in sample 0, ${W("now_q1")} in sample 1, ${W("now_q2")} in sample 2, and ${W("now_q3")} in sample 3 match this rule, and ${W("now_q_temporal")} of these ${W("now_q_total")} is a temporal question. Since the bank of sample ${sid(TEST)} has no replaced notes, demotion cannot act there.`));
// src: memory_consolidation.py happened_around; memory_conflicts.py event_time; s4_h log (label text); sample 3 bank (event_time)
add(p(`**Statement date and event date.** Each timeline step carries two dates: the date it was said and, if the note contains a relative time expression, the date it happened. The event date is computed by a rule-based function from the first relative expression in the note and the note's session date, with no language-model call. Table ${T.event} lists every event date in the bank of sample ${sid(TEST)}. For example, ${X("ex_event_speaker")} said on ${X("ex_event_note_date")}: "${X("ex_event_note_phrase")}." The label shown with that note in the runs reads: "${X("ex_event_label")}."`));
{
  const R = fact("event_rows");
  must(R.length === fact("b3_event_dates"), "event rows");
  tbl("event", `Event Dates in the Bank of Sample ${sid(TEST)}`,
    ["Said on", "First relative expression in the note", "Event date written"],
    R.map((r) => r.map((x) => V(x, "event_rows"))),
    [2300, 2900, 3000],
    `Read from the bank of sample ${sid(TEST)}; each event date was re-derived by running happened_around() in memory_consolidation.py at commit ${X("code_commit")} on the note and its session date. The event date is written in the form the model sees. Only the first relative expression in a note is used; notes without one show only the date said.`);
}

add(h2("How the Modules Combine"));
// src: memory_layer_robust.py consolidated_context_order; memory_layer_tmem_robust.py _semantic_scores (consolidation mask, conflict penalties), then temporal rerank
add(p("When more than one module is on, they act on the same ranking. Consolidation decides which notes may be ranked (archived sources are hidden, and the number of merged notes is capped), conflict handling subtracts the demotion penalty for questions about the present, and time ranking, for temporal questions only, reorders the result. The context is then expanded through A-MEM's links, and conflict handling adds its timeline labels to the notes shown."));
add(h2("Keeping A-MEM Unchanged"));
// src: memory_layer_robust.py find_related_memories_raw (off/off -> _find_related_memories_raw_amem in raw_only_view); checks R10, R11
add(p("Consolidation and conflict handling are optional modes whose default is off, and time ranking is used only when the T-MEM evaluation script is run. With every module off, retrieval calls the original A-MEM function, and only the raw notes at the start of the bank are visible. During the experiment, every run was replayed offline (check R11 below), and for every non-temporal question each setup with time ranking on was compared with its partner with time ranking off (check R10)."));

// ------------------------------------------------------------------ banks
add(h1("Memory Banks Used in the Experiment"));
// src: memory_layer_robust.py raw_only_view, retrievable_indices; checks/build_sample3.json B2
add(p(`All setups read the same bank for a given sample. Each bank holds every layer: the raw A-MEM notes at the start, the merged notes appended after them, and the timeline fields set on the raw notes. A setup with a module switched off ignores that layer: with consolidation off, retrieval sees only the raw notes, and with conflict handling off, the timeline fields are neither shown nor used. One bank can therefore serve all ${W("n_setups")} setups.`));
// src: manifest bank_sources, banks (sha256), sample3_build; build_logs sample3_started_at / finished_at; checks/build_sample3.json; inputs checks
must(fact("build_checks") === 5, "five build checks listed");
add(p(`The banks of samples ${devRange()} were copied into the experiment folder from an earlier build, as the manifest records. The bank of sample ${sid(TEST)} was built for this experiment on ${X("s3_build_date")}, in ${W("s3_build_stages")} steps that took ${V(rnd(fact("s3_build_minutes"), 0), "s3_build_minutes")} minutes. First, the project's build script called A-MEM's unchanged memory code to build A-MEM's notes. Consolidation followed, and then conflict handling, with no cached language-model answers. ${Wc("build_checks")} build checks (B1–B${V(String(fact("build_checks")), "build_checks")}) were passed before the bank was used: one note per turn in turn order; raw notes identical in every A-MEM field in all ${W("s3_build_stages")} build stages; no build warnings or errors; merges and timelines logged; and event dates filled in from relative times. The SHA-256 fingerprint of every bank file was recorded in the experiment manifest and checked again before every wave of runs.`));

// ------------------------------------------------------------------ procedure
add(h1("Experimental Procedure"));
add(p(`Table ${T.settings} lists the settings fixed for every run. They were recorded in the experiment manifest before the first valid run and not changed afterwards.`));
tbl("settings", "Fixed Settings of the Experiment",
  ["Setting", "Value"],
  [["Answering and search-word model", `${X("model")} (served version checked)`], ["Embedding model", X("embedding_model")],
   ["Notes retrieved per question (*k*)", `${N("t_k")}, plus linked notes`], ["Samples", `${list(SMP.map(sid))} (${N("d_total_questions")} questions)`],
   ["Runs per setup", `${N("n_seeds")} (seeds ${fact("seeds").map((s) => V(String(s), "seeds")).join(", ")})`],
   ["Answer temperature", `${D("ans_temp", 1)}; ${D("ans_temp_c5", 1)} for category 5 (A-MEM's own)`],
   ["Time ranking, when on", `Table ${T.time}`], ["Consolidation, when on", `Primary-expand, at most ${N("cons_cap")} merged note in the top ${N("t_k")}`],
   ["Conflict handling, when on", `Annotation and demotion, penalty ${D("demote_penalty", 2)}, statement and event dates`],
   ["Search words", "Made once per question and run with A-MEM's prompt; shared by all setups"],
   ["Option order in category 5", "Fixed per question and run from the seed"],
   ["Code", `Commit ${X("code_commit")}, unchanged during the runs`]],
  [3600, 4200], null);
add(h2("Shared Search Words"));
// src: memory_layer_robust.py get_completion default temperature; shared_keywords.py; test_*_robust.py --keywords_file
add(p(`In A-MEM, the search words for each question come from a language-model call at temperature ${D("kw_temp", 1)}, so two setups asked the same question can retrieve from different search words. A difference between setups could then come from the search words rather than from the modules being compared. To remove this source of variation, one option was added to both evaluation scripts. When a search-word file is given, the script reads the search words for each question from the file instead of generating them. Without the option, the scripts behave exactly as before.`));
// src: make_keywords.py; manifest keywords (files x questions); shared_keywords.lookup_keywords (missing entry raises); checks R7
add(p(`For each of the ${W("kw_files")} runs, the search words for all ${N("d_total_questions")} questions were generated once with A-MEM's own function, prompt, and parsing, and saved, giving ${N("kw_entries")} entries in all. All setups of a run read the same file. A missing entry stops the run with an error rather than falling back silently, and each question's search words are written to the log so that the checks can confirm that the file was used.`));
add(h2("Option Order in Adversarial Questions"));
// src: shared_keywords.trap_draw; PLAN.md "Wave 1, first attempt" (retry jitter)
add(p("A-MEM places the two options of a category 5 question in random order. In this experiment the order was drawn from a random generator seeded with the run's seed, the sample number, and the question number, so the order depends only on the run and the question. Every setup therefore saw the same order for the same question in the same run. A per-question generator was used because the OpenAI client draws from Python's shared random generator when it retries a call, which could otherwise shift a shared sequence."));
add(h2("Running the Experiment"));
// src: manifest halves, attempts; PLAN.md section 9 (token rates); run_wave.py (sleep 10, emergency stop, no overwrite); manifest computer
add(p(`The ${N("n_runs")} runs were organized in ${W("n_seeds")} waves, one per seed. Each wave ran the setups in ${W("n_halves")} halves of ${W("half_size")} runs side by side, ${V(hn(fact("half_A")), "half_A")} and ${V(hn(fact("half_B")), "half_B")}, with the order of the halves alternating between waves. The plan estimated that ${W("half_size")} runs at a time would use about ${N("tpm_planned")} tokens per minute, half${must(fact("tpm_planned") * 2 === fact("tpm_limit"), "half the limit")} the account's limit of ${N("tpm_limit")}. While a half ran, the output of each run was read every ${N("poll_seconds")} seconds, and any final failure of an answer would have stopped the half at once. A result file was written only at the end of a run, and a run never started if its result file already existed, so no result could be overwritten. The computer, an ${X("cpu")} with ${N("memory_gb")} GB of memory, was kept on AC power and prevented from sleeping.`));
const seeds = fact("seeds");
const STAGES = [
  ["Search-word option and its tests, scripts, manifest, served-model check; plan committed", `All ${N("tests_stage0")} unit tests pass; plan approved`],
  [`Build the sample ${sid(TEST)} bank`, `Build checks B1–B${V(String(fact("build_checks")), "build_checks")}`],
  [`Generate the search words for ${W("kw_files")} runs`, `${N("d_total_questions")} questions per file, none empty, fingerprints recorded`],
  [`Trial: A-MEM on sample ${V(String(fact("trial_sample")), "trial_sample")}, seed ${N("trial_seed")}`, "All result checks pass on the trial"],
  [`Wave 1 (seed ${V(String(seeds[0]), "seeds")})`, "All result checks pass"],
  [`Waves 2–${V(String(seeds.length), "n_seeds")} (seeds ${V(String(seeds[1]), "seeds")}–${V(String(seeds[seeds.length - 1]), "seeds")})`, "All result checks pass after every wave"],
  [`Final checks across all ${N("n_runs")} files, analysis`, "All final checks pass"],
];
must(STAGES.length === fact("plan_stages"), "stages = PLAN.md stage table");
const STAGE7 = ["Descriptive counts for this thesis, added after the analysis", "Two runs identical; a recount by a second method agrees"];
add(p(`The plan set out ${V(asCount(fact("plan_stages")), "plan_stages")} stages, each closed by a gate of checks that had to pass before the next stage started; one descriptive stage was added after the analysis. Table ${T.stages} lists them.`));
tbl("stages", "Stages of the Experiment and Their Gates", ["Stage", "Work", "Gate"],
  [...STAGES.map((r, i) => [V(String(i), "stage number"), ...r]), [V(String(STAGES.length), "stage number"), ...STAGE7]], [800, 4300, 2700],
  `Stages 0–${V(String(STAGES.length - 1), "plan_stages - 1")} were planned before the runs. The trial output was never used in the analysis. Before every wave, input checks confirmed the bank and search-word fingerprints, unchanged code, free disk space, AC power, and that no result file for the seed existed.`);
// src: manifest attempts (first wave 42, invalidated), invalid/*/reason.txt; git messages c1fcece5, b84b89cc
add(p(`The first attempt at wave 1 ran all ${W("n_setups")} setups side by side. It reached the tokens-per-minute limit, and ${N("bad_empty")} answers came back empty. All the runs finished, but the result checks failed, so the wave was moved to a separate folder with the reason recorded and was never used. The procedure was then changed to the ${W("n_halves")} halves of ${W("half_size")} runs and the per-question option order described above, before any valid run; ${W("tests_added")} unit tests were added for the change, bringing the total to ${N("tests_after_fix")}, all passing. Wave 1 was then run again. The ${W("n_seeds")} waves used in this thesis, with their checks, ran from ${X("waves_start")} to ${X("waves_end")} on ${X("waves_date")}; each half took between ${D("half_min", 1)} and ${D("half_max", 1)} minutes.`));
add(h2("Checks on Every Run"));
// src: checks/checks_seed42..46.json, checks_all.json (A1); scripts/checks.py
must(fact("checks_r9_per_wave") === 1 && fact("checks_final_extra") === 1, "R9 once per wave; one final extra check");
add(p(`After each wave, ${N("checks_per_file")} checks were applied to each result file and its logs (R0–R8 and R11), and ${N("checks_across_files")} checks covered the whole wave: R9 ${V("once", "checks_r9_per_wave")}, against the expected option order, and R10 for each of the ${N("checks_r10_pairs")} pairs of setups. That made ${N("checks_per_wave")} checks per wave. If any check failed, the whole wave would have been moved aside and the pipeline stopped. Table ${T.checks} lists the checks. After the last wave, all checks were run again across the ${N("n_runs")} files together, with ${W("checks_final_extra")} further check that exactly the ${N("n_runs")} planned result files existed.`));
tbl("checks", "Checks Applied to Every Run",
  ["Check", "What it confirms"],
  [["R0", "The result file and its logs exist"],
   ["R1", `${N("d_total_questions")} questions per file, in the dataset's order and the same order in all files`],
   ["R2", "No empty answers"],
   ["R3", "Settings stored in the file match the setup and seed"],
   ["R4", "The saved overall F1 equals the mean of the per-question F1"],
   ["R5", "The right bank was loaded for each sample, with no rebuild"],
   ["R6", "No errors or failed answers in the log; any retried call is counted and reported"],
   ["R7", "Every question's logged search words match the shared file"],
   ["R8", "Timeline labels appear only with conflict handling on; merged notes only with consolidation on"],
   ["R9", "Every adversarial question shows the expected option order, in all setups"],
   ["R10", "For non-temporal questions, each setup with time ranking on retrieved exactly the same notes as its partner with it off"],
   ["R11", "Replay: the notes in every logged context equal the notes the code gives offline from the same bank and search words"]],
  [900, 6900], null);

// ------------------------------------------------------------------ measures
add(h1("Measures"));
// src: utils.py simple_tokenize, calculate_metrics; git diff 0c8039f2..b84b89cc utils.py (BERTScorer cached; safe_word_tokenize for BLEU)
add(p("Each answer was scored against the stored reference by the evaluation code that ships with A-MEM (utils.py). Token F1 is computed exactly as in A-MEM's version of this file; the project changed only how BERTScore is loaded and added a fallback tokenizer for BLEU. The main measure was token F1. Prediction and reference are lowercased, the characters \".\", \",\", \"!\", and \"?\" are replaced by spaces, and each is split on white space into a set of tokens. Precision is the share of prediction tokens found in the reference, recall the share of reference tokens found in the prediction, and F1 their harmonic mean:"));
const [eqF, nF] = eq("F1 = 2PR / (P + R),   P = |T~pred~ ∩ T~ref~| / |T~pred~|,   R = |T~pred~ ∩ T~ref~| / |T~ref~|"); add(eqF);
const MEASURES = [
  `**Answerable F1:** mean F1 over categories 1–4, the ${N("d_answerable")} questions that have a true answer.`,
  `**Temporal F1:** mean F1 over the ${N("d_total_cat2")} questions of category 2.`,
  `**Refusal rate:** the share of the ${N("d_total_cat5")} category 5 answers that contain the phrase "${X("refusal_phrase")}" and do not contain at least ${must(fact("refusal_share") === 0.5, "half")}${V("half", "refusal_share")} of the adversarial answer's words of ${W("refusal_min_chars")} or more characters.`,
  `**Overall F1 (A-MEM scoring):** mean F1 over all ${N("d_total_questions")} questions, with category 5 scored against the adversarial answer, as the A-MEM evaluation does. Under this scoring a correct refusal scores near zero.`,
  "**Overall score with refusals credited:** as above, except that a category 5 answer scores 1 if it is a refusal and 0 otherwise.",
];
add(p(`In Equation ${nF}, tokens are compared as sets, so repeated words count once. The code also computes exact match, ROUGE-L (Lin, 2004), BLEU-1 (Papineni et al., 2002), METEOR (Banerjee & Lavie, 2005), BERTScore F1 (Zhang et al., 2020), and the cosine similarity of Sentence-BERT embeddings of prediction and reference. From the per-question scores, ${V(asCount(MEASURES.length), "items listed")} summary measures were computed:`));
// src: scripts/analyze.py run_scores; analyze_consolidation_qa.classify_cat5
MEASURES.forEach((m, i) => add(item(i + 1, m)));
add(p("Answerable F1 and temporal F1 are the two main measures. The two overall scores are reported side by side because, for category 5, the scoring of the original code rewards repeating the false premise of the question."));

// ------------------------------------------------------------------ analysis
add(h1("Data Analysis Plan and Statistical Procedures"));
// src: scripts/analyze.py per_question, main
add(p(`For each setup, every measure was computed per run and summarized as the mean and standard deviation over the ${W("n_seeds")} runs. For comparisons, each question's F1 was first averaged over the ${W("n_seeds")} runs, so that each question contributes one value per setup. The difference between two setups is then the mean of the per-question differences.`));
add(h2("Factorial Effects"));
// src: scripts/analyze.py contrast_values
add(p(`With s1 to s8 standing for the per-question scores of the ${W("n_setups")} setups, the average effect of time ranking is the mean of its four on-minus-off differences:`));
{ const [e, n] = eq("T = [(s2 − s1) + (s5 − s3) + (s6 − s4) + (s8 − s7)] / 4"); add(e); REFS.eqT = n; }
add(p("The effects of consolidation and conflict handling are formed in the same way from their own four pairs. The two-way interaction T × C is the effect of T with C on minus the effect of T with C off, each averaged over the two settings of H. On this scale it equals the gain of the two modules together minus the sum of their separate gains; it is twice the interaction as scaled by Montgomery (2017):"));
{ const [e, n] = eq("T × C = [(s5 − s3) − (s2 − s1) + (s8 − s7) − (s6 − s4)] / 2"); add(e); REFS.eqTxC = n; }
add(p("T × H and C × H are formed in the same way, and the three-way interaction T × C × H is the difference between the T × C contrast with H on and with H off: [(s8 − s7) − (s6 − s4)] − [(s5 − s3) − (s2 − s1)]. For a two-way interaction, a positive value means that the two modules together gain more than the sum of their separate gains."));
add(h2("Bootstrap Test"));
// src: scripts/analyze.py bootstrap (REPS, RNG_SEED, percentiles, p)
add(p(`Every difference and effect was tested with a paired bootstrap (Efron & Tibshirani, 1993; Koehn, 2004). The per-question values were resampled with replacement ${N("boot_reps")} times, within each sample separately, so that every resample keeps the original number of questions per sample. The ${V(rnd(fact("ci_lo_pct"), 1), "ci_lo_pct")}th and ${V(rnd(fact("ci_hi_pct"), 1), "ci_hi_pct")}th percentiles of the resampled means give the ${P("ci_level_pct", 0)} interval. The two-sided p-value is twice the smaller of the shares of resampled means above and below zero, plus 1/${N("boot_reps")}. The resampling used a fixed random seed (${N("boot_seed")}), so every interval and p-value can be reproduced exactly. The bootstrap makes no assumption that scores are normally distributed, which suits bounded scores with many ties (Dror et al., 2018).`));
add(h2("Correction for Multiple Tests"));
// src: scripts/analyze.py holm, GROUPS; summary.json row counts and primary flags
const FAM = [["Main tests", "T, C, H, and all three against A-MEM, on answerable F1 and temporal F1", N("fam_main")],
  ["Other setups", "T + C, T + H, and C + H against A-MEM, on the same two measures", N("fam_other")],
  ["Factorial effects", "T, C, H, T × C, T × H, C × H, and T × C × H, on the same two measures", N("fam_factorial")]];
add(p(`The tests were grouped into ${V(asCount(FAM.length), "rows of Table " + T.families)} families, and the Holm (1979) procedure was applied within each family. The procedure keeps the chance of any false rejection within a family at ${P("alpha_pct", 0)}; it does not correct across families. Table ${T.families} defines the families.`));
tbl("families", "Test Families", ["Family", "Tests", "Number of tests"], FAM, [1800, 4800, 1400],
  "Holm correction was applied within each family.");
add(h2("Decision Rule"));
// src: scripts/analyze.py (real = Holm p < alpha), tables.md columns
add(p(`A difference is called significant only if its Holm-adjusted p-value is below ${V(rnd(fact("alpha"), 2).replace(/^0/, ""), "alpha")}. The uncorrected ${P("ci_level_pct", 0)} interval is reported next to every test. For the comparisons with A-MEM on samples ${allRange()}, the number of runs, out of ${W("n_seeds")}, in which the setup scored higher than A-MEM is also given, and for the main tests the number of questions that improved or worsened. The trial run and the failed first attempt at wave 1 were excluded from every analysis, as the plan required.`));

// ------------------------------------------------------------------ ethics
add(h1("Ethical Considerations"));
add(p("The study involved no human participants and collected no personal data. [TO CONFIRM BEFORE SUBMISSION: whether UTPB requires Institutional Review Board review, or a determination that this is not human-subjects research. Ask the committee chair or the IRB office, then replace this note.] The conversations in LoCoMo are not records of real people. Maharana et al. (2024) produced them with a pipeline in which language-model agents, each given a persona and a temporal event graph, held the conversations, and human annotators then verified and edited them. The speakers named in this thesis are those personas. The conversations and questions were sent to the OpenAI API during memory construction and answering, under the API's terms of use. The API key was kept out of the repository. The use of generative AI tools in preparing this thesis is described in the Disclosure of AI Tool Usage at the front of the document."));

add(h1("Summary"));
add(p(`The study compared A-MEM with every combination of ${W("n_modules")} T-MEM modules in a ${lv()} factorial design on ${W("n_samples")} LoCoMo samples, with ${N("d_total_turns")} dialogue turns and ${N("d_total_questions")} questions, ${W("n_seeds")} runs per setup, and ${N("n_runs")} runs in all. All setups shared one memory bank per sample, the same search words, and the same option order, and A-MEM's memory, retrieval, and answering code paths, prompts, and temperatures were not changed. The runs passed ${N("check_kinds")} kinds of check (${X("check_first")}–${X("check_last")}), including an offline replay of every retrieved context. The measures, test families, correction, and decision rule were fixed and committed before any run. Chapter IV reports the results, one research question at a time.`));

function hn(xs) {
  const a = xs.map((x) => x.split("_")[0]), n = a.map((x) => Number(x.slice(1)));
  must(n.every((v, i) => i === 0 || v === n[i - 1] + 1), "half is a consecutive range of setups");
  return `${a[0]}–${a[a.length - 1]}`;
}
module.exports = out;
