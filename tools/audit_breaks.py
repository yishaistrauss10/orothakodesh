# -*- coding: utf-8 -*-
"""Find paragraphs left broken across a page break.

A paragraph interrupted by a page break should be joined again. This reports
the ones that were not: the last paragraph of a page ends mid-sentence and the
next page opens with more of the same paragraph.
"""
import sys, re, glob, os
sys.path.insert(0, "tools")
import convert as C
import structure as S

TAG = re.compile(r"<[^>]+>")
CLOSED = re.compile(r"[.!?:;)\]״\"']\s*$|\.\.\.\s*$")

def first_content_page(texts):
    for i, t in enumerate(texts):
        for line in t.translate(C.BIDI).split("\n"):
            if S.is_section(line.strip()) and not S.DOT_LEADERS.search(line):
                return i + 1
    return 1


def check(path):
    pages = C.convert(path, per_page=True, joined=True)
    start = first_content_page(C.all_page_texts(path))
    rows = []
    prev_text, prev_page = None, None
    for pno, blocks in pages:
        if pno < start:
            continue
        paras = [b for b in blocks if b.startswith("<p")]
        if not paras:
            continue
        if prev_text and not CLOSED.search(prev_text):
            head = TAG.sub("", paras[0]).strip()
            if head and not paras[0].startswith("<p><b>"):
                rows.append((prev_page, pno, prev_text[-45:], head[:40]))
        prev_text = TAG.sub("", paras[-1]).strip()
        prev_page = pno
    return rows

if __name__ == "__main__":
    total = 0
    for f in sorted(glob.glob("assets/pdf/*.pdf")):
        rows = check(f)
        total += len(rows)
        print(f"{os.path.basename(f)[:-4]:10} {len(rows):4}")
        for a, b, t, n in rows[:2]:
            print(f"    p{a}->p{b}: …{t} || {n}")
    print("total:", total)
