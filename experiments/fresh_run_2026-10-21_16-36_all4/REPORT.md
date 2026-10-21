# Fresh run fresh_run_2026-10-21_16-36_all4

- Started (UTC): 2026-10-21T21:36:49Z
- Finished (UTC): 2026-10-21T22:07:37Z
- Report written (local): 2026-10-21 17:07
- Code: `a92ef3ec` on `conflict-handling-support`
- Samples [0, 1], 304 questions, k = 10, seeds 42, 43, 44, model gpt-4o-mini (served as gpt-4o-mini-2024-07-18)
- A-MEM (starting point): runs from `experiments/fresh_run_2026-10-21_16-36_all4`
- + time ranking (T-MEM V2): runs from `experiments/fresh_run_2026-10-21_16-36_all4`
- + consolidation (T-MEM V2 + C): runs from `experiments/fresh_run_2026-10-21_16-36_all4`
- + conflict handling (T-MEM V2 + C + CH): runs from `experiments/fresh_run_2026-10-21_16-36_all4`

## Results (average of the runs)

| Step | System | Answerable questions F1 | Time questions F1 | Trap questions refused | Overall F1 (paper scoring) |
|---|---|---|---|---|---|
| 1 | A-MEM (starting point) | 0.325 | 0.450 | 46.0% | 0.376 |
| 2 | + time ranking (T-MEM V2) | 0.318 | 0.457 | 44.1% | 0.374 |
| 3 | + consolidation (T-MEM V2 + C) | 0.333 | 0.452 | 47.9% | 0.378 |
| 4 | + conflict handling (T-MEM V2 + C + CH) | 0.337 | 0.483 | 46.9% | 0.384 |

## Gain over A-MEM

| System | Answerable questions | Time questions | Trap refusals |
|---|---|---|---|
| + time ranking (T-MEM V2) | -0.007 | +0.006 | -1.9 points |
| + consolidation (T-MEM V2 + C) | +0.008 | +0.002 | +1.9 points |
| + conflict handling (T-MEM V2 + C + CH) | +0.012 | +0.033 | +0.9 points |

## Each step vs the step before (matching runs)

Change in answerable F1 for each seed; the last column counts the runs where the step helped.

| Step | Seed 42 | Seed 43 | Seed 44 | Mean change | Runs better |
|---|---|---|---|---|---|
| + time ranking (T-MEM V2) | -0.000 | -0.017 | -0.005 | -0.007 | 0 of 3 |
| + consolidation (T-MEM V2 + C) | +0.014 | +0.025 | +0.009 | +0.016 | 3 of 3 |
| + conflict handling (T-MEM V2 + C + CH) | +0.004 | +0.000 | +0.008 | +0.004 | 3 of 3 |

## Each run

| System | Seed | Answerable F1 | Time F1 | Trap refused | Overall F1 |
|---|---|---|---|---|---|
| A-MEM (starting point) | 42 | 0.319 | 0.441 | 43.7% | 0.377 |
| A-MEM (starting point) | 43 | 0.327 | 0.451 | 49.3% | 0.371 |
| A-MEM (starting point) | 44 | 0.329 | 0.459 | 45.1% | 0.381 |
| + time ranking (T-MEM V2) | 42 | 0.319 | 0.467 | 43.7% | 0.376 |
| + time ranking (T-MEM V2) | 43 | 0.310 | 0.454 | 45.1% | 0.367 |
| + time ranking (T-MEM V2) | 44 | 0.324 | 0.449 | 43.7% | 0.380 |
| + consolidation (T-MEM V2 + C) | 42 | 0.333 | 0.462 | 43.7% | 0.386 |
| + consolidation (T-MEM V2 + C) | 43 | 0.334 | 0.452 | 52.1% | 0.370 |
| + consolidation (T-MEM V2 + C) | 44 | 0.333 | 0.442 | 47.9% | 0.377 |
| + conflict handling (T-MEM V2 + C + CH) | 42 | 0.337 | 0.506 | 50.7% | 0.375 |
| + conflict handling (T-MEM V2 + C + CH) | 43 | 0.335 | 0.477 | 45.1% | 0.385 |
| + conflict handling (T-MEM V2 + C + CH) | 44 | 0.341 | 0.466 | 45.1% | 0.392 |

## Timeline questions only (90 questions, fixed before results)

Rule: question whose evidence turn is a note in a conflict-handling timeline (conflicts_v1 bank). Answerable: 71, trap questions: 19.

| System | Answerable F1 | Trap questions refused |
|---|---|---|
| A-MEM (starting point) | 0.395 | 49.1% |
| + time ranking (T-MEM V2) | 0.355 | 47.4% |
| + consolidation (T-MEM V2 + C) | 0.396 | 50.9% |
| + conflict handling (T-MEM V2 + C + CH) | 0.402 | 56.1% |

**What the columns mean**
- *Answerable questions*: categories 1–4 (233 questions).
- *Time questions*: category 2 (63 questions), the questions T-MEM V2 is built for.
- *Trap questions refused*: category 5 (71 questions) are about things never said; answering "Not mentioned" is correct.
- *Overall F1 (paper scoring)*: all 304 questions, scored as in the paper (category 5 counts the trap answer as right).

**Notes**
- All 12 runs (4 steps × 3 seeds) ran together, 16:36 to 17:07 local time, with the same code (`a92ef3ec`), model and memory banks. This is the fair comparison.
- **Time questions, step 3 → step 4, matching runs:** +0.044, +0.025, +0.024. Conflict handling helped time questions in all 3 runs.
- **Consolidation (step 3)** helped answerable questions in all 3 runs (+0.016 on average). This matches the earlier batches.
- **T-MEM V2 (step 2)** gave only a small gain on time questions in this batch (+0.006) and none on the other questions. Its effect on time questions varies between batches (+0.006 to +0.023), and on other questions it is run-to-run variation (V2 only changes time questions).
- Conflict handling setting: `annotate_demote`; bank `..._v3_conflicts_v1`. See `manifest.json` for fingerprints.
