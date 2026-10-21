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

## Next step

Repeat each of the four runs 2 more times with different seeds, then compare the averages. Category 2 for T-MEM V2 + C needs particular attention.
