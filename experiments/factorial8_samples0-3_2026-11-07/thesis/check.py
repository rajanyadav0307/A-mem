"""Machine checks on the built chapters (no network, no AI).

  python3 check.py OUTDIR

OUTDIR holds chapters.docx, chapters_marked.docx and used_marked.json from build/make.sh.
Checks (each prints PASS or FAIL with the offending text):
  V1  the marked and plain builds have the same text once the markers are removed
  V2  every marked value was registered by the build (lib.js val())
  V3  after removing every inserted value, no digit is left except in identifiers on the allowlist
  V4  after removing every inserted value, no counting word is left except phrases on the allowlist
  V5  the chapter code passes no hand-typed number to V(), cnt(), num() or val()
  F*  UTPB format rules read from the document XML
  S*  structure: numbering and order of tables, figures and equations; headings
  H*  writing tells from the humanizer skill
Exit status 1 if any check fails.
"""
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
fails = 0


def report(code, ok, msg, items=()):
    global fails
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'} {code} {msg}")
    for it in list(items)[:40]:
        print("      ", it)


def paragraphs(path):
    """[(kind, text)] in document order; kind is 'p', 'cell', 'eq' (a paragraph with an equation tab layout)."""
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    out = []

    def ptext(pel):
        s = ""
        for r in pel.iter(W + "r"):
            rpr = r.find(W + "rPr")
            sub = rpr is not None and rpr.find(W + "vertAlign") is not None and rpr.find(W + "vertAlign").get(W + "val") == "subscript"
            for ch in r:
                if ch.tag == W + "t":
                    s += ("_{" + (ch.text or "") + "}") if sub else (ch.text or "")
                elif ch.tag == W + "tab":
                    s += "\t"
                elif ch.tag == W + "br":
                    s += "\n"
        return s

    for el in body:
        if el.tag == W + "p":
            tabs = el.find(f"{W}pPr/{W}tabs")
            kind = "eq" if tabs is not None and any(t.get(W + "val") == "center" for t in tabs) else "p"
            out.append((kind, ptext(el), el))
        elif el.tag == W + "tbl":
            for tc in el.iter(W + "tc"):
                for pel in tc.iter(W + "p"):
                    out.append(("cell", ptext(pel), pel))
    return out, root, z


plain, proot, pz = paragraphs(os.path.join(OUT, "chapters.docx"))
marked, mroot, mz = paragraphs(os.path.join(OUT, "chapters_marked.docx"))
used = json.load(open(os.path.join(OUT, "used_marked.json")))

# ---------------------------------------------------------------- V1, V2
a = [t for _, t, _ in plain]
b = [t.replace("⟦", "").replace("⟧", "") for _, t, _ in marked]
report("V1", a == b, "plain build = marked build without markers", [f"{x!r} != {y!r}" for x, y in zip(a, b) if x != y])
reg = {u["value"] for u in used}
spans = [m for _, t, _ in marked for m in re.findall(r"⟦(.*?)⟧", t, re.S)]
bad = [s for s in spans if s not in reg]
report("V2", not bad and len(spans) > 0, f"{len(spans)} inserted values, all registered by the build", bad)

