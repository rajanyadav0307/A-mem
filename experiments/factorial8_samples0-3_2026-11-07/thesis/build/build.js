// node build.js OUT.docx CAPTIONS.json USED.json   (env: FACTS SUMMARY EXTRA MANIFEST FIGDIR [MARK=1])
const fs = require("fs");
const { d, tables, figures, USED } = require("./lib");
const { Document, Packer, Footer, Paragraph, TextRun, AlignmentType, PageNumber } = d;
const ch3 = require("./ch3");
const ch4 = require("./ch4");

const doc = new Document({
  creator: "Rajan Yadav",
  title: "T-MEM thesis, Chapters III and IV",
  styles: {
    default: {
      document: { run: { font: "Times New Roman", size: 24, color: "000000" }, paragraph: { spacing: { line: 480, lineRule: "auto" } } },
    },
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 2160, right: 1440, bottom: 1440, left: 2160, header: 720, footer: 720 },
              pageNumbers: { start: 1 } },
    },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { line: 240, lineRule: "auto" },
      children: [new TextRun({ children: [PageNumber.CURRENT] })] })] }) },
    children: [...ch3, ...ch4],
  }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(process.argv[2], buf);
  fs.writeFileSync(process.argv[3], JSON.stringify({ tables, figures }, null, 1));
  fs.writeFileSync(process.argv[4], JSON.stringify(USED, null, 1));
  console.log("wrote", process.argv[2], "tables", tables.length, "figures", figures.length, "values", USED.length);
});
