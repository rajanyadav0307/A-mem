#!/bin/bash
# Build Chapters III and IV from the source of truth.
#   make.sh FACTS.json OUTDIR
# Writes OUTDIR/chapters.docx (the deliverable), OUTDIR/chapters_marked.docx (every inserted value
# wrapped in ⟦ ⟧, for the checks), captions, used values and figures. Needs node with the npm
# package docx (NODE_PATH) and the repository .venv for the figures.
set -euo pipefail
FACTS=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); OUT=$2
REPO=$(cd "$(dirname "$0")/../../../.." && pwd)
E=$REPO/experiments/factorial8_samples0-3_2026-11-07
B=$E/thesis/build
mkdir -p "$OUT/figs"
OUT=$(cd "$OUT" && pwd)
export FACTS SUMMARY=$E/analysis/summary.json EXTRA=$E/analysis/extra.json MANIFEST=$E/manifest.json FIGDIR=$OUT/figs
cd "$REPO" && .venv/bin/python "$B/make_figs.py" "$OUT/figs" "$FACTS" > /dev/null
cd "$B"
for kind in plain marked; do
  if [ $kind = marked ]; then export MARK=1; name=chapters_marked; else export MARK=0; name=chapters; fi
  node build.js "$OUT/${name}_raw.docx" "$OUT/captions_$kind.json" "$OUT/used_$kind.json"
  rm -rf "$OUT/wc" && mkdir "$OUT/wc" && (cd "$OUT/wc" && unzip -q "../${name}_raw.docx")
  python3 - "$OUT/wc/word/styles.xml" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
m = re.search(r'<w:pPrDefault>\s*<w:pPr>', s); assert m
s = s[:m.end()] + '<w:widowControl/>' + s[m.end():]
a = '<w:szCs w:val="24"/></w:rPr></w:rPrDefault>'; assert s.count(a) == 1
s = s.replace(a, '<w:szCs w:val="24"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>')
open(p, 'w').write(s)
PY
  rm -f "$OUT/$name.docx" && (cd "$OUT/wc" && zip -qXr "../$name.docx" '[Content_Types].xml' _rels docProps word)
  rm -rf "$OUT/wc" "$OUT/${name}_raw.docx"
done
python3 "$E/thesis/totext.py" "$OUT/chapters.docx" > "$OUT/chapters.txt"
echo "built $OUT/chapters.docx, $OUT/chapters_marked.docx and chapters.txt"
