# Does consolidation change T-MEM V2's effect? (samples 0–1, 3 seeds)

Script: `analyze_tmem_consolidation.py`. It uses the 12 existing runs and their logs; no new LLM calls. Numbers are in `analysis_tmem_v2.json`.

**Scope (paper-aligned).**
- Samples 0–1 only, using the May 6 memory bank, prompts, metrics and T-MEM V2 settings (α = 0.9, λ = 0.1, pool 20, 2 anchors, category 2 only).
- Consolidation is added on top: v3 merges, `primary_expand`, at most 1 merged note in the top 10.
- The one difference from the May 6 runs is that the category-5 option order was seeded (42/43/44) instead of left random.

## 1. A 2×2 view

Mean F1 over 3 seeds. "C" means consolidation. Interaction = (V2 + C − A-MEM + C) − (V2 − A-MEM): zero means the two effects simply add up.

| Split | A-MEM | V2 | A-MEM + C | V2 + C | C on A-MEM | C on V2 | V2 effect | V2 effect with C | Interaction |
|---|---|---|---|---|---|---|---|---|---|
| Overall | 0.3776 | 0.3742 | 0.3834 | 0.3742 | +0.006 | +0.000 | −0.004 | −0.009 | −0.006 |
| Cats 1–4 | 0.3174 | 0.3134 | 0.3361 | 0.3321 | **+0.019** | **+0.019** | −0.004 | −0.004 | **0.000** |
| Cat 1 multi-hop | 0.1958 | 0.1841 | 0.2075 | 0.2046 | +0.012 | +0.021 | −0.012 | −0.003 | +0.009 |
| **Cat 2 temporal** | 0.4453 | 0.4599 | 0.4509 | 0.4612 | +0.006 | +0.001 | **+0.015** | **+0.010** | −0.004 |
| Cat 3 open-domain | 0.1301 | 0.1228 | 0.1384 | 0.1377 | +0.008 | +0.015 | −0.007 | −0.001 | +0.007 |
| Cat 4 single-hop | 0.3140 | 0.3030 | 0.3437 | 0.3311 | +0.030 | +0.028 | −0.011 | −0.013 | −0.002 |
| Cat 5 F1 (trap-scored) | 0.5752 | 0.5736 | 0.5386 | 0.5123 | −0.037 | −0.061 | −0.002 | −0.026 | −0.025 |
| Cat 5 refusal rate | 0.427 | 0.432 | 0.465 | 0.493 | +0.038 | +0.061 | +0.005 | +0.028 | +0.024 |

**What this shows**
- On answerable questions (categories 1–4), the two effects **add up**. Consolidation gives +0.019 whether V2 is there or not (interaction 0.000), and V2's effect is the same with or without consolidation (−0.004).
- **V2's category-2 gain survives consolidation, slightly smaller:** +0.015 without it, +0.010 with it. The interaction (−0.004) changes sign across seeds (−0.056, +0.014, +0.029), so it is noise-level.
- On category 5, consolidation increases trap refusals more with V2 (+0.061) than with A-MEM (+0.038). That difference also changes sign across seeds.

## 2. Category 2: merged notes hardly ever hold the answer

For each category-2 question, I checked whether a merged note in the V2 + C prompt contains the question's evidence turn. Pooled over 63 questions × 3 seeds:

| Merged notes in the V2 + C prompt | n | Mean ΔF1 vs V2 | Better / worse |
|---|---|---|---|
| A merged note holds the evidence | 3 | +0.000 | 0 / 0 |
| A merged note, but not the evidence | 154 | −0.000 | 31 / 29 |
| No merged note | 32 | +0.008 | 5 / 5 |

On time questions, the merged note is nearly always **unrelated to the answer**. The category-2 changes (31 better, 29 worse) cancel out and are consistent with noise, or with the merged note taking a slot in the prompt.

Questions that changed most (V2 → V2 + C, all 3 seeds):
- **Worse:** "How long has Caroline had her current group of friends?" (reference: 4 years). V2: "4 years" ×3. V2 + C: "Not specified" / "Since approximately July 6, 2023" / "15 July 2023".
- **Better:** "When did Caroline give a speech at a school?" (reference: the week before 9 June 2023). V2: "Not mentioned" ×3. V2 + C: "9 June, 2023" ×3.

## 3. How V2's reranking treats merged notes

Using the question text as the query (the real runs use AI-written keywords, so this is an approximation):

| Category-2 questions (63) | Count |
|---|---|
| Time reranking skipped (one note clearly best by meaning) | 26 |
| Time reranking applied | 37 |
| … a merged note was among the 20 candidates | 35 |
| … a merged note ended up in the top 10 | 29 |
| … time moved a merged note **into** the top 10 | **0** |
| … time moved a merged note **out of** the top 10 | **0** |

**Merged notes look fresher than their sources.** A merged note takes the date of its *last* mention: on average 2.0 months before the end of the conversation, compared with 3.4 months for its oldest source. So V2's freshness score is 0.826 vs 0.723. But because V2 keeps 2 notes fixed by meaning and gives time only 10% of the weight, this boost **never** changed whether a merged note made the top 10. V2's design keeps the merged notes from taking over.

## 4. Did the right evidence reach the prompt? (real logged prompts)

| Setup | Category-2 evidence in the prompt |
|---|---|
| A-MEM | 0.741 |
| A-MEM + C | 0.767 |
| T-MEM V2 | **0.772** |
| T-MEM V2 + C | 0.767 |

Both V2 and consolidation raise category-2 evidence recall by about the same amount (+0.031 and +0.026). **Together they add nothing more** (0.767). On time questions the two mechanisms overlap: each helps the right turn reach the prompt, and combining them doesn't help further. This explains why V2's category-2 edge shrinks from +0.015 to +0.010 when consolidation is added.

## Conclusions

1. **Consolidation and T-MEM V2 work independently on answerable questions.** Each keeps its own effect: consolidation +0.019 on categories 1–4, and V2 about +0.01 to +0.015 on category 2.
2. **V2's category-2 benefit is preserved with consolidation,** a little smaller (+0.010 vs +0.015). The two overlap on category 2 because both improve how often the dated evidence reaches the prompt.
3. **V2's safeguards work with merged notes.** Merged notes look fresher, but the semantic anchors and the small time weight kept time from ever pulling a merged note into the top 10.
4. **On time questions, merged notes rarely carry the answer** (3 of 157 prompts). Category-2 changes from consolidation are noise-level.
5. **Limits:** 2 samples, 3 runs, 63 category-2 questions. The interaction estimates change sign across seeds, so none of the interaction effects are established.
