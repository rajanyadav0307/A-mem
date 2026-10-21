# Full QA pipeline: A-MEM and T-MEM V2, with and without consolidation

Run on 2026-10-21, branch `consolidation-support`.

## Setup

| Setting | Value |
|---|---|
| Samples | 0 and 1 of `data/locomo10.json` (304 questions), `--ratio 0.2` |
| Model | gpt-4o-mini (OpenAI), `--retrieve_k 10` |
| Seed | 42 for the category-5 answer-option order (all four runs) |
| Memory bank, no consolidation | `cached_memories_robust_openai_gpt-4o-mini` (May 6 bank) |
| Memory bank, consolidation | `cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80_v3` |
| Consolidation retrieval | `--consolidation_mode primary_expand --consolidated_top_k_cap 1` |
| T-MEM V2 settings | Thesis defaults (α = 0.9, λ = 0.1, pool 20, 2 anchors, category 2 only) |

All four runs started together at 11:51 and finished in about 12 minutes. The two runs without consolidation use the `off` path, which matches the May 6 retrieval code exactly (`analysis/off_mode_check.json`).

Commands (each run also had `--backend openai --model gpt-4o-mini --dataset data/locomo10.json --ratio 0.2 --retrieve_k 10 --seed 42`):

```
test_advanced_robust.py      --output results/amem_off.json
test_tmem_advanced_robust.py --output results/tmem_v2_off.json
test_advanced_robust.py      --memories_dir <v3 cache> --consolidation_mode primary_expand --consolidated_top_k_cap 1 --output results/amem_consolidated.json
test_tmem_advanced_robust.py --memories_dir <v3 cache> --consolidation_mode primary_expand --consolidated_top_k_cap 1 --output results/tmem_v2_consolidated.json
```

Full tables: `comparison_vs_amem.md` and `comparison_tmem_pair.md` (made with `compare_qa_runs.py`). Run logs are in `logs/` (not committed).

## F1 by category

| Split | n | A-MEM | A-MEM + C | T-MEM V2 | T-MEM V2 + C | A-MEM (May 6) | T-MEM V2 (May 6) |
|---|---|---|---|---|---|---|---|
| Overall | 304 | 0.3601 | **0.3817** | 0.3689 | 0.3767 | 0.3613 | 0.3686 |
| Cat 1 multi-hop | 43 | 0.1851 | 0.2056 | 0.1757 | **0.2097** | 0.1978 | 0.1920 |
| Cat 2 temporal | 63 | 0.4361 | 0.4455 | **0.4813** | 0.4351 | 0.4455 | 0.4610 |
| Cat 3 open-domain | 13 | 0.1266 | 0.1365 | 0.1183 | **0.1413** | 0.1107 | 0.1073 |
| Cat 4 single-hop | 114 | 0.2932 | **0.3429** | 0.3038 | 0.3197 | 0.3203 | 0.3130 |
| Cat 5 adversarial | 71 | 0.5487 | 0.5389 | 0.5365 | **0.5605** | 0.4974 | 0.5305 |

## All metrics, overall

| Metric | A-MEM | A-MEM + C | T-MEM V2 | T-MEM V2 + C |
|---|---|---|---|---|
| F1 | 0.3601 | **0.3817** | 0.3689 | 0.3767 |
| Exact match | 0.1513 | **0.1612** | 0.1480 | 0.1513 |
| ROUGE-L | 0.3657 | **0.3843** | 0.3805 | 0.3743 |
| BLEU-1 | 0.3188 | **0.3356** | 0.3265 | 0.3288 |
| METEOR | 0.2837 | **0.3074** | 0.3015 | 0.2905 |
| BERTScore F1 | 0.9076 | **0.9093** | 0.9092 | 0.9088 |
| SBERT similarity | 0.5200 | 0.5321 | **0.5360** | 0.5291 |

## Question-level F1 (exact two-sided sign test)

| Comparison | Better | Worse | Same | p |
|---|---|---|---|---|
| A-MEM + C vs A-MEM | 65 | 49 | 190 | 0.16 |
| T-MEM V2 vs A-MEM | 56 | 43 | 205 | 0.23 |
| T-MEM V2 + C vs T-MEM V2 | 60 | 55 | 189 | 0.71 |
| **A-MEM (May 6) vs A-MEM (today), same system** | 59 | 52 | 193 | 0.57 |

## What the results show

1. **The thesis T-MEM V2 result reproduces.** Today's V2 scores F1 0.3689 overall (May 6: 0.3686) and 0.4813 on category 2 (May 6: 0.4610). Its edge over A-MEM on category 2 is larger today: +0.045, compared with +0.016 in the thesis.
2. **Consolidation helps A-MEM on every metric but SBERT.** F1 goes up by +0.022 (0.3601 → 0.3817). Most of the gain is in single-hop (category 4, +0.050) and multi-hop (category 1, +0.021).
3. **For T-MEM V2, consolidation gives a small overall gain (+0.008) but cancels V2's category-2 gain.** Category 2 drops from 0.4813 to 0.4351, with 13 questions worse, 8 better and 42 the same. Evidence recall had predicted no category-2 change for this setting, so the drop happens at the answer stage. It may be partly noise.
4. **None of these differences is statistically meaningful yet.** Running the *same* A-MEM system twice (May 6 vs today) already changes the F1 of 111 questions (59 better, 52 worse), and moves category 4 by 0.027 and category 5 by 0.051. The consolidation effects are about the same size as this run-to-run noise. The keyword and answer steps run at temperature 0.7, which is where the noise comes from.

