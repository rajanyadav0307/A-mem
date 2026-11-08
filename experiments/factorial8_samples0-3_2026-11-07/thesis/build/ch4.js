// Chapter IV. Numbers come from analysis/summary.json (the Stage 6 analysis), analysis/extra.json
// (Stage 7), and thesis/facts.json, and enter the text only through V/N/W/D/P/X (lib.js).
// Every sentence that states a result is guarded by must(): if the data do not support it, the build stops.
const fs = require("fs");
const { chapter, h1, h2, p, table, figure, fact, rnd, asCount, cap, N, W, Wc, D, P, X, V, REFS, nextFigure } = require("./lib");
const S = JSON.parse(fs.readFileSync(process.env.SUMMARY));
const XT = JSON.parse(fs.readFileSync(process.env.EXTRA));
const MAN = JSON.parse(fs.readFileSync(process.env.MANIFEST));
const FIG = process.env.FIGDIR;
const T = { complete: 15, scores: 16, main: 17, effects: 18, mech: 19, cats: 20, inter: 21, other: 22, s3: 23, devscores: 24, groups: 25, traps: 26, metrics: 27, summary: 28 };
const out = [];
const add = (...xs) => xs.forEach((x) => (Array.isArray(x) ? out.push(...x) : out.push(x)));
function tbl(key, ...args) { const [els, n] = table(...args); if (n !== T[key]) throw new Error(`table ${key} is ${n}, expected ${T[key]}`); add(els); }
const must = (cond, msg) => { if (!cond) throw new Error("data do not support the sentence: " + msg); return ""; };

const A = "samples 0-3", S3 = "sample 3 (clean test)", DEV = "samples 0-2 (development)";
const SMP = MAN.samples, DEVS = SMP.slice(0, -1), TEST = SMP[SMP.length - 1];
const sid = (s) => V(String(s), "manifest samples");
const devR = () => `${sid(DEVS[0])}–${sid(DEVS[DEVS.length - 1])}`;
const allR = () => `${sid(SMP[0])}–${sid(SMP[SMP.length - 1])}`;
const SET = Object.keys(MAN.setups);
const MAIN = SET.filter((s) => S.vs_amem[A].some((t) => t.setup === s && t.primary));
const OTHER = SET.filter((s) => S.vs_amem[A].some((t) => t.setup === s && !t.primary));
const ALONE = MAIN.filter((s) => Object.values(MAN.setups[s]).filter(Boolean).length === 1);
const NAME = { s1_amem: "A-MEM", s2_t: "T", s3_c: "C", s4_h: "H", s5_tc: "T + C", s6_th: "T + H", s7_ch: "C + H", s8_tch: "All three" };
const WITH_H = SET.filter((s) => MAN.setups[s].conflict), NO_H = SET.filter((s) => !MAN.setups[s].conflict && s !== "s1_amem");
const MEAS = { answerable_f1: "Answerable F1", time_f1: "Temporal F1" };
const EFN = { T: "T", C: "C", H: "H", TxC: "T × C", TxH: "T × H", CxH: "C × H", TxCxH: "T × C × H" };
const INTER = ["TxC", "TxH", "CxH", "TxCxH"], EFF = ["T", "C", "H", ...INTER];
const GROUPS = [[A, () => `Samples ${allR()}`], [DEV, () => `Samples ${devR()}`], [S3, () => `Sample ${sid(TEST)}`]];
must(JSON.stringify(SET) === JSON.stringify(Object.keys(NAME)), "setup ids");
must(JSON.stringify(MAIN) === JSON.stringify(["s2_t", "s3_c", "s4_h", "s8_tch"]) && JSON.stringify(ALONE) === JSON.stringify(["s2_t", "s3_c", "s4_h"]), "families");

// formatters: every output is registered through V
const f3 = (x) => V(rnd(x, 3), "summary/extra");
const sgs = (x) => { const r = rnd(Math.abs(x), 3); return r === "0.000" ? "0.000" : (x < 0 ? "−" : "+") + r; };
const sg = (x) => V(sgs(x), "summary");
const bnd = (x) => V((x < 0 ? "−" : "+") + rnd(Math.abs(x), 3), "summary ci");   // interval bounds keep their sign, even when they round to 0.000
const mag = (x) => V(rnd(Math.abs(x), 3), "summary");
const pvs = (x) => (x >= 0.9995 ? "1.000" : rnd(x, 3).replace(/^0/, ""));
const pv = (x) => V(pvs(x), "summary p_holm");
const ci = (c) => `[${bnd(c[0])}, ${bnd(c[1])}]`;
const pct = (x) => V(rnd(100 * x, 1) + "%", "summary");
const cnt = (x) => V(asCount(x), "count");
const num = (x) => V(Number(x).toLocaleString("en-US"), "count");
const mean = (g, s, m) => S.setups[g][s][m].mean;
const sd = (g, s, m) => S.setups[g][s][m].sd;
const ms = (g, s, m) => `${f3(mean(g, s, m))} ± ${f3(sd(g, s, m))}`;
const mp = (g, s, m) => `${pct(mean(g, s, m))} ± ${V(rnd(100 * sd(g, s, m), 1), "summary")}`;
const vt = (g, s, m) => { const r = S.vs_amem[g].filter((t) => t.setup === s && t.measure === m); if (r.length !== 1) throw new Error(`vs_amem ${g} ${s} ${m}`); return r[0]; };
const fe = (g, e, m) => { const r = S.factorial[g].filter((t) => t.effect === e && t.measure === m); if (r.length !== 1) throw new Error(`factorial ${g} ${e} ${m}`); return r[0]; };
const yes = (t) => V(t.real ? "Yes" : "No", "summary real");
const star = (t) => (t.real ? "*" : "");
const pq = (t) => `p = ${pv(t.p_holm)}`;
const runsOf = (t) => `${num(t.runs_better)} of ${N("n_seeds")}`;   // tables use digits
const NS = fact("n_seeds");
const alpha = () => V(rnd(fact("alpha"), 2).replace(/^0/, ""), "alpha");
const SIGNOTE = () => `* Significant (Holm p < ${alpha()}).`;
const ciLvl = () => P("ci_level_pct", 0);
const minmax = (xs) => [Math.min(...xs), Math.max(...xs)];
const realSet = (g, setups, m) => setups.filter((s) => vt(g, s, m).real);
const eqName = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const nq = (g, m) => vt(g, "s2_t", m).questions;
const qcount = (samples, k) => samples.reduce((a, s) => a + fact(`d${s}_${k}`), 0);
const sampleQ = { [A]: SMP, [DEV]: DEVS, [S3]: [TEST] };
const overlap = (a, b) => a[0] <= b[1] && b[0] <= a[1];
for (const g of [A, DEV, S3]) {
  must(nq(g, "time_f1") === qcount(sampleQ[g], "cat2"), "temporal question count " + g);
  must(nq(g, "answerable_f1") === [1, 2, 3, 4].reduce((a, c) => a + qcount(sampleQ[g], "cat" + c), 0), "answerable count " + g);
}
must(S.method.runs === NS, "runs");

add(chapter("IV", "RESULTS AND FINDINGS"));
add(p(`This chapter reports the results of the factorial experiment in the order of the research questions (RQ1–RQ5). As in Chapter III, T, C, and H stand for the time-ranking, consolidation, and conflict-handling modules, and s1–s8 for the ${W("n_setups")} setups of Table ${REFS.setupsTable}. All numbers come from the ${N("n_runs")} result files of the experiment and their logs, the shared memory banks and search-word files, the build log of sample ${sid(TEST)}, and the data file. Every test, interval, and p-value was computed by the analysis script fixed before the runs. Two analyses were computed afterwards with separate code and are labeled as descriptive: what each module changed in the model's context, and the averages of the other measures over the runs. Values are means over the ${W("n_seeds")} runs unless stated otherwise. Differences are computed question by question, with each question's score first averaged over the ${W("n_seeds")} runs. Following the decision rule of Chapter III, a difference is called significant only when its Holm-adjusted p-value is below ${alpha()}; the p-values reported are Holm-adjusted unless marked otherwise, and every ${ciLvl()} interval is uncorrected.`));

