# Conflict Handling (T-MEM Module 3): Our Plan

Branch: `conflict-handling-support`, on top of `consolidation-support`. Written 2026-10-21.
Background research: [CONFLICT_HANDLING_RESEARCH.md](CONFLICT_HANDLING_RESEARCH.md).

---

## 1. Ground rules

- **The base is the May 6 code.** Nothing in the paper's method changes. With conflict handling switched off, the system must give **exactly** the May 6 results. We check this the same way as for consolidation (`check_off_mode_matches_may6.py`).
- **Samples 0 and 1 first**, the same as the paper.
- **One step at a time:** A-MEM → + time ranking (V2) → + consolidation → **+ conflict handling**.
- **Nothing is deleted.** We only add information to notes.

---

## 2. The idea in one paragraph

When a person says something new that changes an older fact, we **link the two notes in time order** and record when the old one stopped being true. When answering:
- **"now" questions** prefer the newest note.
- **"when" or "before" questions** see the whole story, with dates.
- **The AI is told plainly** which note is outdated, instead of just having that note ranked lower.

We call this **state timelines**.

---

## 3. What is new (novelty)

Other systems (Zep, Mem0g, Engram, MemStrata) mark old facts as invalid. Our version is different in four ways, each tied to our own framework:

### Novelty 1: Timelines, not just "valid / invalid"
- In our data, most changes are **steps of progress** (looking for a studio → opening it → running it), not neat replacements (see research §5).
- So instead of a yes/no "invalid" flag, we link notes into a **timeline** with a type for each step:
  - **PROGRESS**: the plan moved forward
  - **CHANGE**: the fact was replaced
  - **CONTRADICTION**: the two notes disagree and it's unclear which is right
- Zep, Mem0g, Engram and MemStrata work on extracted (subject, relation, object) facts and use a single valid/invalid mark. Ours works directly on A-MEM's free-text notes, with no fact extraction, and fits A-MEM's existing links.

### Novelty 2: Time decay only where a fact really changed
- Our paper's **V1 failed** because it made **every** old note weaker, including old notes that were still true.
- Conflict handling fixes this at the root: a note gets weaker **only if a newer note actually replaced it**. Old notes that are still true keep their full score.
- This links Module 1 (time) and Module 3 (conflicts). It builds directly on our own V1 negative result, which makes it a strong story for the thesis.

### Novelty 3: Tell the AI, don't just hide the note
- STALE shows that models often **see** the new fact but still answer with the old one.
- So instead of hiding outdated notes, we **label** them in the prompt, for example:
  `[OUTDATED since 8 Feb 2023 → see: "I love running my own studio"]`
- The AI can then answer "now" questions with the new fact and "when" questions with the full story.

### Novelty 4: One shared maintenance pass with consolidation
- Consolidation (Module 2) already finds similar notes and asks the AI about them. We extend that **same** check from "same fact?" to a wider choice:

  | AI's answer | What we do |
  |---|---|
  | SAME_FACT / SMALL_TALK | Merge them (Module 2, already built) |
  | PROGRESS / CHANGE | Add to a timeline, mark the older note (Module 3) |
  | CONTRADICTION | Link both, flag them, keep both active |
  | COMPATIBLE / DIFFERENT | Do nothing |

- One pass, one set of AI calls, no extra cost. It also guarantees consolidation never merges two notes that actually conflict.

---

## 4. How it works

### 4.1 New note fields
Added the same way as for consolidation: class-level defaults, so the old memory banks still load.

