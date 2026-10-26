# Fresh run e2e_samples0-2_2026-10-26_13-10

- Started (UTC): 2026-10-26T18:55:58Z
- Finished (UTC): 2026-10-26T19:13:12Z
- Report written (local): 2026-10-26 14:13
- Code: `c44dced9` on `conflict-handling-support`
- Samples [0, 1, 2], 497 questions, k = 10, seeds 42, 43, 44, model gpt-4o-mini (served as gpt-4o-mini-2024-07-18)
- A-MEM: runs from `experiments/e2e_samples0-2_2026-10-26_13-10`
- T-MEM complete (V2 + consolidation + conflict handling): runs from `experiments/e2e_samples0-2_2026-10-26_13-10`

## Results (average of the runs)

| Step | System | Answerable questions F1 | Time questions F1 | Trap questions refused | Overall F1 (paper scoring) |
|---|---|---|---|---|---|
| 1 | A-MEM | 0.346 | 0.440 | 52.4% | 0.377 |
| 2 | T-MEM complete (V2 + consolidation + conflict handling) | 0.356 | 0.470 | 54.2% | 0.380 |

## Gain over A-MEM

| System | Answerable questions | Time questions | Trap refusals |
|---|---|---|---|
| T-MEM complete (V2 + consolidation + conflict handling) | +0.010 | +0.030 | +1.8 points |

## Each setup vs A-MEM (matching runs): answerable F1

Change in answerable F1 for each seed; the last column counts the runs where it helped.

| Setup | Seed 42 | Seed 43 | Seed 44 | Mean change | Runs better |
|---|---|---|---|---|---|
| T-MEM complete (V2 + consolidation + conflict handling) | +0.003 | +0.024 | +0.003 | +0.010 | 3 of 3 |

## Each setup vs A-MEM (matching runs): time F1

Change in time F1 for each seed; the last column counts the runs where it helped.

| Setup | Seed 42 | Seed 43 | Seed 44 | Mean change | Runs better |
|---|---|---|---|---|---|
| T-MEM complete (V2 + consolidation + conflict handling) | -0.002 | +0.046 | +0.044 | +0.030 | 2 of 3 |

## Each run

| System | Seed | Answerable F1 | Time F1 | Trap refused | Overall F1 |
|---|---|---|---|---|---|
| A-MEM | 42 | 0.352 | 0.462 | 52.7% | 0.380 |
| A-MEM | 43 | 0.332 | 0.421 | 55.4% | 0.361 |
| A-MEM | 44 | 0.355 | 0.437 | 49.1% | 0.389 |
| T-MEM complete (V2 + consolidation + conflict handling) | 42 | 0.355 | 0.460 | 51.8% | 0.386 |
| T-MEM complete (V2 + consolidation + conflict handling) | 43 | 0.355 | 0.468 | 55.4% | 0.377 |
| T-MEM complete (V2 + consolidation + conflict handling) | 44 | 0.358 | 0.481 | 55.4% | 0.377 |

## Per sample (average of the runs)

| Sample | Questions | System | Answerable F1 | Time F1 | Trap refused | Overall F1 (paper) |
|---|---|---|---|---|---|---|
| 0 | 199 | A-MEM | 0.288 | 0.388 | 39.7% | 0.361 |
| 0 | 199 | T-MEM complete (V2 + consolidation + conflict handling) | 0.318 | 0.440 | 41.8% | 0.379 |
| 1 | 105 | A-MEM | 0.363 | 0.525 | 62.5% | 0.372 |
| 1 | 105 | T-MEM complete (V2 + consolidation + conflict handling) | 0.371 | 0.585 | 61.1% | 0.380 |
| 2 | 193 | A-MEM | 0.396 | 0.430 | 61.0% | 0.396 |
| 2 | 193 | T-MEM complete (V2 + consolidation + conflict handling) | 0.387 | 0.400 | 64.2% | 0.382 |

**What the columns mean**
- *Answerable questions*: categories 1–4 (233 questions).
- *Time questions*: category 2 (63 questions), the questions T-MEM V2 is built for.
- *Trap questions refused*: category 5 (71 questions) are about things never said; answering "Not mentioned" is correct.
- *Overall F1 (paper scoring)*: all 304 questions, scored as in the paper (category 5 counts the trap answer as right).

**How it was run (end to end)**
1. **Memory banks.** Samples 0–1 were copied byte for byte from the May 6 banks (plain, consolidated v3, conflict v1). **Sample 2 was built from scratch** with `build_memory_bank.py`, the same loop and code as the QA script: 663 notes, 0 errors, 42 minutes. Its consolidated bank (23 merges) and conflict bank (10 timelines, 4 replaced notes) were built with the same settings as samples 0–1. Details and fingerprints are in `manifest.json`; build logs are in `build_logs/`.
2. **QA runs.** A-MEM and T-MEM complete, 3 runs each (seeds 42, 43, 44), all 6 together, 18:55 to 19:13 UTC.
3. **Checks.**
   - Every result has 497 questions (199 / 105 / 193) and 0 empty answers, and its saved total matches the per-question scores.
   - Every log shows the right bank was loaded (A-MEM 419 / 369 / 663 notes; T-MEM 436 / 385 / 686), with 0 rebuilds and 0 failed answers.

**Per sample, run by run (T-MEM complete minus A-MEM)**

| Sample | Answerable F1 by seed | Better | Time F1 by seed | Better |
|---|---|---|---|---|
| 0 | +0.023, +0.037, +0.030 | 3 of 3 | +0.031, +0.050, +0.075 | 3 of 3 |
| 1 | −0.024, +0.044, +0.004 | 2 of 3 | +0.022, +0.109, +0.049 | 3 of 3 |
| 2 | −0.001, +0.000, −0.025 | 1 of 3 | −0.069, −0.018, −0.002 | **0 of 3** |

**What this shows**
- On samples 0–1, the ones T-MEM's settings were developed on, T-MEM is better, especially on time questions.
- **On sample 2, which was never used for tuning, T-MEM is no better on answerable questions and slightly worse on time questions, in all 3 runs.**
- So the overall gain (+0.010 answerable, +0.030 time) comes from samples 0–1. It does not carry over to the new sample yet. The cause has not been checked; it should be looked into before claiming a general improvement.
