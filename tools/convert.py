# -*- coding: utf-8 -*-
"""Convert a booklet PDF into an HTML fragment.

Text comes from pdftotext, which resolves the bidi ordering correctly.
Structure (headings, quoted passages from the source, footnotes, paragraph
breaks) comes from PyMuPDF spans, which carry font, size and geometry.
The two word streams are aligned so each pdftotext word inherits the font
and position of its PyMuPDF counterpart.
"""
import re, subprocess, difflib, html
import pymupdf

BIDI = dict.fromkeys(map(ord, "‪‫‬‭‮‎‏⁦⁧⁨⁩"), None)
LETTERS = re.compile(r"[^֐-תa-zA-Z0-9]")
COMBINING = re.compile(r"([֑-ׇ])\s+(?=\S)")
PUNCT_BEFORE = re.compile(r"\s+([.,;:!?])(?=\S)")
DIGITS_ONLY = re.compile(r"^[\d\s.]+$")


def norm(w):
    return LETTERS.sub("", w.translate(BIDI))


def tidy(text):
    """Undo the artefacts of extracting right-to-left text."""
    text = text.translate(BIDI)
    # "word ,next" -> "word, next"
    text = PUNCT_BEFORE.sub(r"\1 ", text)
    # a space wrongly inserted after a vowel point: "מִֽ י" -> "מִֽי"
    text = COMBINING.sub(r"\1", text)
    # parentheses: mirrored pairs, stray spaces, punctuation pushed inside
    text = re.sub(r"\)(?=[֐-ת])([^()]{1,60}?)(?<=[֐-ת])\(", r"(\1)", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\((\s*[:;,.])", r"\1 (", text)
    text = re.sub(r"(?<=[֐-ת])\(", " (", text)
    text = re.sub(r"\)(?=[֐-ת])", ") ", text)
    text = re.sub(r"\((\d{1,3})(?=[֐-ת])", r"(\1 ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+(['\"])(?=\s|$)", r"\1", text)
    # "word -next" -> "word - next" (the dash separating a quote from its explanation)
    text = re.sub(r"(?<=[֐-ת'\"])\s+-(?=[֐-ת])", " - ", text)
    return text.strip()


def classify(font, size):
    if font.startswith("Arial"):
        return "pageno"
    if "Narkisim" in font:
        return "quote"
    if "Bold" in font and size >= 15:
        return "bold"
    if size <= 13:
        return "note"
    return "body"


def mupdf_words(page):
    """[(word, font, size, x0, x1, y)] in reading order."""
    out = []
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line["spans"]:
                x0, y0, x1, y1 = s["bbox"]
                for w in s["text"].split():
                    out.append((w.translate(BIDI), s["font"], round(s["size"]), x0, x1, y0))
    return out


def all_page_texts(path):
    """pdftotext for the whole document at once, split on the page separator."""
    raw = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"],
                         capture_output=True, text=True).stdout
    return raw.split("\f")


def page_lines(raw, doc, pno):
    """Lines of one PDF page: text, kind, geometry."""
    tl = [l.translate(BIDI).strip() for l in raw.split("\n")]

    words, line_of = [], []
    for li, line in enumerate(tl):
        for w in line.split():
            words.append(w)
            line_of.append(li)

    mw = mupdf_words(doc[pno])
    sm = difflib.SequenceMatcher(None, [norm(w) for w in words],
                                 [norm(w[0]) for w in mw], autojunk=False)
    meta = [None] * len(words)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            meta[a + k] = mw[b + k][1:]

    last = ("David", 16, 0.0, 0.0, 0.0)
    for i, m in enumerate(meta):
        if m is None:
            meta[i] = last
        else:
            last = m

    lines = []
    for li, text in enumerate(tl):
        idx = [i for i, l in enumerate(line_of) if l == li]
        if not idx or not text.strip():
            continue
        kinds = [classify(meta[i][0], meta[i][1]) for i in idx]
        if all(k == "bold" for k in kinds):
            kind = "heading"
        elif kinds.count("note") > len(kinds) / 2:
            kind = "note"
        elif kinds.count("quote") > len(kinds) / 2:
            kind = "quote"
        else:
            kind = "body" if kinds[0] == "bold" else kinds[0]
        if all(k == "pageno" for k in kinds) or DIGITS_ONLY.match(text.translate(BIDI)):
            continue
        x0 = min(meta[i][2] for i in idx)
        x1 = max(meta[i][3] for i in idx)
        y = min(meta[i][4] for i in idx)
        lines.append(dict(text=text, kind=kind, kinds=kinds,
                          words=[words[i] for i in idx],
                          metas=[meta[i] for i in idx], x0=x0, x1=x1, y=y))
    return lines


def paragraphs(lines, page_width):
    """Group lines into paragraphs.

    The booklets separate paragraphs with extra vertical space, so the gap
    between consecutive baselines is the signal: a gap noticeably larger than
    the usual line spacing starts a new paragraph.
    """
    if not lines:
        return []
    gaps = sorted(b["y"] - a["y"] for a, b in zip(lines, lines[1:])
                  if 0 < b["y"] - a["y"] < 200 and a["kind"] == b["kind"])
    leading = gaps[len(gaps) // 2] if gaps else 27.0

    paras, cur = [], None
    for prev, l in zip([None] + lines[:-1], lines):
        start_new = cur is None
        if not start_new:
            gap = l["y"] - prev["y"]
            if l["kind"] == "heading" or prev["kind"] == "heading":
                start_new = True
            elif (l["kind"] == "note") != (prev["kind"] == "note"):
                start_new = True
            elif gap < 0:            # new page or new column
                start_new = True
            elif gap > leading * 1.45:
                start_new = True
        if start_new:
            cur = dict(kind=l["kind"], lines=[l])
            paras.append(cur)
        else:
            cur["lines"].append(l)
            if l["kind"] == "quote" and cur["kind"] != "quote":
                pass
    return paras


def render_words(para):
    """Inline markup: quoted source text bold, footnote markers superscript."""
    out = []
    for line in para["lines"]:
        for w, m in zip(line["words"], line["metas"]):
            kind = classify(m[0], m[1])
            out.append((w, kind))
    chunks, buf, buf_kind = [], [], None
    for w, kind in out:
        if kind == "quote":
            k = "quote"
        elif kind == "bold" and para["kind"] != "heading":
            k = "bold"
        elif kind == "note" and para["kind"] != "note":
            k = "note"
        else:
            k = "text"
        if k != buf_kind and buf:
            chunks.append((buf_kind, buf)); buf = []
        buf_kind = k
        buf.append(w)
    if buf:
        chunks.append((buf_kind, buf))

    parts = []
    for k, ws in chunks:
        text = tidy(" ".join(ws))
        if not text:
            continue
        esc = html.escape(text, quote=False)
        if k == "quote":
            parts.append(f'<em class="src">{esc}</em>')
        elif k == "bold":
            parts.append(f"<b>{esc}</b>")
        elif k == "note" and re.fullmatch(r"\d+[.,]?", text):
            parts.append(f'<sup>{esc}</sup>')
        else:
            parts.append(esc)
    joined = tidy(" ".join(parts)).replace(" </em>", "</em> ").replace(" </b>", "</b> ")
    joined = joined.replace("<sup> ", "<sup>")
    # the dash that separates a quoted phrase from its explanation
    joined = re.sub(r">\s*-(?=[֐-ת])", "> - ", joined)
    return joined


def split_notes(para, text):
    """A footnote block can hold several notes; each starts with its number."""
    marks = [i for i, (w, m) in enumerate(
        (w, m) for line in para["lines"] for w, m in zip(line["words"], line["metas"]))
        if m[1] <= 11 and re.fullmatch(r"\d+", w.translate(BIDI))]
    text = re.sub(r"^\s*<sup>\d+[.,]?</sup>\s*|^\s*\d+(?=[֐-ת])", "", text)
    if len(marks) <= 1:
        return [text] if text.strip() else []
    parts = re.split(r"\s*<sup>(?:\d+)</sup>\s*", text)
    return [p.strip() for p in parts if p.strip()]


def convert(path):
    doc = pymupdf.open(path)
    texts = all_page_texts(path)
    out, notes = [], []
    for pno in range(doc.page_count):
        lines = page_lines(texts[pno] if pno < len(texts) else "", doc, pno)
        for para in paragraphs(lines, doc[pno].rect.width):
            text = render_words(para)
            if not text or DIGITS_ONLY.match(re.sub(r"<[^>]+>", "", text)):
                continue
            if para["kind"] == "heading":
                out.append(f"<h2>{re.sub(r'^<b class=.src.>|</b>$', '', text).strip(' -')}</h2>")
            elif para["kind"] == "note":
                items = split_notes(para, text)
                starts_note = bool(para["lines"] and para["lines"][0]["metas"]
                                   and re.fullmatch(r"\d+", para["lines"][0]["words"][0].translate(BIDI)))
                for i, item in enumerate(items):
                    if i == 0 and notes and not starts_note:
                        notes[-1] = notes[-1][:-len("</li>")] + " " + item + "</li>"
                    else:
                        notes.append(f"<li>{item}</li>")
            elif para["kind"] == "quote" and text.startswith("<em class=\"src\">") and text.endswith("</em>"):
                if notes:
                    out.append('<aside class="notes"><ol>' + "".join(notes) + "</ol></aside>")
                    notes = []
                inner = text[len('<em class="src">'):-len("</em>")]
                out.append(f'<p class="src">{inner}</p>')
            else:
                if notes:
                    out.append('<aside class="notes"><ol>' + "".join(notes) + "</ol></aside>")
                    notes = []
                out.append(f"<p>{text}</p>")
        if notes:
            out.append('<aside class="notes"><ol>' + "".join(notes) + "</ol></aside>")
            notes = []
    return out
