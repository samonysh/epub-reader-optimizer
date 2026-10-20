"""Reading layout adapted from samonysh/epub-translator v1.4.0.
Upstream: 817c210af90555764a2f56a292c3cb007b7c3bb1 (2026-10-19).
Only layout, XML/EPUB handling and validation are included; no translation API.
See docs/upstream-styles.md for local adaptations.
"""
from __future__ import annotations
import html
from html.entities import name2codepoint
import json
import os
import re
import struct
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup, NavigableString, Tag

def document_files(root: Path) -> List[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".xhtml", ".html", ".htm"})


def parse_xml_document(raw: str) -> ET.Element:
    """Validate XML without fetching the XHTML 1.x external entity DTD.

    Legacy EPUBs use XHTML's named entities such as &nbsp;. Resolve only the
    standard HTML4 entity names locally; unknown entities and malformed XML
    still fail instead of being silently repaired by the HTML parser.
    """
    raw = re.sub(r"&([A-Za-z][A-Za-z0-9]+);", lambda m:
                 f"&#{name2codepoint[m[1]]};" if m[1] in name2codepoint else m[0], raw)
    return ET.fromstring(raw)


def parse_document(raw: str) -> BeautifulSoup:
    """Keep the convenient HTML DOM while restoring XML foreign-content case.

    html.parser lowercases viewBox/linearGradient/definitionURL. Restore names
    from the original XML before any edits; no optional XML library is needed.
    """
    soup = BeautifulSoup(raw, "html.parser")
    try:
        root = parse_xml_document(raw)
    except ET.ParseError:
        # Unit-level fragments may have multiple roots. Packaged XHTML is
        # separately required to be well-formed by the pipeline preflight.
        return soup
    local = lambda name: str(name).rsplit("}", 1)[-1].rsplit(":", 1)[-1]
    originals = [n for n in root.iter() if local(n.tag) in {"svg", "math"}]
    parsed = [n for n in soup.find_all(True) if local(n.name).lower() in {"svg", "math"}]
    if len(originals) != len(parsed):
        raise ValueError("Foreign content structure changed during parsing")
    for old, new in zip(originals, parsed):
        old_nodes, new_nodes = list(old.iter()), [new] + new.find_all(True)
        if len(old_nodes) != len(new_nodes):
            raise ValueError("SVG/MathML descendants changed during parsing")
        for original, node in zip(old_nodes, new_nodes):
            if local(original.tag).lower() != local(node.name).lower():
                raise ValueError("SVG/MathML element order changed during parsing")
            prefix = node.name.rsplit(":", 1)[0] + ":" if ":" in node.name else ""
            node.name = prefix + local(original.tag)
            attr_names = {local(key).lower(): local(key) for key in original.attrib}
            for key in list(node.attrs):
                replacement = attr_names.get(local(key).lower())
                if replacement:
                    prefix = key.rsplit(":", 1)[0] + ":" if ":" in key else ""
                    new_key = prefix + replacement
                    if new_key != key:
                        node.attrs[new_key] = node.attrs.pop(key)
    return soup


def read_epub_version(root: Path) -> str:
    for opf in sorted(root.rglob("*.opf")):
        return ET.parse(opf).getroot().get("version", "3.0")
    return "3.0"


def serialize_document(soup: BeautifulSoup, epub_version: str = "3.0") -> str:
    if epub_version.startswith("2"):
        for node in soup.find_all(attrs={"aria-hidden": True}):
            if any(c.startswith("translated-") for c in _classes_of(node)):
                node.attrs.pop("aria-hidden", None)
    return str(soup)


def _classes_of(node: Tag) -> List[str]:
    c = node.get("class", [])
    if isinstance(c, str):
        return c.split()
    return list(c or [])


def _add_class(node: Tag, class_name: str) -> None:
    node["class"] = list(dict.fromkeys(_classes_of(node) + [class_name]))


ILLUSTRATION_CLASS = "epub-image"


GLYPH_CLASS = "epub-inline-image"


FIXED_SIZE_CLASS = "epub-fixed-image"


STYLED_SIZE_CLASS = "epub-styled-image"


FIGURE_CONTAINER_HINTS = ("figure", "cover", "mediaobject", "imageobject", "illustration")


CODE_CONTAINER_CLASSES = {
    "ProgramCode", "programcode", "programcode1", "LineGroup", "FixedLine",
    "CodeBlock", "code-block", "code", "Code", "listing", "Listing",
    "programlisting", "screen", "literallayout",
    "fixedline", "fixedline1", "代码无行号",
}


