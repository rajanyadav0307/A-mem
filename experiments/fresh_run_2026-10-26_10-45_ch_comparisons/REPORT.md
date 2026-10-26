# Fresh run fresh_run_2026-10-26_10-45_ch_comparisons

- Started (UTC): 2026-10-26T17:25:51Z
- Finished (UTC): 2026-10-26T17:58:28Z
- Report written (local): 2026-10-26 12:58
- Code: `aadd9560` on `conflict-handling-support`
- Samples [0, 1], 304 questions, k = 10, seeds 42, 43, 44, model gpt-4o-mini (served as gpt-4o-mini-2024-07-18)
- Reference: V2 + C, no conflict handling (step 3): runs from `experiments/fresh_run_2026-10-26_10-45_ch_comparisons`
- Ours: annotate + demote (step 4): runs from `experiments/fresh_run_2026-10-26_10-45_ch_comparisons`
- Annotate only: runs from `experiments/fresh_run_2026-10-26_10-45_ch_comparisons`
- Demote only: runs from `experiments/fresh_run_2026-10-26_10-45_ch_comparisons`
- Timelines only (Theanine-style): runs from `experiments/fresh_run_2026-10-26_10-45_ch_comparisons`
- Date ranges only (Zep-style): runs from `experiments/fresh_run_2026-10-26_10-45_ch_comparisons`

## Results (average of the runs)

| Step | System | Answerable questions F1 | Time questions F1 | Trap questions refused | Overall F1 (paper scoring) |
|---|---|---|---|---|---|
| 1 | Reference: V2 + C, no conflict handling (step 3) | 0.330 | 0.457 | 47.4% | 0.376 |
| 2 | Ours: annotate + demote (step 4) | 0.342 | 0.493 | 47.9% | 0.385 |
| 3 | Annotate only | 0.324 | 0.462 | 47.9% | 0.372 |
| 4 | Demote only | 0.325 | 0.453 | 46.5% | 0.375 |
| 5 | Timelines only (Theanine-style) | 0.341 | 0.493 | 47.9% | 0.385 |
| 6 | Date ranges only (Zep-style) | 0.340 | 0.466 | 43.7% | 0.392 |

## Gain over Reference: V2 + C, no conflict handling (step 3)

| System | Answerable questions | Time questions | Trap refusals |
|---|---|---|---|
| Ours: annotate + demote (step 4) | +0.013 | +0.036 | +0.5 points |
| Annotate only | -0.006 | +0.005 | +0.5 points |
| Demote only | -0.005 | -0.004 | -0.9 points |
| Timelines only (Theanine-style) | +0.011 | +0.036 | +0.5 points |
| Date ranges only (Zep-style) | +0.010 | +0.009 | -3.8 points |

## Each setup vs Reference: V2 + C, no conflict handling (step 3) (matching runs): answerable F1

Change in answerable F1 for each seed; the last column counts the runs where it helped.

| Setup | Seed 42 | Seed 43 | Seed 44 | Mean change | Runs better |
|---|---|---|---|---|---|
| Ours: annotate + demote (step 4) | +0.003 | +0.008 | +0.026 | +0.013 | 3 of 3 |
| Annotate only | -0.014 | -0.022 | +0.018 | -0.006 | 1 of 3 |
| Demote only | -0.019 | -0.009 | +0.013 | -0.005 | 1 of 3 |
| Timelines only (Theanine-style) | +0.013 | +0.006 | +0.016 | +0.011 | 3 of 3 |
| Date ranges only (Zep-style) | +0.006 | +0.006 | +0.018 | +0.010 | 3 of 3 |

## Each setup vs Reference: V2 + C, no conflict handling (step 3) (matching runs): time F1

Change in time F1 for each seed; the last column counts the runs where it helped.

| Setup | Seed 42 | Seed 43 | Seed 44 | Mean change | Runs better |
|---|---|---|---|---|---|
| Ours: annotate + demote (step 4) | +0.038 | +0.032 | +0.037 | +0.036 | 3 of 3 |
| Annotate only | +0.022 | -0.006 | -0.001 | +0.005 | 1 of 3 |
| Demote only | -0.021 | -0.004 | +0.013 | -0.004 | 1 of 3 |
| Timelines only (Theanine-style) | +0.036 | +0.044 | +0.028 | +0.036 | 3 of 3 |
| Date ranges only (Zep-style) | +0.009 | -0.000 | +0.019 | +0.009 | 2 of 3 |

## Each run

