# T-MEM Progress Log

A simple record of what we did, what we found, and where everything is saved.
Newest entries are at the bottom. Times are local (US Central).

---

## Ground rules

- **The paper's base is the code as of 6 May 2026** (commit `24ad98fa`).
- The paper uses **samples 0 and 1 only** (304 questions), with T-MEM V1 and V2.
- Everything new (consolidation, and later conflict handling) is built **on top of** the May 6 base, with no changes to the paper's method.
- **We test one step at a time:**
  A-MEM → + time ranking (V2) → + consolidation → + conflict handling (later).

## Branches

| Branch | What it holds |
|---|---|
| `progress-temporal-changes` | The May 6 code and results (the paper's base) |
| `consolidation-support` | Consolidation work, on top of the May 6 base |
| `codex-strict-matched-validation` | Older experimental work from June (not part of the paper) |

---

## Log

### 2026-10-16: Setup and the paper's base

- Saved the May 6 code and results on their own branch.
- Checked the paper against the code: all numbers match the May 6 result files.
- Commits: `205c69de`, `3607b5ca`

### 2026-10-16: Consolidation plan

- Read 12 related papers (Mem0, MemTree, LightMem, Zep and others).
- Plan: find notes that repeat the same thing, merge them into one note, keep the originals, lose no facts or dates.
- Plan: [CONSOLIDATION_PLAN.md](CONSOLIDATION_PLAN.md). Commit: `66a46854`

### 2026-10-16: Consolidation built (samples 0–1)

- Built the merging step, with checks that no facts or dates are lost.
- The merge wording was improved 3 times (v1 → v2 → v3). **v3 is the version in use.**
- About 17 merges per conversation, with no facts lost.
- Safety check: with consolidation switched off, the system gives **exactly** the May 6 results (608 of 608 checks).
- Commits: `f3d6248f`, `67cec320`, `c498b3d3`, `54a3ae78`, `4c7023e5`

### 2026-10-21: First full test runs

- Ran A-MEM, T-MEM V2, and each with consolidation, on samples 0–1, 3 times each (12 runs).
- Results: [experiments/consolidation_qa_samples0-1_gpt-4o-mini/](../experiments/consolidation_qa_samples0-1_gpt-4o-mini/README.md)
- Commits: `d9875730`, `9a027acb`

### 2026-10-21: What the results mean

- **Trap questions (category 5):** these ask about things never said, so "Not mentioned" is the right answer. The paper's scoring gives points for the trap answer instead. With consolidation, the model falls for the trap **less** often. The paper's scoring counts that as a loss, but it's actually better.
- **Normal questions (categories 1–4):** consolidation helps, by about +0.02.
- **Consolidation with V2:** both keep their own benefit. They don't get in each other's way.
- Details: [ANALYSIS.md](../experiments/consolidation_qa_samples0-1_gpt-4o-mini/ANALYSIS.md), [ANALYSIS_TMEM_V2.md](../experiments/consolidation_qa_samples0-1_gpt-4o-mini/ANALYSIS_TMEM_V2.md)
- Commits: `2d4e43ae`, `25f38095`

### 2026-10-21: Plan for a stricter experiment (on hold)

- Wrote [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md) with ideas to reduce noise and test on samples 2–9.
- **On hold:** several of these ideas would change the paper's setup (temperature 0, shared keywords, new samples). We stay with the May 6 setup for now.
- Commit: `6bd4b19a`

### 2026-10-21 14:27: Fresh run (main result so far)

- A fresh, separate run of the three steps on samples 0–1, 3 times each, using the May 6 memory and settings.
- Folder: [experiments/fresh_run_2026-10-21_14-27/](../experiments/fresh_run_2026-10-21_14-27/REPORT.md). Ran 14:27 to 14:54.
- Commit: `15cf3861`

| Step | System | Normal questions | Time questions | Traps refused |
|---|---|---|---|---|
| 1 | A-MEM | 0.321 | 0.439 | 45.1% |
| 2 | + time ranking (T-MEM V2) | 0.328 | 0.462 | 45.5% |
| 3 | + consolidation | **0.336** | **0.471** | **47.9%** |

**In short:** each step adds a little. T-MEM V2 helps time questions, and consolidation helps on top of that.

---

### 2026-10-21: Conflict handling: research and plan

- New branch `conflict-handling-support`, on top of consolidation.
- Read how other systems handle conflicts (Mem0, Zep, ROAM, MemStrata, STALE and others).
- Our idea, **state timelines:** link notes about the same thing in date order, mark old facts as outdated (never delete), weaken old notes only if they were really replaced, and label outdated notes in the prompt.
- Main setting chosen: `annotate + demote`.
- Docs: [CONFLICT_HANDLING_RESEARCH.md](CONFLICT_HANDLING_RESEARCH.md), [CONFLICT_HANDLING_PLAN.md](CONFLICT_HANDLING_PLAN.md)
- Commit: `9d41eb38`

### 2026-10-21: Conflict handling step 0, first try

- Measured how many real conflicts samples 0–1 contain (951 AI calls, about $0.07).
- **Found:** similarity search alone misses real conflicts, so we must group notes by topic.
- **Found:** the first try counted too much small talk, so its numbers can't be trusted yet. From reading the conversations: about 5–8 real timelines per sample, mostly plans moving forward, and 1 clear contradiction (Jon's studio).
- Folder: `analysis/conflict_step0_2026-10-21/`
- Next: a stricter second try (about $0.07 more).

