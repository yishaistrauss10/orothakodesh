# -*- coding: utf-8 -*-
"""Generates the static site from the structure described in the source notes."""
import os, shutil, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from structure import build as build_reading

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAGMENTS = json.load(open(os.path.join(ROOT_DIR, "fragments.json"), encoding="utf-8"))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "אורות הקודש"

# --- structure -------------------------------------------------------------
# node: dict(slug,title,subtitle,desc,pdf,children,kind)
def N(slug, title, desc="", pdf=None, children=None, label=""):
    return dict(slug=slug, title=title, desc=desc, pdf=pdf,
                children=children or [], label=label)

v1 = N("kerech-1", "כרך א'", "חכמת הקודש והגיון הקודש — שני שערים.", label="כרך א'", children=[
    N("kerech-1-shaar-1", "שער ראשון — חכמת הקודש", "שבעה סדרים בחכמת הקודש.", label="שער ראשון", children=[
        N("kerech-1-shaar-1-seder-1", "חכמת האמת הכוללת", "סדר א'", pdf="v1-g1-s1.pdf", label="סדר א'"),
        N("kerech-1-shaar-1-seder-2", "איחוד הנסתר והנגלה", "סדר ב'", pdf="v1-g1-s2.pdf", label="סדר ב'"),
        N("kerech-1-shaar-1-seder-3", "איחוד הכללות והפרטות", "סדר ג'", pdf="v1-g1-s3.pdf", label="סדר ג'"),
        N("kerech-1-shaar-1-seder-4", "איחוד מדע הקודש והחול", "סדר ד'", pdf="v1-g1-s4.pdf", label="סדר ד'"),
        N("kerech-1-shaar-1-seder-5", "אור הרזים", "סדר ה'", pdf="v1-g1-s5.pdf", label="סדר ה'"),
        N("kerech-1-shaar-1-seder-6", "קשב היחודים", "סדר ו'", pdf="v1-g1-s6.pdf", label="סדר ו'"),
        N("kerech-1-shaar-1-seder-7", "סדר ז'", "החוברת טרם הוכנה.", label="סדר ז'"),
    ]),
    N("kerech-1-shaar-2", "שער שני — הגיון הקודש", "חמישה סדרים. החוברות טרם הוכנו.", label="שער שני", children=[
        N("kerech-1-shaar-2-seder-1", "סדר א'", "החוברת טרם הוכנה.", label="סדר א'"),
        N("kerech-1-shaar-2-seder-2", "סדר ב'", "החוברת טרם הוכנה.", label="סדר ב'"),
        N("kerech-1-shaar-2-seder-3", "סדר ג'", "החוברת טרם הוכנה.", label="סדר ג'"),
        N("kerech-1-shaar-2-seder-4", "סדר ד'", "החוברת טרם הוכנה.", label="סדר ד'"),
        N("kerech-1-shaar-2-seder-5", "סדר ה'", "החוברת טרם הוכנה.", label="סדר ה'"),
    ]),
])

def essay(vol, i, heb, title, desc, orders=None, pdf=None):
    return N(f"{vol}-maamar-{i}", title, desc, pdf=pdf, label=f"מאמר {heb}", children=orders or [])

hebord = ["ראשון","שני","שלישי","רביעי","חמישי"]

v2 = N("kerech-2", "כרך ב'", "חמישה מאמרים, כל מאמר מחולק לשניים או שלושה סדרים.", label="כרך ב'", children=[
    essay("kerech-2", i+1, hebord[i], f"מאמר {hebord[i]}", "החוברות טרם הוכנו.",
          orders=[N(f"kerech-2-maamar-{i+1}-seder-{j}", f"סדר {['א','ב','ג'][j-1]}'", "החוברת טרם הוכנה.",
                    label=f"סדר {['א','ב','ג'][j-1]}'") for j in (1,2)])
    for i in range(5)
])

