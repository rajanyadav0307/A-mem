# Experiment Protocol: Confirming the Consolidation Result

Branch: `consolidation-support`. Written 2026-10-21. Status: **plan only, no runs started.**

## 0. Why this protocol exists

On samples 0–1, consolidation raised F1 on answerable questions (categories 1–4) by +0.019 for both A-MEM and T-MEM V2, in all 6 seed pairs (`experiments/consolidation_qa_samples0-1_gpt-4o-mini/ANALYSIS.md`). That result is not yet trustworthy:

| Weakness | Evidence |
|---|---|
| High run-to-run noise | Two runs of the same A-MEM setup give different F1 on 93 of 233 answerable questions (40%) |
| Small sample | Per-question ΔF1 has sd 0.161, so with 233 questions the 95% CI is ±0.021: the +0.019 could be zero |
| Post-hoc choices | τ = 0.80, cap = 1 and "exclude category 5" were all chosen on samples 0–1, the same data being reported |
| Category-5 scoring | Scored against LoCoMo's `adversarial_answer` (a trap), so refusing the trap lowers F1 |
| F1 penalizes paraphrase | Correct but reworded answers score low, which is consolidation's main failure mode |
| Unequal inputs between systems | Search keywords are regenerated at temperature 0.7 in every run, so two setups search with different queries |
| Silent failure path | `answer_question` logs a warning and records `""` when an API call fails (`test_advanced_robust.py:151`) |

## 1. Checks already done (2026-10-21)

| Check | Result |
|---|---|
| Category-5 questions in samples 0–1 | **All 71 are unanswerable traps.** 58 name the wrong speaker; the other 13 change a detail, e.g. "grandpa" for grandma, "Barcelona" for Rome, "sculpture" for painting. One trap answer is literally "Not mentioned" (*What temporary job did Jon take…*). |
| Model version | `gpt-4o-mini` is currently served by `gpt-4o-mini-2024-07-18`, which is available to pin |
| Silent failures so far | None: 0 failed answers in the 12 QA runs, and 0 analysis or evolution fallbacks in the May 6 build logs |
| June banks for samples 2–4 | Built with prompts and note-building logic identical to May 6. The only differences are retry handling, the strict-failure option, and local embedding-model loading. |
| Dataset size | 10 samples, 1,986 questions, 1,540 answerable. Samples 2–9: 1,682 questions (1,307 answerable, 375 category 5) and 5,094 turns. |
| `off` = May 6 retrieval | 608/608 contexts identical (`analysis/off_mode_check.json`) |

## 2. Pre-registration

This section must be committed **before** any test-set bank is built or any test run starts.

**Hypotheses**
- **H1 (main):** consolidation (`primary_expand`, cap 1, v3 merge, τ = 0.80) raises F1 on categories 1–4 for A-MEM.
- **H2 (main):** the same for T-MEM V2.
- **H3 (secondary):** consolidation raises category-5 refusal accuracy.
- **H4 (secondary):** T-MEM V2 beats A-MEM on category-2 F1. This is the thesis claim, re-tested.

**Main metric:** F1 on categories 1–4 (the A-MEM / thesis token F1).

**Secondary metrics**
- AI-judge accuracy on categories 1–4
- Category-5 refusal accuracy
- Category-2 F1
- Evidence recall using the saved query keywords
- The original all-category F1, reported for comparison with the thesis

**Success rule for H1 and H2:** the 95% paired-bootstrap CI of ΔF1 (setup with consolidation minus setup without, averaged over runs) lies above 0, after Holm correction across H1 and H2.

**Everything else is exploratory:** category-level F1 (category 3 has only 83 test questions), ablations, and error analysis.

**Frozen settings (no tuning on the test set):** τ = 0.80, max group size 5, same speaker only, merge prompt v3, `union` embedding recipe, `primary_expand`, cap 1, k = 10, and T-MEM V2 at its thesis defaults.

## 3. Data split

| Set | Samples | Use |
|---|---|---|
| Dev | 0, 1 | All tuning (finished), pipeline checks, judge validation |
| Test | 2–9 | Evaluated **once**, with frozen settings |

**Memory banks for the test set**
- **Samples 2–4:** reuse the June banks if their build logs show 0 analysis or evolution fallbacks; otherwise rebuild them. Rebuilding is not "more faithful" in itself, because building runs at temperature 0.7 and so is random anyway.
- **Samples 5–9:** build with the current branch code, whose note building is unchanged since May 6 (3,122 turns).
- Then build the v3 consolidated banks for samples 2–9 with the frozen settings. Consolidation uses no answer labels.

## 4. Noise reduction

1. **Shared query keywords.** Generate the keywords once per question (temperature 0), save them to `keywords_<sample>.json`, and have every setup and every seed read them. Retrieval then becomes the only difference between the two arms. This also makes evidence recall measurable with the real QA queries.
2. **Answer temperature 0** for all categories. The category-5 order stays seeded.
3. **Pinned model:** `gpt-4o-mini-2024-07-18`, recorded in every result file.
4. **3 runs per setup** (seeds 42, 43, 44). Temperature 0 isn't perfectly repeatable, and the seed still sets the category-5 option order. The spread across runs is reported.

