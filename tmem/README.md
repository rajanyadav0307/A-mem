# T-MEM (Temporal-aware Memory)

Thesis prototype extending **A-MEM** (Xu et al., NeurIPS 2025; [arXiv:2502.12110](https://arxiv.org/abs/2502.12110)) with **Module 1: temporal relevance scoring** for retrieval.

The production A-MEM codebase can be cloned alongside this repo for reference (see upstream `AgenticMemorySystem`, `MemoryNote`, `add_note`, `search_agentic`, Chroma-backed retrieval in `agentic_memory/memory_system.py`). This package does **not** modify upstream A-MEM; it adds a self-contained simulation that needs **no LLM API keys**.

## Alignment with A-MEM (original paper methods)

What this repo **matches** from Xu et al. (NeurIPS 2025):

| Paper ingredient | This project |
|------------------|----------------|
| Note fields \(c, t, K, G, X, e, L\) (Sec. 3.1, Eq. 1) | `MemoryNote` + `embedding_input_text()` = concat for \(f_\mathrm{enc}\) |
| Encoder \(f_\mathrm{enc}\) | `all-MiniLM-L6-v2` (Sec. 4.2) via `sentence_transformers.SentenceTransformer` |
| Similarity / retrieval Eq. 4, 9 | Cosine \(\cos(e_q, e_i)\) over all in-memory notes; `amem_retrieve` when \(\alpha=1\) |

What is **still simulated or approximated** here (no LLM calls):

| Paper ingredient | This simulation |
|------------------|-----------------|
| LLM-generated keywords, tags, context (Sec. 3.1) | Hand-written metadata in `simulation/memory_bank.py` |
| LLM link decisions after top‑\(k\) cosine neighbors (Sec. 3.2) | Undirected links if embedding cosine \(>\) threshold (`auto_link_cosine_threshold`) |
| Chroma / `search_agentic` implementation details in A-mem-sys | Flat NumPy ranking over the same vectors — **same ranking** as Eq. 9 over \(M\) if embeddings are identical |

**Paper-aligned embedding mode (recommended for thesis numbers):**

```bash
export TMEM_PAPER_ALIGNED_AMEM=1
python main.py
```

This **disables the hash encoder** and requires a working `SentenceTransformer` load (network once, or `TMEM_LOCAL_MODEL_PATH` to a local snapshot). If loading fails, the process exits with an error instead of silently substituting a non-paper encoder.

**Development / offline (not paper-reported):**

- If the hub is unreachable and **paper mode is off**, `main.py` **may fall back** to `HashTextEncoder` (stderr warning).
- **`TMEM_STRICT=1`** — in non–paper-aligned mode, do not fall back; fail on hub errors.
- **`TMEM_ALLOW_HASH_ENCODER=1`** — force hash (ignored when `TMEM_PAPER_ALIGNED_AMEM=1`).
- **`TMEM_LOCAL_MODEL_PATH=/path/to/model`** — offline folder (e.g. after `huggingface-cli download sentence-transformers/all-MiniLM-L6-v2` elsewhere).

**Temporal decay (extension only; not in A-MEM):**

- **Default:** `use_decay_only_temporal=True` → relevance uses **only** \(\mathrm{decay}(m_i)=\exp(-\lambda\cdot\mathrm{age})\) with `note.timestamp` as \(t_i\). Access counts and links do **not** enter \(r_i\) (reinforce/link factors are fixed at 1 in diagnostics).
- **Full \(r_i\) product:** set `TMemConfig(use_decay_only_temporal=False)` to restore `decay × reinforce × link_bonus`.
- **Age unit:** `decay_age_unit` is `"months_equiv"` (days/30) or `"days"` for literal day count; tune \(\lambda\) accordingly.

## Setup

Python 3.10+ recommended.

```bash
cd tmem
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If Matplotlib warns about a non-writable config directory (e.g. in sandboxes), use:

`export MPLCONFIGDIR=/path/to/writable/dir`

The first run downloads `sentence-transformers` weights for `all-MiniLM-L6-v2` (same encoder as the A-MEM paper, Section 4.2).

## Run

From this directory (`tmem/`):

```bash
python main.py
```

This builds ~30 synthetic memories over 10 sessions, auto-links notes with embedding cosine similarity \(>\) 0.5, runs A-MEM (pure cosine, \(\alpha=1\)) vs T-MEM (blended \(\alpha=0.7\) by default), and writes:

| Output | Description |
|--------|-------------|
| `results/comparison_table.csv` | Per-query ranks and ground-truth score components |
| `results/retrieval_accuracy.png` | Per-category @1 and @3 accuracy |
| `results/decay_curves.png` | Illustrative decay / reinforcement curves |
| `results/score_breakdown.png` | Cosine vs temporal blend for the work query |
| `results/summary_stats.txt` | Aggregate win/tie/loss counts |

## Package layout

- `tmem/memory_note.py` — note structure matching paper Eq. 1 + temporal fields  
- `tmem/temporal_scoring.py` — temporal decay (+ optional reinforce × link); see `use_decay_only_temporal`  
- `tmem/retrieval.py` — `amem_retrieve()` (Eq. 9) and `tmem_retrieve()` (modified Eq. 9)  
- `tmem/config.py` — \(\lambda, \beta, \gamma, \alpha\) defaults  
- `simulation/` — synthetic bank, queries, comparison driver  
- `visualization/plots.py` — matplotlib figures  

## Hyperparameters

Defaults: \(\lambda=0.1\), \(\alpha=0.7\), **decay-only** temporal term (`use_decay_only_temporal=True`). Set \(\alpha=1\) in `TMemConfig` to recover A-MEM ranking exactly. For reinforce + link factors, set `use_decay_only_temporal=False` and tune \(\beta,\gamma\).

Run decay checks: `python -m unittest tests.test_temporal_decay -v`