v3 = N("kerech-3", "כרך ג'", "מוסר הקודש ודרך הקודש — שני שערים.", label="כרך ג'", children=[
    N("kerech-3-hakdama", "הקדמה — ראש דבר", "פתח דבר לכרך ג'.", pdf="v3-intro.pdf", label="הקדמה"),
    N("kerech-3-shaar-1", "שער ראשון — מוסר הקודש", "שבעה סדרים במוסר הקודש.", label="שער ראשון", children=[
        N("kerech-3-shaar-1-seder-1", "המוסר האלהי", "סדר א'", pdf="v3-g1-s1.pdf", label="סדר א'"),
        N("kerech-3-shaar-1-seder-2", "החוק והחופש העליון", "סדר ב'", pdf="v3-g1-s2.pdf", label="סדר ב'"),
        N("kerech-3-shaar-1-seder-3", "הרצון הכללי הפועל", "סדר ג'", pdf="v3-g1-s3.pdf", label="סדר ג'"),
        N("kerech-3-shaar-1-seder-4", "הדעת והשאיפה האצילית", "סדר ד'", pdf="v3-g1-s4.pdf", label="סדר ד'"),
        N("kerech-3-shaar-1-seder-5", "העצמיות והמלחמה הפנימית", "סדר ה'", pdf="v3-g1-s5.pdf", label="סדר ה'"),
        N("kerech-3-shaar-1-seder-6", "יסוד הכללות", "סדר ו'", pdf="v3-g1-s6.pdf", label="סדר ו'"),
        N("kerech-3-shaar-1-seder-7", "מגמת העדן והטוב העליון", "סדר ז'", pdf="v3-g1-s7.pdf", label="סדר ז'"),
    ]),
    N("kerech-3-shaar-2", "שער שני — דרך הקודש", "חמישה סדרים בדרך הקודש.", label="שער שני", children=[
        N("kerech-3-shaar-2-seder-1", "עבודת הקודש", "סדר א'", pdf="v3-g2-s1.pdf", label="סדר א'"),
        N("kerech-3-shaar-2-seder-2", "טהרת מידות הנפש", "סדר ב'", pdf="v3-g2-s2.pdf", label="סדר ב'"),
        N("kerech-3-shaar-2-seder-3", "פרישות", "סדר ג'", pdf="v3-g2-s3.pdf", label="סדר ג'"),
        N("kerech-3-shaar-2-seder-4", "חסידות", "סדר ד'", pdf="v3-g2-s4.pdf", label="סדר ד'"),
        N("kerech-3-shaar-2-seder-5", "צפיה לישועה", "סדר ה'", pdf="v3-g2-s5.pdf", label="סדר ה'"),
    ]),
])

v4 = N("kerech-4", "כרך ד'", "חמישה מאמרים. כל מאמר הוא חוברת בפני עצמה, מלבד המאמר הראשון המחולק לשני סדרים.", label="כרך ד'", children=[
    N("kerech-4-maamar-1", "מאמר ראשון", "מחולק לשני סדרים.", label="מאמר ראשון", children=[
        N("kerech-4-maamar-1-seder-1", "האהבה הכוללת", "סדר א'", pdf="v4-e1-s1.pdf", label="סדר א'"),
        N("kerech-4-maamar-1-seder-2", "היראה העליונה", "סדר ב'", pdf="v4-e1-s2.pdf", label="סדר ב'"),
    ]),
    N("kerech-4-maamar-2", "מאמר שני", "החוברת טרם הוכנה.", label="מאמר שני"),
    N("kerech-4-maamar-3", "הענוה האצילית", "מאמר שלישי", pdf="v4-e3.pdf", label="מאמר שלישי"),
    N("kerech-4-maamar-4", "השלום", "מאמר רביעי", pdf="v4-e4.pdf", label="מאמר רביעי"),
    N("kerech-4-maamar-5", "מאמר חמישי", "החוברת טרם הוכנה.", label="מאמר חמישי"),
])

VOLUMES = [v1, v2, v3, v4]

# --- helpers ---------------------------------------------------------------

def available(node):
    """A node is reachable if it has a PDF or any reachable descendant."""
    return bool(node["pdf"]) or any(available(c) for c in node["children"])

def page_path(node):
    return f"pages/{node['slug']}.html"

def head(title, desc, depth):
    up = "../" * depth
    return f'''<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@400;500;700&family=Heebo:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="{up}assets/css/style.css">
</head>
<body>
'''

def header(depth):
    up = "../" * depth
    pages = up + "pages/" if depth == 0 else ""
    links = "\n".join(
        f'        <a href="{pages}{v["slug"]}.html">{v["label"]}</a>' for v in VOLUMES)
    return f'''
  <header class="site-header">
    <div class="container site-header__inner">
      <p class="site-title"><a href="{up}index.html">{SITE}</a></p>
      <nav class="site-nav" aria-label="ניווט ראשי">
        <a href="{up}index.html">דף הבית</a>
{links}
      </nav>
    </div>
  </header>
'''

def tail(depth):
    up = "../" * depth
    return f'''
  <script src="{up}assets/js/main.js"></script>
</body>
</html>
'''

def breadcrumb(trail, depth):
    """trail: list of (href, text); last item is the current page."""
    up = "../" * depth
    items = [f'<a href="{up}index.html">דף הבית</a>']
    for href, text in trail[:-1]:
        items.append(f'<a href="{href}">{text}</a>')
    items.append(f'<span aria-current="page">{trail[-1][1]}</span>')
    return ('\n  <nav class="breadcrumb container" aria-label="מסלול ניווט">\n    '
            + '\n    '.join(items) + '\n  </nav>\n')

