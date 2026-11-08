"""Plain-text copy of a built chapters.docx (paragraphs and table rows), for reviewers.  python3 totext.py FILE.docx"""
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
body = ET.fromstring(zipfile.ZipFile(sys.argv[1]).read("word/document.xml")).find(W + "body")
for el in body:
    if el.tag == W + "p":
        t = "".join(x.text or "" for x in el.iter(W + "t"))
        if t.strip():
            print(t + "\n")
    elif el.tag == W + "tbl":
        for tr in el.iter(W + "tr"):
            print(" | ".join("".join(x.text or "" for x in tc.iter(W + "t")) for tc in tr.iter(W + "tc")))
        print()