// ---------------- data screening
add(h1("Data Screening and Run Checks"));
must(fact("answers_total") === fact("n_runs") * fact("d_total_questions"), "answers = runs x questions");
must(["r2_empty_total", "r6_bad_total", "r6_retries_total", "r11_differ_total", "r10_differ_total", "r9_mismatch_total"].every((k) => fact(k) === 0), "all checks clean");
must(fact("r10_questions") === fact("d_nontemporal") && fact("r9_questions") === fact("d_total_cat5"), "R10 and R9 cover all questions of their kind");
add(p(`Before any comparison, every result file and its log were checked. Table ${T.complete} summarizes the outcome. All ${N("n_runs")} runs finished, and all ${N("answers_total")} answers were present and non-empty. All ${N("checks_per_wave")} checks of every wave passed, and when the checks were run again across the ${N("n_runs")} files together, all ${N("checks_final")} passed. No call to the language model failed, and no retry was logged, in any of the ${N("n_runs")} runs.`));
tbl("complete", "Completeness and Checks of the Runs",
  ["Item", "Result"],
  [[`Runs (${N("n_setups")} setups × ${N("n_seeds")} seeds)`, `${N("n_runs")} of ${N("n_runs")} finished`],
   [`Answers (${N("n_runs")} runs × ${N("d_total_questions")} questions)`, `${N("answers_total")}, none empty`],
   [`Checks per wave (${X("check_first")}–${X("check_last")})`, `${N("checks_per_wave")} of ${N("checks_per_wave")} passed in each of the ${W("n_seeds")} waves`],
   [`Final checks across all ${N("n_runs")} files`, `${N("checks_final")} of ${N("checks_final")} passed`],
   ["Errors, failed answers, and logged retries (R6)", `${N("r6_bad_total")} errors or failed answers and ${N("r6_retries_total")} retries in all runs`],
   ["Contexts replayed offline (R11)", `${N("answers_total")}; ${N("r11_differ_total")} differ from the log`],
   ["Non-temporal questions, time ranking on vs. off (R10)", `${N("r10_differ_total")} of ${N("r10_questions")} differ, in every pair and every run`],
   ["Adversarial option order (R9)", `${N("r9_mismatch_total")} mismatches in ${N("r9_questions")} questions, all setups and runs`]],
  [4400, 3400],
  "R10 compares s2 with s1, s5 with s3, s6 with s4, and s8 with s7. The failed first attempt at wave 1 and the trial are not included. Source: the check files in the experiment folder (checks/).");
add(p(`Two of the checks bear directly on the comparisons that follow. The replay check shows that every context the answering model received is exactly the context the code produces from the shared bank and the shared search words, so no setup received a different input by accident. Check R10 shows that time ranking changed no retrieved note outside temporal questions: for all ${N("r10_questions")} non-temporal questions, in all ${W("n_seeds")} runs, each setup with time ranking on retrieved exactly the same notes as its partner with it off.`));
{
  const sa = minmax(SET.map((s) => sd(A, s, "answerable_f1"))), st = minmax(SET.map((s) => sd(A, s, "time_f1"))), s3t = minmax(SET.map((s) => sd(S3, s, "time_f1")));
  add(p(`The run-to-run variation gives a sense of scale for the differences that follow. Across the setups, the standard deviation over the ${W("n_seeds")} runs ranged from ${f3(sa[0])} to ${f3(sa[1])} for answerable F1 and from ${f3(st[0])} to ${f3(st[1])} for temporal F1 on samples ${allR()}, and from ${f3(s3t[0])} to ${f3(s3t[1])} for temporal F1 on sample ${sid(TEST)} alone.`));
}

// ---------------- overview
add(h1("Overview of the Setups"));
{
  const rankT = [...SET].sort((a, b) => mean(A, b, "time_f1") - mean(A, a, "time_f1"));
  must(eqName([...rankT.slice(0, WITH_H.length)].sort(), [...WITH_H].sort()), "the setups with H have the highest temporal F1");
  const hr = minmax(WITH_H.map((s) => mean(A, s, "time_f1")));
  const gap = Math.max(...NO_H.map((s) => Math.abs(mean(A, s, "time_f1") - mean(A, "s1_amem", "time_f1"))));
  const g3 = WITH_H.map((s) => mean(S3, s, "time_f1") - mean(S3, "s1_amem", "time_f1")), gA = WITH_H.map((s) => mean(A, s, "time_f1") - mean(A, "s1_amem", "time_f1"));
  must(g3.every((x, i) => x < gA[i]), "gains with H smaller on sample 3");
  const runs3 = (s) => minmax(S.setups[S3][s].time_f1.per_run);
  must(SET.every((s) => overlap(runs3(s), runs3("s1_amem"))), "on sample 3 every setup's runs overlap A-MEM's");
  const fig2 = nextFigure();
  add(p(`Table ${T.scores} gives the scores of the ${W("n_setups")} setups on samples ${allR()}, and Figure ${fig2} shows each run. Three patterns are visible before any test. The ${cnt(WITH_H.length)} setups with conflict handling on have the ${cnt(WITH_H.length)} highest temporal F1 scores, from ${f3(hr[0])} to ${f3(hr[1])}, against ${f3(mean(A, "s1_amem", "time_f1"))} for A-MEM. The setups without conflict handling are within ${f3(gap)} of A-MEM on temporal F1. On sample ${sid(TEST)}, shown in the right half of Figure ${fig2}, the gains of the setups with conflict handling are smaller, and the range of runs of every setup overlaps that of A-MEM.`));
  tbl("scores", `Scores of the Setups (Samples ${allR()}, Mean Over ${V(cap(asCount(NS)), "n_seeds")} Runs)`,
    ["Setup", "Answerable F1", "Temporal F1", "Refusal rate", "Overall F1 (A-MEM scoring)", "Overall, refusals credited"],
    SET.map((s) => [NAME[s], ms(A, s, "answerable_f1"), ms(A, s, "time_f1"), mp(A, s, "trap_refusal"), ms(A, s, "overall_f1_paper"), ms(A, s, "overall_refusal_credited")]),
    [1300, 1350, 1350, 1300, 1400, 1300],
    `Values after ± are standard deviations over the ${W("n_seeds")} runs (in percentage points for the refusal rate). Of the ${N("d_total_questions")} questions, ${N("d_answerable")} are answerable (categories 1–4), of which ${N("d_total_cat2")} are temporal (category 2), and ${N("d_total_cat5")} are adversarial (category 5).`);
  const [els] = figure(`${FIG}/fig2_setups.png`, 5.8, 4.86, `Temporal F1 (top) and answerable F1 (bottom) of the setups on samples ${allR()} (left) and on sample ${sid(TEST)} alone (right). Dots are the ${W("n_seeds")} runs; horizontal bars are the means; the dashed line is the mean of A-MEM. Vertical scales differ between panels.`);
  add(els);
}

