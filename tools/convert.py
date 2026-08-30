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
PASSAGE_START = re.compile(r"^\s*פסקה\s")


def norm(w):
    return LETTERS.sub("", w.translate(BIDI))


def tidy(text):
    """Undo the artefacts of extracting right-to-left text."""
    text = text.translate(BIDI)
    # "word ,next" -> "word, next"
    text = PUNCT_BEFORE.sub(r"\1 ", text)
    text = re.sub(r"(?<=[^\s.,;:!?])\s+([.,;:!?])(?:\s|$)", r"\1 ", text)
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


# the booklets set the body in 16pt; other sizes keep their proportion
SIZE_CLASS = ((11.5, "s-xs"), (14.5, "s-sm"), (17.0, ""), (19.5, "s-md"),
              (22.0, "s-lg"), (999, "s-xl"))


def size_class(para):
    sizes = sorted(m[1] for line in para["lines"] for m in line["metas"])
    if not sizes:
        return ""
    median = sizes[len(sizes) // 2]
    for limit, name in SIZE_CLASS:
        if median < limit:
            return name
    return ""


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


def stroked_boxes(page):
    """Boxes of text Word emboldened by stroking it (render mode 1 or 2).

    Nothing in the font name or flags records that, but it is what makes the
    quoted source passages look heavier than the text around them.
    """
    boxes = []
    for span in page.get_texttrace():
        if span.get("type") in (1, 2):
            boxes.append(pymupdf.Rect(span["bbox"]))
    return boxes


def mupdf_words(page):
    """[(word, font, size, x0, x1, y, bold)] in reading order."""
    boxes = stroked_boxes(page)
    out = []
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line["spans"]:
                x0, y0, x1, y1 = s["bbox"]
                mid = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
                bold = "Bold" in s["font"] or any(mid in r for r in boxes)
                for w in s["text"].split():
                    out.append((w.translate(BIDI), s["font"], round(s["size"]),
                                x0, x1, y0, bold))
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
            # a footnote marker is often glued to the word before or after it;
            # PyMuPDF keeps it as its own span, so split it here too
            for piece in re.findall(r"\d+|[^\d]+", w) if re.search(r"\d", w) else [w]:
                if piece:
                    words.append(piece)
                    line_of.append(li)

    mw = mupdf_words(doc[pno])

    # pdftotext sometimes drops the space between two words of a justified
    # line ("בעולמואלא"); PyMuPDF keeps them apart, so split them back
    known = {norm(w[0]) for w in mw if len(norm(w[0])) > 1}
    split_words, split_lines = [], []
    for w, li in zip(words, line_of):
        n = norm(w)
        if len(n) > 4 and n not in known:
            for k in range(2, len(n) - 1):
                if n[:k] in known and n[k:] in known:
                    cut = len(w) - len(n) + k if w.endswith(n[k:]) else k
                    split_words.extend([w[:cut], w[cut:]])
                    split_lines.extend([li, li])
                    break
            else:
                split_words.append(w); split_lines.append(li)
        else:
            split_words.append(w); split_lines.append(li)
    words, line_of = split_words, split_lines
    line_words = {}
    for i, li in enumerate(line_of):
        line_words.setdefault(li, []).append(i)

    sm = difflib.SequenceMatcher(None, [norm(w) for w in words],
                                 [norm(w[0]) for w in mw], autojunk=False)
    meta = [None] * len(words)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            meta[a + k] = mw[b + k][1:]

    small_numbers = {w.strip() for w, font, size, *_ in mw
                     if size <= 12 and re.fullmatch(r"\d{1,3}", w.strip())}

    last = ("David", 16, 0.0, 0.0, 0.0, False)
    for i, m in enumerate(meta):
        if m is None:
            meta[i] = last
        else:
            last = m

    for i, w in enumerate(words):
        if w in small_numbers and meta[i][1] > 12:
            meta[i] = ("David", 11) + tuple(meta[i][2:])

    # the body runs to a fixed right margin; a quotation is indented from it
    edges = sorted(max(meta[i][3] for i in idx) for idx in line_words.values() if idx)
    right_margin = edges[len(edges) // 2] if edges else 0.0

    lines = []
    dash_pending = False
    for li, text in enumerate(tl):
        idx = line_words.get(li, [])
        if not idx or not text.strip():
            continue
        kinds = [classify(meta[i][0], meta[i][1]) for i in idx]
        bare = text.translate(BIDI).strip()
        if bare in {"-", "–", "•"}:
            dash_pending = True          # the bullet of a quotation
            continue
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
        ys = sorted(meta[i][4] for i in idx)
        y = ys[len(ys) // 2]   # median: a superscript must not shift the line
        indent = right_margin - x1
        if kind == "body" and (dash_pending or indent > 15):
            kind = "cite"   # a passage quoted from another work
        dash_pending = False
        lines.append(dict(text=text, kind=kind, kinds=kinds, indent=indent,
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
    by_kind = {}
    for a, b in zip(lines, lines[1:]):
        gap = b["y"] - a["y"]
        if 0 < gap < 200 and a["kind"] == b["kind"]:
            by_kind.setdefault(a["kind"], []).append(gap)
    leadings = {k: sorted(v)[len(v) // 2] for k, v in by_kind.items() if v}
    all_gaps = sorted(g for v in by_kind.values() for g in v)
    default = all_gaps[len(all_gaps) // 2] if all_gaps else 27.0

    paras, cur = [], None
    for prev, l in zip([None] + lines[:-1], lines):
        start_new = cur is None
        if not start_new:
            gap = l["y"] - prev["y"]
            if l["kind"] == "heading" or prev["kind"] == "heading":
                start_new = True
            elif (l["kind"] == "note") != (prev["kind"] == "note"):
                start_new = True
            elif (l["kind"] == "cite") != (prev["kind"] == "cite"):
                start_new = True
            elif gap < 0:            # new page or new column
                start_new = True
            elif gap > leadings.get(l["kind"], default) * 1.25:
                start_new = True
            elif l["kinds"][0] == "bold" and prev["kinds"][-1] != "bold":
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
            out.append((w, classify(m[0], m[1]), bool(m[5]) if len(m) > 5 else False))
    chunks, buf, buf_kind = [], [], None
    for w, kind, bold in out:
        if kind == "quote":
            k = "quote"
        elif kind == "bold" and para["kind"] != "heading":
            k = "bold"
        elif kind == "note" and para["kind"] != "note":
            k = "note"
        else:
            k = "text"
        key = (k, bold and k != "note")
        if key != buf_kind and buf:
            chunks.append((buf_kind, buf)); buf = []
        buf_kind = key
        buf.append(w)
    if buf:
        chunks.append((buf_kind, buf))

    parts = []
    for (k, bold), ws in chunks:
        text = tidy(" ".join(ws))
        if not text:
            continue
        esc = html.escape(text, quote=False)
        if bold and k in ("quote", "text"):
            esc = f"<b>{esc}</b>"
        if k == "quote":
            parts.append(f'<em class="src">{esc}</em>')
        elif k == "bold":
            parts.append(f"<b>{esc}</b>")
        elif k == "note" and re.fullmatch(r"\d+[.,]?", text):
            parts.append(f'<sup>{esc}</sup>')
        else:
            parts.append(esc)
    joined = tidy(" ".join(parts)).replace(" </em>", "</em> ").replace(" </b>", "</b> ")
    joined = joined.replace("<sup> ", "<sup>").replace(" <sup>", "<sup>")
    # the dash that separates a quoted phrase from its explanation
    joined = re.sub(r">\s*-(?=[֐-ת])", "> - ", joined)
    return joined


def split_notes(para, text):
    """A footnote block can hold several notes; each starts with its number.

    Returns [(reference number or None, text)].
    """
    marks = [i for i, (w, m) in enumerate(
        (w, m) for line in para["lines"] for w, m in zip(line["words"], line["metas"]))
        if m[1] <= 11 and re.fullmatch(r"\d+", w.translate(BIDI))]
    lead = re.match(r"^\s*(?:<sup>(\d+)[.,]?</sup>|(\d+)\s*(?=[֐-ת]))", text)
    first_ref = next((g for g in (lead.groups() if lead else ()) if g), None)
    text = re.sub(r"^\s*<sup>\d+[.,]?</sup>\s*|^\s*\d+\s*(?=[֐-ת])", "", text)
    if len(marks) <= 1:
        return [(first_ref, text)] if text.strip() else []
    parts = re.split(r"\s*<sup>(\d+)</sup>\s*", text)
    out, refs = [], [first_ref]
    for i, part in enumerate(parts):
        if i % 2:
            refs.append(part)
        elif part.strip():
            out.append((refs[len(out)] if len(out) < len(refs) else None, part.strip()))
    return out


def mark_missing_refs(page_blocks, refs):
    """Wrap footnote numbers the font data did not flag as superscript.

    Only a number that appears exactly once in the page body is wrapped, so
    ordinary numbers in the text are left alone.
    """
    for ref in refs:
        if any(f"<sup>{ref}</sup>" in b for b in page_blocks):
            continue
        pattern = re.compile(r"(?<![\d>])" + re.escape(ref) + r"(?![\d<])")
        hits = [(i, len(pattern.findall(b))) for i, b in enumerate(page_blocks)]
        if sum(n for _, n in hits) != 1:
            continue
        for i, n in hits:
            if n:
                page_blocks[i] = pattern.sub(f"<sup>{ref}</sup>", page_blocks[i], count=1)
    return page_blocks


def convert(path):
    doc = pymupdf.open(path)
    texts = all_page_texts(path)
    out, notes = [], []
    for pno in range(doc.page_count):
        lines = page_lines(texts[pno] if pno < len(texts) else "", doc, pno)
        page_blocks, page_refs = [], []
        for para in paragraphs(lines, doc[pno].rect.width):
            text = render_words(para)
            if not text or DIGITS_ONLY.match(re.sub(r"<[^>]+>", "", text)):
                continue
            cls = size_class(para)
            if para["kind"] == "heading":
                page_blocks.append(
                    f"<h2>{re.sub(r'^<em class=.src.>|</em>$', '', text).strip(' -')}</h2>")
            elif para["kind"] == "note":
                items = split_notes(para, text)
                starts_note = bool(para["lines"] and para["lines"][0]["words"]
                                   and re.fullmatch(r"\d+", para["lines"][0]["words"][0].translate(BIDI)))
                for i, (ref, item) in enumerate(items):
                    if i == 0 and notes and not starts_note:
                        notes[-1] = notes[-1][:-len("</li>")] + " " + item + "</li>"
                    else:
                        attr = f' data-ref="{ref}"' if ref else ""
                        notes.append(f"<li{attr}>{item}</li>")
                        if ref:
                            page_refs.append(ref)
            elif para["kind"] == "cite" and len(re.sub(r"<[^>]+>", "", text)) > 24:
                page_blocks.append(f'<p class="cite{" " + cls if cls else ""}">{text}</p>')
            elif para["kind"] == "quote" and text.startswith('<em class="src">') and text.endswith("</em>") \
                    and re.fullmatch(r'(?:<em class="src">.*?</em>\s*)+', text, re.S):
                inner = text.replace('<em class="src">', "").replace("</em>", "")
                page_blocks.append(f'<p class="src{" " + cls if cls else ""}">{inner}</p>')
            else:
                page_blocks.append(f'<p class="{cls}">{text}</p>' if cls else f"<p>{text}</p>")

        page_blocks = mark_missing_refs(page_blocks, page_refs)
        # a paragraph interrupted by a page break continues on the next page
        prev = next((i for i in range(len(out) - 1, -1, -1)
                     if not out[i].startswith("<aside")), None)
        if (prev is not None and page_blocks
                and out[prev].startswith("<p") and page_blocks[0].startswith("<p")
                and out[prev].split(">")[0] == page_blocks[0].split(">")[0]
                and not re.search(r"[.!?:]\s*</p>$", out[prev])
                and not page_blocks[0].startswith("<p><b>")
                and not PASSAGE_START.match(re.sub(r"<[^>]+>", "", page_blocks[0]))
                and not PASSAGE_START.match(re.sub(r"<[^>]+>", "", out[prev]))):
            head = page_blocks.pop(0)
            out[prev] = out[prev][:-len("</p>")] + " " + head[len(head.split(">")[0]) + 1:]
        out.extend(page_blocks)
        if notes:
            out.append('<aside class="notes"><ol>' + "".join(notes) + "</ol></aside>")
            notes = []
    return out
