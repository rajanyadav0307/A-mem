# Plan: 8 on/off setups × 5 runs on LoCoMo samples 0–3

Status: **draft for review. Nothing has been run or paid for.**
Branch: `2026-11-06`. Folder: `experiments/factorial8_samples0-3_2026-11-07/`.

Rule: anything not written in this plan needs your approval first, and is recorded under "Changes to this plan" at the end.

---

## 1. What we want to learn

How each T-MEM part changes A-MEM's answers, on its own and in every combination, with **the same input for every setup**. A-MEM itself is never changed.

| Setup ID | Time ranking | Consolidation | Conflict handling | Script |
|---|---|---|---|---|
| `s1_amem` | off | off | off | `test_advanced_robust.py` (A-MEM) |
| `s2_t` | ON | off | off | `test_tmem_advanced_robust.py` |
| `s3_c` | off | ON | off | `test_advanced_robust.py` |
| `s4_h` | off | off | ON | `test_advanced_robust.py` |
| `s5_tc` | ON | ON | off | `test_tmem_advanced_robust.py` |
| `s6_th` | ON | off | ON | `test_tmem_advanced_robust.py` |
| `s7_ch` | off | ON | ON | `test_advanced_robust.py` |
| `s8_tch` | ON | ON | ON | `test_tmem_advanced_robust.py` |

- **Samples:** 0, 1, 2, 3 (757 questions: 199 / 105 / 193 / 260).
- **Runs:** 5, numbered by seed 42, 43, 44, 45, 46.
- **Total:** 8 setups × 5 runs = **40 result files**.

**How results are read:**
- **Sample 3** is the clean test. T-MEM has never been run on it.
- **Samples 0–2** were used while building T-MEM. They are reported as "development".

## 2. Settings, frozen now

| Setting | Value |
|---|---|
| Model | `gpt-4o-mini-2024-07-18` (exact version) |
| Notes retrieved per question | `--retrieve_k 10` |
| Samples | `--ratio 0.4` (first 4 samples) |
| Time ranking (when ON) | Thesis V2 defaults: blend 0.9, pool 20, 2 fixed, skip margin 0.05, floor 0.25, decay 0.1 per month, category 2 only |
| Consolidation (when ON) | `--consolidation_mode primary_expand --consolidated_top_k_cap 1` |
| Conflict handling (when ON) | `--conflict_mode annotate_demote --demote_penalty 0.10 --timeline_date_style two_dates` |
| Answer randomness | A-MEM's own: temperature 0.7 (0.5 for trap questions). **Not changed.** |
| Trap-question answer order | Fixed by seed (`--seed`) |
| Search words | Made once per question per run with A-MEM's own prompt, then shared by all 8 setups (section 5) |

## 3. Inputs: what is reused and what is built

| Sample | Memory used by all 8 setups | Source |
|---|---|---|
| 0 | Final conflict bank | Copied from `experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/cache/conflict` (fingerprint `1e56b339…`) |
| 1 | Final conflict bank | Same folder (`60e6feb3…`) |
| 2 | Final conflict bank | Same folder (`17053435…`) |
| 3 | **Built fresh** in Stage 1 | A-MEM notes with the author's unchanged code, then merged notes (v3 settings), then timelines (fresh cache folder) |

Why one bank per sample is enough: its first notes are byte-identical to A-MEM's own memory. A-MEM on this bank gives exactly the same lookup as on its own bank (checked on 497 of 497 questions on 2026-11-06).

**Never used (stale or different):**
- `cached_memories_robust_openai_gpt-4o-mini`: the default A-MEM folder. Its sample 2 and sample 3 are old June builds.
- `cached_memories_amem_robust_openai_gpt-4o-mini`: June builds, with different memories for samples 0–2.
- Root `..._consolidated_tau0.80_v1/_v2/_v3` and `..._v3_conflicts_v1`: older versions; the conflict one has no "happened" dates.
- `experiments/e2e_samples0-2_2026-10-26_13-10/cache/conflict`: no "happened" dates.
- Old QA results: they used 3 runs and separate search words, so they are never mixed with these results.