// ---------------- RQ1
add(h1("RQ1: Each Module Alone"));
{
  const h = vt(A, "s4_h", "time_f1");
  must(eqName(realSet(A, ALONE, "time_f1"), ["s4_h"]) && h.diff > 0, "only H alone significant on temporal F1, a gain");
  must(realSet(A, ALONE, "answerable_f1").length === 0, "no module alone significant on answerable F1");
  must(h.runs_better === NS, "H better in all runs");
  const ad = ALONE.map((s) => vt(A, s, "answerable_f1").diff);
  add(p(`Of the ${cnt(ALONE.length)} modules, only conflict handling changed temporal F1 significantly on its own (Table ${T.main}, main tests on samples ${allR()}). It raised temporal F1 from ${f3(mean(A, "s1_amem", "time_f1"))} to ${f3(mean(A, "s4_h", "time_f1"))}, a difference of ${sg(h.diff)} (${ciLvl()} interval ${ci(h.ci95)}, ${pq(h)}), and it scored higher than A-MEM in all ${W("n_seeds")} runs. Time ranking alone (${sg(vt(A, "s2_t", "time_f1").diff)}) and consolidation alone (${sg(vt(A, "s3_c", "time_f1").diff)}) did not change temporal F1 significantly. No module alone changed answerable F1 significantly; the ${cnt(ALONE.length)} differences lie between ${sg(Math.min(...ad))} and ${sg(Math.max(...ad))}.`));
}
tbl("main", `Main Tests: Each Module Alone and All Three Against A-MEM (Samples ${allR()})`,
  ["Setup", "Measure", "Difference", `${ciLvl()} interval`, "Holm p", "Significant", "Runs better", "Questions better / worse"],
  MAIN.flatMap((s) => ["time_f1", "answerable_f1"].map((m) => { const t = vt(A, s, m);
    return [NAME[s], MEAS[m], sg(t.diff), ci(t.ci95), pv(t.p_holm), yes(t), runsOf(t), `${num(t.questions_better)} / ${num(t.questions_worse)}`]; })),
  [1000, 1150, 950, 1500, 700, 950, 800, 1050],
  `Family of ${W("fam_main")} tests, Holm-corrected. Temporal F1 is over ${N("d_total_cat2")} questions and answerable F1 over ${N("d_answerable")}. Questions better or worse compare per-question F1 averaged over the ${W("n_seeds")} runs; the remaining questions tied.`);
{
  const h = vt(A, "s4_h", "time_f1");
  must(h.questions_better > 0 && h.questions_worse > 0, "changes in both directions under H");
  add(p(`The temporal gain of conflict handling was the net result of changes in both directions. On temporal questions, ${num(h.questions_better)} questions scored higher than with A-MEM, ${num(h.questions_worse)} scored lower, and the remaining ${num(h.questions - h.questions_better - h.questions_worse)} tied.`));
}
{
  const ht = fe(A, "H", "time_f1"), ha = fe(A, "H", "answerable_f1"), ta = fe(A, "T", "time_f1"), ca = fe(A, "C", "time_f1");
  must(ht.real && ha.real && ht.value > 0 && ha.value > 0, "H average effect significant and positive on both");
  must(!vt(A, "s4_h", "answerable_f1").real, "H alone not significant on answerable F1");
  must(["T", "C"].every((e) => !fe(A, e, "time_f1").real && !fe(A, e, "answerable_f1").real), "T and C average effects not significant");
  add(p(`Table ${T.effects} gives the average effect of each module over the four settings of the other two modules. The results are similar, except that the average effect of conflict handling on answerable F1 is significant, although conflict handling alone did not change answerable F1 significantly. The average effect of conflict handling was ${sg(ht.value)} on temporal F1 (${ciLvl()} interval ${ci(ht.ci95)}, ${pq(ht)}) and ${sg(ha.value)} on answerable F1 (${ci(ha.ci95)}, ${pq(ha)}), both significant. The average effects of time ranking and consolidation on temporal F1 (${sg(ta.value)} and ${sg(ca.value)}) were not significant, nor were their average effects on answerable F1.`));
}
tbl("effects", "Average Effect of Each Module Over the Other Settings",
  ["Sample group", "Module", "Temporal F1", `${ciLvl()} interval`, "Holm p", "Answerable F1", `${ciLvl()} interval`, "Holm p"],
  GROUPS.flatMap(([g, gl]) => ["T", "C", "H"].map((e) => {
    const a = fe(g, e, "time_f1"), b = fe(g, e, "answerable_f1");
    return [e === "T" ? gl() : "", e, sg(a.value) + star(a), ci(a.ci95), pv(a.p_holm), sg(b.value) + star(b), ci(b.ci95), pv(b.p_holm)]; })),
  [1300, 600, 1050, 1500, 750, 1100, 1500, 750],
  `Each effect is the mean of the four on-minus-off differences for that module (Equation ${REFS.eqT} for T). Holm correction within the family of ${N("fam_factorial")} factorial effects of each sample group. ${SIGNOTE()}`);