BIG_IMAGE_MIN_EDGE = 120


BIG_IMAGE_MIN_AREA = 20000


AUTHORED_SIZE_MIN = 60


TEXT_RUN_TAGS = {
    "p", "li", "td", "th", "dd", "dt", "figcaption", "caption", "span", "a",
    "em", "strong", "i", "b", "sup", "sub", "small",
    "h1", "h2", "h3", "h4", "h5", "h6",
}


MATH_ALT_RE = re.compile(r"\\[A-Za-z]+|[\\{}]")


NON_MATH_ALT_LABELS = {
    "pic", "pics", "image", "images", "img", "figure", "fig", "figs", "graphic",
    "photo", "picture", "cover", "logo", "art", "icon", "unnamed", "untitled",
    "placeholder", "spacer", "blank",
}


IMAGE_SIZE_CACHE: Dict[str, Optional[Tuple[int, int]]] = {}


def _sniff_image_size(data: bytes) -> Optional[Tuple[int, int]]:
    """Read intrinsic dimensions from PNG/GIF/JPEG/WEBP headers without decoding."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])  # type: ignore[return-value]
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])  # type: ignore[return-value]
    if data[:2] == b"\xff\xd8":
        index = 2
        while index < len(data) - 9:
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack(">HH", data[index + 5:index + 9])
                return width, height
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            index += 2 + struct.unpack(">H", data[index + 2:index + 4])[0]
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and data[12:16] == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    return None


def image_pixel_size(src: str, html_dir: Optional[Path]) -> Optional[Tuple[int, int]]:
    """Resolve an <img src> against its HTML file and read the real pixel size."""
    if not src or html_dir is None:
        return None
    target = (html_dir / unquote(src.split("#", 1)[0])).resolve()
    key = str(target)
    if key in IMAGE_SIZE_CACHE:
        return IMAGE_SIZE_CACHE[key]
    size: Optional[Tuple[int, int]] = None
    try:
        with target.open("rb") as handle:
            size = _sniff_image_size(handle.read(4096))
    except OSError:
        size = None
    IMAGE_SIZE_CACHE[key] = size
    return size


def _is_big_image(size: Optional[Tuple[int, int]]) -> bool:
    """Unknown size is treated as large: structure and alt text still decide."""
    if size is None:
        return True
    width, height = size
    return max(width, height) >= BIG_IMAGE_MIN_EDGE or width * height >= BIG_IMAGE_MIN_AREA


def alt_describes_illustration(alt: str) -> bool:
    """True for a figure-caption-like alt, False for maths or short glyph labels."""
    value = " ".join((alt or "").split())
    if len(value) < 40 or len(value.split()) < 6:
        return False
    if MATH_ALT_RE.search(value):
        return False
    letters = sum(1 for char in value if char.isalpha())
    return letters / len(value) >= 0.55


def _ancestor_matches(image: Tag, predicate, levels: int = 4) -> bool:
    node = image.parent
    for _ in range(levels):
        if node is None or not isinstance(node, Tag):
            return False
        if predicate(node):
            return True
        node = node.parent
    return False


def _is_figure_container(node: Tag) -> bool:
    if (node.name or "").lower() == "figure":
        return True
    hay = (" ".join(_classes_of(node)) + " " + (node.get("id") or "")).lower()
    return any(hint in hay for hint in FIGURE_CONTAINER_HINTS)


def _is_code_container(node: Tag) -> bool:
    if (node.name or "").lower() in {"pre", "code"}:
        return True
    return any(cls in CODE_CONTAINER_CLASSES for cls in _classes_of(node))


def _length_attribute(value: object) -> Optional[int]:
    """Parse an HTML width/height attribute (``85``, ``85px``) into pixels."""
    text = str(value or "").strip().lower()
    if text.endswith("px"):
        text = text[:-2].strip()
    return int(text) if text.isdigit() else None


def has_authored_size(image: Tag) -> bool:
    """True when width= and height= both ask for a deliberate, non-tiny size."""
    width = _length_attribute(image.get("width"))
    height = _length_attribute(image.get("height"))
    if width is None or height is None:
        return False
    return width >= AUTHORED_SIZE_MIN and height >= AUTHORED_SIZE_MIN


INLINE_STYLE_SIZE_RE = re.compile(
    r"(?:^|;)\s*(?:width|height)\s*:\s*([0-9]*\.?[0-9]+)\s*(%|px|em|rem|pt)(?![0-9a-z%])",
    re.IGNORECASE,
)


def has_inline_style_size(image: Tag) -> bool:
    """识别出版社写在 style 中的尺寸，避免二维码等图被压成行内字高。"""
    for match in INLINE_STYLE_SIZE_RE.finditer(image.get("style") or ""):
        value, unit = float(match.group(1)), match.group(2).lower()
        if unit == "%" or unit in {"px", "pt"} and value >= AUTHORED_SIZE_MIN:
            return True
        if unit in {"em", "rem"} and value >= 2:
            return True
    return False


def classify_image(image: Tag, size: Optional[Tuple[int, int]] = None) -> str:
    """Decide how an <img> is displayed: block illustration, inline glyph or authored size.

    Structure wins over prose: a figure/cover container always means an
    illustration, because the reading baseline used to clamp everything inside
    such a container to 1.5em (~24px) -- the "thumbnail diagram" defect.  In a
    code listing or a text run the resource has to look like an illustration
    (large, plus caption-like alt inside a paragraph) so that 22px placeholders
    and code glyphs stay inline.  Failing everything else, an explicit
    width=/height= pair keeps the size its publisher authored instead of the
    sentence-height cap.
    """
    if (image.get("role") or "").strip().lower() == "doc-cover":
        return ILLUSTRATION_CLASS
    big = _is_big_image(size)
    caption_like = big and alt_describes_illustration(image.get("alt", "") or "")
    if _ancestor_matches(image, _is_code_container, levels=5):
        return ILLUSTRATION_CLASS if caption_like else GLYPH_CLASS
    if _ancestor_matches(image, _is_figure_container):
        return ILLUSTRATION_CLASS
    if has_inline_style_size(image):
        return STYLED_SIZE_CLASS
    if caption_like:
        return ILLUSTRATION_CLASS
    if big:
        parent = image.parent
        if not isinstance(parent, Tag) or (parent.name or "").lower() not in TEXT_RUN_TAGS:
            # A standalone wrapper (div/section/body) around a large image is an
            # illustration even when the alt text is empty or decorative.
            return ILLUSTRATION_CLASS
    if has_authored_size(image):
        return FIXED_SIZE_CLASS
    return GLYPH_CLASS


def is_illustration_caption_image(image: Tag) -> bool:
    """Figure structure outranks maths quoted in descriptive alternative text."""
    if image.find_parent(["math", "svg"]) is not None:
        return False
    src = image.get("src", "") or ""
    if re.search(r"_TeX_(?:I?Eq|Equ)", src, re.I):
        return False
    if re.search(r"_Fig\d", src, re.I):
        return True
    alt = (image.get("alt") or "").strip()
    # Captions may quote TeX or C structs. Do not let those tokens turn the
    # entire diagram into a sentence-height formula glyph.
    prose = len(alt.split()) >= 6 and sum(c.isalpha() for c in alt) >= 25
    return bool(prose and (
        (image.get("role") or "").strip().lower() == "doc-cover"
        or _ancestor_matches(image, _is_figure_container)
    ))


def formula_from_content(image: Tag) -> bool:
    """Formula evidence from the markup itself, ignoring any `formula-img` class."""
    if image.find_parent(["math", "svg"]) is not None:
        return True
    if {"math-img", "math-formula"} & set(_classes_of(image)):
        return True
    if re.search(r"_TeX_(?:I?Eq|Equ)", image.get("src", "") or "", re.I):
        return True
    if is_illustration_caption_image(image):
        return False
    return has_math_formula((image.get("alt", "") or "").strip())


def _is_formula_image(image: Tag) -> bool:
    """Keep formula images out of illustration sizing/deduplication rules."""
    if is_illustration_caption_image(image):
        return False
    if "formula-img" in _classes_of(image):
        return True
    return formula_from_content(image)


def has_math_formula(alt: str) -> bool:
    """Identify both LaTeX expressions and short inline math symbols."""
    value = alt.strip()
    if not value or value == "{%}":
        return False
    # "PIC" / "image" / "logo" are publisher placeholders, not maths symbols.
    if value.strip(".,;:()[]{}").lower() in NON_MATH_ALT_LABELS:
        return False
    # TeX commands and explicit brace/argument markup are unambiguous. Bare
    # "_" and "^" alone are not matched, because prose alt text frequently
    # contains snake_case identifiers such as fact_sales or get_user_name.
    if re.search(r"\\[A-Za-z]+|[\\{}]|[_^][{\s(]", value):
        return True
    if any(char in value for char in "=+−×÷≤≥≠≈∞√∑∫∈⊂⊆∩∪σμθβαλγδπωε∂"):
        return True
    # A short x_i / v_1 style token is still treated as a math symbol.
    if re.fullmatch(r"[A-Za-zα-ωΑ-Ω0-9][_^][A-Za-z0-9]", value):
        return True
    return len(value) <= 4 and bool(
        re.fullmatch(r"[A-Za-zα-ωΑ-Ω0-9\s,.;]+", value)
    )


def normalise_formula_images(soup: BeautifulSoup) -> None:
    """Give image formulae safe inline/block semantics without changing text."""
    for image in list(soup.find_all("img")):
        if is_illustration_caption_image(image):
            continue
        if not formula_from_content(image):
            continue
        _add_class(image, "formula-img")
        parent = image.parent
        if isinstance(parent, Tag) and parent.name == "span" and "math-inline" in _classes_of(parent):
            continue
        wrapper = soup.new_tag("span")
        wrapper["class"] = ["math-inline"]
        if image.get("alt"):
            wrapper["data-latex"] = image["alt"]
        image.wrap(wrapper)

    # Only formula-only paragraphs become display equations.
    for paragraph in soup.find_all("p"):
        meaningful = [child for child in paragraph.contents
                      if not (isinstance(child, NavigableString) and not child.strip())]
        if len(meaningful) == 1 and isinstance(meaningful[0], Tag):
            only = meaningful[0]
            if only.name == "img" and "formula-img" in _classes_of(only):
                _add_class(paragraph, "formula-block")
            elif only.name == "span" and "math-inline" in _classes_of(only) and only.find("img", class_="formula-img"):
                _add_class(paragraph, "formula-block")


def normalise_images_for_reading(soup: BeautifulSoup, seen_sources: set[str],
                                 html_dir: Optional[Path] = None, *,
                                 deduplicate: bool = False) -> int:
    """Show each ordinary image resource once and assign display classes.

    EPUB conversion pipelines commonly duplicate an illustration in consecutive
    containers or in a translated table clone.  A resource seen earlier in the
    book is removed; formula images are deliberately excluded.

    Classification is structural (see ``classify_image``): judging "inline" by
    whether the parent happens to contain text clamped every captioned
    ``<div class="figure">`` illustration to 1.5em (~24px) -- the thumbnail
    diagram defect -- so structure, alt prose and the real pixel size decide.
    """
    normalise_formula_images(soup)
    removed = 0
    for image in list(soup.find_all("img")):
        if _is_formula_image(image):
            _add_class(image, "formula-img")
            continue
        src = (image.get("src", "") or "").strip()
        if not src:
            continue
        key = src.split("#", 1)[0]
        if html_dir is not None:
            key = str((html_dir / unquote(key)).resolve())
        if deduplicate and key in seen_sources:
            parent = image.parent
            image.decompose()
            # Avoid leaving empty visual paragraphs/figures after deduplication.
            if isinstance(parent, Tag) and parent.name in {"p", "figure", "div"}:
                if not parent.get_text("", strip=True) and not parent.find("img"):
                    parent.decompose()
            removed += 1
            continue
        seen_sources.add(key)
        parent = image.parent
        # Restyling may receive an older artifact with stale formula/inline
        # classes. Keep publisher classes but replace our mutually exclusive ones.
        owned = {ILLUSTRATION_CLASS, GLYPH_CLASS, FIXED_SIZE_CLASS, STYLED_SIZE_CLASS,
                 "formula-img", "reading-portrait", "reading-small-illustration", "reading-wide-illustration"}
        image["class"] = [c for c in _classes_of(image) if c not in owned]
        if isinstance(parent, Tag) and parent.name == "span" and "math-inline" in _classes_of(parent):
            parent.unwrap()
            parent = image.parent
        size = image_pixel_size(src, html_dir)
        display_class = classify_image(image, size)
        _add_class(image, display_class)
        portrait = _ancestor_matches(image, lambda n: any(
            "biography" in c.lower() for c in _classes_of(n)), levels=6)
        if portrait:
            _add_class(image, "reading-portrait")
        elif display_class == ILLUSTRATION_CLASS and size and 60 <= size[0] < 288 and size[1] >= 60:
            _add_class(image, "reading-small-illustration")
        if display_class == ILLUSTRATION_CLASS and not portrait and size and size[0] >= 500 and size[0] / max(size[1], 1) >= 4:
            _add_class(image, "reading-wide-illustration")
            if "reading-image-scroll" not in _classes_of(image.parent):
                image.wrap(soup.new_tag("span", attrs={"class": "reading-image-scroll"}))
        if display_class == ILLUSTRATION_CLASS and isinstance(parent, Tag) \
                and parent.name in {"p", "figure", "div"}:
            _add_class(parent, "epub-image-container")
    return removed


def normalise_reading_layout(soup: BeautifulSoup) -> None:
    """Add idempotent layout hooks without changing prose, code or math content."""
    for zh in soup.select(".translated-zh:not(.translated-inline):not(.translated-noop), p[lang|='zh'], p[xml\\:lang|='zh'], div.para[lang|='zh'], div.para2[lang|='zh'], div.collaboratorsection[lang|='zh']"):
        previous = zh.find_previous_sibling()
        if isinstance(previous, Tag) and previous.name == zh.name and zh.name in {
            "p", "div", "li", "blockquote", "dd", "dt", "figcaption"
        } and "translated-zh" not in _classes_of(previous):
            _add_class(previous, "reading-source")
    for table in list(soup.find_all("table")):
        if table.find_parent("table") is not None:
            continue
        cols = max((sum(int(c.get("colspan", "1")) if str(c.get("colspan", "1")).isdigit() else 1
                        for c in row.find_all(["td", "th"], recursive=False))
                    for row in table.find_all("tr")), default=1)
        if cols >= 5:
            _add_class(table, "reading-table-wide")
        if "reading-table-wrap" not in _classes_of(table.parent):
            wrapper = soup.new_tag("div", attrs={"class": "reading-table-wrap"})
            table.wrap(wrapper)
    for equation in list(soup.select(".Equation, .equation, .formula-block, math[display='block']")):
        if equation.find_parent(class_="reading-equation-scroll") is not None:
            continue
        # A div cannot be inserted into a paragraph. Use an inline-block span
        # there; block equations at body/section level use a div.
        inline = equation.find_parent(["p", "span"]) is not None
        wrapper = soup.new_tag("span" if inline else "div",
                               attrs={"class": "reading-equation-scroll"})
        equation.wrap(wrapper)
    for math in list(soup.find_all("math")):
        if math.find_parent(class_="reading-equation-scroll") is not None:
            continue
        if math.find_parent(class_="reading-inline-math") is None:
            math.wrap(soup.new_tag("span", attrs={"class": "reading-inline-math"}))
    # Only the outer code container gets padding, background and a scroll box.
    for block in soup.find_all(True):
        if not _is_code_container(block) or block.name in {"code", "span", "kbd", "samp", "tt"}:
            continue
        if any(_is_code_container(p) for p in block.parents if isinstance(p, Tag)):
            _add_class(block, "reading-code-content")
        else:
            _add_class(block, "reading-code-block")


def unpack_epub(epub_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "r") as zf:
        names = zf.namelist()
        if len(names) != len(set(names)):
            raise ValueError("EPUB contains duplicate ZIP paths")
        for name in names:
            parts = name.replace("\\", "/").split("/")
            if name.startswith(("/", "\\")) or ".." in parts or any(":" in p for p in parts):
                raise ValueError(f"Unsafe EPUB ZIP path: {name}")
        if zf.read("mimetype") != b"application/epub+zip":
            raise ValueError("Invalid EPUB mimetype")
        zf.extractall(dest)


def pack_epub(src_dir: Path, out_path: Path) -> None:
    src_dir, out_path = src_dir.resolve(), out_path.resolve()
    if out_path.is_relative_to(src_dir):
        raise ValueError("Output EPUB must be outside the extracted directory")
    if (src_dir / "mimetype").read_bytes() != b"application/epub+zip":
        raise ValueError("Invalid EPUB mimetype")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".epub-package-", suffix=".epub", dir=out_path.parent)
    os.close(handle)
    candidate = Path(name)
    try:
        _pack_epub_contents(src_dir, candidate)
        os.replace(candidate, out_path)
    finally:
        candidate.unlink(missing_ok=True)


def _pack_epub_contents(src_dir: Path, out_path: Path) -> None:
    # mimetype 必须 STORED 且为第一个条目
    with zipfile.ZipFile(out_path, "w") as zf:
        mt = src_dir / "mimetype"
        if mt.exists():
            zi = zipfile.ZipInfo("mimetype")
            zi.compress_type = zipfile.ZIP_STORED
            zf.writestr(zi, mt.read_bytes())
        for root, _, files in os.walk(src_dir):
            for name in files:
                p = Path(root) / name
                rel = p.relative_to(src_dir).as_posix()
                if rel == "mimetype":
                    continue
                zf.write(p, rel, compress_type=zipfile.ZIP_DEFLATED)


def validate_epub(epub_path: Path) -> tuple[bool, Path, int, int, int]:
    """检查最终 EPUB 并保存完整报告；工具不可用时向上报告故障。"""
    from epubcheck import EpubCheck

    report_path = epub_path.with_suffix(".epubcheck.json")
    # 避免检查器启动失败后留下上一次运行的报告，造成误判。
    report_path.unlink(missing_ok=True)
    result = EpubCheck(str(epub_path))
    report_path.write_text(
        json.dumps(result.result_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    checker = result.checker
    return (
        result.valid is True,
        report_path,
        checker.nFatal,
        checker.nError,
        checker.nWarning,
    )


def _load_translated_css() -> str:
    """Load the project-owned stylesheet that is embedded in each output EPUB."""
    css_source = Path(__file__).resolve().parent.parent / "assets" / "stylesheet.template.css"
    try:
        return css_source.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"无法读取内建阅读样式：{css_source}") from exc


def inject_css(work_dir: Path) -> None:
    """把 translated.css 放到与 content.opf 同级的 styles 目录或 OEBPS 根，并写入引用。"""
    # 找到所有 xhtml/html 文件
    html_files = document_files(work_dir)
    if not html_files:
        return

    # 把 css 文件放到第一个 html 同级目录
    base = html_files[0].parent
    existing_css = sorted(work_dir.rglob("translated.css"))
    css_path = existing_css[0] if existing_css else base / "translated.css"
    for target in existing_css or [css_path]:
        target.write_text(_load_translated_css(), encoding="utf-8", newline="")

    # 只插入引用，不重新序列化整份 XHTML。XML 解析器可能丢掉 <pre> 中
    # 仅包含空白的文本节点，进而改变原始代码的换行与缩进。
    for hf in html_files:
        raw = hf.read_text(encoding="utf-8")
        # Ensure our stylesheet follows publisher styles, also when restyling an
        # artifact which already contains a translated.css link elsewhere.
        link_re = r'<(?:\w+:)?link\b[^>]*\bhref\s*=\s*["\'][^"\']*translated\.css["\'][^>]*?/?>'
        raw = re.sub(link_re, "", raw, flags=re.IGNORECASE)
        rel = os.path.relpath(css_path, hf.parent).replace("\\", "/")
        close = re.search(r"</(?:\w+:)?head\s*>", raw, re.IGNORECASE)
        if close is None:
            continue
        prefix_match = re.match(r"</(\w+:)?head", close.group(0), re.IGNORECASE)
        prefix = (prefix_match.group(1) or "") if prefix_match else ""
        link = f'<{prefix}link href="{html.escape(rel, quote=True)}" rel="stylesheet" type="text/css"/>'
        hf.write_text(raw[:close.start()] + link + raw[close.start():], encoding="utf-8", newline="")

    # OPF 也只修改 manifest 的闭合处，保留出版社其余元数据与格式。
    opfs = list(work_dir.rglob("*.opf"))
    for opf in opfs:
        raw = opf.read_text(encoding="utf-8")
        if re.search(r'<(?:\w+:)?item\b[^>]*\bhref\s*=\s*["\'][^"\']*translated\.css["\']',
                     raw, re.IGNORECASE):
            continue
        close = re.search(r"</(?:\w+:)?manifest\s*>", raw, re.IGNORECASE)
        if close is None:
            continue
        rel = os.path.relpath(css_path, opf.parent).replace("\\", "/")
        prefix_match = re.match(r"</(\w+:)?manifest", close.group(0), re.IGNORECASE)
        prefix = prefix_match.group(1) or "" if prefix_match else ""
        existing_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', raw))
        item_id = "translated-css"
        while item_id in existing_ids:
            item_id += "-1"
        item = f'<{prefix}item id="{item_id}" href="{html.escape(rel, quote=True)}" media-type="text/css" />'
        opf.write_text(raw[:close.start()] + item + raw[close.start():], encoding="utf-8")
