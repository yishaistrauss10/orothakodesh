# -*- coding: utf-8 -*-
"""Turn the converter's flat block list into a structured reading section."""
import re, html

# "פסקה ט'", and also "ראש דבר, פסקה א'" where the passage is introduced
SECTION = re.compile(r"^(?:ראש דבר[,\s]\s*)?פסקה\s+([א-ת]{1,4})\s*['׳.]?\s*(?:[-–]\s*)?(?=[\u05d0-\u05ea(\d])")
# words that follow "פסקה" in ordinary prose rather than in a section heading
NOT_A_NUMERAL = {"זאת", "זו", "זה", "אלו", "אלה", "הזאת", "אחת", "כזאת", "אחרת", "שלנו", "הזו"}
# a table-of-contents line: dot leaders running to a page number
DOT_LEADERS = re.compile(r"\.{4,}[\s.]*\d|\.{4,}[\s.]*\.{4,}")
SUBHEAD = re.compile(r"^(נושא הפסקה|ביאור הפסקה)")
# only ever applied to the cover pages, before the first passage begins
FRONT_MATTER = re.compile(r"@|לא עבר הגהה|נכתב בחבורת|מייל|להערות|שיעורים באורות הקודש")

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()

def clean_section_title(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\s*\(\s*(?:<sup>\d+</sup>)?\s*\d*\s*(?=עמ)", " (", t)
    t = re.sub(r"<sup>\d+</sup>", "", t)
    t = TRAILING_REF.sub("", t)
    t = re.sub(r"(?<=[֐-ת'])\(", " (", t)   # "האלוהי(עמוד" -> "האלוהי (עמוד"
    t = re.sub(r"\s*-\s*$", "", t)
    return re.sub(r"\s{2,}", " ", t).strip()

def is_section(text):
    m = SECTION.match(text)
    return bool(m) and m.group(1) not in NOT_A_NUMERAL and len(text) < 120



NOTE_BLOCK = re.compile(r'<aside class="notes"><ol>(.*?)</ol></aside>', re.S)
NOTE_ITEM = re.compile(r'<li(?: data-ref="(\d+)")?>(.*?)</li>', re.S)
TRAILING_REF = re.compile(r"\s*(\d{1,3})\s*$")
MARKER = re.compile(r"<sup>(\d+)</sup>")


def build(blocks):
    """Split a booklet into passages, each with its own list of sources.

    Returns (preamble_html, sections) where sections is a list of
    (anchor, plain title, html).

    Footnotes are collected per printed page, so a note and the marker that
    points at it can end up on opposite sides of a passage boundary. Notes are
    therefore matched to the marker nearest to them, and only then moved to the
    end of the passage that marker sits in.
    """
    start = 0
    for i, b in enumerate(blocks):
        t = strip_tags(b)
        if is_section(t) and not DOT_LEADERS.search(t):
            start = i
            break
    else:
        # no numbered passages: the cover pages end at the first real paragraph
        for i, b in enumerate(blocks):
            if len(strip_tags(b)) >= 120:
                start = i
                break

    # first pass: flow blocks per passage, and every note with its position
    groups = [dict(anchor=None, title="", blocks=[])]   # index 0 is the preamble
    notes = []
    for pos, b in enumerate(blocks[start:]):
        text = strip_tags(b)
        if not text:
            continue
        m = NOTE_BLOCK.fullmatch(b.strip())
        # a footnote is filtered item by item, so one table-of-contents line
        # among them does not take the whole block with it
        if not m and DOT_LEADERS.search(text):
            continue
        if len(groups) == 1 and FRONT_MATTER.search(text):
            continue   # still on the cover pages
        if m:
            for ref, note in NOTE_ITEM.findall(m.group(1)):
                if DOT_LEADERS.search(note):
                    continue   # a table-of-contents line, not a footnote
                notes.append(dict(pos=pos, ref=ref, text=note.strip(),
                                  group=len(groups) - 1, used=False))
            continue
        if is_section(text):
            # the footnote marker is dropped from the title text and re-added
            # from the block's own <sup>, so it does not leave a stray digit
            title = clean_section_title(strip_tags(MARKER.sub("", b)))
            refs = "".join(f"<sup>{r}</sup>" for r in MARKER.findall(b))
            groups.append(dict(anchor=f"p{len(groups)}",
                               title=TRAILING_REF.sub("", strip_tags(title)),
                               blocks=[(pos, f'<h2 class="section-title">{title}{refs}</h2>')]))
            continue
        if b.startswith("<h2>"):
            b = "<h3>" + b[4:-5] + "</h3>"
        groups[-1]["blocks"].append((pos, b))

    # second pass: give every marker the note that sits closest to it
    for gi, g in enumerate(groups):
        g["notes"] = []
        for pos, b in g["blocks"]:
            for ref in MARKER.findall(b):
                pool = [n for n in notes if n["ref"] == ref and not n["used"]]
                if not pool:
                    continue
                note = min(pool, key=lambda n: abs(n["pos"] - pos))
                note["used"] = True
                g["notes"].append(note)

    # notes nobody points at stay with the passage they were printed in
    for note in notes:
        if not note["used"]:
            groups[min(note["group"], len(groups) - 1)]["notes"].append(note)
            note["used"] = True

    rendered = [render_group(g) for g in groups]
    preamble = rendered[0]
    return preamble, [(g["anchor"], g["title"], html)
                      for g, html in zip(groups[1:], rendered[1:])]


def render_group(g):
    """Markers become asterisks; the notes follow under "מקורות"."""
    anchor = g["anchor"] or "pre"
    notes = g["notes"]
    index = {}
    for i, note in enumerate(notes, 1):
        index.setdefault(note["ref"], []).append(i)
    many = len(notes) > 1

    def mark(i):
        return "*" + (str(i) if many else "")

    def link(i):
        return (f'<a class="ref" id="{anchor}-r{i}" href="#{anchor}-n{i}">'
                f"<sup>{mark(i)}</sup></a>")

    taken = {}

    def next_index(ref):
        seen = taken.get(ref, 0)
        slots = index.get(ref, [])
        if seen < len(slots):
            taken[ref] = seen + 1
            return slots[seen]
        return None

    out = []
    for pos, b in g["blocks"]:
        def replace(m):
            i = next_index(m.group(1))
            return link(i) if i else m.group(0)
        b = MARKER.sub(replace, b)
        # a marker whose note could not be matched still reads as a reference
        out.append(MARKER.sub("<sup>*</sup>", b))

    html = "\n        ".join(out)
    if notes:
        rows = "\n          ".join(
            f'<li id="{anchor}-n{i}"><span class="ref">{mark(i)}</span> {n["text"]}</li>'
            for i, n in enumerate(notes, 1))
        html += (f'\n        <aside class="sources">\n          <h3>מקורות</h3>\n'
                 f'          <ul>\n          {rows}\n          </ul>\n        </aside>')
    return html
