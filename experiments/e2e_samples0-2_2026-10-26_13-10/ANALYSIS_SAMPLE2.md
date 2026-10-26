# Why T-MEM doesn't help sample 2's time questions

Written 2026-10-26. Uses only the saved runs, logs and memory banks in this folder; no new AI calls.
Script: `analyze_e2e_time_questions.py`. Numbers are in `time_question_analysis.json`.

## The problem

On sample 2's **27 time questions**, T-MEM complete scored lower than A-MEM in all 3 runs (−0.069, −0.018, −0.002; mean −0.030). By question: 9 worse, 5 better, 13 the same.

## Findings

### 1. Retrieval is not the cause

With the question text as the search query (local calculation, no AI), every setup finds **the same evidence** for sample 2's time questions:

| Setup | Evidence found |
|---|---|
| A-MEM | 0.741 |
| V2 | 0.741 |
| V2 + consolidation | 0.741 |
| V2 + consolidation + conflict handling | 0.741 |

The same is true for samples 0 and 1. V2 changes the **order** of the top 10, but linked notes bring the same evidence in. So T-MEM's effect on time questions comes from **what the prompt shows** (order, merged notes, timeline labels), not from finding new evidence.

In the real runs, T-MEM's prompts held the evidence slightly less often on sample 2 (0.716 vs 0.747). That's because the AI writes different search keywords in every run. Example: for "When did Maria take up community work with her church friends?", the evidence was missing in 2 of 3 T-MEM runs and present in all 3 A-MEM runs.

### 2. Timelines rarely apply to sample 2

| Sample | Time questions | Evidence in a timeline | T-MEM change on those | T-MEM change on the rest |
|---|---|---|---|---|
| 0 | 37 | 9 | −0.024 | +0.076 |
| 1 | 26 | **17** | **+0.094** | −0.004 |
| 2 | 27 | **3** | −0.040 | −0.029 |

- In sample 1, most time questions are about things in a timeline, and that is where T-MEM gains.
- In sample 2, only 3 of 27 are, so the main source of the gain has almost nothing to work on.
- Sample 0 gains on the *other* questions instead. So the "timelines help" story is partly specific to sample 1.

### 3. A real flaw: timeline labels date things by when they were *said*, not when they *happened*

Example from sample 2:
- **3 Aug 2023,** Maria: "I started volunteering here **about a year ago**", so the reference answer is "around August 2022".
- **But the timeline label says:** `before: started volunteering (28 January 2023)`. That's the day she *mentioned* volunteering, not the day she started.
- **T-MEM's answer** in one run: "28 January 2023".

Sample 2's conversations talk a lot about past events with relative times ("a year ago", "last week", "10 years ago"):

| Sample | Time questions whose evidence uses a relative time | T-MEM change on those | T-MEM change on the rest |
|---|---|---|---|
| 0 | 30 of 37 | +0.037 | +0.114 |
| 1 | 15 of 26 | +0.012 | +0.126 |
| 2 | **23 of 27** | **−0.040** | +0.028 |

In every sample, T-MEM helps **least** when the answer depends on a relative time, and sample 2 is mostly such questions.

### 4. Many losses are date mistakes in the answer, not in the memory

In most of the worst cases, the evidence was in **both** prompts and T-MEM's answer gave a date that **isn't in the prompt at all**. For example, "When did Maria get Coco?" got "12 July 2023" in one run. This is the run-to-run variation of the answering AI (temperature 0.7). With only 27 time questions, a few such answers move the average a lot.

## Conclusion

- T-MEM's lower score on sample 2's time questions is **not a retrieval problem**.
- It comes from three things:
  1. sample 2 has very few time questions that touch a timeline, so the main gain can't happen
  2. timeline labels give the **date something was said**, which misleads questions about past events
  3. normal answer variation on a small set (27 questions)

## What would fix the real flaw

Give each timeline step **two dates**: when it was said, and when it happened. For example, "said on 3 Aug 2023; happened around Aug 2022". The relative-date resolution needed for this already exists in the consolidation code (v3). This is the same "two kinds of time" idea Zep uses. It would need the conflict banks rebuilt and samples 0–2 rerun.