// ---------------- mechanism (Stage 7, descriptive)
add(h2("What Each Module Changed in the Model's Context"));
add(p(`To see how each module changed what the answering model saw, the retrieval of every question in every run was compared across setups, from the shared banks and search words and from the run logs. This analysis was not part of the plan fixed before the runs; it is descriptive and involves no significance test. It was run twice with identical output and recounted by a second method from the run logs, with no difference. Table ${T.mech} gives the results, counted over question-and-run cases.`));
{
  const Mx = XT.mechanism, G = XT.merged_ctx, smp = SMP.map(String);
  const tot = (o, k) => smp.reduce((a, s) => a + o[s][k], 0);
  const get = (o, k, i) => (i === "all" ? tot(o, k) : o[i][k]);
  const share = (a, b) => `${num(a)} (${V(rnd(100 * a / b, 1), "extra")}%)`;
  const col = (fn) => [...smp.map(fn), fn("all")];
  smp.forEach((s) => must(Mx[s].now_q % NS === 0 && G[s].tq === Mx[s].time_q && G[s].all === Mx[s].all_q, "extra.json consistency " + s));
  tbl("mech", "How Often Each Module Changed What the Model Was Shown",
    ["Measure", ...smp.map((s) => `Sample ${sid(s)}`), "All"],
    [["Temporal question-and-run cases", ...col((i) => num(get(Mx, "time_q", i)))],
     [`Time ranking: same ${N("t_k")} notes as A-MEM`, ...col((i) => share(get(Mx, "t_same_set", i), get(Mx, "time_q", i)))],
     [`Time ranking skipped (best note leads by ≥ ${D("t_margin", 2)})`, ...col((i) => share(get(Mx, "t_margin_skip", i), get(Mx, "time_q", i)))],
     ["Time ranking: notes replaced per case, mean", ...col((i) => V(rnd(get(Mx, "t_notes_swapped", i) / get(Mx, "time_q", i), 2), "extra"))],
     ["Conflict handling: temporal contexts with a timeline label", ...col((i) => share(get(Mx, "h_time_ctx_with_timeline", i), get(Mx, "time_q", i)))],
     ["Conflict handling: temporal contexts with an event date", ...col((i) => share(get(Mx, "h_time_ctx_with_happened", i), get(Mx, "time_q", i)))],
     ["Conflict handling: contexts with an OUTDATED label, all questions", ...col((i) => share(get(Mx, "h_ctx_with_outdated", i), get(Mx, "all_q", i)))],
     ["Questions about the present (demotion applies only to replaced notes)", ...col((i) => num(get(Mx, "now_q", i) / NS))],
     ["Consolidation: temporal contexts with a merged note", ...col((i) => share(get(G, "tm", i), get(G, "tq", i)))],
     ["Consolidation: contexts with a merged note, all questions", ...col((i) => share(get(G, "m", i), get(G, "all", i)))]],
    [3300, 1000, 1000, 1000, 1000, 1000],
    `Each question counts once per run (${W("n_seeds")} runs), except the row of questions about the present, which counts questions. Time-ranking rows compare s2 with s1; conflict-handling rows describe s4, and consolidation rows s3. Descriptive analysis, not part of the plan fixed before the runs. Source: analysis/extra.json, recounted in analysis/extra_recount.json.`);
  const tq = tot(Mx, "time_q");
  must(tot(Mx, "t_same_set") / tq > 0.5 && tot(Mx, "t_margin_skip") <= tot(Mx, "t_same_order") && tot(Mx, "t_same_order") <= tot(Mx, "t_same_set"), "time ranking usually left the notes unchanged; skipped cases are a subset");
  must(!vt(A, "s2_t", "time_f1").real, "T not significant");
  add(p(`Time ranking usually left the retrieved notes unchanged. In ${V(rnd(100 * tot(Mx, "t_same_set") / tq, 1), "extra")}% of temporal cases it returned the same ${N("t_k")} notes as A-MEM, at most in a different order; these include the ${V(rnd(100 * tot(Mx, "t_margin_skip") / tq, 1), "extra")}% of cases in which it did not act at all because the best note already led by the skip margin. On average it replaced ${V(rnd(tot(Mx, "t_notes_swapped") / tq, 2), "extra")} of the ${N("t_k")} notes. A change of order alone adds no new note to the context, and temporal F1 did not change significantly.`));
  must(tot(Mx, "h_time_ctx_with_timeline") / tq > 0.5, "timeline labels in most temporal cases");
  must(tot(Mx, "now_q") / NS === fact("now_q_total") && fact("now_q_temporal") === 1 && fact("b3_replaced") === 0, "present-tense questions; sample 3 nothing to demote");
  add(p(`Conflict handling, by contrast, changed what the model saw in most temporal cases. In ${V(rnd(100 * tot(Mx, "h_time_ctx_with_timeline") / tq, 1), "extra")}% of temporal cases the context carried at least one timeline label, and in ${V(rnd(100 * tot(Mx, "h_time_ctx_with_happened") / tq, 1), "extra")}% an event date. Demotion, the other mechanism of conflict handling, could act on very few questions: only ${N("now_q_total")} of the ${N("d_total_questions")} questions are about the present, only ${W("now_q_temporal")} of them is a temporal question, and the bank of sample ${sid(TEST)} has no replaced notes to demote. For temporal questions, therefore, conflict handling changed the retrieved notes in at most ${W("now_q_temporal")} question and otherwise changed only the annotations shown with the notes: timeline labels, event dates, and OUTDATED marks. Its effect most likely came from these annotations, although the experiment did not test which of them mattered.`));
  must(!vt(A, "s3_c", "time_f1").real && !vt(A, "s3_c", "answerable_f1").real, "C not significant on samples 0-3");
  add(p(`Consolidation showed no significant gain, although it changed the context often: a merged note appeared in ${V(rnd(100 * tot(G, "m") / tot(G, "all"), 1), "extra")}% of all contexts and in ${V(rnd(100 * tot(G, "tm") / tot(G, "tq"), 1), "extra")}% of temporal contexts. With consolidation on, a high-scoring merged note takes one of the ${N("t_k")} retrieval slots and brings its sources back through link expansion. One possible explanation, not tested here, is that many merged notes add no new fact: in the build of sample ${sid(TEST)}, ${N("c3_merged_small_talk")} of the ${N("c3_merged")} merged notes summarize small talk (Chapter III).`));
}
add(h2("Scores by Question Category"));
{
  const others = SET.filter((s) => s !== "s1_amem");
  const dev = Math.max(...others.flatMap((s) => [1, 3, 4].map((c) => Math.abs(mean(A, s, `cat${c}_f1`) - mean(A, "s1_amem", `cat${c}_f1`)))));
  add(p(`Table ${T.cats} breaks F1 down by question category; differences by category were not tested. On multi-hop, open-domain, and single-hop questions, every setup was within ${f3(dev)} of A-MEM, and the open-domain scores rest on only ${N("d_total_cat3")} questions.`));
}
tbl("cats", `F1 by Question Category (Samples ${allR()}, Mean Over ${V(cap(asCount(NS)), "n_seeds")} Runs)`,
  ["Setup", "Multi-hop (cat. 1)", "Temporal (cat. 2)", "Open-domain (cat. 3)", "Single-hop (cat. 4)", "Adversarial (cat. 5)"],
  SET.map((s) => [NAME[s], ...[1, 2, 3, 4, 5].map((c) => f3(mean(A, s, `cat${c}_f1`)))]),
  [1500, 1300, 1300, 1300, 1300, 1200],
  `Question counts: ${N("d_total_cat1")}, ${N("d_total_cat2")}, ${N("d_total_cat3")}, ${N("d_total_cat4")}, and ${N("d_total_cat5")}. Category 5 is scored against the adversarial reference answer, as in the A-MEM evaluation, so a correct refusal scores near zero.`);

// ---------------- RQ2
add(h1("RQ2: All Three Together"));
{
  const s8t = vt(A, "s8_tch", "time_f1"), s8a = vt(A, "s8_tch", "answerable_f1");
  must(s8t.runs_better === NS && s8a.runs_better === NS, "all three better in all runs on both");
  must(s8t.real && s8t.diff > 0 && !s8a.real && s8a.ci95[0] > 0, "s8 temporal significant gain; answerable CI excludes zero but not significant");
  add(p(`With all three modules switched on, the all-three setup scored higher than A-MEM on both measures in all ${W("n_seeds")} runs (Table ${T.main}). Temporal F1 rose from ${f3(mean(A, "s1_amem", "time_f1"))} to ${f3(mean(A, "s8_tch", "time_f1"))}, a difference of ${sg(s8t.diff)} (${ciLvl()} interval ${ci(s8t.ci95)}, ${pq(s8t)}), which is significant. Of the temporal questions, ${num(s8t.questions_better)} scored higher and ${num(s8t.questions_worse)} lower. Answerable F1 was ${f3(mean(A, "s8_tch", "answerable_f1"))}, against ${f3(mean(A, "s1_amem", "answerable_f1"))} for A-MEM, a difference of ${sg(s8a.diff)} (${ciLvl()} interval ${ci(s8a.ci95)}). The uncorrected interval excludes zero, but after the Holm correction for the ${W("fam_main")} main tests the difference is not significant (${pq(s8a)}).`));
  const h = vt(A, "s4_h", "time_f1"), ht = fe(A, "H", "time_f1"), tt = fe(A, "T", "time_f1"), ct = fe(A, "C", "time_f1");
  must(sd(A, "s8_tch", "time_f1") === Math.min(...SET.map((s) => sd(A, s, "time_f1"))), "s8 smallest temporal SD");
  must(s8t.diff > h.diff, "s8 temporal gain larger than H alone");
  must(ht.value > s8t.diff / 2 && ht.value > Math.abs(tt.value) + Math.abs(ct.value) && !tt.real && !ct.real, "most of the gain attributed to H");
  add(p(`On temporal questions, the gain of the all-three setup (${sg(s8t.diff)}) exceeds the gain of conflict handling alone (${sg(h.diff)}) by ${mag(s8t.diff - h.diff)}; this difference was not tested. The average effect of conflict handling (${sg(ht.value)}) accounts for most of the gain of the all-three setup, while the average effects of time ranking and consolidation (${sg(tt.value)} and ${sg(ct.value)}) were not significant. The all-three setup also had the smallest run-to-run spread on temporal F1 of the setups (standard deviation ${f3(sd(A, "s8_tch", "time_f1"))}).`));
}

