# -*- coding: utf-8 -*-
"""Turn the converter's flat block list into a structured reading section."""
import re, html

SECTION = re.compile(r"^פסקה\s+([א-ת]{1,4})\s*['׳.]?\s*(?:[-–]\s*)?(?=[\u05d0-\u05ea(])")
# words that follow "פסקה" in ordinary prose rather than in a section heading
NOT_A_NUMERAL = {"זאת", "זו", "זה", "אלו", "אלה", "הזאת", "אחת", "כזאת", "אחרת", "שלנו", "הזו"}
DOT_LEADERS = re.compile(r"\.{4,}")
SUBHEAD = re.compile(r"^(נושא הפסקה|ביאור הפסקה)")
FRONT_MATTER = re.compile(r"@|לא עבר הגהה|נכתב בחבורת|פלא|מייל|להערות|^\d{9,}$|שיעורים באורות הקודש")

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()

def clean_section_title(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\s*\(\s*\d+\s+", " (", t)   # drop the footnote number glued to "(עמוד"
    t = re.sub(r"(?<=[֐-ת'])\(", " (", t)   # "האלוהי(עמוד" -> "האלוהי (עמוד"
    t = re.sub(r"\s*-\s*$", "", t)
    return re.sub(r"\s{2,}", " ", t).strip()

def is_section(text):
    m = SECTION.match(text)
    return bool(m) and m.group(1) not in NOT_A_NUMERAL and len(text) < 120


def build(blocks):
    """Split a booklet into sections.

    Returns (preamble_html, sections) where sections is a list of
    (anchor, plain title, html) - one entry per numbered passage.
    """
    start = 0
    for i, b in enumerate(blocks):
        t = strip_tags(b)
        if is_section(t) and not DOT_LEADERS.search(t):
            start = i
            break
    else:
        for i, b in enumerate(blocks):
            if b.startswith("<p class=\"src\"") or b.startswith("<blockquote"):
                start = i
                break
    body = blocks[start:]

    preamble, sections = [], []
    cur = None
    for b in body:
        text = strip_tags(b)
        if not text or FRONT_MATTER.search(text) or DOT_LEADERS.search(text):
            continue
        if is_section(text):
            title = clean_section_title(text)
            anchor = f"p{len(sections) + 1}"
            heading = f'<h2 class="section-title">{title}</h2>'
            cur = dict(anchor=anchor, title=re.sub(r"<[^>]+>", "", title), html=[heading])
            sections.append(cur)
            continue
        block = b
        if b.startswith("<h2>"):
            block = "<h3>" + b[4:-5] + "</h3>"
        (cur["html"] if cur else preamble).append(block)

    return ("\n      ".join(preamble),
            [(s["anchor"], s["title"], "\n        ".join(s["html"])) for s in sections])
