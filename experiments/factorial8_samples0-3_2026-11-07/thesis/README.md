# Thesis Chapters III and IV, built from the source of truth

Chapters III (Methodology) and IV (Results) are built by code. No number is typed into the text.

## Steps

1. **Facts.** `facts.py` reads every fact the chapters need from the source of truth and writes `facts.json`. The sources are:
   - this experiment folder: manifest, plan, checks, results, `analysis/summary.json`, `analysis/extra.json`, build logs, local logs and banks
   - `data/locomo10.json`
   - the code at the frozen commit
   - git

   Each fact records where it was read. The script is run twice and the two outputs must be byte-identical.

   ```bash
   HF_HUB_OFFLINE=1 .venv/bin/python experiments/factorial8_samples0-3_2026-11-07/thesis/facts.py facts.json
   ```

2. **Build.** `build/make.sh FACTS.json OUTDIR` draws the figures and writes two builds:
   - `chapters.docx`, the deliverable
   - `chapters_marked.docx`, in which every inserted value is wrapped in ⟦ ⟧

   Values enter the text only through the functions in `build/lib.js`, which read `facts.json`, `analysis/summary.json` and `analysis/extra.json`. Every sentence in Chapter IV that states a result is guarded by `must()`. If the data do not support the sentence, the build stops.

   ```bash
   NODE_PATH=<node_modules with docx@9> experiments/factorial8_samples0-3_2026-11-07/thesis/build/make.sh facts.json out
   ```

3. **Machine checks.** `check.py OUTDIR`:
   - V1–V5: no hand-typed number. After every inserted value is removed from the marked build, no digit is left outside identifiers, and no counting word is left outside `allowed_count_words.json`. Each allowlisted phrase has a reason.
   - N1–N2: APA number style.
   - F1–F9: UTPB format.
   - S1–S5: numbering and order of tables, figures and equations.
   - H1–H4: writing tells from the humanizer skill.

   ```bash
   python3 experiments/factorial8_samples0-3_2026-11-07/thesis/check.py out
   ```

4. **Independent recount.**
   - `verify/recompute.py` recomputes every Chapter IV result from the 40 raw result files without reading `summary.json`. It is run twice and the outputs must be identical.
   - `verify/compare.py` compares every table cell in the Word file with that recount, with the Stage 7 recount (`analysis/extra_recount.json`), with its own recount of the Chapter III tables, and with the check files.

   ```bash
   .venv/bin/python experiments/factorial8_samples0-3_2026-11-07/thesis/verify/recompute.py recomputed.json
   .venv/bin/python experiments/factorial8_samples0-3_2026-11-07/thesis/verify/compare.py out/chapters.docx recomputed.json
   ```

5. **Review.** Fresh reviewers check every claim against its source; the `src` comments in `build/ch3.js` give the source of each paragraph. Any finding is fixed in the code. Then everything is rebuilt and every check is re-run.
