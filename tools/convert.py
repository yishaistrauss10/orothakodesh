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
        return "heading"
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
        if kinds.count("note") > len(kinds) / 2:
            kind = "note"
        elif kinds.count("quote") > len(kinds) / 2:
            kind = "quote"
        else:
            kind = kinds[0]
        if all(k == "pageno" for k in kinds) or DIGITS_ONLY.match(text.translate(BIDI)):
            continue
        x0 = min(meta[i][2] for i in idx)
        x1 = max(meta[i][3] for i in idx)
        lines.append(dict(text=text, kind=kind, kinds=kinds,
                          words=[words[i] for i in idx],
                          metas=[meta[i] for i in idx], x0=x0, x1=x1))
    return lines


def paragraphs(lines, page_width):
    """Group lines into paragraphs, splitting on short lines and kind changes."""
    if not lines:
        return []
    body_widths = [l["x1"] - l["x0"] for l in lines if l["kind"] in ("body", "quote")]
    full = max(body_widths) if body_widths else page_width
    paras, cur = [], None

    for i, l in enumerate(lines):
        start_new = cur is None
        if not start_new:
            prev = cur["lines"][-1]
            if l["kind"] == "heading" or prev["kind"] == "heading":
                start_new = True
            elif (l["kind"] == "note") != (prev["kind"] == "note"):
                start_new = True
            elif l["kind"] == "quote" and prev["kind"] != "quote":
                start_new = True
            elif ((prev["x1"] - prev["x0"]) < 0.92 * full
                  and re.search(r"[.!?:]\s*$", prev["text"].translate(BIDI))):
                start_new = True  # previous line ended short and closed a sentence
        if start_new:
            cur = dict(kind=l["kind"], lines=[l])
            paras.append(cur)
        else:
            cur["lines"].append(l)
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
        k = "quote" if kind == "quote" else ("note" if kind == "note" and para["kind"] != "note" else "text")
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
            parts.append(f'<b class="src">{esc}</b>')
        elif k == "note" and re.fullmatch(r"\d+[.,]?", text):
            parts.append(f'<sup>{esc}</sup>')
        else:
            parts.append(esc)
    joined = tidy(" ".join(parts)).replace(" </b>", "</b> ").replace("<sup> ", "<sup>")
    # the dash that separates a quoted phrase from its explanation
    joined = re.sub(r">\s*-(?=[֐-ת])", "> - ", joined)
    return joined


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
                notes.append("<li>" + re.sub(r"^\s*<sup>\d+[.,]?</sup>\s*|^\s*\d+(?=[֐-ת])", "", text) + "</li>")
            elif para["kind"] == "quote" and text.startswith("<b class=\"src\">") and text.endswith("</b>"):
                if notes:
                    out.append('<aside class="notes"><ol>' + "".join(notes) + "</ol></aside>")
                    notes = []
                inner = text[len('<b class="src">'):-len("</b>")]
                out.append(f'<blockquote class="src">{inner}</blockquote>')
            else:
                if notes:
                    out.append('<aside class="notes"><ol>' + "".join(notes) + "</ol></aside>")
                    notes = []
                out.append(f"<p>{text}</p>")
        if notes:
            out.append('<aside class="notes"><ol>' + "".join(notes) + "</ol></aside>")
            notes = []
    return out