// ---------------- RQ3
add(h1("RQ3: How the Modules Combine"));
{
  const realI = (g) => INTER.flatMap((e) => ["time_f1", "answerable_f1"].filter((m) => fe(g, e, m).real).map((m) => `${e}:${m}`));
  must(realI(A).length === 0 && realI(S3).length === 0 && eqName(realI(DEV), ["CxH:answerable_f1"]), "only C x H on answerable F1, samples 0-2");
  const big = (g, m) => INTER.reduce((b, e) => (Math.abs(fe(g, e, m).value) > Math.abs(fe(g, b, m).value) ? e : b));
  must(big(A, "time_f1") === "CxH" && big(A, "answerable_f1") === "CxH", "C x H largest on both");
  const ct = fe(A, "CxH", "time_f1"), ca = fe(A, "CxH", "answerable_f1"), cd = fe(DEV, "CxH", "answerable_f1"), c3 = fe(S3, "CxH", "answerable_f1");
  must(ct.ci95[0] > 0 && ca.ci95[0] > 0, "C x H uncorrected intervals exclude zero");
  const fig3 = nextFigure();
  add(p(`Table ${T.inter} gives the ${cnt(INTER.length)} interaction effects in each sample group, and Figure ${fig3} shows all ${cnt(EFF.length)} factorial effects with their intervals. On samples ${allR()}, no interaction was significant on either measure after the Holm correction. The largest was between consolidation and conflict handling, whose uncorrected intervals exclude zero on both measures: ${sg(ct.value)} on temporal F1 (${ci(ct.ci95)}, ${pq(ct)}) and ${sg(ca.value)} on answerable F1 (${ci(ca.ci95)}, ${pq(ca)}). On samples ${devR()} alone, this C × H interaction on answerable F1 was significant (${sg(cd.value)}, ${ci(cd.ci95)}, ${pq(cd)}). It is the only significant interaction in any sample group, and on sample ${sid(TEST)} it was ${sg(c3.value)}. No interaction involving time ranking was significant in any sample group.`));
  tbl("inter", "Interaction Effects in Each Sample Group",
    ["Sample group", "Interaction", "Temporal F1", `${ciLvl()} interval`, "Holm p", "Answerable F1", `${ciLvl()} interval`, "Holm p"],
    GROUPS.flatMap(([g, gl]) => INTER.map((e) => {
      const a = fe(g, e, "time_f1"), b = fe(g, e, "answerable_f1");
      return [e === "TxC" ? gl() : "", EFN[e], sg(a.value) + star(a), ci(a.ci95), pv(a.p_holm), sg(b.value) + star(b), ci(b.ci95), pv(b.p_holm)]; })),
    [1300, 950, 1000, 1450, 700, 1050, 1450, 700],
    `Interactions as defined in Chapter III (Equation ${REFS.eqTxC} for T × C). For the two-way interactions, a positive value means that the two modules together gain more than the sum of their separate gains. Holm correction within the family of ${N("fam_factorial")} factorial effects of each sample group. ${SIGNOTE()}`);
  const [els] = figure(`${FIG}/fig3_effects.png`, 6.0, 4.31, `The ${cnt(EFF.length)} factorial effects on temporal F1 (top) and answerable F1 (bottom) in the ${W("n_groups")} sample groups. Lines are ${ciLvl()} bootstrap intervals; filled markers are significant after Holm correction. Horizontal scales differ between the two rows.`);
  add(els);
}
{
  const withHo = OTHER.filter((s) => MAN.setups[s].conflict);
  must(eqName(realSet(A, OTHER, "time_f1"), withHo) && withHo.every((s) => vt(A, s, "time_f1").diff > 0) && realSet(A, OTHER, "answerable_f1").length === 0, "two-module results, samples 0-3");
  must(eqName(realSet(DEV, OTHER, "time_f1"), withHo) && withHo.every((s) => vt(DEV, s, "time_f1").diff > 0) && realSet(DEV, OTHER, "answerable_f1").length === 0, "two-module results, samples 0-2");
  must(realSet(S3, OTHER, "time_f1").length === 0 && realSet(S3, OTHER, "answerable_f1").length === 0, "two-module results, sample 3");
  add(p(`Table ${T.other} compares the ${cnt(OTHER.length)} two-module setups with A-MEM. Both setups that include conflict handling raised temporal F1 significantly on samples ${allR()}, by ${sg(vt(A, "s6_th", "time_f1").diff)} (T + H, ${pq(vt(A, "s6_th", "time_f1"))}) and ${sg(vt(A, "s7_ch", "time_f1").diff)} (C + H, ${pq(vt(A, "s7_ch", "time_f1"))}), while T + C did not differ significantly (${sg(vt(A, "s5_tc", "time_f1").diff)}, ${pq(vt(A, "s5_tc", "time_f1"))}). None changed answerable F1 significantly. The pattern was the same on samples ${devR()}, and on sample ${sid(TEST)} none of the ${cnt(OTHER.length)} differed significantly from A-MEM; both comparisons are reported under RQ4. Comparisons of T + H and C + H with conflict handling alone were not part of the plan; on samples ${allR()} their temporal gains of ${sg(vt(A, "s6_th", "time_f1").diff)} and ${sg(vt(A, "s7_ch", "time_f1").diff)} compare with ${sg(vt(A, "s4_h", "time_f1").diff)} for conflict handling alone.`));
}
tbl("other", `Two-Module Setups Against A-MEM (Samples ${allR()})`,
  ["Setup", "Measure", "Difference", `${ciLvl()} interval`, "Holm p", "Significant", "Runs better"],
  OTHER.flatMap((s) => ["time_f1", "answerable_f1"].map((m) => { const t = vt(A, s, m);
    return [NAME[s], MEAS[m], sg(t.diff), ci(t.ci95), pv(t.p_holm), yes(t), runsOf(t)]; })),
  [1100, 1400, 1100, 1700, 900, 1000, 900],
  `Family of ${W("fam_other")} tests, Holm-corrected.`);

