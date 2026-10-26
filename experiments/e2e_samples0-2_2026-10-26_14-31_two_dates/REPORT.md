# Fresh run e2e_samples0-2_2026-10-26_14-31_two_dates

- Started (UTC): 2026-10-26T19:32:57Z
- Finished (UTC): 2026-10-26T20:03:03Z
- Report written (local): 2026-10-26 15:03
- Code: `c8dfdad7` on `conflict-handling-support`
- Samples [0, 1, 2], 497 questions, k = 10, seeds 42, 43, 44, model gpt-4o-mini (served as gpt-4o-mini-2024-07-18)
- A-MEM: runs from `experiments/e2e_samples0-2_2026-10-26_14-31_two_dates`
- T-MEM complete, one date (previous labels): runs from `experiments/e2e_samples0-2_2026-10-26_14-31_two_dates`
- T-MEM complete, two dates (new labels): runs from `experiments/e2e_samples0-2_2026-10-26_14-31_two_dates`

## Results (average of the runs)

| Step | System | Answerable questions F1 | Time questions F1 | Trap questions refused | Overall F1 (paper scoring) |
|---|---|---|---|---|---|
| 1 | A-MEM | 0.355 | 0.440 | 49.1% | 0.390 |
| 2 | T-MEM complete, one date (previous labels) | 0.356 | 0.459 | 53.9% | 0.382 |
| 3 | T-MEM complete, two dates (new labels) | 0.365 | 0.498 | 54.2% | 0.388 |

## Gain over A-MEM

| System | Answerable questions | Time questions | Trap refusals |
|---|---|---|---|
| T-MEM complete, one date (previous labels) | +0.001 | +0.019 | +4.8 points |
| T-MEM complete, two dates (new labels) | +0.010 | +0.058 | +5.1 points |

## Each setup vs A-MEM (matching runs): answerable F1

Change in answerable F1 for each seed; the last column counts the runs where it helped.

| Setup | Seed 42 | Seed 43 | Seed 44 | Mean change | Runs better |
|---|---|---|---|---|---|
| T-MEM complete, one date (previous labels) | -0.004 | +0.002 | +0.006 | +0.001 | 2 of 3 |
| T-MEM complete, two dates (new labels) | +0.003 | +0.012 | +0.015 | +0.010 | 3 of 3 |

## Each setup vs A-MEM (matching runs): time F1

Change in time F1 for each seed; the last column counts the runs where it helped.

| Setup | Seed 42 | Seed 43 | Seed 44 | Mean change | Runs better |
|---|---|---|---|---|---|
| T-MEM complete, one date (previous labels) | +0.014 | +0.034 | +0.010 | +0.019 | 3 of 3 |
| T-MEM complete, two dates (new labels) | +0.078 | +0.037 | +0.058 | +0.058 | 3 of 3 |

## Each run

| System | Seed | Answerable F1 | Time F1 | Trap refused | Overall F1 |
|---|---|---|---|---|---|
| A-MEM | 42 | 0.359 | 0.432 | 51.8% | 0.388 |
| A-MEM | 43 | 0.352 | 0.439 | 49.1% | 0.390 |
| A-MEM | 44 | 0.354 | 0.449 | 46.4% | 0.393 |
| T-MEM complete, one date (previous labels) | 42 | 0.355 | 0.445 | 52.7% | 0.385 |
| T-MEM complete, one date (previous labels) | 43 | 0.354 | 0.473 | 55.4% | 0.377 |
| T-MEM complete, one date (previous labels) | 44 | 0.360 | 0.459 | 53.6% | 0.383 |
| T-MEM complete, two dates (new labels) | 42 | 0.362 | 0.510 | 55.4% | 0.383 |
| T-MEM complete, two dates (new labels) | 43 | 0.364 | 0.476 | 51.8% | 0.392 |
| T-MEM complete, two dates (new labels) | 44 | 0.369 | 0.507 | 55.4% | 0.388 |

## Per sample (average of the runs)

