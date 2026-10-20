# epub-reader-optimizer

Improve Chinese and bilingual EN/ZH EPUB layout while preserving prose, code, formulae, image resources and anchors. Use it as a Codex skill or run the Python scripts directly. No translation API or API key is required.

[中文](README.md) · [Skill workflow (Chinese)](SKILL.md) · [Upstream provenance and adaptations (Chinese)](docs/upstream-styles.md)

The bundled baseline is pinned to [epub-translator v1.4.0](https://github.com/samonysh/epub-translator/tree/817c210af90555764a2f56a292c3cb007b7c3bb1), commit `817c210` (2026-10-19). This identifies the imported version; running the optimizer does not fetch upstream updates.

## Reading layout

- Serif body text, sans-serif headings and monospace code, with Chinese font fallbacks. WenKai embedding is an optional manual workflow.
- Paired spacing for existing EN/ZH paragraphs, undecorated Chinese translations and hierarchy for existing inline heading translations. The optimizer does not translate, reorder paragraphs or merge headings.
- Preserved code indentation and blank lines, with a lightly bordered outer panel and local horizontal scrolling for long lines.
- Separate handling of illustrations, portraits, covers, formulae and icons; repeated images are preserved and very wide diagrams scroll locally.
- Local scrolling for wide tables, MathML and display equations; compatibility with older publisher classes and Sigil formula-image books.
- Dark text on a light page without dark-scheme media rules. Publisher overrides and reader themes still need inspection.

## Install and run

Requires Python 3.10+ and Java available on PATH for the default EPUBCheck step. Run commands from the repository root:

```powershell
python -m pip install -r requirements.txt
java -version
python scripts/optimize_epub.py input.epub output.epub
```

`output.epub` is the exact filename. Passing the same input and output enables in-place updates; prefer a separate file initially. Input XHTML/HTML/HTM must be well-formed XML; this is not a general malformed-HTML repair tool.

| Output or option | Behavior |
|---|---|
| `output.epub` | Replaces the destination after content checks and, by default, EPUBCheck succeed |
| `output.style.json` | Input/output hashes, document count, content-preservation status and validation result |
| `output.epubcheck.json` | Diagnostics from a completed checker run, including failed validation; unavailable tools may produce no new report |
| `--skip-epubcheck` | Explicitly skips validation and labels the result `not_run` |
| `--style-review` | Captures samples after optimization; requires review dependencies |
| `--review-dir PATH` | Sets the screenshot directory; defaults to `.style-review-<stem>` beside the output |
| `--browser-executable PATH` | Uses an installed Chrome/Edge for screenshots |

HTML is reserialized. Content checks compare parsed text, image references, code, MathML/SVG and anchors, rather than XHTML bytes. Other original resources are compared byte for byte, excluding HTML, OPF and the project-owned `translated.css`. The `chapters` report field counts all scanned HTML documents and may include navigation pages.

Content or validation failure, including an unavailable checker, returns a nonzero exit status without replacing the output EPUB. Screenshot review runs after the EPUB and `.style.json` have been written: a review failure also returns nonzero, but the optimized EPUB may already exist. Skipping EPUBCheck is not a validation pass.

## Screenshots and feedback

Playwright is optional for optimization. To capture screenshots:

```powershell
python -m pip install -r requirements-review.txt
python -m playwright install chromium
python scripts/optimize_epub.py input.epub output.epub --style-review --review-dir .style-review-book
```

Alternatively, skip the Chromium download and supply an installed browser:

```powershell
python scripts/review_epub.py output.epub --output .style-review-book --scan-all --browser-executable 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

Use a new review directory for each render: an existing `report.json` prevents overwriting. Feedback registration uses the matching report directory. The browser configurations above are alternatives, not sequential commands against the same directory.

Default viewports are 1050×1080 and 420×1080. Standalone `review_epub.py` supports `--scan-all` (scan all documents at narrow width), `--spread` (default: up to six reading-order samples plus content-category samples), `--plan` and `--compare`. These options do not belong to the optimizer. Integrated `--style-review` samples the book without scanning every document; standalone review does not run EPUBCheck.

Inspect `gallery.html`, PNGs and `report.json`, including `missing_categories`. `awaiting_agent_review` means screenshots still need inspection, `render_failed` means rendering failed, and `agent_reviewed` records accepted feedback. Zero automatic layout issues is not a visual review.

After fixing the shared styles and producing `updated.epub`, reuse sample locations for comparison:

```powershell
python scripts/review_epub.py updated.epub --output .style-review-updated --scan-all --plan .style-review-book/samples.json --compare .style-review-book/report.json
```

Inspect the images as described in `review-task.md`, then fill `feedback.template.json` into `feedback.json`, covering the final artifact hash, every reviewed screenshot and issue dispositions. Register it with:

```powershell
python scripts/review_epub.py updated.epub --output .style-review-updated --accept-feedback .style-review-updated/feedback.json
```

These are reflowed XHTML viewport screenshots, not stable page numbers or real-reader certification.

## Files and stylesheet maintenance

```text
epub-reader-optimizer/
├── SKILL.md                       # Codex skill entry point
├── README.md / README.en.md        # Chinese / English usage
├── requirements.txt               # Core dependencies
├── requirements-review.txt        # Core dependencies + Playwright
├── assets/
│   ├── translated.css             # Untouched upstream baseline
│   ├── reader-compat.css          # Local customizations and publisher compatibility
│   ├── stylesheet.template.css    # Generated standalone base template
│   └── stylesheet.formula-image.css # Standalone template + optional WenKai declarations
├── scripts/
│   ├── optimize_epub.py            # Complete EPUB optimization entry point
│   ├── reading_layout.py           # Shared layout, classification, packaging and checks
│   ├── review_epub.py              # Screenshots, layout scanning and feedback
│   ├── sync_styles.py              # Rebuild both CSS templates
│   ├── optimize_formula_images.py  # Layout repair for extracted documents
│   ├── subset_fonts.py             # WenKai font subsetting
│   └── build_epub.py               # Package an extracted directory
├── tests/                         # Layout and content-preservation regressions
└── docs/upstream-styles.md         # Provenance and historical verification
```

Prefer local customizations in `assets/reader-compat.css`, keeping `assets/translated.css` as the upstream snapshot. Run `python scripts/sync_styles.py` afterwards; it overwrites both generated templates, so do not edit only those outputs. The optimizer embeds the base template as `translated.css` after publisher styles. Copying CSS alone does not classify images or create scroll containers.

## Manual layout and font customization

After extracting a copy, `python scripts/optimize_formula_images.py EXTRACT_DIR` recursively updates `.xhtml/.html/.htm` in place with layout hooks. It does not link CSS, register OPF resources, package the book or run EPUBCheck.

Font files are not distributed or downloaded/embedded by the optimizer. Manual WenKai embedding requires `python -m pip install fonttools brotli`, source fonts, corrected CSS paths and OPF registration. `subset_fonts.py` scans only `OEBPS_DIR/Text/*.xhtml` and deletes each corresponding source TTF from the working copy after successful conversion. Other chapter layouts require adapting character collection first. See [SKILL.md](SKILL.md#解包后定制与可选字体) for filenames, directories and ordering.

Optimize first, then apply final font customizations: another optimizer run reinstalls the base template. `stylesheet.formula-image.css` is an optional manual template and is not selected automatically.

`python scripts/build_epub.py EXTRACT_DIR final.epub` packages and checks ZIP mimetype invariants only, overwriting existing output; place the output outside the extracted directory. It does not run EPUBCheck or the full optimizer's content comparison and candidate replacement protection. Run separate validation and visual checks afterwards. Do not package EPUBs with PowerShell `Compress-Archive`.

## Verification

```powershell
python -m unittest discover -s tests -v
```

EPUBCheck integration tests skip when Java or the checker is missing; browser tests skip unless `EPUB_REVIEW_BROWSER` is set. Full regression requires review dependencies, Java and a working browser path:

```powershell
python -m pip install -r requirements-review.txt
$env:EPUB_REVIEW_BROWSER = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
python -m unittest discover -s tests -v
```

A successful test run with skipped cases is not full verification. Historical synthetic-fixture results are recorded in the [sync notes](docs/upstream-styles.md#本次验证); they do not validate a new book. The companion translation project is [epub-translator](https://github.com/samonysh/epub-translator).
