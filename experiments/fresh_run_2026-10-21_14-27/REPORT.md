# Fresh run fresh_run_2026-10-21_14-27

- Started (UTC): 2026-10-21T19:27:50Z
- Finished (UTC): 2026-10-21T19:54:15Z
- Report written (local): 2026-10-21 14:54
- Code: `25f38095` on `consolidation-support`
- Samples [0, 1], 304 questions, k = 10, seeds 42, 43, 44, model gpt-4o-mini (served as gpt-4o-mini-2024-07-18)

## Results (average of the runs)

| Step | System | Answerable questions F1 | Time questions F1 | Trap questions refused | Overall F1 (paper scoring) |
|---|---|---|---|---|---|
| 1 | A-MEM (starting point) | 0.321 | 0.439 | 45.1% | 0.375 |
| 2 | + time ranking (T-MEM V2) | 0.328 | 0.462 | 45.5% | 0.380 |
| 3 | + consolidation (T-MEM V2 + C) | 0.336 | 0.471 | 47.9% | 0.379 |

## Gain over A-MEM

| System | Answerable questions | Time questions | Trap refusals |
|---|---|---|---|
| + time ranking (T-MEM V2) | +0.007 | +0.023 | +0.5 points |
| + consolidation (T-MEM V2 + C) | +0.015 | +0.031 | +2.8 points |

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

**What the columns mean**
- *Answerable questions*: categories 1–4 (233 questions).
- *Time questions*: category 2 (63 questions), the questions T-MEM V2 is built for.
- *Trap questions refused*: category 5 (71 questions) are about things never said; answering "Not mentioned" is correct.
- *Overall F1 (paper scoring)*: all 304 questions, scored as in the paper (category 5 counts the trap answer as right).
