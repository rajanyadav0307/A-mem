# Fresh run fresh_run_2026-10-21_16-21_step4_conflict

- Started (UTC): 2026-10-21T21:21:48Z
- Finished (UTC): 2026-10-21T21:31:28Z
- Report written (local): 2026-10-21 16:31
- Code: `b5c26250` on `conflict-handling-support`
- Samples [0, 1], 304 questions, k = 10, seeds 42, 43, 44, model gpt-4o-mini (served as gpt-4o-mini-2024-07-18)
- A-MEM (starting point): runs from `experiments/fresh_run_2026-10-21_14-27`
- + time ranking (T-MEM V2): runs from `experiments/fresh_run_2026-10-21_14-27`
- + consolidation (T-MEM V2 + C): runs from `experiments/fresh_run_2026-10-21_14-27`
- + conflict handling (T-MEM V2 + C + CH): runs from `experiments/fresh_run_2026-10-21_16-21_step4_conflict`

## Results (average of the runs)

| Step | System | Answerable questions F1 | Time questions F1 | Trap questions refused | Overall F1 (paper scoring) |
|---|---|---|---|---|---|
| 1 | A-MEM (starting point) | 0.321 | 0.439 | 45.1% | 0.375 |
| 2 | + time ranking (T-MEM V2) | 0.328 | 0.462 | 45.5% | 0.380 |
| 3 | + consolidation (T-MEM V2 + C) | 0.336 | 0.471 | 47.9% | 0.379 |
| 4 | + conflict handling (T-MEM V2 + C + CH) | 0.342 | 0.490 | 47.4% | 0.388 |

## Gain over A-MEM

| System | Answerable questions | Time questions | Trap refusals |
|---|---|---|---|
| + time ranking (T-MEM V2) | +0.007 | +0.023 | +0.5 points |
| + consolidation (T-MEM V2 + C) | +0.015 | +0.031 | +2.8 points |
| + conflict handling (T-MEM V2 + C + CH) | +0.021 | +0.050 | +2.3 points |

## Each run

| System | Seed | Answerable F1 | Time F1 | Trap refused | Overall F1 |
|---|---|---|---|---|---|
| A-MEM (starting point) | 42 | 0.334 | 0.480 | 40.8% | 0.394 |
| A-MEM (starting point) | 43 | 0.316 | 0.424 | 50.7% | 0.360 |
| A-MEM (starting point) | 44 | 0.312 | 0.413 | 43.7% | 0.372 |
| + time ranking (T-MEM V2) | 42 | 0.326 | 0.434 | 45.1% | 0.379 |
| + time ranking (T-MEM V2) | 43 | 0.330 | 0.497 | 49.3% | 0.374 |
| + time ranking (T-MEM V2) | 44 | 0.326 | 0.455 | 42.3% | 0.386 |
| + consolidation (T-MEM V2 + C) | 42 | 0.343 | 0.464 | 46.5% | 0.387 |
| + consolidation (T-MEM V2 + C) | 43 | 0.324 | 0.457 | 46.5% | 0.374 |
| + consolidation (T-MEM V2 + C) | 44 | 0.340 | 0.491 | 50.7% | 0.376 |
| + conflict handling (T-MEM V2 + C + CH) | 42 | 0.352 | 0.492 | 49.3% | 0.392 |
| + conflict handling (T-MEM V2 + C + CH) | 43 | 0.337 | 0.500 | 47.9% | 0.383 |
| + conflict handling (T-MEM V2 + C + CH) | 44 | 0.336 | 0.477 | 45.1% | 0.388 |

## Timeline questions only (90 questions, fixed before results)

Rule: question whose evidence turn is a note in a conflict-handling timeline (conflicts_v1 bank). Answerable: 71, trap questions: 19.

| System | Answerable F1 | Trap questions refused |
|---|---|---|
| A-MEM (starting point) | 0.377 | 47.4% |
| + time ranking (T-MEM V2) | 0.393 | 47.4% |
| + consolidation (T-MEM V2 + C) | 0.383 | 49.1% |
| + conflict handling (T-MEM V2 + C + CH) | 0.411 | 52.6% |

**What the columns mean**
- *Answerable questions*: categories 1–4 (233 questions).
- *Time questions*: category 2 (63 questions), the questions T-MEM V2 is built for.
- *Trap questions refused*: category 5 (71 questions) are about things never said; answering "Not mentioned" is correct.
- *Overall F1 (paper scoring)*: all 304 questions, scored as in the paper (category 5 counts the trap answer as right).

**Notes**
- Steps 1–3 ran together at 14:27. Step 4 ran on its own at 16:21. The AI answers a little differently in every run, so part of the step 3 → step 4 difference may be run-to-run variation.
- Step 4 vs step 3, matching seeds: answerable F1 is higher in 2 of 3 runs (+0.009, +0.013, −0.004), and time F1 is higher in 2 of 3 (+0.028, +0.043, −0.014).
- Conflict handling setting: `annotate_demote`. Timeline labels appear in the prompts; demotion applies only to the 5 "now" questions.
- Bank: `cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80_v3_conflicts_v1` (see `manifest.json` for fingerprints).
