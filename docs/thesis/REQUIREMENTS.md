# Thesis Requirements (reference note)

Written 2026-10-29, from reading these files in full:

| Source | Path | Notes |
|---|---|---|
| Thesis template | `/Users/rajanyadav/Desktop/Thesis/UTPB_Thesis_Template.docx` (md5 `7557f15b`, same as `docs/thesis/UTPB_Thesis_Template.docx`) | Text, styles, 1 table, captions, and one long comment with the formatting rules |
| UTPB style manual | `/Users/rajanyadav/Downloads/Graduate Thesis Style Manual 2021.pdf` (18 pages, revised 9.01.2021) | The template's rules come from this manual |
| Submitted mid-semester report | `/Users/rajanyadav/Desktop/Thesis/untitled folder/Thesis-Mid-Sem-Progress.docx` (same as `docs/thesis/T-MEM_Progress_Report.docx`) | Shows what has already been reported; the thesis must not contradict it |

---

## 1. Required order of parts (manual "Arrangement of contents"; template follows it)

| # | Part | Required? | Page number |
|---|---|---|---|
| 1 | Fly page (blank) | yes | not numbered |
| 2 | Signature page (title + "APPROVED BY SUPERVISORY COMMITTEE:", committee names) | yes | not numbered |
| 3 | Title page | yes | counted as i, number not printed |
| 4 | Copyright notice | optional (only if copyright is applied for) | ii |
| 5 | Dedication | optional | roman |
| 6 | Acknowledgments (max one page) | optional; **required** if support came from outside UTPB | roman |
| 7 | Abstract (**max 150 words**, states the purpose) | yes | roman |
| 8 | Table of contents | yes | roman |
| 9 | Lists of tables / figures | only if there are tables/figures | roman |
| 10 | Chapters | yes | arabic from Chapter I |
| 11 | References | yes | arabic |
| 12 | Appendices | optional | arabic |
| 13 | Glossary | optional | |
| 14 | Curriculum vita | optional | |

**Conflict to resolve:** the manual's list and sample put appendices **after** references, but its Appendix paragraph says **before**. The template points this out and says to confirm with the Graduate Studies Office.

## 2. Formatting rules (manual + template comment)

- **Type:** Times New Roman 12 pt, one typeface everywhere (tables and figures too). No headline, script or novelty fonts.
- **Spacing:** double-spaced, standard paragraph indent, no extra space between paragraphs (Body Text style). Widow and orphan control on. No large white spaces inside chapters. **No running heads.**
- **Margins:** left 1.5 in, right 1 in, bottom 1 in, top 1.5 in (**2 in** on pages with a major heading).
- **Page numbers:** bottom center, 0.5 in from the edge. Lowercase roman in the front matter; arabic from Chapter I.
- **Major divisions** (chapters, references, appendices) start on a new page: "CHAPTER" + capital roman numeral, centered 2 in from the top; triple space; title in ALL CAPS, centered, not bold, no period; long titles as an inverted pyramid. This is built into the ChapterNumber and ChapterTitle styles.
- **Subheadings:** Computer Science is not listed in the manual, so the fallback is **Turabian** (confirm with the chair). Template: Level 1 = Heading 2 (flush left, bold), Level 2 = Heading 3 (flush left, bold italic). Only chapter titles and major divisions are ALL CAPS. Double spacing before and after subheadings.
- **Tables and figures:** same typeface as the body. A table may be reduced but its caption may not. Never on facing pages. Full citations for borrowed material. Statistical symbols (*N*, *p*, *R*) in italics. Captions via References > Insert Caption so the lists update. The template caption style is "Table 1. …" and "Figure 1. …".
- **The file must stay in Word Compatibility Mode.** Don't convert it, or major headings lose the 0.5 in spacing.
- **Title page wording:** "Presented to the Graduate Faculty of Computer Science of The University of Texas Permian Basin in Partial Fulfillment of Requirements for the Degree of MASTER OF SCIENCE". The template comment says to confirm the exact department name and degree.

## 3. Writing-style rules

From the manual:
- One author: **do not use "we" or "our"**. Use "I" only when needed.
- **No future tense** for the method ("This project will examine…"). The thesis is a finished argument.
- No Mr., Ms., Dr. or Professor in the text; use last names or full names.
- Avoid he/him for people in general; plurals preferred; "s/he" is not allowed.
- Numbers under 10 are spelled out, except where the style guide differs. A number that starts a sentence is spelled out. Use "10%", not "10 percent".
- Every work cited in the text must be in the references, and every reference must be cited.

