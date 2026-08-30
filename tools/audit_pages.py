# -*- coding: utf-8 -*-
"""Compare each generated page against its booklet, end to end.

tools/audit.py checks the converter; this checks what actually ends up on the
site, so anything the page builder drops shows up too.
"""
import sys, re, glob, os, collections
sys.path.insert(0, "tools")
import convert as C
import structure as S

MARKS = re.compile(r"[\u0591-\u05c7]")          # nikud and cantillation
# digits are dropped too: footnote markers are renumbered on the page
STRIP = re.compile(r"[^\u05d0-\u05eaA-Za-z]")
PAGE_OF = {}

def norm(s):
    """Letters only: pointing and punctuation differ harmlessly between the
    extractor and the page."""
    return STRIP.sub("", MARKS.sub("", re.sub(r"<[^>]+>", " ", s).translate(C.BIDI)))

def first_content_page(refs):
    for i, text in enumerate(refs):
        for line in text.translate(C.BIDI).split("\n"):
            if S.is_section(line.strip()) and not S.DOT_LEADERS.search(line):
                return i
    return 0

def page_html(key):
    for f in glob.glob("pages/*.html"):
        html = open(f, encoding="utf-8").read()
        if f"assets/pdf/{key}.pdf" in html:
            body = re.search(r'<article class="reading">.*?</article>', html, re.S)
            return f, body.group(0) if body else ""
    return None, ""

def audit(pdf, window=30):
    """Every stretch of the booklet must be findable on the generated page.

    tools/audit.py checks the converter page by page; this one checks what
    survives the page builder, which is where whole sections can go missing.
    """
    key = os.path.basename(pdf)[:-4]
    refs = C.all_page_texts(pdf)
    start = first_content_page(refs)
    name, html = page_html(key)
    out = norm(html)
    missing = []
    for pno, text in enumerate(refs[start:], start + 1):
        ref = norm(text)
        chunks = [ref[i:i + window] for i in range(0, max(0, len(ref) - window), window)]
        found = [c in out for c in chunks]
        # a single gap is a seam - the footnotes move to the end of the
        # passage, so one stretch straddles their old place. Two in a row
        # means text really is absent.
        run = []
        for chunk, ok in zip(chunks + [""], found + [True]):
            if not ok:
                run.append(chunk)
                continue
            if len(run) >= 2:
                missing.append((pno, "".join(run)))
            run = []
    return key, name, missing

if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(glob.glob("assets/pdf/*.pdf"))
    total = 0
    for pdf in targets:
        key, name, missing = audit(pdf)
        total += len(missing)
        print(f"{key:10} stretches not on the page: {len(missing):4}")
        for pno, chunk in missing[:3]:
            print(f"    p{pno}: {chunk[:70]}")
    print("total:", total)
