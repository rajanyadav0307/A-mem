# Analysis of the consolidation QA runs (samples 0–1, 3 seeds)

Script: `analyze_consolidation_qa.py`. It reads the 12 result files and the run logs; no new LLM calls. Numbers are in `analysis.json`.

## 1. The category-5 "drop" is the model avoiding a trap

**How this pipeline scores category 5.** It uses LoCoMo's `adversarial_answer` as the reference, and the prompt offers two options: that answer or "Not mentioned in the conversation". This scoring comes from the original A-MEM code (`QA.final_answer` in `load_dataset.py`) and the thesis used it unchanged.

**The reference is a trap.** In 58 of the 71 category-5 questions, the question names the **wrong person**. The fact belongs to the other speaker. Example: "What was grandma's gift to Melanie?" → reference "necklace", but the necklace was Caroline's grandmother's gift to Caroline. For these questions the truthful answer is "Not mentioned", and a higher category-5 F1 means the model fell for the trap more often.

**Answer types** (mean over 3 seeds, 71 questions):

| Setup | "Not mentioned" | Trap answer | Both |
|---|---|---|---|
| A-MEM | 30.3 | 36.3 | 4.3 |
| A-MEM + C | **33.0** | 34.7 | 3.3 |
| T-MEM V2 | 30.7 | 37.0 | 3.3 |
| T-MEM V2 + C | **35.0** | 32.7 | 3.3 |

With consolidation, the model refuses the trap more often (+2.7 questions for A-MEM, +4.3 for T-MEM V2). That is what lowers category-5 F1.

**Examples** (A-MEM vs A-MEM + C, all 3 seeds):
- "What was grandma's gift to Melanie?" A-MEM said "necklace" every time; with consolidation it said "Not mentioned" every time. The merged note "On 27 June 2023, Melanie … complimented [Caroline's] necklace" makes clear whose necklace it was.
- "What kind of professional experience did Jon get accepted for on May 23, 2023?" (the internship was Gina's): "fashion internship" ×3 → "Not mentioned" ×3.

## 2. On answerable questions, consolidation helps in all 6 seed pairs

F1 on categories 1–4 (233 questions):

| Setup | Mean ± std | Seed 42 | Seed 43 | Seed 44 |
|---|---|---|---|---|
| A-MEM | 0.3174 ± 0.0132 | 0.3026 | 0.3278 | 0.3219 |
| A-MEM + C | **0.3361** ± 0.0093 | 0.3338 | 0.3463 | 0.3282 |
| T-MEM V2 | 0.3134 ± 0.0049 | 0.3178 | 0.3143 | 0.3082 |
| T-MEM V2 + C | **0.3321** ± 0.0103 | 0.3207 | 0.3404 | 0.3353 |

| Comparison | Mean change | Per seed | Positive |
|---|---|---|---|
| A-MEM + C − A-MEM | **+0.019** | +0.031, +0.019, +0.006 | 3/3 |
| T-MEM V2 + C − T-MEM V2 | **+0.019** | +0.003, +0.026, +0.027 | 3/3 |
| T-MEM V2 − A-MEM | −0.004 | +0.015, −0.014, −0.014 | 1/3 |

All 6 seed-matched comparisons favour consolidation. If consolidation had no effect, all 6 coming out positive would happen about 3% of the time (two-sided). **Caveat:** I chose to leave out category 5 *after* seeing the results, so this should be treated as a hypothesis to confirm on new samples, not as a final result.

## 3. What changed in the answer prompts

| Setup | Notes per prompt | Different notes | Merged notes | Questions with a merged note |
|---|---|---|---|---|
| A-MEM | 51.1 | 23.4 | 0 | 0% |
| A-MEM + C | 49.6 | 24.7 | 0.77 | 77% |
| T-MEM V2 | 51.2 | 23.5 | 0 | 0% |
| T-MEM V2 + C | 49.7 | 24.7 | 0.78 | 78% |

The change is small: about one merged note in most prompts, slightly fewer repeated notes, and about 1.3 more different notes.

## 4. The gains come from questions whose prompt had a merged note

F1 change per question, 3 seeds pooled:

| Comparison | Group | n | Mean ΔF1 | Better / worse |
|---|---|---|---|---|
| A-MEM + C vs A-MEM | cats 1–4, merged note in prompt | 555 | **+0.021** | 140 / 118 |
| | cats 1–4, no merged note | 144 | +0.010 | 29 / 24 |
| | cat 5, merged note | 147 | −0.040 | 12 / 16 |
| | cat 5, no merged note | 66 | −0.028 | 4 / 5 |
| T-MEM V2 + C vs T-MEM V2 | cats 1–4, merged note in prompt | 559 | **+0.025** | 147 / 119 |
| | cats 1–4, no merged note | 140 | −0.004 | 25 / 30 |
| | cat 5, merged note | 148 | **−0.084** | 6 / 18 |
| | cat 5, no merged note | 65 | −0.009 | 3 / 4 |

Both effects, the gain on categories 1–4 and the shift toward "Not mentioned" on category 5, sit mainly in prompts that contain a merged note. That points to the merged notes as the cause. This is a correlation, though: questions that pull in a merged note may differ in other ways.

## 5. Where consolidation hurts: paraphrase loses exact wording

The biggest category-4 losses come from the merged summary rewording the source:
- "Why did Gina combine her clothing business with dance?" Reference: "she is passionate about dance and fashion". A-MEM quoted the source ("to blend my love for dance and fashion"). With consolidation the model used the summary's wording ("to show her creativity and share her love with others"), and F1 dropped by 0.19.
- "What is Gina's favorite style of dance?" A-MEM answered "contemporary" ×3; with consolidation, "the context does not specify" ×3.

The biggest gains look like the opposite: the merged note made a fact easier to find. "What was Melanie's favorite childhood book?" went from "not specified" in 2 of 3 seeds to "Charlotte's Web" in 3 of 3.

## Conclusions

1. **The reported category-5 loss is not a real loss.** Consolidation makes the model refuse more wrong-person traps. Under the pipeline's scoring that lowers F1, but the answers are more truthful. Any write-up should say how category 5 is scored, or report categories 1–4 separately (as Mem0 and others do).
2. **On answerable questions, consolidation gives +0.019 F1 for both A-MEM and T-MEM V2, in all 3 seeds each.** This is promising but was found after the fact on 2 samples, so it needs confirming on samples 2–9.
3. **T-MEM V2 vs A-MEM is a wash on categories 1–4** (−0.004). Its category-2 gain (+0.015) is the only benefit, as in the thesis.
4. **The main risk of consolidation is paraphrase**: when the summary rewords the source, the exact words the reference uses can be lost.
5. **Run-to-run noise** (overall F1 range up to 0.034 for the same setup) means single runs should not be compared.
