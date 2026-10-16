# T-MEM Module 2: Consolidation — Research and Plan

Branch: `consolidation-support` (starts from the May 6 thesis code, `progress-temporal-changes`).

Goal: add the second T-MEM module, **consolidation**. It should merge repeated or near-duplicate notes into one well-organized note, without losing facts or dates, and evaluate it under the same LoCoMo pipeline used in the thesis.

---

## 1. What others have done

| Work | What "consolidation" means there | When it runs | What we take from it |
|---|---|---|---|
| **Mem0** (Chhikara et al., 2025) | For each new fact, an LLM looks at the top similar memories and picks ADD / UPDATE / DELETE / NOOP. UPDATE merges new detail into an old memory. | Online, every write | The operation set is a useful vocabulary. Their newer version moved toward ADD-only extraction that keeps the history of state changes, which is a hint that destructive edits are risky. |
| **Memory-R1** (2025, ACL 2026) | Same four operations, but the manager is trained with RL. Key example: a prompted system treated "adopted a second dog" as a contradiction and deleted the first dog. The trained agent issued one UPDATE that kept both. | Online | Merging distinct facts is the main failure mode. We need an explicit "same fact?" check before any merge. |
| **Think-in-Memory** (Liu et al., 2023) | Insert, forget and **merge** operations over stored "thoughts", grouped with locality-sensitive hashing. | After each response | Already cited in the thesis. Grouping similar items first, then merging, is the basic pattern. |
| **Generative Agents** (Park et al., 2023) | "Reflection": when enough important memories pile up, the agent writes higher-level insights and stores them as new memories, pointing back to the sources. | Periodic, threshold-triggered | Store the merged result as a **new** note that points to its sources, rather than overwriting. |
| **MemoryBank** (Zhong et al., 2024) | Daily event summaries plus a global user profile, alongside a forgetting curve. | Periodic | Summaries live next to the raw memories, not instead of them. |
| **MemTree** (Rezazadeh et al., ICLR 2025) | Tree memory. New content is routed to a similar node, and parent nodes keep an aggregated summary. | Online | Hierarchy: raw notes at the bottom, summaries above. Retrieval can hit either level. |
| **SeCom** (Pan et al., ICLR 2025) | Groups turns into topic segments, then compresses them to remove noise. Turn-level units hurt retrieval on LoCoMo. | At build time | Strong evidence that one-note-per-turn (what A-MEM does) is noisy. Grouping should help. |
| **RMM** (Tan et al., ACL 2025) | "Prospective reflection" summarizes at utterance, turn and session level and merges into a topic-based memory bank. | After each session | Topic-level merging plus a check of which memories the LLM actually cites. |
| **LightMem** (2025, ICLR 2026) | Filter → topic-grouped short-term summaries → **offline "sleep-time"** long-term update. Reports gains over A-MEM on LoCoMo. | Offline | Running consolidation offline, separate from answering, is cheaper and easier to evaluate. |
| **Zep / Graphiti** (Rasmussen et al., 2025) | Deduplicates entities and facts with embedding plus text search. Contradicted facts get an `invalid_at` time instead of being deleted. | Online | Mark, don't delete. This is also the right basis for Module 3 (conflict handling). |
| **Auto-Dreamer** (Ye et al., 2026) | A learned offline consolidator reads a region of the memory bank and writes a smaller replacement set. Trained with RL on task success. | Offline | Confirms the "offline pass over a region" design. RL training is out of scope for us. |
| **ROAM** (Zheng et al., 2026) | Classifies each pair of memories as independent / equivalent / subsumes / conflicting. Only "Primary" views are retrieved; the rest stay as "Evidence". Argues that letting one LLM call directly add, update or delete memories is error-prone. | At write time | The closest match to our design: a merged note is the primary view, and the source notes stay as evidence. |

