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
    t = re.sub(r"\(\s*\d+\s*", "(", t)      # drop the footnote number glued to "(עמוד"
    t = re.sub(r"(?<=[֐-ת'])\(", " (", t)   # "האלוהי(עמוד" -> "האלוהי (עמוד"
    t = re.sub(r"\s*-\s*$", "", t)
    return re.sub(r"\s{2,}", " ", t).strip()

def is_section(text):
    m = SECTION.match(text)
    return bool(m) and m.group(1) not in NOT_A_NUMERAL and len(text) < 120


def build(blocks):
    """Returns (toc_items, html_string). toc_items: [(anchor, title)]."""
    # find where the front matter ends
    start = 0
    for i, b in enumerate(blocks):
        t = strip_tags(b)
        if is_section(t) and not DOT_LEADERS.search(t):
            start = i
            break
    else:
        for i, b in enumerate(blocks):
            if b.startswith("<blockquote"):
                start = i
                break
    body = blocks[start:]

    out, toc, n = [], [], 0
    for b in body:
        text = strip_tags(b)
        if not text or FRONT_MATTER.search(text):
            continue
        if DOT_LEADERS.search(text):
            continue
        if is_section(text):
            n += 1
            anchor = f"p{n}"
            title = clean_section_title(text)
            toc.append((anchor, title))
            out.append(f'<h2 id="{anchor}" class="section-title">{html.escape(title, quote=False)}</h2>')
        elif SUBHEAD.match(text):
            out.append(f'<h3>{html.escape(clean_section_title(text), quote=False)}</h3>')
        elif b.startswith("<h2>"):
            out.append("<h3>" + b[4:-5] + "</h3>")
        else:
            out.append(b)
    return toc, "\n      ".join(out)
