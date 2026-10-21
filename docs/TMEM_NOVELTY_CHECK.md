# T-MEM Novelty Check (V2 + Consolidation + Conflict Handling)

Branch: `conflict-handling-support`. Written 2026-10-21.
Purpose: an honest check of what in T-MEM is new compared with published work, and what is not.

---

## 1. Short answer

- **No single idea in T-MEM is new on its own.** Time-aware ranking, merging memories, and marking outdated facts all exist in other systems.
- **What is new is how they are designed and combined:**
  1. time is used only as a **tie-breaker**, and only where a fact **really changed**
  2. merges are **checked so no facts or dates are lost**
  3. changes are **typed** (progress vs change vs contradiction) and **verified with a quote**
  4. it is all built as **switchable modules on top of A-MEM**, each tested step by step, with proof that switching a module off gives back the exact baseline
- **We found no published system that combines all three modules** this way and tests them step by step on LoCoMo.
- **Strength:** moderate. This is a careful, well-tested design and analysis contribution, not a brand-new idea.

---

## 2. Part by part

Strength: **Strong** = we found no close prior work. **Moderate** = close prior work exists, but our version differs in a clear way. **Weak** = essentially already done by others.

### 2.1 Time ranking (Module 1)

| | |
|---|---|
| **What we do** | **V1:** 70% meaning + 30% recency over all notes. **It failed.** **V2:** meaning first; recency reorders only the top 20; the top 2 by meaning stay fixed; recency is skipped when one note is clearly best; used only for time questions |
| **Closest prior work** | **Generative Agents** (recency × relevance over all memories); **TempRALM** (adds a time score to the semantic score); **Mem0 temporal reasoning** (blog: query intent decides how time is used, only at the reranking step); **Cognis** (temporal boosting for time-sensitive queries) |
| **What is new** | The anchored, pool-limited design, plus the evidence for it: a global blend (V1, the same idea as Generative Agents and TempRALM) **hurt** LoCoMo, while the anchored version does not |
| **Strength** | **Moderate to weak.** The design is our own, but "use time only for time questions" also appears in Mem0's and Cognis's designs. The measured gain is small and varies (+0.006 to +0.023 on time questions) |

### 2.2 Consolidation (Module 2)

| | |
|---|---|
| **What we do** | Offline merging of repeated notes. Originals are kept and linked. The AI checks the notes are the same fact. A rule checks no names, numbers or dates are lost, and that relative dates ("next month") are turned into real dates. At most 1 merged note in the top 10 |
| **Closest prior work** | **Mem0** (UPDATE merges new info into old); **LightMem** (offline "sleep-time" consolidation); **ROAM** (merged "primary" view, originals kept as "evidence"); **Generative Agents** (reflection notes); **MemTree**, **Auto-Dreamer** |
| **What is new** | (a) A **date-faithfulness check**: merges that keep or silently drop relative dates are rejected. We found no prior work that checks this. (b) A documented failure mode with its fix: merged summaries **crowd** retrieval (they match many questions), and the fix is a cap of 1, while a "cleaner" embedding made it worse |
| **Strength** | **Moderate.** Keeping originals and offline merging are not new (ROAM, LightMem). The date check and the crowding analysis are our own |

### 2.3 Conflict handling (Module 3)

| | |
|---|---|
| **What we do** | Group a person's concrete facts into **timelines by topic**. Label each step **PROGRESS / CHANGE / CONTRADICTION / COMPATIBLE**. Confirm CHANGE and CONTRADICTION with a second check that must **quote** the newer note. Show the AI the timeline and "OUTDATED since …" labels. Lower replaced notes **only** for "now" questions |
| **Closest prior work** | **Theanine** (NAACL 2025): links memories into **timelines** with relations including "Changed", keeps old memories, and gives timelines to the model. **This is the closest work.** **Zep/Graphiti:** marks old facts invalid and puts **date ranges** in the prompt. **Mem0g, Engram, MemStrata, TOKI:** mark or retire old facts and keep history. **Cognis:** keeps version history and keeps superseded memories for historical questions. **Mem0 temporal reasoning:** has a "current-state" query mode |
| **What is new** | (a) **Lowering only the notes that really changed**, only for "now" questions. This is the direct fix for our own V1 failure, where global decay penalized old-but-true notes. (b) **Typed state changes on free-text notes** (progress vs replacement vs contradiction) with quote-verified replacement. Most systems use a single valid/invalid flag on extracted facts; Theanine's relation types are about cause and effect. (c) **Empirical finding:** in LoCoMo, changes are almost all *progress*, not replacement, so showing the timeline matters more than demoting old notes |
| **Strength** | **Moderate.** Timelines (Theanine), keeping history (Zep and others) and current-vs-historical handling (Cognis, Mem0) all exist. The "targeted decay" link to Module 1, the typed and verified changes, and the LoCoMo analysis are our own |

### 2.4 The combination