// ---------------- RQ4
add(h1(`RQ4: The Clean Test on Sample ${sid(TEST)}`));
{
  const h3 = vt(S3, "s4_h", "time_f1"), a3 = vt(S3, "s8_tch", "time_f1"), hd = vt(DEV, "s4_h", "time_f1"), ad = vt(DEV, "s8_tch", "time_f1");
  const c3 = vt(S3, "s3_c", "time_f1"), cd = vt(DEV, "s3_c", "time_f1");
  const gains3 = [...MAIN, ...OTHER].flatMap((s) => ["time_f1", "answerable_f1"].filter((m) => vt(S3, s, m).real && vt(S3, s, m).diff > 0));
  must(gains3.length === 0, "no significant gain on sample 3");
  must(h3.diff > 0 && a3.diff > 0 && hd.diff > 0 && ad.diff > 0 && h3.ci95[0] < 0 && a3.ci95[0] < 0, "same direction in both groups; sample 3 intervals include zero");
  must(h3.ci95[1] < hd.diff && a3.ci95[1] < ad.diff && overlap(h3.ci95, hd.ci95) && overlap(a3.ci95, ad.ci95), "sample 3 intervals exclude the samples 0-2 estimates but overlap their intervals");
  const real3 = [...MAIN, ...OTHER].flatMap((s) => ["time_f1", "answerable_f1"].filter((m) => vt(S3, s, m).real).map((m) => `${s}:${m}`));
  must(eqName(real3, ["s3_c:time_f1"]) && c3.diff < 0 && !cd.real, "the only significant difference on sample 3 is a loss for C");
  add(p(`Table ${T.s3} gives the scores and all comparisons with A-MEM on sample ${sid(TEST)} alone, the clean test. No setup improved on A-MEM significantly. With conflict handling alone, temporal F1 was higher by ${sg(h3.diff)} (${ci(h3.ci95)}, ${pq(h3)}) and with all three modules by ${sg(a3.diff)} (${ci(a3.ci95)}, ${pq(a3)}). Both differences point in the same direction as on the development samples, but their intervals include zero. Their intervals also exclude the corresponding estimates on samples ${devR()} (${sg(hd.diff)} and ${sg(ad.diff)}), although they overlap the intervals of those estimates (${ci(hd.ci95)} and ${ci(ad.ci95)}). The data therefore suggest a smaller gain on sample ${sid(TEST)}; the difference between the two sample groups was not itself tested. The only significant difference on sample ${sid(TEST)} was a loss: consolidation alone lowered temporal F1 by ${mag(c3.diff)} (${ci(c3.ci95)}, ${pq(c3)}), and it scored higher than A-MEM in ${cnt(c3.runs_better)} of the ${W("n_seeds")} runs. This loss rests on few questions: of the ${N("d3_cat2")} temporal questions, ${num(c3.questions_better)} scored higher and ${num(c3.questions_worse)} lower, and on samples ${devR()} the same comparison was ${sg(cd.diff)} and not significant.`));
}
tbl("s3", `Scores and Comparisons With A-MEM on Sample ${sid(TEST)}, the Clean Test`,
  ["Setup", "Answerable F1", "Temporal F1", `Temporal F1 vs. A-MEM [${ciLvl()} interval]`, "Holm p", `Answerable F1 vs. A-MEM [${ciLvl()} interval]`, "Holm p"],
  SET.map((s) => { if (s === "s1_amem") return [NAME[s], ms(S3, s, "answerable_f1"), ms(S3, s, "time_f1"), "—", "—", "—", "—"];
    const a = vt(S3, s, "time_f1"), b = vt(S3, s, "answerable_f1");
    return [NAME[s], ms(S3, s, "answerable_f1"), ms(S3, s, "time_f1"), `${sg(a.diff)}${star(a)} ${ci(a.ci95)}`, pv(a.p_holm), `${sg(b.diff)}${star(b)} ${ci(b.ci95)}`, pv(b.p_holm)]; }),
  [1000, 1250, 1250, 1900, 650, 1900, 650],
  `Sample ${sid(TEST)} has ${N("d3_questions")} questions: ${V((fact("d3_questions") - fact("d3_cat5")).toLocaleString("en-US"), "d3_questions - d3_cat5")} answerable, of which ${N("d3_cat2")} temporal. Values after ± are standard deviations over the ${W("n_seeds")} runs. T, C, H, and All three belong to the family of main tests; T + C, T + H, and C + H to the family of other setups; Holm correction within each family. ${SIGNOTE()}`);
tbl("devscores", `Scores of the Setups on Samples ${devR()} (Mean Over ${V(cap(asCount(NS)), "n_seeds")} Runs)`,
  ["Setup", "Answerable F1", "Temporal F1", "Refusal rate", "Overall F1 (A-MEM scoring)", "Overall, refusals credited"],
  SET.map((s) => [NAME[s], ms(DEV, s, "answerable_f1"), ms(DEV, s, "time_f1"), mp(DEV, s, "trap_refusal"), ms(DEV, s, "overall_f1_paper"), ms(DEV, s, "overall_refusal_credited")]),
  [1300, 1350, 1350, 1300, 1400, 1300],
  `Values after ± are standard deviations over the ${W("n_seeds")} runs (in percentage points for the refusal rate). Samples ${devR()} hold ${V(qcount(DEVS, "questions").toLocaleString("en-US"), "d0-2 questions")} questions, of which ${V(String(qcount(DEVS, "cat2")), "d0-2 cat2")} are temporal and ${V(String(qcount(DEVS, "cat5")), "d0-2 cat5")} adversarial.`);
{
  const hd = vt(DEV, "s4_h", "time_f1"), ad = vt(DEV, "s8_tch", "time_f1"), h3 = vt(S3, "s4_h", "time_f1"), a3 = vt(S3, "s8_tch", "time_f1");
  must(hd.real && ad.real, "dev significant");
  const hd_e = fe(DEV, "H", "time_f1"), h3_e = fe(S3, "H", "time_f1");
  must(!h3_e.real && hd_e.real, "H average effect significant on samples 0-2 only");
  add(p(`Table ${T.devscores} gives the scores on the development samples, and Table ${T.groups} sets every comparison with A-MEM on those samples beside the same comparison on sample ${sid(TEST)}. On samples ${devR()}, conflict handling alone raised temporal F1 by ${sg(hd.diff)} and all three modules by ${sg(ad.diff)}, both significant. On sample ${sid(TEST)} the same differences were ${sg(h3.diff)} and ${sg(a3.diff)}, ${V(rnd(h3.diff / hd.diff, 2), "ratio")} and ${V(rnd(a3.diff / ad.diff, 2), "ratio")} times the development values. The average effect of conflict handling on temporal F1 was ${sg(hd_e.value)} on samples ${devR()} (significant) and ${sg(h3_e.value)} on sample ${sid(TEST)} (${ci(h3_e.ci95)}, ${pq(h3_e)}).`));
}
tbl("groups", "Comparisons With A-MEM on the Development Samples and on the Clean Test",
  ["Setup", "Measure", `Samples ${devR()}: difference [${ciLvl()} interval]`, "Holm p", `Sample ${sid(TEST)}: difference [${ciLvl()} interval]`, "Holm p"],
  [...MAIN, ...OTHER].flatMap((s) => ["time_f1", "answerable_f1"].map((m) => { const a = vt(DEV, s, m), b = vt(S3, s, m);
    return [NAME[s], MEAS[m], `${sg(a.diff)}${star(a)} ${ci(a.ci95)}`, pv(a.p_holm), `${sg(b.diff)}${star(b)} ${ci(b.ci95)}`, pv(b.p_holm)]; })),
  [1000, 1300, 2300, 700, 2300, 700],
  `Samples ${devR()}: ${V(qcount(DEVS, "questions").toLocaleString("en-US"), "d0-2 questions")} questions, ${V(String(qcount(DEVS, "cat2")), "d0-2 cat2")} temporal. Sample ${sid(TEST)}: ${N("d3_questions")} questions, ${N("d3_cat2")} temporal. T, C, H, and All three belong to the family of main tests and T + C, T + H, and C + H to the family of other setups, each Holm-corrected within its sample group. ${SIGNOTE()}`);
{
  const M3 = XT.mechanism[String(TEST)];
  must(sd(S3, "s1_amem", "time_f1") > sd(DEV, "s1_amem", "time_f1") && mean(S3, "s1_amem", "time_f1") < mean(DEV, "s1_amem", "time_f1"), "sample 3 A-MEM more variable and lower");
  must(fact("b3_replaced") === 0 && fact("h3_CHANGE") === 0 && fact("h3_CONTRADICTION") === 0 && fact("h3_SAME") === 0 && fact("h3_UNRELATED") === 0 && fact("h3_PROGRESS") + fact("h3_COMPATIBLE") === fact("h3_comparisons"), "sample 3: no replaced notes; only progress or compatible labels");
  add(p(`Two features of sample ${sid(TEST)} bear on this result. First, sample ${sid(TEST)} has ${N("d3_cat2")} temporal questions, against ${V(String(qcount(DEVS, "cat2")), "d0-2 cat2")} in samples ${devR()}, and A-MEM's temporal F1 on sample ${sid(TEST)} varied more from run to run (standard deviation ${f3(sd(S3, "s1_amem", "time_f1"))}, against ${f3(sd(DEV, "s1_amem", "time_f1"))} on samples ${devR()}), so the test on sample ${sid(TEST)} alone can detect only large effects. A-MEM's temporal F1 was also lower on sample ${sid(TEST)} (${f3(mean(S3, "s1_amem", "time_f1"))}, against ${f3(mean(DEV, "s1_amem", "time_f1"))} on samples ${devR()}). Second, the bank of sample ${sid(TEST)} differs from the development banks in the way Chapter III described: it has no replaced notes, so no OUTDATED label and no demotion could act, and its timelines record only progress or compatible detail. Timeline labels and event dates were still shown often (Table ${T.mech}): ${V(rnd(100 * M3.h_time_ctx_with_timeline / M3.time_q, 1), "extra")}% of sample ${sid(TEST)}'s temporal contexts carried a timeline label and ${V(rnd(100 * M3.h_time_ctx_with_happened / M3.time_q, 1), "extra")}% an event date. The result therefore shows neither that conflict handling fails on new conversations nor that its gain carries over.`));
}

