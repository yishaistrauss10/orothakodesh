Scripts that generate the site.

  convert.py    reads a booklet PDF and returns HTML blocks (text from
                pdftotext, structure from PyMuPDF font/geometry data)
  structure.py  turns those blocks into sections with a table of contents
  gen.py        writes index.html and every page under pages/

Regenerate everything (needs python3, poppler-utils and pymupdf):

  python3 tools/gen.py

gen.py reads the converted text from fragments.json, which is produced by:

  python3 -c "import glob,json,os,sys; sys.path.insert(0,'tools'); \
    from convert import convert; \
    json.dump({os.path.basename(f)[:-4]: convert(f) for f in sorted(glob.glob('assets/pdf/*.pdf'))}, \
    open('fragments.json','w'), ensure_ascii=False)"

Editing the generated HTML by hand is fine; just remember that rerunning
gen.py overwrites everything under pages/.