| System | Seed | Answerable F1 | Time F1 | Trap refused | Overall F1 |
|---|---|---|---|---|---|
| Reference: V2 + C, no conflict handling (step 3) | 42 | 0.336 | 0.460 | 52.1% | 0.371 |
| Reference: V2 + C, no conflict handling (step 3) | 43 | 0.331 | 0.457 | 45.1% | 0.381 |
| Reference: V2 + C, no conflict handling (step 3) | 44 | 0.321 | 0.455 | 45.1% | 0.375 |
| Ours: annotate + demote (step 4) | 42 | 0.340 | 0.498 | 52.1% | 0.375 |
| Ours: annotate + demote (step 4) | 43 | 0.339 | 0.489 | 46.5% | 0.386 |
| Ours: annotate + demote (step 4) | 44 | 0.348 | 0.492 | 45.1% | 0.395 |
| Annotate only | 42 | 0.323 | 0.482 | 50.7% | 0.364 |
| Annotate only | 43 | 0.309 | 0.450 | 50.7% | 0.355 |
| Annotate only | 44 | 0.339 | 0.454 | 42.3% | 0.395 |
| Demote only | 42 | 0.317 | 0.439 | 47.9% | 0.366 |
| Demote only | 43 | 0.322 | 0.452 | 47.9% | 0.370 |
| Demote only | 44 | 0.335 | 0.468 | 43.7% | 0.389 |
| Timelines only (Theanine-style) | 42 | 0.349 | 0.496 | 52.1% | 0.381 |
| Timelines only (Theanine-style) | 43 | 0.337 | 0.501 | 45.1% | 0.388 |
| Timelines only (Theanine-style) | 44 | 0.337 | 0.483 | 46.5% | 0.385 |
| Date ranges only (Zep-style) | 42 | 0.343 | 0.469 | 40.8% | 0.398 |
| Date ranges only (Zep-style) | 43 | 0.337 | 0.456 | 47.9% | 0.383 |
| Date ranges only (Zep-style) | 44 | 0.340 | 0.474 | 42.3% | 0.395 |

## Timeline questions only (90 questions, fixed before results)

Rule: question whose evidence turn is a note in a conflict-handling timeline (conflicts_v1 bank). Answerable: 71, trap questions: 19.

| System | Answerable F1 | Trap questions refused |
|---|---|---|
| Reference: V2 + C, no conflict handling (step 3) | 0.381 | 50.9% |
| Ours: annotate + demote (step 4) | 0.421 | 50.9% |
| Annotate only | 0.407 | 52.6% |
| Demote only | 0.388 | 50.9% |
| Timelines only (Theanine-style) | 0.414 | 52.6% |
| Date ranges only (Zep-style) | 0.399 | 49.1% |

**What the columns mean**
- *Answerable questions*: categories 1–4 (233 questions).
- *Time questions*: category 2 (63 questions), the questions T-MEM V2 is built for.
- *Trap questions refused*: category 5 (71 questions) are about things never said; answering "Not mentioned" is correct.
- *Overall F1 (paper scoring)*: all 304 questions, scored as in the paper (category 5 counts the trap answer as right).

**How it was run**
- All 18 runs used T-MEM V2 + consolidation (v3 bank, `primary_expand`, cap 1). Only the conflict-handling setting differs.
- They ran in 3 waves, one seed per wave, with all 6 setups of a seed together. Wave times are in `waves.json`.
- A first try at 10:45 ran all 18 at once, ran out of memory, and was stopped. Its results were not kept; see `manifest.json`.

**Reading the results**
- **Two pairs of setups give the AI almost the same prompts:** "annotate + demote" vs "annotate only", and "demote only" vs the reference. Demotion only applies to the 5 "now" questions, so for the other 299 questions each pair is identical. Yet "annotate + demote" beat "annotate only" by +0.018 on answerable questions, in all 3 runs. **That gap is run-to-run noise**, and it shows that a "3 of 3" result of about this size is not proof by itself.
- **Fairer estimate:** combine the near-identical setups (6 runs each):

| Group | Answerable F1 | Time F1 |
|---|---|---|
| No labels (reference + demote only) | 0.328 | 0.455 |
| Our labels (annotate + annotate & demote) | 0.333 | 0.478 |
| Timelines only (Theanine-style) | 0.341 | 0.493 |
| Date ranges only (Zep-style) | 0.340 | 0.466 |

- **Timeline labels help time questions** by about +0.02 to +0.04 F1. The Theanine-style timelines (no OUTDATED or CONFLICT labels) do **at least as well** as our full labels.
- **Our extra pieces (OUTDATED / CONFLICT labels, demotion) show no measurable benefit here.** That is expected: samples 0–1 have only 9 replaced notes, 0 contradictions and 5 "now" questions.
- **Zep-style date ranges** help answerable questions a little but help time questions less. They also lower trap refusals (43.7% vs 47.4%), maybe because "valid … – present" makes facts look current.
