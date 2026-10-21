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

## 6b. Step 0 results, second try (2026-10-21)

Command: `measure_conflicts.py --method v2`. Output: `analysis/conflict_step0_v2_2026-10-21/`. 1,234 AI calls, about $0.09 (estimated $0.07). The memory bank was only read.

**What changed from the first try:** a strict "situation" test (concrete facts only), finer topics (threshold 0.78), and each note compared with up to 8 earlier distinct statuses on the same topic.

| | Sample 0 | Sample 1 |
|---|---|---|
| Notes tagged as situations | **52** (was 204) | **93** (was 230) |
| Timelines | 6 | 7 |
| Questions whose evidence is in a timeline note | 37 | 48 |

**The timelines found are the real ones:**
- Sample 0: Caroline's adoption (researching → applied → contacted mentor → passed interviews), Caroline's counselling career, Caroline's art show, Caroline's painting, Melanie's pottery class, Melanie's pets.
- Sample 1: Jon's business, Jon's dance studio (searching for a location → opened and thriving → teaching → expanding), Gina's job, Gina's store, Gina's fashion piece, Gina's design internship (interviewed → accepted).

**Spot check:** 15 of 16 random "situation" notes were real concrete facts. The one mistake was a fact about the other speaker ("Gina's own studio | opened" was really about Jon).

**Known cases:**

| Case | Result |
|---|---|
| Caroline: researching agencies → applied | ✅ found (PROGRESS) |
| Caroline: applied → passed interviews | ✅ found (PROGRESS) |
| Jon: searching for a location → running the studio | ✅ found (PROGRESS) |
| Jon: running the studio (8 Feb) → "still working on opening" (19 Jun) | ❌ not compared. Jon's studio has more than 12 statuses, and the 8 Feb one fell outside the 8 most recent |
| Gina: lost DoorDash job → clothing store | ❌ put under two different topics (job vs store) |
| Melanie: signed up for pottery → made a bowl | Not a valid test: both were said on the same day |
| **"Two dogs" check** (Melanie: owns a dog and cat → got another cat) | ✅ correctly labelled COMPATIBLE, nothing replaced |

**Labels:** almost every step is **PROGRESS**. There are a few CHANGEs, but the 6 in sample 0 all come from one wrongly tagged note. There are **no CONTRADICTIONs**. The pair counts (65 and 320 PROGRESS) are inflated, because each note is compared with several earlier statuses. The useful count is the number of timelines and their steps.

**What this means for the design:**
1. **In LoCoMo, changes are almost all progress, not replacements.** An earlier step ("researching agencies") is not *wrong* later; it's history. So:
   - **Annotate** should present each timeline in date order ("earlier step on 25 May → later: applied on 23 Aug"). This is where most of the value is, because about 85 of 304 questions (28%) have evidence in timeline notes.
   - **Demote** should weaken only notes replaced by a **CHANGE** or **CONTRADICTION**, and only for "now" questions. In samples 0–1 that will rarely trigger.
   - This keeps the chosen setting (`annotate + demote`) and makes clear which part does the work on LoCoMo.
2. **Contradictions in this data are rare and hard to catch.** The one we know of (Jon's studio) needs comparison with *all* earlier statuses, or a check focused on the first and most recent.
3. **Cross-topic changes** (job → business) aren't caught. That's acceptable for now; we'll note it as a limit.

## 6c. Steps 1–3 built (2026-10-21)

**Code**
- **Note fields:** `timeline_id`, `timeline_topic`, `timeline_status`, `transition`, `valid_until`, `superseded_by`, `conflicts_with`. They are class-level defaults on `RobustMemoryNote`, so old banks still load.
- **Detection:** `memory_conflicts.py`, run with `build_conflict_bank.py`.
  1. Tag concrete facts with the strict prompt.
  2. Group them into topics (threshold 0.78).
  3. Compare each note with **all** earlier distinct statuses of its topic.
  4. **Verify** every CHANGE or CONTRADICTION with a second prompt that must quote the newer note. Unconfirmed ones change nothing.
  5. Set the fields.

  Only raw notes are tagged. Nothing is added or removed. Retriever files are copied unchanged.
- **Retrieval:** `conflict_mode` is `off` / `annotate` / `demote` / `annotate_demote`, with `demote_penalty` = 0.10.
  - `annotate` adds one `memory timeline:` field to timeline notes, for example: topic, step k of n, the step before and after with dates, an `OUTDATED since …` label, or a `CONFLICTS with …` label.
  - `demote` lowers replaced notes, and the older side of a contradiction, only for "now" questions.
- **"Now" questions** (fixed before any QA run): the question contains *now, currently, current, still, these days, nowadays, at the moment, latest, anymore* and **none** of *when, before, first, used to, originally, previously, initially, ago, earlier, in <year>* (`is_now_question` in `memory_layer_robust.py`).
- **QA scripts:** new flags `--conflict_mode` and `--demote_penalty`. The agent stores the question so demotion can see it.
- **Tests:** `tests/test_conflicts.py`, 14 tests; 45 tests pass in total.

**Bank built:** `cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80_v3_conflicts_v1/`. This is the v3 consolidated bank plus conflict fields. Log: `analysis/conflict_build_v1_2026-10-21/`. It cost 197 + 19 new AI calls; the rest were reused from step 0.

| | Sample 0 | Sample 1 |
|---|---|---|
| Situation notes / timelines | 52 / 6 | 93 / 7 |
| CHANGE or CONTRADICTION before verification | 6 | 13 |
| Kept after verification (notes marked replaced) | 5 | 4 |
| Contradictions kept | 0 | 0 |

**What was marked as replaced (9):**
- **Sample 0:** five of Melanie's pottery notes, replaced on 13 Oct by "Last month I got hurt and had to take a break from pottery". The change is real, but the old notes are events (making a bowl), so "OUTDATED" may read oddly for "what did she make" questions.
- **Sample 1:** Jon's "I love running my own studio" (8 Feb), replaced on 19 Jun by "Still working on opening a dance studio". This is the known contradiction, labelled CHANGE.
- **Sample 1:** two of Jon's earlier studio notes, replaced on 11 May by "Losing my job gave me the push to finally start my dream business". This is the same inconsistency in the data.
- **Sample 1:** Gina's "The store's doing great!", replaced by "I lost my job. I opened an online clothing store". This is doubtful: a restatement, not a change.

Verification removed 10 wrong ones, such as dance-competition notes "replaced" by "determined to make this studio work".

**Known cases:** 4 of 5 valid cases found (adoption ×2, Jon search → running, Jon running → "still opening"). Missed: Gina job → store (two topics). The two-dogs check works (COMPATIBLE).

**Checks:**

| Check | Result |
|---|---|
| `off` vs May 6 code: original bank, v3 bank, conflict bank | 608/608 identical, all three (`analysis/off_mode_check.json`) |
| Consolidation step (`primary_expand`, cap 1) vs code before conflict work (`f3686cef`), with conflict off: v3 bank and conflict bank | 608/608 identical (`analysis/stage3_unchanged_check.json`) |
| Negative control: prompts that change when conflict handling is on | annotate 408/608, demote 4/608, annotate_demote 408/608 |

**What this tells us before any QA run:**
- **Annotate does almost all the work.** Timeline labels reach about 2/3 of prompts.
- **Demote barely matters on LoCoMo.** Only **5** questions in samples 0–1 count as "now" questions, and demote changes just 4 prompts.

**Not done yet:** the QA run (step 5, the 4th row of the stacked table).

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