// ---------------- RQ5
add(h1("RQ5: Adversarial Questions and Scoring"));
{
  const rA = minmax(SET.map((s) => mean(A, s, "trap_refusal"))), r3 = minmax(SET.map((s) => mean(S3, s, "trap_refusal"))), rD = minmax(SET.map((s) => mean(DEV, s, "trap_refusal")));
  must(r3[0] > rD[1], "every setup refused more on sample 3 than any on samples 0-2");
  add(p(`Table ${T.traps} gives the refusal rate on adversarial questions and the two overall scores for every setup on samples ${allR()} and on sample ${sid(TEST)}. The setups refused at similar rates: on samples ${allR()}, between ${pct(rA[0])} and ${pct(rA[1])}, against ${pct(mean(A, "s1_amem", "trap_refusal"))} for A-MEM. These differences were not tested, as fixed in the plan. All setups refused more often on sample ${sid(TEST)} (${pct(r3[0])} to ${pct(r3[1])}) than on samples ${devR()} (${pct(rD[0])} to ${pct(rD[1])}, Table ${T.devscores}).`));
}
tbl("traps", "Refusal Rate and the Two Overall Scores",
  ["Setup", `Refusal rate, samples ${allR()}`, `Overall F1 (A-MEM scoring), samples ${allR()}`, `Overall, refusals credited, samples ${allR()}`, `Refusal rate, sample ${sid(TEST)}`, `Overall F1 (A-MEM scoring), sample ${sid(TEST)}`, `Overall, refusals credited, sample ${sid(TEST)}`],
  SET.map((s) => [NAME[s], mp(A, s, "trap_refusal"), ms(A, s, "overall_f1_paper"), ms(A, s, "overall_refusal_credited"),
    mp(S3, s, "trap_refusal"), ms(S3, s, "overall_f1_paper"), ms(S3, s, "overall_refusal_credited")]),
  [1000, 1150, 1300, 1250, 1100, 1300, 1250],
  `Samples ${allR()} hold ${N("d_total_cat5")} adversarial questions and sample ${sid(TEST)} holds ${N("d3_cat5")}. Means over ${W("n_seeds")} runs; values after ± are standard deviations (in percentage points for the refusal rate). No significance tests, as fixed in the plan.`);
{
  const byP = [...SET].sort((a, b) => mean(A, b, "overall_f1_paper") - mean(A, a, "overall_f1_paper"));
  const byC = [...SET].sort((a, b) => mean(A, b, "overall_refusal_credited") - mean(A, a, "overall_refusal_credited"));
  must(eqName(byP.slice(0, 3), ["s6_th", "s8_tch", "s4_h"]) && eqName(byC.slice(0, 2), ["s8_tch", "s7_ch"]), "rankings");
  const byR = [...SET].sort((a, b) => mean(A, b, "trap_refusal") - mean(A, a, "trap_refusal"));
  const most = ["s7_ch", "s8_tch"];
  must(eqName([...byR.slice(0, most.length)].sort(), most), "C + H and all three refused most");
  must(most.every((s) => byP.indexOf(s) > byC.indexOf(s)), "they rank lower under A-MEM scoring");
  const gaps = [mean(A, byP[0], "overall_f1_paper") - mean(A, byP[1], "overall_f1_paper"), mean(A, byP[1], "overall_f1_paper") - mean(A, byP[2], "overall_f1_paper"),
    mean(A, byC[0], "overall_refusal_credited") - mean(A, byC[1], "overall_refusal_credited")];
  const sds = SET.flatMap((s) => [sd(A, s, "overall_f1_paper"), sd(A, s, "overall_refusal_credited")]);
  const gapMax = Math.ceil(Math.max(...gaps) * 1000 - 1e-9) / 1000;
  must(gapMax <= Math.min(...sds), "ranking gaps smaller than every run-to-run SD");
  add(p(`The scoring rule changes which setup ranks first. Under A-MEM's scoring, which rewards repeating the adversarial answer, T + H had the highest overall F1 on samples ${allR()} (${f3(mean(A, "s6_th", "overall_f1_paper"))}), followed by the all-three setup (${f3(mean(A, "s8_tch", "overall_f1_paper"))}) and H (${f3(mean(A, "s4_h", "overall_f1_paper"))}). With refusals credited, the all-three setup ranked first (${f3(mean(A, "s8_tch", "overall_refusal_credited"))}), followed by C + H (${f3(mean(A, "s7_ch", "overall_refusal_credited"))}), and T + H had ${f3(mean(A, "s6_th", "overall_refusal_credited"))}. The ${cnt(most.length)} setups that refused most often, C + H and the all-three setup, rank lower under A-MEM's scoring than with refusals credited. These rankings rest on gaps of less than ${V(gapMax.toFixed(3), "max gap rounded up")} before rounding, below every standard deviation of these scores over the ${W("n_seeds")} runs (${f3(Math.min(...sds))} to ${f3(Math.max(...sds))}), so they are indicative only. Because the refusal rates differ little, the scoring rule has little effect on the conclusions of this experiment; it may matter more for systems whose refusal rates differ widely.`));
}

// ---------------- other measures (named in the plan; averaged with separate code)
add(h1("Other Measures"));
{
  const MT = XT.metrics;
  SET.forEach((s) => must(Math.abs(MT[s].f1 - mean(A, s, "overall_f1_paper")) < 1e-9, "metrics f1 = overall F1 " + s));
  const top = (k, n) => [...SET].sort((a, b) => MT[b][k] - MT[a][k]).slice(0, n);
  must(eqName([...top("rougeL_f", WITH_H.length)].sort(), [...WITH_H].sort()), "ROUGE-L highest for the setups with H");
  must(eqName([...top("meteor", 3)].sort(), ["s4_h", "s6_th", "s8_tch"].sort()), "METEOR highest for H, T + H, all three");
  const pairEM = ["s7_ch", "s8_tch"];
  const emLow = [...SET].sort((a, b) => MT[a].exact_match - MT[b].exact_match).slice(0, pairEM.length);
  must(eqName([...emLow].sort(), pairEM) && rnd(MT.s7_ch.exact_match, 3) === rnd(MT.s8_tch.exact_match, 3), "exact match lowest for C + H and all three");
  const ansTop = [...SET].sort((a, b) => mean(A, b, "answerable_f1") - mean(A, a, "answerable_f1")).slice(0, pairEM.length);
  must(eqName([...ansTop].sort(), pairEM), "C + H and all three have the highest answerable F1");
  must(top("bleu1", 1)[0] === "s1_amem", "BLEU-1 highest for A-MEM");
  const spread = (k) => Math.max(...SET.map((s) => MT[s][k])) - Math.min(...SET.map((s) => MT[s][k]));
  const bert = [...new Set(SET.map((s) => rnd(MT[s].bert_f1, 3)))].sort();
  add(p(`Table ${T.metrics} gives the other measures computed by the evaluation code, over all ${N("d_total_questions")} questions with A-MEM's scoring of category 5. The plan named them as other measures to be reported without tests; their averages over the ${W("n_seeds")} runs were computed afterwards with separate code. ROUGE-L and METEOR broadly follow token F1: ROUGE-L is highest for the ${cnt(WITH_H.length)} setups with conflict handling, and METEOR for H, T + H, and the all-three setup. Exact match and BLEU-1 do not: exact match is lowest for C + H and the all-three setup (${f3(MT.s8_tch.exact_match)}), although these ${cnt(pairEM.length)} setups have the highest answerable F1, and BLEU-1 is highest for A-MEM (${f3(MT.s1_amem.bleu1)}). Exact match differs by ${f3(spread("exact_match"))} and BLEU-1 by ${f3(spread("bleu1"))} between the highest and lowest setup, and BERTScore F1 is ${bert.map((b) => V(b, "extra")).join(" or ")} for every setup.`));
  tbl("metrics", `Other Measures, All Questions (Samples ${allR()}, Mean Over ${V(cap(asCount(NS)), "n_seeds")} Runs)`,
    ["Setup", "Token F1", "Exact match", "ROUGE-L", "BLEU-1", "METEOR", "BERTScore F1", "Sentence-BERT similarity"],
    SET.map((s) => [NAME[s], ...["f1", "exact_match", "rougeL_f", "bleu1", "meteor", "bert_f1", "sbert_similarity"].map((k) => f3(MT[s][k]))]),
    [1300, 900, 950, 950, 900, 900, 1100, 1100],
    "Computed by utils.py in the A-MEM evaluation; category 5 is scored against the adversarial reference answer. Named in the plan as other measures, reported without tests; averaged over the runs afterwards with separate code. Source: analysis/extra.json, recounted per question in analysis/extra_recount.json.");
}