# ---------------------------------------------------------------- V3 digits
ID = [
    r"\bTable \d+\b", r"\bTables \d+ and \d+\b", r"\bFigure \d+\b", r"\bEquation \d+\b", r"\bChapter (III|IV|V)\b",
    r"\bRQ[1-5](–RQ[1-5])?\b", r"\bH[1-3]_\{0\}", r"\bR(1[01]|[0-9])\b", r"\bB[1-5]\b", r"\bB1–B", r"\bs[1-8]\b", r"\bs[1-8]–s[1-8]\b",
    r"\b[Ss]amples? [0-3]\b", r"\b[Cc]ategor(y|ies) [1-5](–[1-5])?\b", r"\b[Cc]at\. [1-5]\b", r"gpt-4o-mini",
    r"\b[Ww]ave 1\b", r"\bWaves 2–", r"\bStages? [0-7](–)?", r"\bF1\b", r"\bBLEU-1\b", r"\bSHA-256\b",
    r"\(\d\)$",                                                    # equation number at the end of an equation line
    r"^\d\.\t",                                                    # list item numbers
    r"\b1 if it is a refusal and 0 otherwise\b",                   # scoring rule of analyze.py: float(refusal)
    r"plus 1/",                                                    # p formula of analyze.py: + 1 / REPS
]
# citation years: exactly the citations used in the chapters
CITES = ["W. Xu et al., 2025", "Montgomery, 2017", "Reimers & Gurevych, 2017", "Maharana et al., 2024", "Maharana et al. (2024)", "OpenAI, 2024",
         "Reimers & Gurevych, 2019", "W. Wang et al., 2020", "Yadav & Kumar, 2026", "Lin, 2004", "Papineni et al., 2002", "Banerjee & Lavie, 2005",
         "Zhang et al., 2020", "Montgomery (2017)", "Efron & Tibshirani, 1993", "Koehn, 2004", "Dror et al., 2018", "Holm (1979)"]
ID += [re.escape(c) for c in CITES]
ID_RE = re.compile("|".join(f"(?:{x})" for x in ID), re.M)
left = []
for kind, t, _ in marked:
    s = re.sub(r"⟦.*?⟧", "§", t, flags=re.S)
    if kind == "eq":
        continue                                                   # equations: structural constants, reviewed by hand
    s2 = ID_RE.sub("", s)
    for m in re.finditer(r"\d", s2):
        left.append(f"{kind}: …{s2[max(0, m.start() - 50):m.end() + 30]}…")
report("V3", not left, "no typed digit outside identifiers", left)

# ---------------------------------------------------------------- V4 counting words
COUNT = r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|hundred|thousand|once|twice|thrice|half|halves|dozen|single)\b"
ALLOW = json.load(open(os.path.join(HERE, "allowed_count_words.json")))
left = []
for kind, t, _ in marked:
    s = re.sub(r"⟦.*?⟧", "§", t, flags=re.S)
    for ph in ALLOW:
        s = s.replace(ph["phrase"], "")
    for m in re.finditer(COUNT, s, re.I):
        left.append(f"{kind}: …{s[max(0, m.start() - 60):m.end() + 40]}…")
report("V4", not left, f"no counting word outside {len(ALLOW)} allowlisted phrases", left)
unused = [ph["phrase"] for ph in ALLOW if not any(ph["phrase"] in re.sub(r"⟦.*?⟧", "§", t, flags=re.S) for _, t, _ in marked)]
report("V4b", not unused, "every allowlisted phrase occurs in the text", unused)

# ---------------------------------------------------------------- V5 typed numbers in code
WORDING = {"none", "no", "No", "Yes", "half", "once", "T-MEM", "A-MEM"}   # words chosen by a must() guard just before