### 2026-10-21: Conflict handling step 0, second try

- Stricter tagging: only concrete facts count (52 and 93 notes instead of 204 and 230). 15 of 16 spot-checked were correct.
- Found the real timelines: Caroline's adoption, Jon's dance studio, Gina's store, Gina's internship, and others (6 in sample 0, 7 in sample 1).
- Known cases: 3 of 5 found. Missed: Jon's studio contradiction, and Gina's job → store (filed under two topics).
- **Main lesson:** in LoCoMo, changes are almost all **progress** (steps of a plan), not replacements. So showing the timeline with dates matters most; weakening old notes will rarely apply.
- About 85 of 304 questions (28%) have evidence in timeline notes.
- Cost: 1,234 AI calls, about $0.09.
- Folder: `analysis/conflict_step0_v2_2026-10-21/`

### 2026-10-21: Conflict handling built (steps 1–3)

- Built the new note fields, timeline detection, and the `annotate` / `demote` options.
- Added a second check before marking any note as replaced. It cut 15 doubtful replacements down to 9.
- Built the conflict-aware memory bank for samples 0–1. Nothing was deleted or added.
- **Safety:** with conflict handling off, results are exactly May 6 (608 of 608), and exactly the consolidation step (608 of 608).
- With conflict handling on, timeline labels appear in about 2/3 of prompts. "Now" questions are rare (5), so demotion barely matters on LoCoMo.
- 45 tests pass.
- Next: QA run of the 4th step (A-MEM → V2 → + consolidation → + conflict handling).

### 2026-10-21 16:21: Step 4 run: + conflict handling

- Ran T-MEM V2 + consolidation + conflict handling (`annotate_demote`) on samples 0–1, 3 runs (16:21 to 16:31).
- Folder: [experiments/fresh_run_2026-10-21_16-21_step4_conflict/](../experiments/fresh_run_2026-10-21_16-21_step4_conflict/REPORT.md). Steps 1–3 are taken from the 14:27 run.

| Step | System | Normal questions | Time questions | Traps refused |
|---|---|---|---|---|
| 1 | A-MEM | 0.321 | 0.439 | 45.1% |
| 2 | + time ranking (T-MEM V2) | 0.328 | 0.462 | 45.5% |
| 3 | + consolidation | 0.336 | 0.471 | 47.9% |
| 4 | **+ conflict handling** | **0.342** | **0.490** | 47.4% |

- On the 90 "timeline questions" (fixed before the run): 0.383 → **0.411** with conflict handling.
- **Caution:** step 4 ran separately from steps 1–3, and it beats step 3 in 2 of 3 matching runs. It looks promising, but isn't proven yet.

## Things to keep in mind

- **Results vary between runs.** The AI answers a little differently each time, so always compare averages of several runs, never a single run.
- **Only 2 samples.** All results so far are from samples 0 and 1, like the paper.
- **One small difference from May 6:** our runs fix the order of the two answer choices for trap questions (seeds 42, 43, 44). On May 6 that order was random. The method is the same.

## Next steps

1. Build conflict handling (step 4) on top of V2 + consolidation.
2. Run all four steps on samples 0–1 in a new timestamped folder.
3. Add the result here as a new entry.

---

## How to add a new entry

```
### YYYY-MM-DD HH:MM: Short title

- What we did, in one or two lines.
- What we found, in one line.
- Folder: experiments/<name>_<YYYY-MM-DD_HH-MM>/
- Commit: <hash>
```
