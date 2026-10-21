# Conflict Handling: What Existing Work Does

Branch: `conflict-handling-support`. Written 2026-10-21.

**Goal of T-MEM Module 3 (from the paper):** "detect when a newer note supersedes an older one and lower the priority of the older fact without deleting it."

This document collects how other systems handle memories that disagree, so we can design our own version.

---

## 1. Kinds of conflict

| Kind | Example | What should happen |
|---|---|---|
| **Change of fact** | "I work at Google" → later "I moved to Meta" | The old fact is outdated, but still true for its time |
| **Progress of a plan** | "Looking for a studio" → "Opening the studio" → "Running my studio" | Each step was true at its time; the latest is the current state |
| **Plain contradiction** | Feb: "I love running my own studio" / June: "Still working on opening a studio" | Unclear which is true; keep both and flag them |
| **Looks like a conflict but isn't** | "Adopted a dog" → later "Adopted another dog" | Both stay true; nothing should be replaced |

The last row is the main danger: treating an addition as a replacement deletes a true fact. Memory-R1 calls this out with its "two dogs" example.

The LLM-conflict survey (Xu et al., EMNLP 2024) names three kinds of knowledge conflict. Ours is the **inter-context** kind: retrieved pieces of text that disagree with each other.

---

## 2. Existing systems

| System | How it finds conflicts | What it does with the old memory | When it runs |
|---|---|---|---|
| **A-MEM** (our base, NeurIPS 2025) | It doesn't. "Evolution" only updates tags and context of neighbor notes | Nothing; both stay equally active | At write time |
| **Mem0** (base, 2025) | An LLM compares a new fact with the most similar stored memories and picks ADD / UPDATE / DELETE / NOOP | **Deletes** it ("DELETE for removal of memories contradicted by new information") | At write time |
| **Mem0g** (graph variant, same paper) | A conflict detector finds existing relationships that may clash; an LLM resolver decides | **Marks it invalid** and keeps it, "to enable temporal reasoning" | At write time |
| **Mem0 v3** (later rewrite) | Reportedly removed the conflict resolver; adds facts alongside old ones | Keeps both; retrieval ranks them | At read time |
| **Zep / Graphiti** (2025) | An LLM compares new and existing edges (facts) between the same entities | Sets `invalid_at` on the old edge, using the new fact's `valid_at`. Bi-temporal: when it was true vs when we learned it | At write time |
| **Memory-R1** (ACL 2026) | Same 4 operations as Mem0, but the manager is trained with reinforcement learning | Learns to UPDATE (merge) instead of DELETE + ADD when facts can coexist | At write time |
| **ROAM** (2026) | Classifies each pair of memories as independent / equivalent / subsumes / **conflicting** | Keeps the current one as "primary" and moves the old one to "evidence"; only primary is retrieved | At write time |
| **MemStrata** (2026) | Fixed rule over (subject, relation, object) facts; no LLM | Retires the old value in a bi-temporal ledger | At write time |
| **Engram** (2026) | Rules first, then an LLM when the rules fail | `valid_at` / `invalid_at` plus a "supersedes" pointer | At write time |
| **CUPMem** (with the STALE benchmark, 2026) | Write-time revision with "structured state consolidation and propagation-aware search" | Revises the stored state | At write time |
| **LongMemEval system tips** (ICLR 2025) | No conflict detection; adds dates to memory keys ("fact-augmented key expansion") and uses "time-aware query expansion" | Nothing; relies on time-aware retrieval | At read time |

---

## 3. Benchmarks that test conflict handling

| Benchmark | What it tests | Notes |
|---|---|---|
| **LoCoMo** (our benchmark) | No dedicated conflict category | Conflicts appear only indirectly, as state changes inside long chats (see §5) |
| **LongMemEval** (ICLR 2025) | A "knowledge updates" ability, among 5 abilities, in 500 questions | The most common external test for updates |
| **MemoryAgentBench** (ICLR 2026) | "Conflict resolution" competency; FactConsolidation dataset (a numbered newer fact overrides an older one) | A follow-up preprint reports multi-hop conflict accuracy of at most 7% across 22 systems |
| **STALE** (2026) | 400 conflict scenarios, 1,200 queries; includes **implicit conflicts** (a later fact invalidates an earlier one without saying so) | Best model: 55.2%. Main finding: models often **retrieve** the updated evidence but **fail to act on it** |
| **Memora** (ACL 2026 Findings) | Memory over weeks to months with frequent updates; a metric that penalizes using outdated memories | Memory agents gave only small gains |

---

## 4. Lessons for our design

