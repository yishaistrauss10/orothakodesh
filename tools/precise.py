# -*- coding: utf-8 -*-
"""High-precision boundary check: both signals must agree.

A break is wrong only when the page shows no extra space AND the line before
it fills the column - a paragraph that was cut mid-line.
"""
import sys, glob, os
sys.path.insert(0, "tools")
import convert as C, structure as S
import pymupdf

def check(path):
    doc = pymupdf.open(path)
    texts = C.all_page_texts(path)
    start = 0
    for i, t in enumerate(texts):
        if any(S.is_section(l.strip()) and not S.DOT_LEADERS.search(l)
               for l in t.translate(C.BIDI).split("\n")):
            start = i
            break
    bad = []
    for pno in range(start, doc.page_count):
        lines = C.page_lines(texts[pno] if pno < len(texts) else "", doc, pno)
        if len(lines) < 5:
            continue
        paras = C.paragraphs(lines, doc[pno].rect.width)
        for a, b in zip(paras, paras[1:]):
            if a["kind"] != b["kind"] or a["kind"] not in ("body", "quote", "cite"):
                continue
            same = [l for l in lines if l["kind"] == a["kind"]]
            if len(same) < 4:
                continue
            gaps = sorted(y2["y"] - y1["y"] for y1, y2 in zip(same, same[1:])
                          if 0 < y2["y"] - y1["y"] < 200)
            if not gaps:
                continue
            lead = gaps[len(gaps) // 2]
            left = min(l["x0"] for l in same)
            gap = b["lines"][0]["y"] - a["lines"][-1]["y"]
            full_line = a["lines"][-1]["x0"] - left < 6
            if 0 < gap <= lead * 1.15 and full_line:
                bad.append((pno + 1, a["kind"], a["lines"][-1]["text"][-40:],
                            b["lines"][0]["text"][:40]))
    return bad

if __name__ == "__main__":
    total = 0
    for f in sorted(glob.glob("assets/pdf/*.pdf")):
        rows = check(f)
        total += len(rows)
        if rows:
            print(f"{os.path.basename(f)[:-4]:10} {len(rows):3}")
            for r in rows[:3]:
                print("   p%s %s: …%s || %s" % r)
    print("total:", total)