## 4. Folder layout and file names (fixed)

```
experiments/factorial8_samples0-3_2026-11-07/
  PLAN.md                     this plan (committed before any spending)
  manifest.json               fingerprints of every input, code commit, settings, served model, computer, every attempt
  scripts/
    common.py                 the one place where setups, settings, seeds and paths are defined
    preflight.py              copies banks, writes manifest.json, records the served model and code commit
    build_sample3.sh          Stage 1
    make_keywords.py          Stage 2
    run_wave.py               Stage 3 (--trial) and one wave = all 8 setups for one seed
    checks.py                 every check in section 7
    analyze.py                Stage 6 analysis
  build_logs/                 small sample 3 build records (in git)
  cache/                      memory banks (kept on this computer only; git ignores cache/)
    shared/                   memory_cache_sample_{0..3}.pkl + retriever files, one bank per sample
    build_sample3/            base/, consolidated/, conflict/ and their build logs
  keywords/
    keywords_seed42.json … keywords_seed46.json
  trial/                      Stage 3 output (never used in the analysis)
  results/
    s1_amem_seed42.json … s8_tch_seed46.json        (40 files)
  logs/                       (kept on this computer only; about 5 GB)
    s1_amem_seed42.log, s1_amem_seed42.stdout …
  checks/
    inputs_seed42.json …      input checks before each wave
    checks_seed42.json …      result checks after each wave
    checks_all.json           final check across all 40 files
  invalid/                    any failed run, moved here with a reason.txt (never deleted)
  analysis/
    summary.json, tables.md
  REPORT.md
```

**Storage rules**
1. **Write once.** A run never starts if its result file already exists, so nothing can be overwritten.
2. **No partial files.** The evaluator writes its result file only at the very end. A run that stops early leaves no result file.
3. **One name, one meaning.** The file name always holds the setup ID and the seed. The check confirms that the settings inside the file match the name.
4. **Inputs are locked.** Every input file's fingerprint (SHA-256) goes into `manifest.json`, and is checked again before every wave.
5. **Nothing is edited by hand.** A failed run is moved to `invalid/` with its reason and redone, never patched.
6. **What goes into git:** `PLAN.md`, `manifest.json`, `scripts/`, `keywords/`, `results/`, `checks/`, `analysis/` and `REPORT.md`, committed to branch `2026-11-06`.
7. **What stays local:** `cache/` and `logs/`. After the test, copy the whole folder to a backup location of your choice.

## 5. The one code addition (before any spending)

**Shared search words:** a new option `--keywords_file` in both evaluators.
- When it is not given, nothing changes: A-MEM makes its own search words as before.
- When it is given, the evaluator reads the search words for each question from the file instead of asking the AI again.
- The words in the file are made by A-MEM's own `generate_query_llm`, with the same prompt and the same parsing.
- File format: `{"seed": 42, "model": "...", "made_with": "<commit>", "keywords": {"<sample>:<question number>": "<words>"}}`.
- If a question is missing from the file, the run **stops with an error**. It never falls back silently.
- Each question's search words are written to the log, so the check can confirm the file was used.

**Tests (before spending):**
- With the option off, the code path is unchanged.
- With the option on, the words from the file reach the lookup.
- A missing entry raises an error.

## 6. Stages, with a check gate after each one

Money is spent only when the previous gate passes. If any gate fails, everything stops and I report to you.