| Field | Meaning |
|---|---|
| `valid_from` | When this fact became true (the note's date, or a resolved date such as "last Friday" → 14 July 2023) |
| `valid_until` | When it stopped being true (set when a newer note replaces it) |
| `superseded_by` | The newer note that replaced it |
| `timeline_id` | Which timeline the note belongs to |
| `transition` | PROGRESS / CHANGE / CONTRADICTION (how this note relates to the one before it) |

### 4.2 Finding conflicts (offline, after the bank is built, like consolidation)
1. **Candidates:** pairs of notes from the **same speaker**, in **different sessions**, that are fairly similar in meaning. We also use A-MEM's existing links as hints.
2. **The AI decides** for each pair, using the labels in Novelty 4. **When unsure, it answers COMPATIBLE.** That avoids the "two dogs" mistake.
3. **Dates:** the date of a change is resolved to a real date, reusing the date checks we built for consolidation v3.
4. **Safety checks**, as in consolidation: the decision is logged, and nothing is changed if the AI's answer can't be read.

### 4.3 Using it when answering
Retrieval options, so each idea can be tested on its own:

| Option | What it does |
|---|---|
| `off` | Exactly May 6 (and exactly the consolidation step, if consolidation is on) |
| `annotate` | Outdated notes stay in the prompt but carry an "OUTDATED since …" label (Novelty 3) |
| `demote` | Outdated notes get a lower score, **only** for "now / current / still" questions (Novelty 2) |
| `annotate + demote` | Both; expected to be the main setting |

**Which questions count as "now" questions:** a short, fixed list of words (now, currently, still, these days, latest, anymore). It is decided **before** seeing any results and written down here. "When did…" questions are never demoted.

---

## 5. How we will test it

**Main test:** step 4 of the stacked table on samples 0–1, using the May 6 setup and 3 runs, saved in a new timestamped folder:

| Step | System |
|---|---|
| 1 | A-MEM |
| 2 | + time ranking (V2) |
| 3 | + consolidation |
| **4** | **+ conflict handling** |

We report the same simple columns as the fresh run: normal questions, time questions, and traps refused.

**Extra checks** (because LoCoMo has few clear conflicts, the overall score may hardly move):
1. **"State" questions:** the questions that depend on the latest state or on when something changed (about 37 in samples 0–1, listed in the research document). The list is fixed **before** any runs.
2. **Detection quality:** you label about 60 candidate pairs by hand, so we can measure how often the AI's PROGRESS / CHANGE / CONTRADICTION / COMPATIBLE labels are right.
3. **Does the AI use the update?** For state questions where the newer note was in the prompt, how often did the answer use it? This is STALE's "sees it but doesn't use it" gap.

**Not in scope for now** (they would change the paper's setup): LongMemEval, MemoryAgentBench, STALE, and samples 2–9. These are listed as future work.

---

## 6. Steps

| # | Step | Output | API cost |
|---|---|---|---|
| 0 | **Measure:** run the AI check on candidate pairs in samples 0–1 and read the results | How many real PROGRESS / CHANGE / CONTRADICTION cases exist | under $0.10 |
| 1 | New note fields, timeline links, unit tests | Code; old banks still load | none |
| 2 | Detection, sharing the consolidation pass | Conflict-aware memory banks for samples 0–1, plus a decision log | under $0.50 |
| 3 | Retrieval options (`annotate`, `demote`); check that `off` still matches May 6 | Code and checks pass | none |
| 4 | Fix the list of state questions and the "now" words in writing | A dated list in this document | none |
| 5 | Full test: 4 steps × 3 runs, in a new timestamped folder | REPORT.md, as in the fresh run | about $5 |
| 6 | Analysis and progress log entry | Results in plain words | none |

---

## 6a. Step 0 results, first try (2026-10-21)

Script: `measure_conflicts.py`. Output: `analysis/conflict_step0_2026-10-21/`. 951 AI calls with gpt-4o-mini, about $0.07. The May 6 memory bank was only read, never changed.

**Finding 1: similarity alone misses real conflicts.**
For known conflicts (Jon's studio, Caroline's adoption), the older note ranked **8th to 35th** among that person's similar earlier notes. A "top 3 most similar" search would miss them. So candidates have to come from **topics**, not from similarity alone. This matches MemStrata's finding (research §4).

**Finding 2: the first try is too loose to trust its counts.**

| | Sample 0 | Sample 1 |
|---|---|---|
| Notes | 419 | 369 |
| Tagged as "situation" notes | 204 (49%) | 230 (62%) |
| Topic timelines | 17 | 12 |
| Timeline steps checked | 74 | 89 |
| PROGRESS / CHANGE / CONTRADICTION | 16 / 0 / 0 | 50 / 1 / 0 |

When I read 16 random PROGRESS steps, only about **4 were real progress**. Three problems:
1. **Too much counted as a "situation".** Lines like "Thanks! I'm going for my dreams!" and "Let's plan something special!" got tagged.
2. **Topics are too broad.** For example, "Caroline's self-acceptance" holds 50 notes, so a timeline mixes unrelated statements.
3. **Only neighbouring notes are compared.** The known contradiction (Jon, 8 Feb "I love running my own studio" vs 19 Jun "Still working on opening a dance studio") was never compared directly. Jon's 19 Jun note was only compared with his 16 Jun note, and labelled PROGRESS.

**Rough count from reading the conversations myself (not measured):** about 5–8 real timelines per sample, each with 2–5 steps. Almost all are PROGRESS (adoption, counselling career, Jon's studio, Gina's store, Melanie's pottery class), with **1 clear CONTRADICTION** (Jon's studio) and very few clean CHANGEs (Gina losing her DoorDash job).

**What to fix in the second try:**
- A stricter "situation" test: concrete, checkable facts only (an event, a status, a possession, a job, a place, a step in a plan). No feelings, thanks or encouragement.
- Finer topics: a higher similarity threshold, and topics named by the thing itself ("Jon's dance studio"), not a feeling.
- Compare each new note with **every** earlier note on the same topic that has a different status, not only the one just before it.
- Before trusting any counts, check that the known cases are found (Jon's studio contradiction, Caroline's adoption steps, Gina's job → store).

## 7. Risks and how we handle them

| Risk | How we handle it |
|---|---|
| Treating an addition as a replacement (two dogs) | When unsure the AI answers COMPATIBLE; replaced notes are labelled, never removed |
| Hurting "when did…" questions by weakening old notes | Never demote for "when / before / first" questions; labels keep the full story visible |
| Very few conflicts in samples 0–1, so no visible effect | Step 0 measures this first; the state-question set shows effects the overall score would hide |
| A conflict-aware merge undoes a consolidation merge | One shared pass, so a pair gets only one label |
| Contradictions in the data itself (Jon's studio) | Labelled CONTRADICTION: both notes stay active, and the label shows the AI both |
| Run-to-run noise | 3 runs, compare averages, as before |

---

## 8. Decisions

1. **Main retrieval setting:** `annotate + demote` (decided 2026-10-21). `annotate` and `demote` on their own are tested as extra checks.
2. **Step 0:** approved 2026-10-21.
3. **Hand labelling** of about 60 pairs: still open.
