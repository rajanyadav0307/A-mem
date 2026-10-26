# Complete Result Summary: A-MEM vs T-MEM on samples 0–2 (two-date timelines)

Run folder: `experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/`. Runs from 19:32 to 20:03 UTC on 2026-10-26 (14:32–15:03 local). Code `c8dfdad7`, branch `conflict-handling-support`.
Detail files: `REPORT.md` (simple tables), `comparison_all_metrics.md` (all metrics, mean ± std), `summary.json`, `manifest.json`.

## 1. What was run

| | |
|---|---|
| Data | LoCoMo `data/locomo10.json`, unchanged (same SHA-256 as at May 6). Samples 0, 1, 2 |
| Questions | 497: 199 (sample 0), 105 (sample 1), 193 (sample 2) |
| By category | 1 multi-hop: 74; **2 time: 90**; 3 open-domain: 21; 4 single-hop: 200; 5 trap: 112 |
| Model | gpt-4o-mini (gpt-4o-mini-2024-07-18), top 10 notes |
| Runs | 3 per system (seeds 42, 43, 44), all 9 in one batch |

| System | What it is |
|---|---|
| **A-MEM** | The paper's baseline, May 6 code |
| **T-MEM, one date** | V2 + consolidation + conflict handling, with the old timeline labels (date said only) |
| **T-MEM, two dates** | The same, with new timeline labels: "said on …; happened: …" |

**Memory:**
- Samples 0–1 use the paper's May 6 memory.
- Sample 2's memory was built from scratch on 2026-10-26: 663 notes, 0 errors.
- The T-MEM banks add merged notes and timelines. The two-date bank differs from the one-date bank **only** in the new "happened" dates.

## 2. Accuracy checks (all passed)

- Every run: 497 questions (199 / 105 / 193), 0 empty answers, 0 failed answers.
- Every run loaded the right memory: A-MEM 419 / 369 / 663 notes; T-MEM 436 / 385 / 686. No rebuilds.
- The saved totals match the per-question scores.
- The new labels appear only in the two-date runs.
- The dataset is unchanged.

## 3. Main results (average of 3 runs)

| System | Normal questions (cats 1–4) | **Time questions (cat 2)** | Traps refused (cat 5) | Overall F1, paper scoring |
|---|---|---|---|---|
| A-MEM | 0.355 | 0.440 | 49.1% | **0.390** |
| T-MEM, one date | 0.356 | 0.459 | 53.9% | 0.382 |
| **T-MEM, two dates** | **0.365** | **0.498** | **54.2%** | 0.388 |

**Change vs A-MEM, run by run:**

| | Normal questions | Time questions |
|---|---|---|
| T-MEM, one date | +0.001 (better 2 of 3) | +0.019 (better 3 of 3) |
| **T-MEM, two dates** | **+0.010 (better 3 of 3)** | **+0.058 (better 3 of 3)** |

## 4. F1 by category (mean ± std over 3 runs)

| Category | A-MEM | T-MEM one date | T-MEM two dates | Two dates vs A-MEM |
|---|---|---|---|---|
| 1 Multi-hop (74) | 0.279 ± 0.006 | 0.277 ± 0.014 | 0.277 ± 0.014 | −0.002 (1 of 3) |
| **2 Time (90)** | 0.440 ± 0.009 | 0.459 ± 0.014 | **0.498 ± 0.019** | **+0.058 (3 of 3)** |
| 3 Open-domain (21) | 0.091 ± 0.006 | 0.115 ± 0.025 | 0.105 ± 0.020 | +0.013 (2 of 3) |
| 4 Single-hop (200) | 0.373 ± 0.010 | 0.364 ± 0.007 | 0.365 ± 0.008 | −0.008 (1 of 3) |
| 5 Trap, paper scoring (112) | 0.513 ± 0.020 | 0.469 ± 0.016 | 0.467 ± 0.020 | −0.046 (0 of 3) |
| **Overall, paper scoring (497)** | **0.391 ± 0.003** | 0.382 ± 0.004 | 0.388 ± 0.005 | −0.003 (1 of 3) |

## 5. All metrics, overall, paper scoring (mean ± std)