| Stage | What | Cost | Time | Gate (all must pass) |
|---|---|---|---|---|
| **0** | Code option + tests, scripts, `manifest.json`, one tiny API call to record the served model, commit | ~$0 | ~1 h of work | Tests pass; you approve this plan |
| **1** | Build sample 3: A-MEM notes → merged notes → timelines | ~$0.30 | ~47 min | B1–B5 below |
| **2** | Make search words: 5 runs × 757 questions (3,785 calls) | ~$0.05 | ~8 min | K1–K3 below |
| **3** | Trial: `s1_amem`, sample 0 only, seed 42, with the keywords file | ~$0.18 | ~6 min | All result checks pass on the trial |
| **4** | Wave 1: all 8 setups, seed 42, side by side | ~$5.55 | ~40 min | All result checks pass; real cost on your OpenAI usage page within ±20% of the estimate |
| **5** | Waves 2–5: seeds 43, 44, 45, 46, one wave at a time | ~$22.20 | ~2 h 40 min | All result checks pass after every wave |
| **6** | Final checks across all 40 files, analysis, report, commit | $0 | ~30 min | `checks_all.json` passes |
| | **Total** | **~$28.30** | **~4 h 50 min** | |

Each redone run, if one is ever needed, costs about $0.69.

## 7. Checks

**Sample 3 build (B1–B5)**
- B1: 629 A-MEM notes, one per conversation turn, in turn order.
- B2: The base, consolidated and conflict banks start with byte-identical A-MEM notes and search vectors.
- B3: 0 build warnings or errors.
- B4: Merged notes and timelines are logged (counts recorded in the manifest).
- B5: The "happened" dates are filled in from relative times, as in samples 0–2.

**Search words (K1–K3)**
- K1: Every file has all 757 questions.
- K2: No empty search words.
- K3: The file fingerprints are recorded in `manifest.json`.

**Before every wave (inputs)**
- Bank and keywords fingerprints match `manifest.json`.
- The seed's search-words file holds all 757 questions, none empty.
- No Python file has changed since the recorded commit.
- The API key is present.
- At least 15 GB of free disk.
- The computer is on mains power and kept awake.
- None of the 8 result files for this seed exist yet.

**After every wave (results)**

| # | Check |
|---|---|
| R1 | 757 questions per file (199 / 105 / 193 / 260), in the same order as the dataset and the same in all files |
| R2 | 0 empty answers |
| R3 | Settings in the file match the setup ID and seed exactly (modes, cap, penalty, date style, seed, memory folder, time settings) |
| R4 | The saved overall F1 equals the mean of the per-question F1 |
| R5 | The log shows the right memory loaded for each sample (note counts from the manifest) and 0 rebuilds |
| R6 | 0 errors and 0 failed answers in the log. Any rate-limit retry is counted and reported. |
| R7 | Every question used the shared search words (757 log lines), with 0 search-word AI calls |
| R8 | Timeline labels and "happened" dates appear only in setups with conflict handling on. Merged notes appear only in setups with consolidation on. |
| R9 | Trap-question answer order is identical in all 8 setups for the same seed |
| R10 | For non-time questions, each "time ranking ON" setup has exactly the same retrieved notes as its "OFF" partner (s2=s1, s5=s3, s6=s4, s8=s7). This is exact now that the search words are shared. |
| R11 | **Replay:** for every question, the retrieved notes in the log equal what the code gives offline from the same bank and the same search words |

A run that fails any check is moved to `invalid/`, and the pipeline stops. It is redone only after you say so.

Every check run is also appended to `checks/history.jsonl`, with its time, result and failed checks. That file is never rewritten.

## 8. Analysis (fixed now, before any results)

- **Main measures:** F1 on time questions (category 2), and F1 on answerable questions (categories 1–4).
- **Other measures:** trap refusal rate, overall F1 with A-MEM's scoring, overall score with refusals counted as correct, and the other metrics in the result files.
- **Effects:**
  - each part alone (s2, s3, s4 against s1)
  - all three (s8 against s1)
  - the average effect of each part across the other settings
  - how each pair and all three work together beyond adding up
- **Method:**
  - compare question by question, each question averaged over the 5 runs
  - paired bootstrap stratified by sample (10,000 resamples, random seed 7), as in the thesis
  - 95% range and a two-sided p-value from the bootstrap
