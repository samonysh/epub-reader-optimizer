"""Regression checks for local publisher compatibility and failure behavior."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reading_layout as layout
from optimize_epub import optimize_epub
from optimize_formula_images import process


class LegacyMarkupTests(unittest.TestCase):
    def test_formula_repair_preserves_attributes_entities_and_code_and_is_idempotent(self):
        source = ("<html><head><title>Test</title></head><body>"
                  "<p>For <img src='eq.gif' alt='x_i' id='eq' width='24' style='height:1em'/> &amp; y.</p>"
                  "<p class='图'><img src='display.gif' alt='\\sum{x}'/></p>"
                  "<pre class='代码无行号'><code>  first()\n\n    next()</code></pre>"
                  "<figure><img src='diagram.png' alt='A figure showing fact_sales in a database diagram with many linked tables.'/></figure>"
                  "</body></html>")
        result = process(source)
        self.assertEqual(process(result), result)
        soup = layout.parse_document(result)
        image = soup.find(id="eq")
        self.assertEqual(image["width"], "24")
        self.assertEqual(image["style"], "height:1em")
        self.assertEqual(image["src"], "eq.gif")
        self.assertIn("formula-img", image["class"])
        self.assertIn("formula-block", soup.select_one("p.图")["class"])
        self.assertIn("epub-image", soup.figure.img["class"])
        self.assertEqual(soup.pre.get_text(), "  first()\n\n    next()")
        self.assertEqual(soup.get_text(), layout.parse_document(source).get_text())

    def test_language_marked_pairs_do_not_resize_inline_fragments(self):
        soup = layout.parse_document('<body><p lang="en">Source</p><p lang="zh-CN">译文</p>'
                                     '<p xml:lang="en">Next</p><p xml:lang="zh">译文</p>'
                                     '<h1>Heading <span lang="zh">标题</span></h1></body>')
        layout.normalise_reading_layout(soup)
        self.assertEqual(len(soup.select("p.reading-source")), 2)
        self.assertFalse(soup.h1.get("class"))


class ArtifactFailureTests(unittest.TestCase):
    def setUp(self):
        self.scratch = ROOT / ".test-scratch"
        self.scratch.mkdir(exist_ok=True)

    def test_malformed_input_does_not_replace_previous_output(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as directory:
            source, output = Path(directory)/"in.epub", Path(directory)/"out.epub"
            with zipfile.ZipFile(source, "w") as z:
                z.writestr("mimetype", "application/epub+zip")
                z.writestr("chapter.xhtml", "<html><head></head><body><p>Unclosed</body></html>")
            output.write_bytes(b"previous output")
            with self.assertRaises(Exception):
                optimize_epub(source, output, check=False)
            self.assertEqual(output.read_bytes(), b"previous output")

    def test_failed_checker_preserves_output_and_retains_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as directory:
            source, output = Path(directory)/"in.epub", Path(directory)/"out.epub"
            with zipfile.ZipFile(source, "w") as z:
                z.writestr("mimetype", "application/epub+zip")
                z.writestr("chapter.xhtml", "<html><head><title>Test</title></head><body><p>Text</p></body></html>")
            output.write_bytes(b"previous output")
            def reject(candidate):
                report = candidate.with_suffix(".epubcheck.json")
                report.write_text(json.dumps({"error": "fixture"}), encoding="utf-8")
                return False, report, 0, 1, 0
            with patch.object(layout, "validate_epub", side_effect=reject), self.assertRaises(ValueError):
                optimize_epub(source, output)
            self.assertEqual(output.read_bytes(), b"previous output")
            self.assertEqual(json.loads(output.with_suffix(".epubcheck.json").read_text())["error"], "fixture")


if __name__ == "__main__":
    unittest.main()