## Repeated runs: seeds 42, 43, 44 (added 2026-10-21)

Each setup was run 2 more times with seeds 43 and 44 (results `*_seed43.json`, `*_seed44.json`), with everything else identical. The 8 extra runs ran in parallel, from 12:11 to about 12:45. Full tables are in `comparison_3seeds.md` (made with `average_qa_runs.py`).

**F1, mean ± std over 3 runs**

| Split | A-MEM | A-MEM + C | T-MEM V2 | T-MEM V2 + C |
|---|---|---|---|---|
| Overall | 0.3776 ± 0.0170 | **0.3834 ± 0.0132** | 0.3742 ± 0.0077 | 0.3742 ± 0.0027 |
| Cat 1 multi-hop | 0.1958 ± 0.0093 | **0.2075 ± 0.0144** | 0.1841 ± 0.0074 | 0.2046 ± 0.0200 |
| Cat 2 temporal | 0.4453 ± 0.0081 | 0.4509 ± 0.0150 | 0.4599 ± 0.0189 | **0.4612 ± 0.0256** |
| Cat 3 open-domain | 0.1301 ± 0.0045 | **0.1384 ± 0.0019** | 0.1228 ± 0.0158 | 0.1377 ± 0.0031 |
| Cat 4 single-hop | 0.3140 ± 0.0193 | **0.3437 ± 0.0052** | 0.3030 ± 0.0021 | 0.3311 ± 0.0115 |
| Cat 5 adversarial | **0.5752 ± 0.0327** | 0.5386 ± 0.0263 | 0.5736 ± 0.0488 | 0.5123 ± 0.0417 |

**Overall F1 per run**

| Setup | Seed 42 | Seed 43 | Seed 44 | Range |
|---|---|---|---|---|
| A-MEM | 0.3601 | 0.3941 | 0.3788 | 0.034 |
| A-MEM + C | 0.3817 | 0.3974 | 0.3712 | 0.026 |
| T-MEM V2 | 0.3689 | 0.3706 | 0.3831 | 0.014 |
| T-MEM V2 + C | 0.3767 | 0.3747 | 0.3713 | 0.005 |

**Mean F1 change from adding consolidation (seeds where it helped)**

| Split | A-MEM + C vs A-MEM | T-MEM V2 + C vs T-MEM V2 |
|---|---|---|
| Overall | +0.006 (2/3) | +0.000 (2/3) |
| Cat 1 multi-hop | +0.012 (2/3) | +0.021 (2/3) |
| Cat 2 temporal | +0.006 (2/3) | +0.001 (2/3) |
| Cat 3 open-domain | +0.008 (3/3) | +0.015 (2/3) |
| Cat 4 single-hop | **+0.030 (3/3)** | **+0.028 (3/3)** |
| Cat 5 adversarial | **−0.037 (0/3)** | **−0.061 (1/3)** |

**Question-level sign tests** (F1 averaged over the 3 runs for each question)

| Comparison | Overall better / worse, p | Cat 4 better / worse, p | Cat 5 better / worse, p |
|---|---|---|---|
| A-MEM + C vs A-MEM | 85 / 77, 0.58 | 39 / 35, 0.73 | 10 / 13, 0.68 |
| T-MEM V2 + C vs T-MEM V2 | 87 / 78, 0.53 | 46 / 30, 0.085 | 5 / 13, 0.096 |
| T-MEM V2 vs A-MEM | 67 / 80, 0.32 | 30 / 39, 0.34 | 8 / 10, 0.82 |

## What the 3-run averages show

1. **Run-to-run noise is large.** The same A-MEM setup ranges from 0.360 to 0.394 overall F1 across seeds, a spread of 0.034. That is larger than any difference between setups.
2. **Overall, consolidation makes no clear difference:** +0.006 for A-MEM and +0.000 for T-MEM V2. Seed 42's +0.022 for A-MEM was partly luck.
3. **It does shift where answers improve, consistently.** Single-hop questions (category 4, 114 questions) improve by about +0.03 in every seed for both systems. Adversarial questions (category 5, 71 questions) get worse by 0.04–0.06. These two effects roughly cancel. At the question level, the T-MEM V2 trends are close to significant (p ≈ 0.09 each); the A-MEM ones are not.
4. **T-MEM V2's temporal gain holds on average:** +0.015 on category 2 vs A-MEM (thesis: +0.016). But it holds in only 2 of 3 seeds, and V2 has no overall gain. Consolidation does not remove it (V2 + C category 2 = 0.461). The drop seen with seed 42 alone was noise.
5. **One possible reason category 5 gets worse:** adversarial questions ask about things that were never said, and the merged summaries ("X expressed … on DATE") may make an unmentioned detail look mentioned. This is a guess and has not been checked yet.

## Next step options

- Check category-5 answers where consolidation hurt, to see whether merged notes mislead the model.
- Lower the noise: run the keyword and answer steps at temperature 0, or use more seeds.
- Test on samples 2–9, which have not been used to tune anything.