From the write-like-human skill and Wikipedia "Signs of AI writing":
- Vary sentence length; avoid uniform 18–24-word sentences.
- No inflated significance ("pivotal", "testament", "stands as"), no promotional words, and no vague attribution ("experts argue").
- None of the banned words: delve, crucial, pivotal, tapestry, underscore, showcase, intricate, foster, landscape (as a metaphor), seamless, realm, multifaceted, paramount, vibrant, embark, catalyst, overarching.
- No "not just X, but Y"; no "-ing" tails that add significance; no "from X to Y" false ranges; no "Furthermore / Moreover / Additionally / In conclusion" openers.
- No rule-of-three habit. No bolded inline headers in lists. No overuse of bold. No Title Case in body headings beyond what the template sets.
- No "Despite these challenges…" upbeat endings; end on the concrete next step or the open problem.
- Academic register: no contractions, but varied clause structure. State precise limits instead of general praise.
- Fix the substance, not just the surface: every claim must be accurate and sourced.

## 4. Content required, chapter by chapter (from the template's placeholders)

| Chapter / section | Template asks for |
|---|---|
| Abstract | ≤150 words: purpose, method, main result, what it means |
| **I Introduction** | Opening context paragraph · Background and Motivation (why LLM agents need memory; why freshness matters) · Problem Statement (what A-MEM does not handle: time, repeated facts, changing facts) · Research Questions · Contributions (temporal retrieval, consolidation, conflict handling) · Scope and Limitations · Organization of the Thesis |
| **II Background and Related Work** | Intro · Memory in LLM Agents · A-MEM (notes, links, evolution, embedding retrieval) · Temporal Reasoning in Retrieval (recency, decay, time-aware retrieval) · Memory Consolidation · Conflict Handling and Timelines (incl. timeline and temporal-graph work) · Benchmarks (LoCoMo and related) · Research Gap |
| **III The T-MEM Framework** | Overview of the three modules · Design Overview (on top of A-MEM) · Temporal Retrieval, with Semantic-First Reranking and Category-Selective Temporal Scoring · **Two-Date Timeline Labels** (said on / happened) · Memory Consolidation (verify and merge) · Conflict Handling (detect, annotate, demote) |
| **IV Implementation** | Intro · System Architecture (components, data flow) · Integration with the A-MEM Pipeline · Tools and Environment (language, models, embedding model, libraries **actually used**) |
| **V Experimental Setup** | Intro · Dataset (LoCoMo samples used, question counts) · Question Categories (each category and counts) · Evaluation Metrics (F1 and others) · Systems Compared (A-MEM, each T-MEM variant, references) · Experimental Protocol (seeds, repeated runs, averaging) |
| **VI Results** | In the order of the research questions · Temporal Retrieval · Consolidation · Conflict Handling · End-to-End A-MEM vs T-MEM, with **Table 1 "Overall and Category 2 F1 by System"** and **Figure 1 "Overview of the T-MEM Retrieval Pipeline"**, each referred to in the text before it appears |
| **VII Discussion** | Interpretation of Findings · Error Analysis (where T-MEM helps and where not) · Limitations · Threats to Validity (sample size, model choice, other risks) |
| **VIII Conclusion and Future Work** | Restate the problem and findings · Summary of Contributions · Future Work |
| References | Template shows 5 example IEEE-style entries; the comment says "**Check every detail before you submit**" |
| Appendix A | Prompt templates |
| Appendix B | Additional results |
| Glossary | Example entries A-MEM, F1, LLM |
| Curriculum vita | Brief academic and professional history |

**Placeholders the template gives:** `[PRIOR DEGREE, e.g., B.S.]`, `[Month Year of graduation]`, `Copyright [Year]`, `[Dedication text]`, committee names (Chair, two members, Graduate Faculty Representative). These are personal or administrative facts and can't be found in the project files.

## 5. Things already noticed that need care

- **Template reference [5] looks wrong.** It reads "S. Kim et al., Theanine: Revisiting memory management in long-term conversations with timeline-augmented response generation, arXiv:2406.10996". The NAACL 2025 version of arXiv 2406.10996 is "Towards Lifelong Dialogue Agents via Timeline-based Memory Management" by Ong et al. The first author must be verified against arXiv and the ACL Anthology before use.
- **Reference [1], A-MEM:** the template cites arXiv only. Thesis-1 cites the NeurIPS 2025 version. To be verified.
- **Two Thesis-1 candidates differ:** `Thesis1-RajanYadav.pdf` (title "T-MEM: **Toward** Temporal-Aware…", student email ending r30680) and `Thesis-5.pdf` (title without "Toward", email ending r77867). The abstract wording and some content also differ.
- **Already reported numbers must stay consistent.** The mid-semester report gives Tables 1–9. The thesis must either use the same verified numbers or explain any difference.
