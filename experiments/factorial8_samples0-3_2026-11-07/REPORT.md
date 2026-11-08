# 8-setup test: report

**Date:** 2026-11-07. **Branch:** `2026-11-06`. **Plan:** [PLAN.md](PLAN.md) (fixed before any results).
**Full tables:** [analysis/tables.md](analysis/tables.md). **All numbers:** [analysis/summary.json](analysis/summary.json).

## What was tested

Every on/off combination of T-MEM's three parts, each added on top of the unchanged A-MEM:

| Setup | Time ranking (T) | Consolidation (C) | Conflict handling (H) |
|---|---|---|---|
| s1 A-MEM | off | off | off |
| s2 | on | off | off |
| s3 | off | on | off |
| s4 | off | off | on |
| s5 | on | on | off |
| s6 | on | off | on |
| s7 | off | on | on |
| s8 (all three) | on | on | on |

- **Questions:** samples 0–3 of LoCoMo, 757 questions. Samples 0–2 are where T-MEM was developed. **Sample 3 is the clean test.** It was never used while T-MEM was being built.
- **Runs:** 5 runs per setup (seeds 42–46), 40 runs in all, model `gpt-4o-mini-2024-07-18`.
- **Same input for every setup:**
  - one memory bank per sample
  - the same search words per question in each run (made once by A-MEM's own code)
  - the same answer order for every trap question

## Were the runs clean?

Yes.

- **Checks after each run:** every run passed all 85 result checks, with 0 errors and 0 retries.
- **Final check:** across all 40 files, 426 of 426 checks passed ([checks/checks_all.json](checks/checks_all.json)).
- **Replay:** for every one of the 30,280 answers, the notes in the log equal the notes the code gives offline.
- **Time ranking:** it changed nothing outside time questions. For all 627 non-time questions, in all 5 runs, it found exactly the same notes.
- **One failed attempt:** the first try of run 42 hit the API limit. It was moved to `invalid/` and redone (see PLAN.md). It is not used here.
- **Analysis numbers checked a second way:**
  - Per-run scores, recomputed from the evaluator's own saved averages: 120 of 120 match.
  - Differences, recomputed question by question with separate code: 14 of 14 match.
  - Bootstrap ranges, re-run with a different random generator: they agree closely.
  - Holm corrections, recomputed: all match.

**Cost:** about $5.50 per run (measured on run 42; runs 43–46 have logs within 0.2% of the same size). The whole test cost about $34, including the sample 3 build, the trial and the failed first attempt.

## Main results

Scores are F1, averaged over the 5 runs (± spread between runs). "Real" means the Holm-corrected p-value is below 0.05, as fixed in the plan.

### All four samples (757 questions; 130 time questions, 584 answerable)

| Setup | Answerable F1 | Time F1 |
|---|---|---|
| A-MEM | 0.314 ± 0.003 | 0.386 ± 0.015 |
| Time ranking | 0.310 ± 0.007 | 0.388 ± 0.008 |
| Consolidation | 0.311 ± 0.005 | 0.376 ± 0.009 |
| Conflict handling | 0.317 ± 0.005 | 0.423 ± 0.010 |
| Time + Consolidation | 0.314 ± 0.005 | 0.380 ± 0.008 |
| Time + Conflict | 0.317 ± 0.002 | 0.429 ± 0.010 |
| Consolidation + Conflict | 0.323 ± 0.006 | 0.435 ± 0.012 |
| **All three** | **0.326 ± 0.006** | **0.439 ± 0.004** |

The main tests, each against A-MEM:

| Setup | Time F1 change | Real? | Answerable F1 change | Real? |
|---|---|---|---|---|
| Time ranking | +0.002 | no | −0.003 | no |
| Consolidation | −0.010 | no | −0.002 | no |
| Conflict handling | **+0.037** (better in 5 of 5 runs) | **yes** | +0.004 | no |
| All three | **+0.053** (better in 5 of 5 runs) | **yes** | +0.012 (better in 5 of 5 runs) | no (p = 0.089) |

The average effect of each part (on its own, across the other settings):

| Part | Time F1 | Real? | Answerable F1 | Real? |
|---|---|---|---|---|
| Time ranking (T) | +0.004 | no | +0.001 | no |
| Consolidation (C) | +0.001 | no | +0.004 | no |
| **Conflict handling (H)** | **+0.049** | **yes** | **+0.009** | **yes** |

On all four samples, none of the parts work together beyond adding up (no pair or triple interaction is real).

### Sample 3 alone (the clean test: 260 questions, 40 time questions)

| Setup | Answerable F1 | Time F1 |
|---|---|---|
| A-MEM | 0.235 ± 0.011 | 0.256 ± 0.022 |
| Conflict handling | 0.239 ± 0.007 | 0.268 ± 0.012 |
| Consolidation | 0.231 ± 0.005 | 0.238 ± 0.006 |
| All three | 0.241 ± 0.003 | 0.269 ± 0.015 |

- **No gain is real on sample 3.** Conflict handling (+0.012 time F1) and all three (+0.013 time F1) point the right way, but the ranges include zero.
- **Consolidation hurts time questions on sample 3:** −0.018 time F1, real (Holm p = 0.025), better in only 1 of 5 runs.

### Samples 0–2 (development)

The same pattern as all four samples, but larger:
- Conflict handling: +0.048 time F1 (real).
- All three: +0.071 time F1 (real), and +0.016 answerable F1 (not real, p = 0.173).
- Consolidation and conflict handling work together on answerable questions: +0.010 beyond adding up (C×H, real, Holm p = 0.043). This is the only real interaction in any sample group. It is not real on all four samples (+0.007, p = 0.234) or on sample 3 (+0.000).

## What this means

1. **Conflict handling is the part that works.** It is the only part with a real effect, and it accounts for almost all of T-MEM's gain on time questions. It helps in every run.
2. **Time ranking (V2) does nothing measurable here.** Its effect is close to zero everywhere: alone, with the other parts, and on every sample group. The earlier V2 gain on samples 0–1 does not appear here. One possible reason is that in earlier tests each setup made its own search words, while here all setups share them. This was not tested directly.
3. **Consolidation does not help.** Alone it is close to zero, and on the clean test it lowers time F1.
4. **The gains are much smaller on the clean test.** On sample 3, T-MEM's time gain drops from about +0.05 to about +0.013 and is no longer real. Sample 3 has only 40 time questions, so a small real gain could be missed. But the result does not show that T-MEM's gains carry over to a new conversation.
5. **Trap questions:** the setups refuse traps at similar rates (57–60% on all four samples). No part changes this much.

## Limits

- Sample 3 alone is small (40 time questions). The test can only see large effects there.
- One model (gpt-4o-mini), one dataset (LoCoMo).
- Holm p-values close to 0.05 depend a little on the random resampling. Re-running the bootstrap with a different random generator kept every "real" result real.

## Stage 7: extra counts for the thesis (added 2026-11-08)

Descriptive only: no tests, not part of the plan. Offline, no AI calls. Numbers: [analysis/extra.json](analysis/extra.json), made by `scripts/extra_analysis.py`.

- **Made twice:** the two runs gave byte-identical files.
- **Recounted another way:** `scripts/extra_recount.py` reads what the runs actually showed the model (the logged contexts), takes merged notes from the consolidation build logs, averages metrics per question, and computes the time-ranking margin with its own arithmetic. Result: [analysis/extra_recount.json](analysis/extra_recount.json), 0 differences. Run twice, byte-identical.

### What each part changed in the model's context (question × run cases)

| Count | Sample 0 | Sample 1 | Sample 2 | Sample 3 | All |
|---|---|---|---|---|---|
| Time questions × runs | 185 | 130 | 135 | 200 | 650 |
| T: same 10 notes as A-MEM | 132 of 185 (71.4%) | 97 of 130 (74.6%) | 92 of 135 (68.1%) | 150 of 200 (75.0%) | 471 of 650 (72.5%) |
| T: same 10 notes in the same order | 53 of 185 (28.6%) | 60 of 130 (46.2%) | 36 of 135 (26.7%) | 75 of 200 (37.5%) | 224 of 650 (34.5%) |
| T: skipped (best note leads by ≥ 0.05) | 26 of 185 (14.1%) | 44 of 130 (33.8%) | 31 of 135 (23.0%) | 63 of 200 (31.5%) | 164 of 650 (25.2%) |
| T: notes replaced, total | 59 | 33 | 45 | 57 | 194 |
| H: time contexts with a timeline label | 87 of 185 (47.0%) | 130 of 130 (100.0%) | 135 of 135 (100.0%) | 148 of 200 (74.0%) | 500 of 650 (76.9%) |
| H: time contexts with an event date | 76 of 185 (41.1%) | 130 of 130 (100.0%) | 31 of 135 (23.0%) | 133 of 200 (66.5%) | 370 of 650 (56.9%) |
| H: all contexts with a timeline label | 483 of 995 (48.5%) | 525 of 525 (100.0%) | 965 of 965 (100.0%) | 894 of 1,300 (68.8%) | 2,867 of 3,785 (75.7%) |
| H: all contexts with an OUTDATED label | 153 of 995 (15.4%) | 301 of 525 (57.3%) | 73 of 965 (7.6%) | 0 of 1,300 (0.0%) | 527 of 3,785 (13.9%) |
| Questions about the present × runs | 15 | 10 | 5 | 10 | 40 |
| C: s3 contexts with a merged note | 778 of 995 (78.2%) | 401 of 525 (76.4%) | 564 of 965 (58.4%) | 1,015 of 1,300 (78.1%) | 2,758 of 3,785 (72.9%) |
| C: s3 time contexts with a merged note | 149 of 185 (80.5%) | 111 of 130 (85.4%) | 106 of 135 (78.5%) | 181 of 200 (90.5%) | 547 of 650 (84.2%) |

### Other measures (all 757 questions, mean of the five runs)

| Setup | f1 | exact_match | rougeL_f | bleu1 | meteor | bert_f1 | sbert_similarity |
|---|---|---|---|---|---|---|---|
| s1 A-MEM | 0.3373 | 0.1358 | 0.3394 | 0.2926 | 0.2586 | 0.9030 | 0.4952 |
| s2 T | 0.3354 | 0.1324 | 0.3393 | 0.2897 | 0.2580 | 0.9028 | 0.4937 |
| s3 C | 0.3322 | 0.1266 | 0.3360 | 0.2860 | 0.2555 | 0.9025 | 0.4909 |
| s4 H | 0.3414 | 0.1363 | 0.3451 | 0.2913 | 0.2616 | 0.9033 | 0.4962 |
| s5 T+C | 0.3337 | 0.1279 | 0.3380 | 0.2871 | 0.2547 | 0.9027 | 0.4915 |
| s6 T+H | 0.3429 | 0.1371 | 0.3472 | 0.2920 | 0.2620 | 0.9036 | 0.4986 |
| s7 C+H | 0.3390 | 0.1258 | 0.3431 | 0.2846 | 0.2583 | 0.9032 | 0.4921 |
| s8 all three | 0.3419 | 0.1263 | 0.3451 | 0.2872 | 0.2610 | 0.9032 | 0.4950 |

## Where things are

| What | Where |
|---|---|
| Plan, fixed before results | [PLAN.md](PLAN.md) |
| Inputs, commands, fingerprints | [manifest.json](manifest.json) |
| 40 result files | [results/](results/) |
| All checks | [checks/](checks/) (`checks_all.json`, `history.jsonl`) |
| Analysis | [analysis/tables.md](analysis/tables.md), [analysis/summary.json](analysis/summary.json) |
| Stage 7 extra counts | [analysis/extra.json](analysis/extra.json), check: [analysis/extra_recount.json](analysis/extra_recount.json) |
| Logs (5 GB) and memory banks | `logs/`, `cache/` (on this computer only, not in git) |