// ---------------- summary
add(h1("Summary of Findings"));
add(p(`Table ${T.summary} summarizes the answer to each research question.`));
{
  const s8t = vt(A, "s8_tch", "time_f1"), s8a = vt(A, "s8_tch", "answerable_f1");
  must(vt(DEV, "s4_h", "time_f1").real && fe(DEV, "H", "time_f1").real && !vt(DEV, "s4_h", "answerable_f1").real, "dev H outcomes");
  must(!vt(DEV, "s8_tch", "answerable_f1").real && vt(DEV, "s8_tch", "time_f1").real && !vt(S3, "s8_tch", "time_f1").real && !vt(S3, "s8_tch", "answerable_f1").real, "RQ2 outcomes");
  const devReal = ALONE.flatMap((s) => ["time_f1", "answerable_f1"].filter((m) => vt(DEV, s, m).real).map((m) => `${s}:${m}`));
  const devEff = ["T", "C", "H"].flatMap((e) => ["time_f1", "answerable_f1"].filter((m) => fe(DEV, e, m).real).map((m) => `${e}:${m}`));
  const s3Eff = ["T", "C", "H"].flatMap((e) => ["time_f1", "answerable_f1"].filter((m) => fe(S3, e, m).real).map((m) => `${e}:${m}`));
  must(eqName(devReal, ["s4_h:time_f1"]) && eqName(devEff, ["H:time_f1"]) && s3Eff.length === 0, "dev and sample 3 outcomes for RQ1");
  const h3 = vt(S3, "s4_h", "time_f1"), a3 = vt(S3, "s8_tch", "time_f1");
  tbl("summary", "Summary of Findings by Research Question",
    ["Research question", "Finding", "Null hypothesis"],
    [["RQ1 Each module alone", `On samples ${allR()}, conflict handling alone raised temporal F1 (${sg(vt(A, "s4_h", "time_f1").diff)}, significant), and its average effect was significant on both measures; time ranking and consolidation had no significant effect. On sample ${sid(TEST)}, consolidation alone lowered temporal F1 (${sg(vt(S3, "s3_c", "time_f1").diff)}, significant).`,
      `Samples ${allR()}: rejected for conflict handling on temporal F1 (alone and average effect) and on answerable F1 (average effect only); not rejected for conflict handling alone on answerable F1 or for time ranking or consolidation. Samples ${devR()}: rejected for conflict handling on temporal F1, alone and average effect. Sample ${sid(TEST)}: rejected only for consolidation alone on temporal F1.`],
     ["RQ2 All three together", `On samples ${allR()}, temporal F1 ${sg(s8t.diff)} (significant) and answerable F1 ${sg(s8a.diff)} (not significant after correction); higher than A-MEM in all ${W("n_seeds")} runs on both measures.`, `Rejected for temporal F1 on samples ${allR()} and ${devR()}. Not rejected on sample ${sid(TEST)} or for answerable F1.`],
     ["RQ3 How the modules combine", `No interaction was significant on samples ${allR()} or on sample ${sid(TEST)}. C × H on answerable F1 was significant on samples ${devR()} (${sg(fe(DEV, "CxH", "answerable_f1").value)}) and ${sg(fe(S3, "CxH", "answerable_f1").value)} on sample ${sid(TEST)}. T + H and C + H raised temporal F1 significantly on samples ${allR()} and ${devR()}; T + C did not.`, `Interactions: not rejected on samples ${allR()} or sample ${sid(TEST)}; rejected for C × H on answerable F1 on samples ${devR()}.`],
     ["RQ4 The clean test", `No significant gain on sample ${sid(TEST)}. The differences of H (${sg(h3.diff)}) and the all-three setup (${sg(a3.diff)}) on temporal F1 point the same way and are ${V(rnd(h3.diff / vt(DEV, "s4_h", "time_f1").diff, 2), "ratio")} and ${V(rnd(a3.diff / vt(DEV, "s8_tch", "time_f1").diff, 2), "ratio")} times those on samples ${devR()}; their intervals exclude the samples ${devR()} estimates but overlap their intervals. Consolidation alone lowered temporal F1 significantly.`, "No separate hypothesis."],
     ["RQ5 Adversarial questions", "Refusal rates were similar across setups (not tested). The scoring rule changes the order of the top setups, by gaps smaller than the run-to-run spread, but not the main conclusions.", "Descriptive."]],
    [1700, 3800, 2300], null);
}
add(p(`Several limits apply to these results and are taken up in Chapter V. The bootstrap resamples questions, not conversations, so the intervals do not cover variation between conversations, of which there are only ${W("n_samples")}. Each memory bank was built once, so variation in building it is not sampled. The Holm correction controls false rejections within each family and sample group, not across the ${W("n_families")} families or the ${W("n_groups")} overlapping sample groups. The settings of the modules were chosen on samples ${devR()}, so the estimates on those samples may be optimistic. Time ranking was tested with an oracle router, so its results reflect perfect routing; it showed no significant gain even so, and routing from the question text was not tested. All answers came from one model on one benchmark.`));
{
  const dev2 = qcount(DEVS, "cat2");
  must(dev2 > fact("d_total_cat2") / 2, "development holds most temporal questions");
  must(SET.filter((s) => s !== "s1_amem").every((s) => vt(A, s, "time_f1").diff <= vt(A, "s8_tch", "time_f1").diff), "all three has the largest temporal gain");
  const c3 = vt(S3, "s3_c", "time_f1");
  must(c3.real && c3.diff < 0, "consolidation loss on sample 3");
  add(p(`In short, conflict handling was the only module with a significant effect on samples ${allR()}: it raised temporal F1, a result carried mainly by the development samples, which hold ${V(String(dev2), "d0-2 cat2")} of the ${N("d_total_cat2")} temporal questions. The descriptive analysis suggests that it works through the annotations it adds to each note, but the experiment did not test this mechanism. The all-three setup had the largest estimated temporal gain (${sg(vt(A, "s8_tch", "time_f1").diff)}), though this was not tested against conflict handling alone. Time ranking and consolidation showed no significant gain on samples ${allR()}. On sample ${sid(TEST)}, the gains of conflict handling and of the all-three setup pointed the same way but were smaller and not significant, and consolidation alone lowered temporal F1 significantly. Chapter V discusses what these results mean.`));
}

module.exports = out;
