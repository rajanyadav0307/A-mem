// Formatting helpers for the UTPB thesis format (Times New Roman 12 pt, double spacing,
// 1.5" top/left margins, APA-style tables) and the single route by which values enter the text.
//
// Every number or quoted value in Chapters III and IV must enter through val(), which records it.
// With MARK=1 each inserted value is wrapped in ⟦ ⟧, so a checker can remove every inserted value
// from the marked build and confirm that no number is left that was typed into the chapter code.
const fs = require("fs");
const d = require("docx");
const { Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, BorderStyle,
        ImageRun, TabStopType, PageBreak, Tab } = d;

const MARK = process.env.MARK === "1";
const FACTS = JSON.parse(fs.readFileSync(process.env.FACTS));
const USED = [];
function val(s, from) {
  const v = String(s);
  USED.push({ value: v, from });
  return MARK ? `⟦${v}⟧` : v;
}
function fact(k) {
  if (!(k in FACTS)) throw new Error(`missing fact ${k}`);
  return FACTS[k].value;
}
// round half away from zero (the same rule for every number in both chapters)
const rnd = (x, dp) => {
  const v = Math.floor(Math.abs(x) * 10 ** dp + 0.5 + 1e-9) / 10 ** dp;
  return (x < 0 && v !== 0 ? -v : v).toFixed(dp);
};
const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];
// APA: words for zero to nine, digits from 10 (with thousands separators)
const asCount = (x) => {
  if (!Number.isInteger(x)) throw new Error(`not an integer: ${x}`);
  return x >= 0 && x <= 9 ? WORDS[x] : x.toLocaleString("en-US");
};
const cap = (s) => s[0].toUpperCase() + s.slice(1);

// fact formatters
const N = (k) => val(Number(fact(k)).toLocaleString("en-US"), k);                 // number in digits
const W = (k) => val(asCount(fact(k)), k);                                          // count, words below 10
const Wc = (k) => val(cap(asCount(fact(k))), k);                                   // same, capitalized
const D = (k, dp) => val(rnd(fact(k), dp), k);                                      // fixed decimals
const P = (k, dp) => val(rnd(fact(k), dp) + "%", k);                                // percentage value
const X = (k) => { const v = fact(k); if (typeof v !== "string") throw new Error(`not text: ${k}`); return val(v, k); };
// a value computed in the chapter code from facts, summary.json or extra.json
const V = (s, from) => val(s, from);

// Markup inside strings: **bold**, *italic*, ~subscript~; the statistical symbol p is set in italics.
const PSYM = /((?<![A-Za-z\-])p(?= [=<])|(?<=Holm )p\b)/;
function plain(text, base, out) {
  text.split(PSYM).forEach((part, i) => {
    if (!part) return;
    if (i % 2 === 1) out.push(new TextRun({ text: part, ...base, italics: true }));
    else out.push(new TextRun({ text: part, ...base }));
  });
}
function runs(text, base = {}) {
  const out = [];
  text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|~[^~]+~)/).forEach((part) => {
    if (!part) return;
    if (part.startsWith("**")) out.push(new TextRun({ text: part.slice(2, -2), bold: true, ...base }));
    else if (part.startsWith("*")) out.push(new TextRun({ text: part.slice(1, -1), italics: true, ...base }));
    else if (part.startsWith("~")) out.push(new TextRun({ text: part.slice(1, -1), subScript: true, ...base }));
    else plain(part, base, out);
  });
  return out;
}
const TAB = () => new TextRun({ children: [new Tab()] });

let tableNo = 3, figureNo = 1, eqNo = 1;   // Chapters I-II hold Tables 1-2 and no figures or equations
const tables = [], figures = [];
const REFS = {};   // equation and table numbers set in Chapter III and read in Chapter IV