1. **Never delete.** Mem0g, Zep, ROAM, Engram and MemStrata all keep the old fact and mark it. Deleting breaks questions about the past ("When did Jon start…?", "Where did he work before?").
2. **Store two times:** when a fact became true, and when it stopped being true (Zep, Engram, MemStrata).
3. **Similarity alone can't find conflicts.** MemStrata reports that cosine similarity separates contradicted facts from duplicates poorly (AUROC 0.59). We need a classification step after the similarity search, as in our consolidation step.
4. **Additions are not replacements** (Memory-R1's two dogs). When unsure, keep both.
5. **Finding the update isn't enough.** STALE shows models can see the new fact and still answer with the old one. How the notes are **shown** to the answering model matters, not just which notes are retrieved.
6. **Real conversations mostly contain implicit, gradual changes,** not neat "X is now Y" statements (STALE, Memora). Rule-based triple systems like MemStrata note that text extraction is the hard part.

---

## 5. What conflicts look like in our data (samples 0–1)

Found by reading the conversations:

| Who | Timeline | Kind |
|---|---|---|
| Jon (sample 1) | 29 Jan "on the hunt for the ideal spot for my dance studio" → 4 Feb "searching for a location" → **8 Feb "I love running my own studio"** → 3 Apr "expanding my studio's social media" → **19 Jun "Still working on opening a dance studio"** | Progress, then a **plain contradiction** in the data |
| Caroline (sample 0) | 25 May "researching adoption agencies" → 15 Jul council meeting for adoption → 23 Aug "applied" → 13 Oct contacted mentor → 22 Oct "passed the adoption agency interviews" | Progress of a plan |
| Gina (sample 1) | 20 Jan lost her job at DoorDash → runs a clothing store → later internship and fashion editors | Change of fact, then progress |

**A quick automatic scan** looked for pairs of notes from the same speaker in different sessions that are similar in meaning and contain a change word ("now", "still", "started", "quit"…). It found 175 pairs in sample 0 and 403 in sample 1, but most were small talk or repeats ("Thanks, I won't quit!"). This matches lesson 3: similarity finds many candidates, but a classification step must pick out the real conflicts.

**Questions that depend on the latest state** exist, but there aren't many. Examples: "What book is Jon currently reading?", "When did Jon start to go to the gym?", "What workshop did Caroline attend recently?". About 23 questions in sample 0 and 14 in sample 1 contain change words such as now, still, currently, recently or started.

---

## References

- A-MEM: Xu et al., NeurIPS 2025, [arXiv 2502.12110](https://arxiv.org/abs/2502.12110)
- Mem0 and Mem0g: Chhikara et al., 2025, [arXiv 2504.19413](https://arxiv.org/html/2504.19413)
- Mem0 v3 note: [Field Guide to AI Memory: updates and conflicts](https://www.memoryplugin.com/wiki/updates-and-conflicts.html)
- Zep / Graphiti: Rasmussen et al., 2025, [arXiv 2501.13956](https://arxiv.org/abs/2501.13956); [Graphiti temporal model](https://mintlify.com/getzep/graphiti/concepts/temporal-model); [Zep blog](https://blog.getzep.com/beyond-static-knowledge-graphs/)
- Memory-R1: [arXiv 2508.19828](https://arxiv.org/html/2508.19828v4)
- ROAM: Zheng et al., 2026, [arXiv 2609.09778](https://arxiv.org/abs/2609.09778)
- MemStrata: Yadav, 2026, [arXiv 2606.26511](https://arxiv.org/abs/2606.26511)
- Engram: 2026, [arXiv 2606.09900](https://arxiv.org/pdf/2606.09900)
- STALE and CUPMem: Chao et al., 2026, [arXiv 2605.06527](https://arxiv.org/abs/2605.06527)
- Memora: Uddin et al., ACL 2026 Findings, [arXiv 2604.20006](https://arxiv.org/abs/2604.20006)
- LongMemEval: Wu et al., ICLR 2025, [arXiv 2410.10813](https://arxiv.org/abs/2410.10813v2)
- MemoryAgentBench: Hu et al., ICLR 2026, [arXiv 2507.05257](https://arxiv.org/html/2507.05257v1); follow-up results in [arXiv 2606.01435](https://arxiv.org/pdf/2606.01435)
- Knowledge conflicts survey: Xu et al., EMNLP 2024, [arXiv 2403.08319](https://arxiv.org/html/2403.08319)
- Memory survey (destructive vs non-destructive updates): [arXiv 2512.13564](https://arxiv.org/pdf/2512.13564)
- Belief revision and agent memory: "Operative Contexts", [NeurIPS 2026](https://neurips.cc/virtual/2026/169569)
