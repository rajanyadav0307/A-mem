# Thesis Report Gap Analysis

This note compares the current mid-term report against the code and benchmark artifacts now present in the repo.

## Biggest Gaps

1. The report often describes the full `T-MEM` design as if it already exists in code.
Current code status:
- Module 1 is implemented and benchmarked.
- Module 2 (consolidation) is still planned.
- Module 3 (conflict handling) is still planned.

Relevant code:
- [memory_layer_tmem_robust.py](/Users/rajanyadav/Desktop/Projects/A-mem/memory_layer_tmem_robust.py)
- [test_tmem_advanced_robust.py](/Users/rajanyadav/Desktop/Projects/A-mem/test_tmem_advanced_robust.py)

2. The abstract and conclusion are outdated.
The current report still ends with the older synthetic result only:
- 6 of 7 LoCoMo-style queries improved in the simulation

That part is still true for the standalone prototype, but it is no longer the full story. You now also have a real QA pilot on the repo's `locomo10` subset:
- first `T-MEM` version underperformed `A-MEM`
- revised `T-MEM` v2 slightly outperformed `A-MEM` overall on the same 2-sample pilot

Relevant result files:
- [results_amem_2samples_gpt-4o-mini.json](/Users/rajanyadav/Desktop/Projects/A-mem/results_amem_2samples_gpt-4o-mini.json)
- [results_tmem_2samples_gpt-4o-mini.json](/Users/rajanyadav/Desktop/Projects/A-mem/results_tmem_2samples_gpt-4o-mini.json)
- [results_tmem_2samples_gpt-4o-mini_v2.json](/Users/rajanyadav/Desktop/Projects/A-mem/results_tmem_2samples_gpt-4o-mini_v2.json)
- [amem_vs_tmem_2samples.md](/Users/rajanyadav/Desktop/Projects/A-mem/amem_vs_tmem_2samples.md)
- [amem_vs_tmem_2samples_v2.md](/Users/rajanyadav/Desktop/Projects/A-mem/amem_vs_tmem_2samples_v2.md)

3. The current report overstates the status of consolidation and conflict handling.
Examples that should be softened:
- "`T-MEM (Ours)`" with checkmarks for all three capabilities
- workflow figure showing all three modules without clearly labeling two of them as future work
- conclusion sentence saying "`T-MEM fills that gap with three extensions on top of A-MEM`"

Safer wording:
- "`T-MEM` is the proposed three-module framework"
- "`The current implementation covers only the temporal retrieval module`"

4. The temporal scoring section no longer matches the current benchmarked code path.
The current report describes:
- global blending across the memory bank
- default `alpha = 0.7`
- a combined relevance formula as if it were the main active mode

The current best-performing code does something narrower:
- temporal reranking is applied only to configured categories, currently category `2`
- retrieval is semantic-first, then reranked within a candidate pool
- default `blend_alpha = 0.9`
- top semantic memories are anchored
- temporal reranking is skipped when the semantic leader is clearly ahead
- current benchmark runs are still in decay-only mode

Relevant code:
- [memory_layer_tmem_robust.py](/Users/rajanyadav/Desktop/Projects/A-mem/memory_layer_tmem_robust.py)

5. The tools table is broader than the tools used in the results you now report.
Potentially misleading entries in the current draft:
- `ChromaDB / FAISS`
- `Weights & Biases`

Those tools are not part of the reported `T-MEM` benchmark results in this repo.

What was actually used for the reported pilot:
- Python
- OpenAI API with `gpt-4o-mini`
- `all-MiniLM-L6-v2`
- repo-local robust A-MEM evaluator
- local pickle / NumPy caches
- JSON result files plus a local comparison script

6. The report currently blurs together three different code paths.
There are really three distinct things:
- the original-style robust `A-MEM` QA evaluator in the repo root
- the separate self-contained `tmem/` simulation
- the integrated `T-MEM` robust QA evaluator added on top of the root pipeline

Those should be clearly separated in the report.

Relevant files:
- [test_advanced_robust.py](/Users/rajanyadav/Desktop/Projects/A-mem/test_advanced_robust.py)
- [memory_layer_robust.py](/Users/rajanyadav/Desktop/Projects/A-mem/memory_layer_robust.py)
- [tmem/README.md](/Users/rajanyadav/Desktop/Projects/A-mem/tmem/README.md)
- [test_tmem_advanced_robust.py](/Users/rajanyadav/Desktop/Projects/A-mem/test_tmem_advanced_robust.py)

7. The current report uses stronger venue wording than the uploaded paper supports directly.
The uploaded PDF front matter clearly shows an arXiv preprint:
- "`arXiv:2502.12110v11 [cs.CL] 8 Oct 2025`"

To avoid overclaiming, safer wording is:
- "`A-MEM (Xu et al., 2025)`"
- "`the A-MEM paper`"

instead of asserting a final venue unless you have a confirmed source you want to cite separately.

## What The Revised Report Should Say

1. `T-MEM` is a proposed three-module framework, but only Module 1 is implemented today.

2. The project has progressed in two stages:
- a standalone LoCoMo-style retrieval simulation
- an integrated LoCoMo QA pilot using the same robust evaluator as `A-MEM`

3. The honest experimental story is:
- `T-MEM v1` with a global recency blend hurt performance
- `T-MEM v2` with selective semantic-first reranking slightly improved overall performance on the 2-sample pilot

4. The strongest interpretable gain is on category `2` temporal questions, because that is where temporal reranking is actually enabled in the current best code path.

5. The current evidence is still preliminary:
- only the first two samples of the repo's `locomo10` subset
- 304 questions total
- not yet a full LoCoMo or DialSim evaluation

## Current Benchmark Facts Worth Keeping

- Synthetic LoCoMo-style simulation:
  - correct-memory rank improved in 6 of 7 queries
  - average improvement about 2.3 positions

- Integrated QA pilot, 2 samples, 304 questions, same `gpt-4o-mini` backend:
  - `A-MEM` overall F1: `0.3613`
  - `T-MEM v1` overall F1: `0.2768`
  - `T-MEM v2` overall F1: `0.3686`
  - `A-MEM` category 2 F1: `0.4455`
  - `T-MEM v2` category 2 F1: `0.4610`

## Files Created For This Rewrite

- [T_MEM_Midterm_Report_Revised.tex](/Users/rajanyadav/Desktop/Projects/A-mem/T_MEM_Midterm_Report_Revised.tex)
- [THESIS_REPORT_GAP_ANALYSIS.md](/Users/rajanyadav/Desktop/Projects/A-mem/THESIS_REPORT_GAP_ANALYSIS.md)