**Comparability note.** Steps 1–2 change the protocol relative to the thesis and the A-MEM paper (keywords and answers at temperature 0.7). The main results therefore use the controlled protocol, and the thesis-protocol runs from 2026-10-21 (samples 0–1) are kept separately for comparison. The two are never mixed in one table without a label.

## 5. Metrics

1. **Token F1, categories 1–4.** This is the main metric.
2. **Category-5 refusal accuracy.** Correct if the answer says "not mentioned" and does not give the trap answer. Any question whose trap answer is itself "Not mentioned" is excluded and listed by name.
3. **AI-judge accuracy.** A yes/no prompt, `gpt-4o-mini-2024-07-18` at temperature 0, which sees the question, the reference and the answer but not which system produced it. Before use, it is validated against about 100 dev-set answers labelled by hand (target agreement ≥ 90%, report Cohen's κ). If it falls short, fix the prompt on the dev set and re-validate; it is never tuned on the test set.
4. **Evidence recall@context,** using the saved keywords. This runs without any LLM calls.
5. **All-category F1 with the original scoring,** for comparison with the thesis only.

## 6. Statistics

- **Paired design:** the same question in both arms. For each question, average F1 over the 3 runs, then compute ΔF1.
- **95% CI:** paired bootstrap over questions, stratified by conversation (10,000 resamples). With only 8 test conversations, a pure resample-by-conversation bootstrap would be unstable, so it isn't used.
- **Consistency across conversations:** report in how many of the 8 conversations ΔF1 > 0, with a sign test.
- **Multiple comparisons:** Holm correction across H1 and H2. All other tests are labelled exploratory.
- **Power,** from the dev data: per-question sd 0.161 with 1,307 test questions gives SE ≈ 0.0045, a 95% CI of about ±0.009, and a detectable effect of about 0.013 at 80% power. This assumes the sd stays the same; noise reduction should make it smaller.

## 7. Controls and ablations (exploratory)

1. **Dedupe-only control.** A-MEM with duplicate notes removed from the prompt and no merged notes. Consolidation also raised the number of different notes in the prompt (23.4 → 24.7), so this tests whether the gain comes from removing duplicates alone.
2. **Cap 0.** Merged notes exist but are never retrieved: is it hiding the sources, or the summaries, that matters?
3. **Merge type.** Small-talk merges only vs same-fact merges only.
4. **Paraphrase check.** Count losses where the merged note rewords the words the reference uses (see `ANALYSIS.md` §5).

## 8. Error-proofing the pipeline

1. **Fail loudly.** Stop the run if an LLM call fails after retries, or if any answer is empty. No `""` answers get scored.
2. **Record in every result file:** git commit, model version, seed, all CLI settings, memory-bank fingerprint (SHA-256 of the notes), keywords-file fingerprint, start and end time.
3. **Checks before scoring:** identical question lists and order across all runs; the expected question count; the keyword file covers every question.
4. **Re-run `check_off_mode_matches_may6.py`** after any change to retrieval code.
5. **Log retries and rate-limit events** at INFO, and report their counts per run.
6. **Manual error analysis:** read 50 randomly chosen answers that changed between arms, and classify each as a retrieval change, paraphrase, judge disagreement, or a trap refusal.

## 9. Order of work

| Step | Output | Est. API cost |
|---|---|---|
| 1. Code: shared keywords, temperature 0, pinned model, fail loudly, recorded settings, refusal metric, AI judge | Tested code, `off` check passes | — |
| 2. Validate the judge on 100 hand-labelled dev answers | Agreement, κ | <$1 |
| 3. Dev rerun on samples 0–1 with the new protocol (4 setups × 3 runs) | Confirms the pipeline; noise estimate | ~$4 |
| 4. Commit the pre-registration (this file, final) | Commit hash cited in the write-up | — |
| 5. Check or reuse banks for 2–4; build 5–9 | Banks plus build logs | ~$5–10 |
| 6. Build v3 consolidated banks for 2–9 | Merge logs | ~$2 |
| 7. Test run: 4 setups × 3 runs on samples 2–9 | Results JSONs | ~$30–35 |
| 8. Statistics, controls, error analysis, write-up | Final tables | ~$5 for controls |

**Cost basis:** one test run is 1,682 answer prompts of about 9k tokens, roughly 15M input tokens (about $2.3), plus the judge.

## 10. Corrections to the first draft of this plan (2026-10-21)

- Turns to build for samples 2–9: **5,094**, not about 5,300. Only 3,122 (samples 5–9) if the 2–4 banks are reused.
- Test-run cost: **about $30–35**, not $15–20.
- Category 5: **all 71** questions are traps, not 58. The refusal metric must handle the one trap answer that is "Not mentioned".
- Rebuilding the June banks is optional. Their prompts match May 6, and rebuilding would not remove randomness.
- Bootstrap: stratified by conversation, not resampled by conversation (8 test conversations is too few).
- Placebo control replaced by the **dedupe-only control**, which tests the more likely alternative explanation.
- Added the comparability note: temperature 0 and shared keywords change the protocol, so results are not directly comparable with the thesis numbers.