| Metric | A-MEM | T-MEM one date | T-MEM two dates |
|---|---|---|---|
| F1 | **0.391** ± 0.003 | 0.382 ± 0.004 | 0.388 ± 0.005 |
| Exact match | **0.158** ± 0.006 | 0.146 ± 0.007 | 0.150 ± 0.002 |
| ROUGE-L | **0.391** ± 0.003 | 0.386 ± 0.004 | 0.389 ± 0.006 |
| BLEU-1 | **0.335** ± 0.002 | 0.322 ± 0.005 | 0.324 ± 0.003 |
| METEOR | **0.299** ± 0.005 | 0.289 ± 0.008 | 0.294 ± 0.009 |
| BERTScore F1 | **0.911** ± 0.000 | 0.910 ± 0.000 | 0.910 ± 0.001 |
| SBERT similarity | **0.539** ± 0.002 | 0.533 ± 0.004 | 0.529 ± 0.008 |

These overall numbers include the trap questions, where the paper's scoring gives points for falling for the trap. T-MEM refuses traps more often, which lowers all of these.

## 6. Per sample (average of 3 runs)

| Sample | System | Normal questions | Time questions | Traps refused | Overall F1 (paper) |
|---|---|---|---|---|---|
| 0 (199) | A-MEM | 0.313 | 0.409 | 35.5% | 0.390 |
| | T-MEM one date | 0.316 | 0.420 | 40.4% | 0.380 |
| | **T-MEM two dates** | **0.332** | **0.425** | 41.1% | 0.392 |
| 1 (105) | A-MEM | 0.371 | 0.510 | 51.4% | 0.402 |
| | T-MEM one date | 0.373 | 0.579 | 63.9% | 0.378 |
| | **T-MEM two dates** | **0.392** | **0.657** | 63.9% | 0.391 |
| 2 (193) | A-MEM | **0.388** | 0.414 | 63.4% | **0.385** |
| | T-MEM one date | **0.388** | 0.397 | 63.4% | **0.385** |
| | **T-MEM two dates** | 0.384 | **0.444** | 63.4% | 0.382 |

## 7. Per run

| System | Seed | Normal questions | Time questions | Traps refused | Overall F1 (paper) |
|---|---|---|---|---|---|
| A-MEM | 42 | 0.359 | 0.432 | 51.8% | 0.388 |
| A-MEM | 43 | 0.352 | 0.439 | 49.1% | 0.390 |
| A-MEM | 44 | 0.354 | 0.449 | 46.4% | 0.393 |
| T-MEM one date | 42 | 0.355 | 0.445 | 52.7% | 0.385 |
| T-MEM one date | 43 | 0.354 | 0.473 | 55.4% | 0.377 |
| T-MEM one date | 44 | 0.360 | 0.459 | 53.6% | 0.383 |
| T-MEM two dates | 42 | 0.362 | 0.510 | 55.4% | 0.383 |
| T-MEM two dates | 43 | 0.364 | 0.476 | 51.8% | 0.392 |
| T-MEM two dates | 44 | 0.369 | 0.507 | 55.4% | 0.388 |

Time F1 vs A-MEM per seed: one date +0.014 / +0.034 / +0.010; **two dates +0.078 / +0.037 / +0.058**.

## 8. Question by question (F1 averaged over the 3 runs, sign test)

| Comparison | Better | Worse | Same | p |
|---|---|---|---|---|
| Two dates vs A-MEM, all 497 | 126 | 138 | 233 | 0.50 |
| Two dates vs one date, all 497 | 127 | 109 | 261 | 0.27 |

Over all question types, the per-question changes balance out. The clear, repeatable gain is on time questions.

## 9. What the results say

1. **Time questions improve clearly:** 0.440 → 0.498 (+0.058), better in all 3 runs, and on every sample (sample 2: 0.414 → 0.444).
2. **The two-date labels are the main reason.** Same batch: one date 0.459 → two dates 0.498 on time questions, better in all 3 runs. The fix also removed the sample 2 drop: one date was below A-MEM there (0.397 vs 0.414); two dates is above (0.444).
3. **Other question types are flat.** Multi-hop −0.002, single-hop −0.008, open-domain +0.013 (only 21 questions). The +0.010 on normal questions comes from time questions.
4. **Trap questions:** T-MEM refuses traps more often (54.2% vs 49.1%), which is the correct behaviour. The paper's scoring counts this as a loss, so the paper-scored overall F1 is about the same as A-MEM (0.388 vs 0.391), and every overall metric is slightly lower.
5. **Not from copied wording:** only 6 of 270 two-date time answers used phrases like "the week before", and the gain appears whichever way the reference is worded.

## 10. Limits

- 3 samples and 3 runs each. Categories 1 and 3 are small (74 and 21 questions).
- Same-setup runs vary by up to about 0.01 overall and 0.02 on time questions.
- Sample 2's normal (non-time) questions are not improved (−0.004).
- Run settings were developed on samples 0–1. Sample 2 is the only sample not used for development.