Surveys that frame this as an open problem: a 2025 survey ([arXiv 2505.00675](https://arxiv.org/abs/2505.00675)) list consolidation as one of six core memory operations, and a 2026 survey ([arXiv 2603.07670](https://arxiv.org/abs/2603.07670)) names "continual consolidation" as an open challenge.

**Common lessons**
1. **Non-destructive wins.** Zep, ROAM, Generative Agents and newer Mem0 all keep the originals and add a summary or mark status.
2. **Over-merging is the main risk** (Memory-R1's two-dogs example). Similarity alone is not enough to decide two notes are the same fact.
3. **Offline passes are easier to control and evaluate** (LightMem, Auto-Dreamer).
4. **Turn-level notes are noisy** (SeCom), so there is real room for gains on LoCoMo.

---

## 2. Our framework today (May 6 code)

**Where notes come from.** `RobustAgenticMemorySystem.add_note()` in `memory_layer_robust.py` creates one `RobustMemoryNote` per conversation turn. Sample 0 has 419 turns and 419 notes; sample 1 has 369.

**Fields on a note.** `content`, `timestamp`, `keywords`, `tags`, `context`, `links`, `retrieval_count`, `last_accessed`, `evolution_history`, `category`, `importance_score`.

**What A-MEM already does.** "Evolution" (`process_memory`) can add links and rewrite the tags and context of neighbors. It never merges or removes notes.

**A naming trap.** The existing method `consolidate_memories()` does **not** consolidate anything. It only rebuilds the embedding index every 100 evolutions. We should leave it alone and use a different name for real consolidation.

**Hard constraint: links are list positions.** `links` holds integer positions into `list(self.memories.values())`, not note ids. The retriever's embedding matrix is aligned to the same order. If any note is deleted or reordered, every link and every embedding row after it points to the wrong note. **Consolidation must therefore be append-only:** add new notes at the end and never remove old ones.

**Hidden link to the dataset.** Notes are stored in turn order, so note position `i` maps to a LoCoMo `dia_id` such as `D1:3`. LoCoMo questions list their `evidence` dia_ids, so we can measure **whether the right evidence was retrieved**, with no LLM involved.

**How it's run.** The memory bank for each sample is cached in `cached_memories_robust_openai_gpt-4o-mini/` and shared by the A-MEM and T-MEM runs. T-MEM only changes retrieval, in `memory_layer_tmem_robust.py`.

### What the data shows (measured on the May 6 caches)

I measured similarity using the note text only (embeddings with `all-MiniLM-L6-v2`).

| | Sample 0 | Sample 1 |
|---|---|---|
| Notes | 419 | 369 |
| Notes with a near-twin (cosine ≥ 0.85) | 17 | 19 |
| Notes with a close neighbor (cosine ≥ 0.80) | 67 | 57 |
| Groups of 2+ at 0.80 | 20 groups (largest 10) | 21 groups (largest 7) |

Almost no notes are exact copies. About 15% belong to a group of very similar notes. These groups are of two kinds:

1. **The same fact repeated across sessions, with relative dates.** Example: on 17 July 2023, "Next month I'm having an LGBTQ art show", and on 25 August 2023, "I'm putting together an LGBTQ art show next month" (similarity 0.956). Here "next month" means August in one note and September in the other. **Merging these naively would destroy the information needed for time questions.** The merged note must keep each source date and turn relative dates into absolute ones.
2. **Small talk** ("Thanks, appreciate our friendship", "Wow, that painting is awesome!"). These are low-risk to merge, and they take up retrieval slots that real facts could use.

Note: the cached embeddings include keywords, tags and context, which makes unrelated notes look more alike. Group detection should use content-only embeddings.

---

## 3. Design

### 3.1 Core idea

Consolidation is an **offline pass** that runs after the memory bank is built, like LightMem's sleep-time update. It **adds** a new consolidated note for each verified group and **marks** the source notes. It never deletes anything.

```
built memory bank (cached, unchanged)
   │
   ├─ 1. find candidate groups      (content embeddings, threshold τ, max group size)
   ├─ 2. verify each group with LLM (SAME_FACT / SMALL_TALK / DIFFERENT)
   ├─ 3. write a consolidated note  (absolute dates, every fact kept)
   ├─ 4. check for lost information (rule-based; reject if facts are missing)
   └─ 5. append the note, mark sources  → consolidated bank (saved as a new cache)
```

### 3.2 New note fields

All fields are optional, with defaults, so old pickled caches still load (read them with `getattr`).

| Field | Meaning |
|---|---|
| `note_type` | `"raw"` (default) or `"consolidated"` |
| `source_indices` | Positions of the source notes (for consolidated notes) |
| `source_timestamps` | Timestamp of each source note |
| `first_seen` / `last_seen` | Earliest and latest source time |
| `consolidated_into` | Position of the consolidated note (set on source notes) |
| `status` | `"active"` or `"archived"`. An archived note is hidden from the first retrieval step but still exists. |

T-MEM's time decay uses `last_seen` for consolidated notes, so a fact repeated recently counts as recent.

### 3.3 Retrieval modes

These are switched with a flag, so each one is a clean ablation.

| Mode | What retrieval sees |
|---|---|
| `off` | Today's behavior (baseline) |
| `add_only` | Consolidated notes are added; sources still compete normally |
| `primary` | Sources are hidden from top-k; a consolidated note can appear in their place (ROAM-style) |
| `primary_expand` | Like `primary`, but when a consolidated note is retrieved, its sources are added to the context, deduplicated and within a budget |

`primary_expand` is the expected winner: retrieval gets less crowded, and answers still see the original wording and dates.

### 3.4 Prompts (plain text, in the same style as `llm_text_parsers.py`)

- **Verify:** given 2–5 notes with dates, answer `SAME_FACT`, `SMALL_TALK` or `DIFFERENT`. Bias toward `DIFFERENT` when unsure (Memory-R1's lesson).
- **Merge:** write one note that keeps every name, number and event; states each date as an absolute date ("on 17 July 2023 … art show planned for August 2023"); and records which speaker said what.
- **Small talk:** a short merged note such as "Caroline and Melanie often thank each other for support (dates: …)".

### 3.5 Rule-based guard against lost information

Before accepting a merged note, check that every date, number and capitalized name in the source notes appears in it. If anything is missing, reject the merge and log it. This makes "consolidation lost information" something we can measure.

### 3.6 Where the code goes

| File | Change |
|---|---|
| `memory_consolidation.py` (new) | `ConsolidationConfig`, `find_candidate_groups()`, `consolidate_bank()`, the information check |
| `llm_text_parsers.py` | Verify and merge prompts and parsers |
| `memory_layer_robust.py` | Optional note fields; retrieval respects `status`; consolidated notes in neighbor expansion |
| `memory_layer_tmem_robust.py` | Use `last_seen`; respect the retrieval mode |
| `build_consolidated_cache.py` (new) | Reads the frozen May 6 cache and writes `cached_memories_consolidated_<cfg>/`. Never touches the original. |
| `test_advanced_robust.py`, `test_tmem_advanced_robust.py` | `--consolidation_mode`, `--consolidated_cache_dir` flags |
| `evaluate_evidence_recall.py` (new) | Retrieval-only metric: did the retrieved context contain the evidence turns? |
| `tests/test_consolidation.py` (new) | Append-only invariants, links unchanged, old caches load, information check |

---

## 4. Evaluation plan

**Fairness.** Every system uses the same frozen May 6 memory bank. The consolidated bank is built once from it and saved, then reused by every run. The prompts, metrics, model (gpt-4o-mini) and k=10 are the same as in the thesis.

**Systems to compare**

| System | Retrieval | Consolidation |
|---|---|---|
| A-MEM | cosine | off |
| A-MEM + C | cosine | `primary_expand` |
| T-MEM v2 | thesis v2 | off |
| T-MEM v2 + C | thesis v2 | `primary_expand` |

Ablations: the other retrieval modes, τ ∈ {0.80, 0.85, 0.90}, small talk only vs facts only.

**Metrics**
1. **Evidence recall@context.** The share of each question's evidence turns found in the retrieved context. It's deterministic, needs no LLM, and is reported per category. This is the main signal, because it avoids the answer-generation noise that limited the thesis.
2. **QA metrics.** The same suite as the thesis: F1, exact match, ROUGE-L, BLEU-1, METEOR, BERTScore, SBERT.
3. **Memory-bank and context size.** Active notes, average context length in tokens, and redundancy inside the top-k (average pairwise similarity).
4. **Information loss.** The share of merges rejected by the guard, plus a manual check of about 20 merges.
5. **Cost.** LLM calls and tokens per sample.

**Expected effects** (to confirm or reject):
- Fewer redundant notes in the top-k, so better recall for multi-hop questions (category 1).
- With `primary_expand`, no loss on single-hop (4) or time questions (2).
- With `primary` alone, a risk of losing detail on categories 2 and 4. That is why it's an ablation.

**Randomness.** The May 6 code shuffles category-5 answer order without a fixed seed. Fix the seed on this branch so that A-MEM vs A-MEM + C differences are not drowned by noise. That noise was the exact weakness in the thesis.

---

## 5. Steps

| # | Step | Output | LLM cost |
|---|---|---|---|
| 0 | Diagnostics: content-only groups, cluster examples, evidence-recall script for current A-MEM and T-MEM v2 | Baseline recall numbers | None |
| 1 | Note fields and append-only consolidation core with unit tests | `memory_consolidation.py`, tests pass | None |
| 2 | Group finding with threshold sweep; inspect groups by hand | Chosen τ and group cap | None |
| 3 | Verify and merge prompts and the information check; run on samples 0–1 | Consolidated caches, merge log | ~40 groups × 2 calls per sample |
| 4 | Retrieval modes in A-MEM and T-MEM | Flags work, old behavior unchanged when `off` | None |
| 5 | Evidence-recall evaluation of all modes | Table of recall by category | None |
| 6 | QA runs: 4 systems on samples 0–1 with a fixed seed | Comparison reports | Same as thesis runs |
| 7 | If promising: all 10 samples, plus write-up for the thesis | Final tables | Higher |

Check after step 4: with `--consolidation_mode off`, the output must match the May 6 results exactly. This proves we didn't change the baseline.

---

### Step 0 results (2026-10-16)

**Candidate groups.** Produced by `analyze_consolidation_candidates.py`, using complete linkage, same speaker only, and a maximum group size of 5. Full data is in `analysis/consolidation_candidates.json`.

| τ | Sample 0 groups / notes | Sample 1 groups / notes | Largest group |
|---|---|---|---|
| 0.80 | 23 / 49 (11.7%) | 23 / 47 (12.7%) | 3 |
| 0.85 | 7 / 14 (3.3%) | 7 / 15 (4.1%) | 2–3 |
| 0.90 | 2 / 4 (1.0%) | 2 / 4 (1.1%) | 2 |

Complete linkage is much stricter than the earlier single-link estimate. At 0.85, the groups are the art-show repeat, small talk ("Thanks, Melanie…"), and one text-plus-image pair that is not the same fact. This confirms that the LLM verification step is needed. τ = 0.80 gives enough groups to matter.

**Baseline evidence recall.** Produced by `evaluate_evidence_recall.py` on samples 0–1 with k = 10, using the question text as the query. 302 questions have evidence that maps to a note. Full data is in `analysis/evidence_recall_baseline.json`. The script checked that its retrieved notes exactly match the real `find_related_memories_raw` output for every question.

| System | Recall | Top-k (seed) recall | All evidence found | Notes in context | Unique notes |
|---|---|---|---|---|---|
| A-MEM | 0.556 | 0.472 | 0.510 | 50.7 | 23.7 |
| T-MEM v2 | 0.556 | 0.475 | 0.510 | 50.7 | 23.7 |

By category, multi-hop (1) is the weakest: recall 0.384, and only 14% of questions have all their evidence found. For time questions (2), T-MEM v2 raises top-k recall from 0.667 to 0.683, but recall after neighbor expansion is the same (0.714).

**Key finding:** the answer prompt contains about 51 notes, but only about 24 are unique. More than half of the context is repeated notes from link expansion. Removing repeats and merging near-duplicates could free a lot of room.

### Steps 2–3 results (2026-10-16)

**Threshold: τ = 0.80.** I read every group at 0.80 (`analysis/candidates_080_review.json`). Most are small talk or repeated facts. Several look alike but are different (two different campfire photos, two different painting comments), and the LLM check is there to catch those. 0.85 leaves too few groups (7 per sample) to matter.

**Build:** `build_consolidated_cache.py` with gpt-4o-mini at temperature 0, writing to `cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80/`. Merge logs are in `analysis/consolidation_log_sample_{0,1}.json`.

| | Sample 0 | Sample 1 |
|---|---|---|
| Groups | 23 | 23 |
| Merged | 18 (9 small talk, 9 same fact) | 16 (6 small talk, 10 same fact) |
| Kept separate (LLM said DIFFERENT) | 5 | 7 |
| Rejected by the information check | 0 | 0 |
| LLM calls | 41 | 39 |
| Notes | 419 → 437 | 369 → 385 |

**The verification step works.** All 12 "DIFFERENT" decisions look correct when read by hand (for example: different camping trips, a conference vs joining an activist group).

**The merges are concatenations, not summaries.** gpt-4o-mini mostly copies each source note word for word with its date. The merged text is 1.22× the length of its sources. It did **not** follow the rule to turn relative dates into absolute ones (the art-show note still says "next month" twice). No facts were lost, but the notes aren't compressed either. Two causes:
1. The information check requires every capitalized word, including words like "Yay" and "Super", so copying is the easiest way to pass.
2. gpt-4o-mini follows the "keep every detail" rule over the "rewrite" rules.

**What this means for step 4.** Because each merged note already contains its sources word for word, `primary_expand` would show the same text twice. With these merges, `primary` (hide the sources, show only the merged note) loses nothing and is the cleaner mode. Either the merge prompt and check should be revised so merges really compress, or step 4 should use `primary` as the main mode.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Merging different facts (two-dogs problem) | LLM verification biased to `DIFFERENT`; group size cap; rule-based check |
| Lost dates for time questions | Absolute dates required; `source_timestamps` kept; `primary_expand` brings back the sources |
| Broken links or embeddings | Append-only; unit test asserting old positions are unchanged |
| Old caches fail to load | `getattr` defaults for the new fields |
| Too few groups to matter (~15% of notes) | Report the size effect honestly. Small talk may still help by freeing top-k slots. |
| Overlap with Module 3 (conflicts) | Consolidation only merges **compatible** information. Changed facts ("moved from Google to Meta") are passed through untouched and logged as candidates for Module 3. |

---

## 7. Decisions (agreed 2026-10-16)

1. **Main mode: `primary_expand`.** The other modes are kept as ablations.
2. **Offline only.** Consolidation runs on the frozen bank after it is built, not while it is being built.
3. **Only fix the random seed.** The strict evaluation tools from `codex-strict-matched-validation` are not copied to this branch.

---

## Sources

- Mem0: [arXiv 2504.19413](https://arxiv.org/abs/2504.19413), [research page](https://mem0.ai/research-3)
- Memory-R1: [arXiv 2508.19828](https://arxiv.org/html/2508.19828v4)
- Think-in-Memory: [arXiv 2311.08719](https://arxiv.org/abs/2311.08719v1)
- MemTree: [arXiv 2410.14052](https://arxiv.org/html/2410.14052v3)
- SeCom: [arXiv 2502.05589](https://arxiv.org/abs/2502.05589v3)
- RMM: [ACL 2025](https://aclanthology.org/2025.acl-long.413)
- LightMem: [arXiv 2510.18866](https://arxiv.org/pdf/2510.18866v4)
- Zep / Graphiti: [graphiti-core](https://pypi.org/project/graphiti-core/0.8.6/)
- Auto-Dreamer: [arXiv 2605.20616](https://arxiv.org/abs/2605.20616)
- ROAM: [arXiv 2609.09778](https://arxiv.org/abs/2609.09778)
- Nemori: [arXiv 2508.03341](https://arxiv.org/pdf/2508.03341)
- Surveys: [arXiv 2505.00675](https://arxiv.org/abs/2505.00675v3), [arXiv 2603.07670](https://arxiv.org/abs/2603.07670)
