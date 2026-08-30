# -*- coding: utf-8 -*-
"""Check the footnotes of each booklet reach the page.

The booklets number their footnotes 1..N without gaps, so the highest number
found in the PDF says how many there should be. Cover and contents pages are
skipped: their page numbers look like footnote markers.
"""
import sys, re, glob, os
sys.path.insert(0, "tools")
import convert as C
import structure as S

def first_content_page(texts):
    for i, t in enumerate(texts):
        for line in t.translate(C.BIDI).split("\n"):
            if S.is_section(line.strip()) and not S.DOT_LEADERS.search(line):
                return i
    return 0

def page_notes(key):
    for f in glob.glob("pages/*.html"):
        html = open(f, encoding="utf-8").read()
        if f"assets/pdf/{key}.pdf" in html:
            return os.path.basename(f), len(re.findall(r'<li id="[^"]*-n\d+"', html))
    return None, 0

def check(path):
    key = os.path.basename(path)[:-4]
    blocks = C.convert(path, per_page=True)
    texts = C.all_page_texts(path)
    start = first_content_page(texts)
    refs = set()
    for pno, page in blocks:
        if pno - 1 < start:
            continue
        for b in page:
            if b.startswith("<aside"):
                for ref, text in re.findall(r'<li data-ref="(\d+)">(.*?)</li>', b, re.S):
                    if not S.DOT_LEADERS.search(text):
                        refs.add(int(ref))
    top = 0
    while top + 1 in refs:
        top += 1
    name, on_page = page_notes(key)
    return key, top, sorted(r for r in refs if r > top), on_page

if __name__ == "__main__":
    for f in sorted(glob.glob("assets/pdf/*.pdf")):
        key, top, stray, on_page = check(f)
        flag = "" if on_page >= top and not stray else "   <-- check"
        print(f"{key:10} numbered in the PDF 1..{top:<4} on the page {on_page:<4}"
              f" stray={stray[:4]}{flag}")