const chapter = (num, title) => [
  new Paragraph({ children: [new TextRun(`CHAPTER ${num}`)], alignment: AlignmentType.CENTER, pageBreakBefore: true, keepNext: true, spacing: { before: 720 } }),
  new Paragraph({ children: [new TextRun(title)], alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 240 } }),
];
const h1 = (t) => new Paragraph({ children: [new TextRun({ text: t, bold: true })], alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 240 } });
const h2 = (t) => new Paragraph({ children: [new TextRun({ text: t, bold: true })], keepNext: true, spacing: { before: 240 } });
const p = (t) => new Paragraph({ children: runs(t), indent: { firstLine: 720 } });
const item = (n, t) => new Paragraph({ children: [new TextRun(`${n}.`), TAB(), ...runs(t)],
  tabStops: [{ type: TabStopType.LEFT, position: 1080 }], indent: { left: 1080, hanging: 360 } });
function eq(text) {
  const n = eqNo++;
  return [new Paragraph({ children: [TAB(), ...runs(text), TAB(), new TextRun(`(${n})`)],
    tabStops: [{ type: TabStopType.CENTER, position: 4320 }, { type: TabStopType.RIGHT, position: 8640 }] }), n];
}
const note = (t) => new Paragraph({ children: [new TextRun({ text: "Note.", italics: true }), new TextRun(" "), ...runs(t)],
  spacing: { before: 60, after: 240, line: 240, lineRule: "auto" } });

// APA-style table: rules above and below the header row and below the last row; 11 pt, single spaced.
function table(title, header, rows, widths, noteText) {
  const n = tableNo++; tables.push([n, title]);
  const total = widths.reduce((a, b) => a + b, 0);
  const rule = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const cell = (text, w, top, bottom) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: { top: top ? rule : none, bottom: bottom ? rule : none, left: none, right: none },
    children: [new Paragraph({ children: runs(String(text), { size: 22 }), keepNext: true, run: { size: 22 }, spacing: { line: 240, lineRule: "auto" } })],
  });
  const trs = [new TableRow({ tableHeader: true, cantSplit: true, children: header.map((h, i) => cell(h, widths[i], true, true)) })];
  rows.forEach((r, ri) => {
    const last = ri === rows.length - 1;
    if (r.length !== header.length) throw new Error(`table ${n}: row ${ri} has ${r.length} cells`);
    trs.push(new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], false, last)) }));
  });
  const out = [
    new Paragraph({ children: [new TextRun({ text: `Table ${n}`, bold: true }), new TextRun({ break: 1 }), new TextRun({ text: title, italics: true })],
      keepNext: true, spacing: { before: 240, line: 240, lineRule: "auto" } }),
    new Table({ columnWidths: widths, width: { size: total, type: WidthType.DXA }, alignment: AlignmentType.CENTER, rows: trs,
      borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none },
      margins: { top: 20, bottom: 20, left: 80, right: 80 } }),
  ];
  if (noteText) out.push(note(noteText));
  else out.push(new Paragraph({ children: [], spacing: { after: 120, line: 240, lineRule: "auto" } }));
  return [out, n];
}
function figure(path, wIn, hIn, caption) {
  const n = figureNo++; figures.push([n, caption]);
  return [[
    new Paragraph({ children: [new ImageRun({ type: "png", data: fs.readFileSync(path), transformation: { width: wIn * 96, height: hIn * 96 },
      altText: { title: `Figure ${n}`, description: caption.replace(/[⟦⟧]/g, ""), name: `Figure ${n}` } })],
      alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 240, line: 240, lineRule: "auto" } }),
    new Paragraph({ children: [new TextRun({ text: `Figure ${n}. `, bold: true }), ...runs(caption, { italics: true })],
      spacing: { before: 120, after: 240, line: 240, lineRule: "auto" } }),
  ], n];
}
module.exports = { d, chapter, h1, h2, p, item, eq, note, table, figure, tables, figures, runs, PageBreak,
  fact, val, rnd, asCount, cap, N, W, Wc, D, P, X, V, USED, FACTS, REFS };