| Sample | Questions | System | Answerable F1 | Time F1 | Trap refused | Overall F1 (paper) |
|---|---|---|---|---|---|---|
| 0 | 199 | A-MEM | 0.313 | 0.409 | 35.5% | 0.390 |
| 0 | 199 | T-MEM complete, one date (previous labels) | 0.316 | 0.420 | 40.4% | 0.380 |
| 0 | 199 | T-MEM complete, two dates (new labels) | 0.332 | 0.425 | 41.1% | 0.392 |
| 1 | 105 | A-MEM | 0.371 | 0.510 | 51.4% | 0.402 |
| 1 | 105 | T-MEM complete, one date (previous labels) | 0.373 | 0.579 | 63.9% | 0.378 |
| 1 | 105 | T-MEM complete, two dates (new labels) | 0.392 | 0.657 | 63.9% | 0.391 |
| 2 | 193 | A-MEM | 0.388 | 0.414 | 63.4% | 0.385 |
| 2 | 193 | T-MEM complete, one date (previous labels) | 0.388 | 0.397 | 63.4% | 0.385 |
| 2 | 193 | T-MEM complete, two dates (new labels) | 0.384 | 0.444 | 63.4% | 0.382 |

**What the columns mean**
- *Answerable questions*: categories 1–4 (233 questions).
- *Time questions*: category 2 (63 questions), the questions T-MEM V2 is built for.
- *Trap questions refused*: category 5 (71 questions) are about things never said; answering "Not mentioned" is correct.
- *Overall F1 (paper scoring)*: all 304 questions, scored as in the paper (category 5 counts the trap answer as right).

**How it was run**
- Memory banks: base and consolidated copied from `e2e_samples0-2_2026-10-26_13-10` (checked identical). The conflict bank was rebuilt to add the "happened" date (`event_time`) to timeline notes. It reused the cached AI answers (0 new calls), and every other note field and the retriever files are identical to the previous conflict bank.
- 9 runs together (3 systems × seeds 42, 43, 44), 19:32 to 20:03 UTC. Code `c8dfdad7`.
- Checks:
  - Every result has 497 questions (199 / 105 / 193) and 0 empty answers, and its saved total matches the per-question scores.
  - Every log loaded the right bank, with 0 rebuilds and 0 failed answers.
  - "said on" and "happened:" labels appear only in the two-date runs.

**The fix: what each timeline step now shows**
- **Before (one date):** `before: started volunteering (28 January 2023)`, the date it was *said*.
- **After (two dates):** `before: started volunteering (said on 28 January 2023)`, and when the note gives a relative time, for example `(said on 3 August 2023; happened: around August 2022)`.

**Results, run by run**

| Comparison | Answerable F1 | Time F1 |
|---|---|---|
| Two dates vs A-MEM (all samples) | +0.010, better 3 of 3 | **+0.058, better 3 of 3** |
| One date vs A-MEM (all samples) | +0.001, better 2 of 3 | +0.019, better 3 of 3 |
| **Two dates vs one date, sample 2** | −0.004 (0 of 3) | **+0.047** (+0.110, +0.031, +0.000) |
| Two dates vs one date, sample 1 | +0.019 (3 of 3) | +0.078 (3 of 3) |
| Two dates vs one date, sample 0 | +0.016 (3 of 3) | +0.005 (2 of 3) |

**What this shows**
- **The two-date labels fix the sample 2 problem on time questions.** With one date, sample 2's time F1 was below A-MEM (−0.017). With two dates it is above A-MEM (+0.030, better in 2 of 3 runs).
- Two dates also help samples 0 and 1, and overall time F1 rises from 0.459 to 0.498 in the same batch.
- **Not from copying wording:** only 6 of 270 two-date answers used phrases like "the week before". The gain shows up both on questions whose reference uses that wording (0.450 → 0.523 vs A-MEM) and on those that don't (0.435 → 0.486).
- **Still open:** sample 2's answerable F1 is unchanged (−0.004 to −0.005), so the fix helps time questions but not the others on sample 2.
- The paper-scoring overall F1 is about the same as A-MEM (0.388 vs 0.390). That's because T-MEM refuses more trap questions (54.2% vs 49.1%), which that scoring counts as wrong.