- **Test families**, each Holm-corrected on its own, for each sample group:
  1. **Main tests (8):** s2, s3, s4 and s8 against s1, on answerable F1 and time F1.
  2. **Other setups (6):** s5, s6 and s7 against s1, on the same two measures.
  3. **Factorial effects (14):** the average effect of each part (T, C, H), each pair together (T×C, T×H, C×H) and all three (T×C×H), on the same two measures.
- **Sample groups:** every family is run on samples 0–3, on sample 3 alone (the clean test), and on samples 0–2 (development).
- **What counts as real:** a difference counts as real only if its Holm-corrected p-value is below 0.05. The uncorrected 95% range is always shown next to it.
- **Also reported, without tests:**
  - mean ± spread over the 5 runs for every setup and measure
  - trap refusal rate
  - both overall scores
  - F1 per question category
  - how many runs and how many questions were better or worse
- **Reported in full:** everything is reported, including results where T-MEM does not help.
- **The analysis script (`scripts/analyze.py`) is written and committed in Stage 0, before any results exist.** It was tested on made-up results on 2026-11-07.

## 9. Computer and time (measured 2026-11-07)

**Computer:** Apple M4, 10 cores (4 performance, 6 efficiency), 16 GB memory, 100 GB free disk, macOS 26.5.2, mains power. BERTScore runs on the processor (CPU).

**Past speed:** 4, 6, 9 and 12 runs side by side gave 126, 175, 151 and 119 questions per minute in total. The computer, not the API, sets the speed.

**This test:**
- 8 side by side at about 150 questions per minute.
- One wave of 6,056 questions takes about 40 minutes (35–50).
- About 0.95 million tokens per minute, against your limit of 2,000,000 tokens and 5,000 requests per minute.

**Keep awake:** each stage runs under `caffeinate`. Keep the lid open and the power connected; on 2026-11-06 a closed lid paused a wave for 18 hours.

## 10. Cost (measured from real prompts)

Prices assumed: $0.15 per million input tokens and $0.60 per million output tokens. Check them on OpenAI's pricing page before Stage 1.

- **Answer prompts:** 5,842–6,418 tokens, depending on the setup. Counted for all 8 setups; the offline count matches the real logs within 1%.
- **Sample 3 prompts:** about 4% shorter.
- **Answers:** about 10 tokens each.
- **Per wave:** about 36.8 million input tokens, about $5.55.
- **Five waves:** about $27.80. With the build, search words and trial, the total is about **$28.30**.

## Changes to this plan

All of these were made on 2026-11-07, before any money was spent, and are also listed in `manifest.json` → `changes`.

1. **Missing files are reported, not crashed on.** A missing input file is now a FAIL line in the input check, instead of stopping the check script.
2. **The scripts keep the computer awake.** `run_wave.py`, `make_keywords.py` and `build_sample3.sh` start `caffeinate` themselves, so the computer cannot sleep during a stage.
3. **R7 and T4 handle multi-line search words.** They compare the first line of the search words, which is what the log line holds.
4. **R6 and T5 ignore retried calls.** A call that failed once and was retried successfully is no longer counted as an error. A final failure or an empty answer still fails the run.
5. **New check I2b.** Before a wave, the search-words file must have all 757 questions.
6. **New `checks/history.jsonl`.** Every check run is appended to it.

**Zero-cost rehearsal (2026-11-07).** Every stage ran with these exact scripts against a fake AI server on this computer, in a throwaway folder that was deleted afterwards:
- the sample 3 build
- the search words for all 5 runs
- the trial
- one full wave of 8 setups
- the analysis

All checks passed: B1–B5, K1–K3, T1–T6, and 85 of 85 result checks, including the replay of every one of the 6,056 answers. Failure tests confirmed that the checks catch each of these, and that a crashed run is moved to `invalid/` with its reason:
- a repeated wave
- one changed byte in a memory file
- a changed code file
- an empty answer
- a wrong setting
- one changed note in a log
- a missing search-words entry