def cards(nodes, extra_class="", prefix=""):
    out = []
    for n in nodes:
        label = f'<span class="card__index">{n["label"]}</span>' if n["label"] else ""
        if available(n):
            out.append(f'''      <li>
        <a class="card" href="{prefix}{n['slug']}.html">
          {label}
          <h2 class="card__title">{n['title']}</h2>
          <p class="card__text">{n['desc']}</p>
        </a>
      </li>''')
        else:
            out.append(f'''      <li>
        <div class="card card--soon" aria-disabled="true">
          {label}
          <h2 class="card__title">{n['title']}</h2>
          <p class="card__text">{n['desc']}</p>
          <span class="card__badge">בקרוב</span>
        </div>
      </li>''')
    cls = ("card-grid " + extra_class).strip()
    return f'    <ul class="{cls}">\n' + "\n".join(out) + "\n    </ul>\n"

# --- writers ---------------------------------------------------------------
written = []

def write(path, html):
    with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
        f.write(html)
    written.append(path)

def write_home():
    h = head(SITE, "אורות הקודש — ארבעת הכרכים, מחולקים לשערים, מאמרים וסדרים, להורדה ולעיון.", 0)
    h += header(0)
    h += f'''
  <main>
    <section class="hero container">
      <h1>{SITE}</h1>
      <p>ארבעת הכרכים, מחולקים לשערים, למאמרים ולסדרים. כל סדר הוא חוברת נפרדת לעיון ולהורדה.</p>
    </section>
'''
    h += '    <div class="container">\n' + cards(VOLUMES, prefix="pages/") + '    </div>\n  </main>\n'
    h += tail(0)
    write("index.html", h)

def write_node(node, trail):
    """trail: ancestors as list of (href, text) not including this node."""
    depth = 1
    my_trail = trail + [(f"{node['slug']}.html", node["title"])]
    h = head(f"{node['title']} | {SITE}", node["desc"] or node["title"], depth)
    h += header(depth)
    h += breadcrumb(my_trail, depth)
    h += '\n  <main class="page container">\n'
    h += f'    <h1>{node["title"]}</h1>\n'
    if node["desc"]:
        h += f'    <p class="page__lead">{node["desc"]}</p>\n'

    if node["pdf"]:
        key = node["pdf"][:-4]
        preamble, sections = build_reading(FRAGMENTS[key])
        h += f'''
    <div class="reader__actions">
      <a class="btn" href="../assets/pdf/{node['pdf']}" download>הורדה כקובץ PDF</a>
    </div>
'''
        if sections:
            items = "\n        ".join(
                f'<li><a class="picker__item" href="#{a}">{t}</a></li>' for a, t, _ in sections)
            h += f'''
    <nav class="picker" aria-label="בחירת פסקה">
      <p class="picker__label">פסקאות</p>
      <ol class="picker__list">
        {items}
      </ol>
    </nav>
'''
        h += '\n    <article class="reading">\n'
        if preamble:
            h += f'      {preamble}\n'
        for a, t, body in sections:
            h += f'      <section class="piska" id="{a}" data-title="{t}">\n        {body}\n      </section>\n'
        h += '    </article>\n'

    if node["children"]:
        heading = "תתי-נושאים"
        if any(c["slug"].count("seder") for c in node["children"]):
            heading = "סדרים"
        if all("shaar" in c["slug"] or "hakdama" in c["slug"] for c in node["children"]):
            heading = "שערים"
        if all("maamar" in c["slug"] for c in node["children"]):
            heading = "מאמרים"
        h += f'\n    <h2 class="section-heading">{heading}</h2>\n'
        h += cards(node["children"], "card-grid--auto")

    back_href, back_text = (trail[-1] if trail else (None, None))
    if back_href:
        h += f'\n    <a class="back-link" href="{back_href}">חזרה אל {back_text}</a>\n'
    else:
        h += '\n    <a class="back-link" href="../index.html">חזרה לדף הבית</a>\n'
    h += '  </main>\n'
    h += tail(depth)
    write(page_path(node), h)

    for c in node["children"]:
        write_node(c, my_trail)

# --- run -------------------------------------------------------------------
pages_dir = os.path.join(ROOT, "pages")
for f in os.listdir(pages_dir):
    os.remove(os.path.join(pages_dir, f))
write_home()
for v in VOLUMES:
    write_node(v, [])
print(len(written), "pages written")
