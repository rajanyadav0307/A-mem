T-MEM presentation bundle
========================

This folder is a self-contained export for slides/posters.

**PPT_SLIDE_MATERIAL.txt** — long-form bullet lists, tables, and speaker-note
hints to copy into PowerPoint (equations, file map, queries, limitations).

Contents
--------
- comparison_table.csv   — per-query A-MEM vs T-MEM ranks and ground-truth score components
- summary_stats.txt      — win/tie/loss counts and per-category @1/@3 accuracy
- retrieval_accuracy.png — bar chart by LoCoMo-style category
- decay_curves.png       — illustrative decay / reinforcement curves
- score_breakdown.png    — cosine vs temporal blend for the "currently work" query
- snapshot.json          — same results + formulas + file map (machine-readable)
- T_MEM_Deck.pptx        — 11-slide PowerPoint (run build_deck.py to refresh)
- build_deck.py          — regenerates the deck from comparison_table.csv + PNGs

Regenerating
------------
From the tmem/ project root:

  export MPLCONFIGDIR="$(pwd)/.mpl"
  python main.py

Optional (offline / no Hugging Face): TMEM_ALLOW_HASH_ENCODER=1

For thesis numbers, omit TMEM_ALLOW_HASH_ENCODER so all-MiniLM-L6-v2 loads.

Also mirrored under results/ after each main.py run.

PowerPoint deck
----------------
After `pip install -r requirements.txt`:

  python presentation/build_deck.py

Edits the deck in place as presentation/T_MEM_Deck.pptx (pulls comparison_table.csv and PNGs from this folder).
