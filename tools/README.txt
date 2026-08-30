Scripts that generate the site.

  convert.py    reads a booklet PDF and returns HTML blocks (text from
                pdftotext, structure from PyMuPDF font/geometry data)
  structure.py  turns those blocks into sections with a table of contents
  gen.py        writes index.html and every page under pages/

Requirements: python3, poppler-utils (pdftotext) and pymupdf. Install
pymupdf into a virtual environment, never into the system python:

  python3 -m venv .venv && .venv/bin/pip install pymupdf

Regenerate everything:

  python3 tools/gen.py        # uses fragments.json, no pymupdf needed

gen.py reads the converted text from fragments.json, which is produced by:

  .venv/bin/python -c "import glob,json,os,sys; sys.path.insert(0,'tools'); \
    from convert import convert; \
    json.dump({os.path.basename(f)[:-4]: convert(f) for f in sorted(glob.glob('assets/pdf/*.pdf'))}, \
    open('fragments.json','w'), ensure_ascii=False)"

Editing the generated HTML by hand is fine; just remember that rerunning
gen.py overwrites everything under pages/.

Checking the conversion:

  python3 tools/audit.py     compares every page against pdftotext and
                             reports text that went missing, was added, or
                             changed places
  python3 tools/precise.py   reports paragraph breaks the printed page does
                             not support (no extra space, and the line before
                             the break fills the column)
