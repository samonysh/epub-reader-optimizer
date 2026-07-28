# epub-reader-optimizer

Optimize the Chinese reading experience of EPUB files: rewrite CSS, unify bilingual
(EN/ZH) paragraph layout, enforce fonts (e.g. LXGW WenKai), prettify code blocks and
tables, and fix the "white text on white background" issue seen in some readers.

Core idea: **never touch the chapter structure, HTML body text or image assets** of the
original EPUB — only rewrite CSS and the minimal metadata needed to improve reading and
fix rendering defects.

## When to use

- EPUB text is invisible in a reader/editor (white-on-white, black-on-black).
- Ugly fonts, cramped line-height, misaligned figures, broken code blocks, crushed tables.
- A bilingual EPUB that needs to become "Chinese-primary, English-secondary" or
  "English on top, Chinese below".
- You want to force a Chinese font (LXGW WenKai family) into an EPUB.
- "Formula-as-image" EPUBs where a single inline char like `x` / `y` is wrongly forced
  onto its own centered line.

## Directory layout (follows the SkillHub recommended Skill format)

```
epub-reader-optimizer/
├── SKILL.md                      # The only required file: YAML metadata + Markdown instructions
├── README.md / README.en.md      # CN / EN docs
├── scripts/                      # Executable scripts
│   ├── build_epub.py             # Pack a directory into a spec-compliant EPUB (mimetype STORED first)
│   ├── optimize_formula_images.py# HTML structure repair for "formula-as-image" EPUBs
│   └── subset_fonts.py          # LXGW WenKai TTF -> subset WOFF2
└── assets/                       # Templates / resources
    ├── stylesheet.template.css       # Base CSS template for bilingual EPUBs
    └── stylesheet.formula-image.css  # Formula-as-image CSS (inline vs block dual-track)
```

## Environment & dependencies

- Python 3 (used for `zipfile` repacking)
- 7-Zip or any unzip tool (an EPUB is just a zip)
- For the formula-as-image flow: `pip install fonttools brotli`
- Optional: `epubcheck` (stricter validation; not required)

> ⚠️ **Always repack an EPUB with Python `zipfile`**, never with PowerShell's
> `Compress-Archive` — the latter produces a zip that violates the EPUB spec (wrong
> mimetype ordering / compression). `scripts/build_epub.py` handles this for you.

## Usage overview

```
1. Unpack the EPUB (7z x book.epub -oepub_extract -y)
2. Inspect content.opf / toc.ncx / sample chapter XHTML to choose which selectors to rewrite
3. Rewrite stylesheet.css from the assets/ templates (page_styles.css if needed)
4. Formula-as-image EPUBs: first run scripts/optimize_formula_images.py on the XHTML,
   then subset + embed LXGW WenKai with scripts/subset_fonts.py
5. Repack a spec-compliant EPUB with scripts/build_epub.py
6. Self-check: verify mimetype is the first entry and STORED
```

For the full callable workflow, CSS rewrite guidance (white-text fix, forced fonts,
bilingual paragraphs, code blocks, tables, images/formulas, heading hierarchy), font
subsetting details, and the quick troubleshooting table, see [SKILL.md](SKILL.md).

## Companion skill

`epub-translator` (EN->ZH bilingual translation) calls this skill as the final
beautification step after translation.

## License & disclaimer

This skill only rewrites styles and minimal metadata; it never modifies the copyrighted
body text of an EPUB. Use it on ebooks you have the legal right to use.