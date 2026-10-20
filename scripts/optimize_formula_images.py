"""Repair image formulae with the shared v1.4.0 reading classifier.
Usage: python scripts/optimize_formula_images.py <xhtml_file_or_dir>
Preserves text, image attributes and repeated resources; adds layout hooks only.
"""
import sys
from pathlib import Path
from reading_layout import (
    has_math_formula as _has_math_formula, normalise_images_for_reading,
    normalise_reading_layout, parse_document, parse_xml_document,
)


def has_math_formula(alt_text: str | None) -> bool:
    return _has_math_formula(alt_text or "")


def process(html: str, *, html_dir: Path | None = None) -> str:
    soup = parse_document(html)
    before = soup.get_text()
    normalise_images_for_reading(soup, set(), html_dir=html_dir, deduplicate=False)
    normalise_reading_layout(soup)
    if soup.get_text() != before:
        raise ValueError("Content changed while repairing image formulae")
    return str(soup)


def process_path(target: Path) -> int:
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(p for p in target.rglob("*")
                       if p.is_file() and p.suffix.lower() in {".xhtml", ".html", ".htm"})
    else:
        raise SystemExit(f"路径不存在：{target}")
    for path in files:
        source = path.read_text(encoding="utf-8")
        parse_xml_document(source)
        result = process(source, html_dir=path.parent)
        parse_xml_document(result)
        path.write_text(result, encoding="utf-8", newline="")
        print(f"Updated {path}")
    return len(files)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法：python scripts/optimize_formula_images.py <xhtml_file_or_dir>")
    print(f"完成，共处理 {process_path(Path(sys.argv[1]))} 个文件。")
