# -*- coding: utf-8 -*-
"""Compare the converted text of every booklet against the PDF, page by page."""
import sys, re, difflib, glob, os
sys.path.insert(0, "tools")
import convert as C
import structure as S

MARKS = re.compile(r"[\u0591-\u05c7]")            # nikud and cantillation
STRIP = re.compile(r"[^\u05d0-\u05eaA-Za-z]")     # digits: markers are renumbered

def norm(s):
    s = MARKS.sub("", re.sub(r"<[^>]+>", " ", s))
    return STRIP.sub("", s.translate(C.BIDI))

def mostly_present(chunk, hay, width=20):
    """Is this text somewhere in the booklet, even if broken across blocks?"""
    if len(chunk) < width:
        return chunk in hay
    windows = [chunk[i:i + width] for i in range(0, len(chunk) - width + 1, width)]
    hits = sum(1 for w in windows if w in hay)
    return hits >= max(1, int(0.9 * len(windows)))


def first_content_page(refs):
    """Cover pages and the table of contents are dropped on purpose."""
    for i, text in enumerate(refs):
        for line in text.translate(C.BIDI).split("\n"):
            line = line.strip()
            if S.is_section(line) and not S.DOT_LEADERS.search(line):
                return i
    return 0


def audit(path):
    pages = C.convert(path, per_page=True, joined=True)
    # footnotes move to the end of their passage and can continue onto the
    # next page, so text that turns up anywhere in the booklet is not lost -
    # only text that is nowhere at all is a fault
    everywhere = norm("".join(b for _, blocks in pages for b in blocks))
    refs = C.all_page_texts(path)
    start = first_content_page(refs)
    problems = []
    for pno, blocks in pages:
        if pno - 1 < start:
            continue
        ref = norm(refs[pno - 1] if pno - 1 < len(refs) else "")
        out = norm("".join(blocks))
        notes = everywhere
        sm = difflib.SequenceMatcher(None, ref, out, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            gone, added = ref[i1:i2], out[j1:j2]
            # footnotes move to the end of the passage, and a footnote split
            # by a page break is joined onto the one before it: text that
            # turns up elsewhere in the booklet has moved, not gone
            if gone and mostly_present(gone, notes):
                continue
            if added and mostly_present(added, notes):
                continue
            if tag == "delete" and len(gone) >= 25:
                problems.append((pno, "missing", gone))
            elif tag == "insert" and len(added) >= 25:
                problems.append((pno, "added", added))
            elif tag == "replace" and abs(len(gone) - len(added)) >= 25:
                problems.append((pno, "changed", f"{gone[:60]} -> {added[:60]}"))
    return problems

if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(glob.glob("assets/pdf/*.pdf"))
    total = 0
    for f in targets:
        p = audit(f)
        total += len(p)
        print(f"{os.path.basename(f)[:-4]:10} {len(p):4} suspect spans")
        for pno, kind, text in p[:3]:
            print(f"   p{pno} {kind}: {text[:90]}")
    print("total:", total)