| | |
|---|---|
| **What we do** | All three modules on top of A-MEM, each switchable. When a module is off, the system gives **exactly** the earlier result (checked on 608 of 608 retrievals). Tested step by step: A-MEM → +V2 → +consolidation → +conflict handling, with 3 runs per step in one batch |
| **Closest prior work** | Surveys and systems cover these pieces separately (Hindsight's consolidation levers, SSGM, GAM, TOKI). We found **no system that combines all three** on top of A-MEM with step-by-step tests on LoCoMo |
| **What is new** | The combination, the step-by-step evidence, and the exact-baseline guarantee |
| **Strength** | **Moderate.** Combination novelty is real, but reviewers usually weigh it less than a new idea. The step-by-step evidence is what makes it convincing |

---

## 3. Contributions to the evaluation itself

1. **How category 5 is scored.** In the A-MEM evaluation code, adversarial questions are scored against the **trap answer**, so a correct "Not mentioned" counts as a loss. Mem0 leaves category 5 out because it has no ground truth. We go further and show that, in this pipeline, refusing the trap **lowers** the score. This is worth stating, carefully.
2. **Step-by-step testing with an exact-baseline check.** Each module can be shown not to change anything when switched off.
3. **What LoCoMo contains.** Similarity alone misses real conflicts (the old note ranked 8th to 35th). And changes are mostly progress, with very few clean replacements or contradictions.

---

## 4. Claims to avoid

- "The first to use timelines for memory." Theanine did this.
- "The first to keep outdated facts instead of deleting them." Zep, Mem0g, Engram, TOKI, Cognis and Theanine all do.
- "The first time-aware memory retrieval." Generative Agents, TempRALM, Mem0 and Cognis came first.
- "Consolidation and conflict detection share one pass." The plan proposed this, but the **built version uses separate topic timelines**, because step 0 showed similarity search misses conflicts. Don't claim a shared pass.
- "Large or significant gains." So far: 2 samples, 3 runs, gains of about +0.01 to +0.03 F1, some only in 2 of 3 runs.

---

## 5. Suggested novelty statement (for the paper)

> T-MEM extends A-MEM with three switchable modules for time-aware memory: (1) semantic-first temporal reranking that uses recency only as a tie-breaker within a semantic candidate pool, motivated by our finding that a global recency blend degrades LoCoMo performance; (2) non-destructive consolidation with a date-faithfulness check that rejects merges which lose or fail to resolve relative times; and (3) state timelines that type each change as progress, replacement or contradiction, verify replacements with quoted evidence, and apply decay only to notes that were actually replaced and only for current-state questions. Each module can be switched off to recover the exact baseline, and we evaluate them cumulatively on LoCoMo.

---

## 6. What would make the novelty stronger

1. **Compare against the closest ideas directly** on samples 0–1:
   - a Theanine-style timeline (timelines without CHANGE / verification / demotion)
   - a Zep-style date range ("valid from – to") instead of our labels
2. **Ablations of Module 3:** annotate only vs demote only vs both. This shows which part does the work. From the prompt check, demote touches only 4 prompts, so annotate is the likely driver.
3. **More data:** more runs, or samples 2–9, so the gains can be shown to be real. Keep this separate from the paper's two-sample setup.
4. **A test with real replacements:** LongMemEval's knowledge-update questions would test CHANGE and demotion more than LoCoMo can. This is future work, outside the paper's current setup.

---

## References

- Generative Agents: Park et al., UIST 2023
- TempRALM: Gade et al., [arXiv 2401.13222](https://arxiv.org/abs/2401.13222)
- Mem0 temporal reasoning: [Mem0 blog](https://mem0.ai/blog/introducing-temporal-reasoning-in-mem0); Mem0 and Mem0g: [arXiv 2504.19413](https://arxiv.org/html/2504.19413)
- Cognis: Daftari et al., 2026, [arXiv 2604.19771](https://arxiv.org/abs/2604.19771)
- Theanine: Ong et al., NAACL 2025, [arXiv 2406.10996](https://arxiv.org/html/2406.10996v3), [ACL Anthology](https://aclanthology.org/2025.naacl-long.435)
- TReMu: Ge et al., Findings of ACL 2025, [arXiv 2502.01630](https://arxiv.org/abs/2502.01630)
- Zep / Graphiti: [arXiv 2501.13956](https://arxiv.org/abs/2501.13956); [Zep docs: facts with valid_at / invalid_at in the context](https://help.getzep.com/v2/concepts)
- ROAM: [arXiv 2609.09778](https://arxiv.org/abs/2609.09778); LightMem: [arXiv 2510.18866](https://arxiv.org/pdf/2510.18866v4); Auto-Dreamer: [arXiv 2605.20616](https://arxiv.org/abs/2605.20616)
- Engram: [arXiv 2606.09900](https://arxiv.org/pdf/2606.09900); MemStrata: [arXiv 2606.26511](https://arxiv.org/abs/2606.26511); TOKI: [arXiv 2606.06240](https://arxiv.org/abs/2606.06240)
- REALM (retrieval-driven reconsolidation): [arXiv 2609.16053](https://arxiv.org/abs/2609.16053)
- Combined frameworks and surveys: [Hindsight: The Consolidation Problem](https://hindsight.vectorize.io/blog/2026/05/21/agent-memory-consolidation), [SSGM, arXiv 2603.11768](https://arxiv.org/html/2603.11768v1), [GAM, arXiv 2604.12285](https://arxiv.org/pdf/2604.12285)
- STALE: [arXiv 2605.06527](https://arxiv.org/abs/2605.06527)