def first_arg(src, start):
    depth, i, q = 0, start, None
    while i < len(src):
        c = src[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return src[start:i]
            depth -= 1
        elif c == "," and depth == 0:
            return src[start:i]
        i += 1
    return src[start:]


left = []
for fn in ("ch3.js", "ch4.js"):
    src = open(os.path.join(HERE, "build", fn)).read()
    for m in re.finditer(r"(?<![\w.])(V|cnt|num|val)\(", src):
        arg = first_arg(src, m.end()).strip()
        line = src.count("\n", 0, m.start()) + 1
        code = re.sub(r"(\"[^\"]*\"|'[^']*'|`[^`]*`)", "S", arg)        # string literals out of the way
        # formatting constants, not data: array indexes, decimal places, percent scaling, last index
        code = re.sub(r"\[\s*\d+\s*\]|,\s*\d\s*\)|\b100\s*\*|toFixed\(\d\)|length - 1|/\^0/|[<>]=?\s*0\b", "", code)
        if re.search(r"(?<![\w.])\d+(\.\d+)?(?![\w])", code) and not re.fullmatch(r".*\b(1000|1e-9)\b.*", code):
            left.append(f"{fn}:{line}: number literal in {arg[:80]}")
        lit = re.fullmatch(r"\"([^\"]*)\"|'([^']*)'", arg)
        if lit and (lit.group(1) or lit.group(2) or "") not in WORDING:
            left.append(f"{fn}:{line}: text literal {arg[:80]}")
report("V5", not left, "no hand-typed number (and no unexplained text) passed to V/cnt/num/val", left)

# ---------------------------------------------------------------- V6 equations equal the analysis code
import random as _r
src_an = open(os.path.join(HERE, "..", "scripts", "analyze.py")).read()
ns = {"S": ["s1_amem", "s2_t", "s3_c", "s4_h", "s5_tc", "s6_th", "s7_ch", "s8_tch"]}
exec(re.search(r"def contrast_values\(q, kind\):.*?(?=\n\S)", src_an, re.S).group(0), ns)
eqs = [t for k, t, _ in plain if k == "eq"]
body_txt = " ".join(t for k, t, _ in plain if k == "p")
want = {"T": next(e for e in eqs if e.strip().startswith("T =")), "TxC": next(e for e in eqs if e.strip().startswith("T × C ="))}
want["TxCxH"] = "T × C × H = " + re.search(r"with H off: (\[.*?\] − \[.*?\])", body_txt).group(1)
bad = []
for kind, text in want.items():
    expr = text.split("=", 1)[1].rsplit("(", 1)[0] if kind != "TxCxH" else text.split("=", 1)[1]
    expr = expr.replace("−", "-").replace("[", "(").replace("]", ")").strip()
    expr = re.sub(r"s([1-8])", r"v[\1-1]", expr)
    for _ in range(20):
        v = [_r.random() for _ in range(8)]
        q = {s: v[i] for i, s in enumerate(["s1_amem", "s2_t", "s3_c", "s4_h", "s5_tc", "s6_th", "s7_ch", "s8_tch"])}
        try:
            got = eval(expr, {"v": v})
            ref = ns["contrast_values"](q, kind)
        except Exception as e:                                    # noqa: BLE001
            bad.append(f"{kind}: {e}")
            break
        if abs(got - ref) > 1e-12:
            bad.append(f"{kind}: chapter formula differs from analyze.py ({got} vs {ref})")
            break
report("V6", not bad, "Equations of T and T × C and the three-way formula equal analyze.py contrast_values", bad)

# ---------------------------------------------------------------- F: UTPB format
st = ET.fromstring(pz.read("word/styles.xml"))
rpr = st.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")
fonts = rpr.find(W + "rFonts")
report("F1", fonts is not None and fonts.get(W + "ascii") == "Times New Roman" and rpr.find(W + "sz").get(W + "val") == "24",
       "default font Times New Roman 12 pt")
ppr = st.find(f"{W}docDefaults/{W}pPrDefault/{W}pPr")
report("F2", ppr.find(W + "spacing").get(W + "line") == "480", "default line spacing double")
report("F3", ppr.find(W + "widowControl") is not None, "widow and orphan control on")
sect = proot.find(f"{W}body/{W}sectPr")
mar = sect.find(W + "pgMar")
pg = sect.find(W + "pgSz")
report("F4", (mar.get(W + "top"), mar.get(W + "left"), mar.get(W + "right"), mar.get(W + "bottom")) == ("2160", "2160", "1440", "1440")
       and (pg.get(W + "w"), pg.get(W + "h")) == ("12240", "15840"), "Letter page; margins top/left 1.5 in, right/bottom 1 in")
fonts_used = {f.get(W + "ascii") for f in proot.iter(W + "rFonts")} - {None}
report("F5", fonts_used <= {"Times New Roman"}, "no other font in the text", sorted(fonts_used))
cell_sizes = set()
for tbl in proot.iter(W + "tbl"):
    for r in tbl.iter(W + "r"):
        sz = r.find(f"{W}rPr/{W}sz")
        cell_sizes.add(sz.get(W + "val") if sz is not None else None)
report("F6", cell_sizes == {"22"}, "table text 11 pt", sorted(map(str, cell_sizes)))
# captions: "Table N" bold, line break, italic title; "Figure N." bold then italic caption
capbad = []
for _, t, el in plain:
    if re.match(r"^Table \d+\n", t):
        rs = list(el.iter(W + "r"))
        if not (rs[0].find(f"{W}rPr/{W}b") is not None and all(r.find(f"{W}rPr/{W}i") is not None for r in rs[2:])):
            capbad.append(t[:40])
    if re.match(r"^Figure \d+\. ", t):
        rs = list(el.iter(W + "r"))
        if rs[0].find(f"{W}rPr/{W}b") is None or rs[1].find(f"{W}rPr/{W}i") is None:
            capbad.append(t[:40])
report("F7", not capbad, "table and figure captions formatted", capbad)
# italic statistical p
pbad = []
for _, t, el in plain:
    for r in el.iter(W + "r"):
        tx = "".join((x.text or "") for x in r.iter(W + "t"))
        if re.search(r"(?<![A-Za-z\-])p(?= [=<]|-value)", tx) or (re.search(r"Holm p\b", tx) and not tx.strip() == "p"):
            if r.find(f"{W}rPr/{W}i") is None:
                pbad.append(tx[:60])
report("F8", not pbad, "statistical p in italics", pbad)
report("F9", not any("\t" in (x.text or "") for x in proot.iter(W + "t")), "no literal tab characters inside text runs")

# ---------------------------------------------------------------- S: structure
texts = [t for _, t, _ in plain]
full = "\n".join(t for k, t, _ in plain if k != "cell")
tnums = [int(m.group(1)) for t in texts for m in [re.match(r"^Table (\d+)\n", t)] if m]
fnums = [int(m.group(1)) for t in texts for m in [re.match(r"^Figure (\d+)\. ", t)] if m]
enums = [int(m.group(1)) for k, t, _ in plain if k == "eq" for m in [re.search(r"\((\d+)\)$", t)] if m]
report("S1", tnums == list(range(3, 3 + len(tnums))), f"tables numbered {tnums[0]}–{tnums[-1]} in order", [tnums])
report("S2", fnums == list(range(1, 1 + len(fnums))), f"figures numbered 1–{len(fnums)} in order")
report("S3", enums == list(range(1, 1 + len(enums))), f"equations numbered 1–{len(enums)} in order")
# every table/figure/equation is mentioned in the running text, first mentions in order, before the object
body = [(k, t) for k, t, _ in plain if k == "p" and not re.match(r"^(Table \d+\n|Figure \d+\. )", t)]
order_bad = []
for kind, nums in (("Table", tnums), ("Figure", fnums), ("Equation", enums)):
    first = {}
    for i, (_, t) in enumerate(body):
        for m in re.finditer(rf"\b{kind}s? (\d+)(?: and (\d+))?", t):
            for g in m.groups():
                if g and int(g) not in first:
                    first[int(g)] = i
    missing = [n for n in nums if n not in first]
    seq = [first[n] for n in nums if n in first]
    if missing:
        order_bad.append(f"{kind} never mentioned in the text: {missing}")
    if seq != sorted(seq):
        order_bad.append(f"{kind} first mentions out of order: {[(n, first.get(n)) for n in nums]}")
report("S4", not order_bad, "every table, figure and equation mentioned in the text, first mentions in order", order_bad)
# headings: level 1 centered bold; no level-1 section with exactly one level-2 subheading
heads = []
for _, t, el in plain:
    if el.tag != W + "p":
        continue
    rs = list(el.iter(W + "r"))
    if rs and all(r.find(f"{W}rPr/{W}b") is not None for r in rs) and not re.match(r"^(Table|Figure) \d", t) and "\n" not in t and len(t) < 90:
        jc = el.find(f"{W}pPr/{W}jc")
        heads.append((("1" if jc is not None and jc.get(W + "val") == "center" else "2"), t))
single = []
for i, (lv, t) in enumerate(heads):
    if lv == "1":
        subs = []
        for lv2, t2 in heads[i + 1:]:
            if lv2 == "1":
                break
            subs.append(t2)
        if len(subs) == 1:
            single.append(f"{t} → {subs}")
report("S5", not single, "no level-1 heading with a single level-2 subheading", single)

# ---------------------------------------------------------------- N: APA number style
start = []
for kind, t, _ in plain:
    if kind != "p":
        continue                                                   # table cells and equations hold values, not sentences
    for m in re.finditer(r"(?:^|[.!?]\s+)(\d[\d,.]*)\s", t):
        if not re.match(r"^\d\.\t", t[m.start():] if m.start() == 0 else ""):
            start.append(f"{kind}: …{t[max(0, m.start() - 20):m.end() + 30]}…")
report("N1", not start, "no sentence starts with a numeral", start)
small = []
for kind, t, _ in marked:
    if kind != "p":
        continue
    for m in re.finditer(r"⟦(\d)⟧(?![%.,]\d|%)", t):
        # APA exceptions: factorial notation, labels (category N, seed N), and numbers compared with 10 or more
        sent_start = max(t.rfind(". ", 0, m.start()), 0)
        sent_end = t.find(". ", m.end()); sent_end = len(t) if sent_end < 0 else sent_end
        sent = t[sent_start:sent_end]
        ctx_b, ctx_a = t[max(0, m.start() - 12):m.start()], t[m.end():m.end() + 3]
        if (ctx_a.startswith(" ×") or ctx_b.endswith("× ") or ctx_b.endswith("category ") or ctx_b.endswith("seed (")
                or re.search(r"[Ss]amples? $", ctx_b) or ctx_b.endswith("–") or ctx_a.startswith("–") or ctx_b.endswith("Stages ") or ctx_b.endswith("–B")):
            continue
        if any(int(x.replace(",", "")) >= 10 for x in re.findall(r"⟦(\d[\d,]*)⟧", sent)):
            continue
        before = re.sub(r"⟦.*?⟧", "§", t[max(0, m.start() - 40):m.start()])
        small.append(f"…{before}[{m.group(1)}]{re.sub(r'⟦.*?⟧', '§', t[m.end():m.end() + 30])}…")
report("N2", not small, "counts below 10 in running text are written as words (APA), unless compared with 10 or more", small)

# ---------------------------------------------------------------- H: humanizer tells
prose = [(k, t) for k, t, _ in plain if k == "p"]
em = [t[:80] for k, t in prose if "—" in t]
report("H1", not em, "no em dashes in running text", em)
en = [f"…{t[max(0, m.start() - 20):m.end() + 20]}…" for k, t in prose for m in re.finditer(r"\s–|–\s", t)]
report("H2", not en, "en dashes only inside ranges or compounds", en)
STOCK = r"\b(delve|crucial|pivotal|underscore[sd]?|showcas\w*|tapestry|testament|meticulous\w*|vibrant|intricate|garner\w*|landscape|additionally|enhanc\w+|robust(?!\" implementation)|interplay|bolster\w*|quietly|valuable|(?<!API )key (?=[a-z]))\b"
st_hits = [f"…{t[max(0, m.start() - 30):m.end() + 30]}…" for k, t in prose for m in re.finditer(STOCK, t, re.I)]
report("H3", not st_hits, "no stock AI words", st_hits)
NX = r"\b(not just|not only|not merely|it's not|this is not about|let's|here's|to be clear|at its core|in reality|the real question)\b"
nx = [f"…{t[max(0, m.start() - 30):m.end() + 30]}…" for k, t in prose for m in re.finditer(NX, t, re.I)]
report("H4", not nx, "no staged contrasts or run-ups", nx)

print(f"\n{'ALL CHECKS PASSED' if fails == 0 else f'{fails} CHECK(S) FAILED'}")
sys.exit(1 if fails else 0)
