"""Static, dependency-free checks for the suite-separated benchmark index."""

import html
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class IndexParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.reports = []
        self.rows = {}
        self.key = None
        self.cell = None
        self.structure = []
        self.structure_errors = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"main", "section", "article", "div", "table", "tbody", "details"}:
            self.structure.append(tag)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for attr in ("href", "src"):
            if attr in attrs:
                self.links.append(attrs[attr])
        if "report-row" in attrs.get("class", "").split():
            self.reports.append(attrs["href"])
        if tag == "tr" and "data-model" in attrs:
            self.key = (attrs["data-model"], attrs["data-effort"])
            if self.key in self.rows:
                raise ValueError(f"Duplicate result: {self.key}")
            self.rows[self.key] = []
        if tag in {"th", "td"} and self.key:
            self.cell = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in {"main", "section", "article", "div", "table", "tbody", "details"}:
            if not self.structure or self.structure[-1] != tag:
                self.structure_errors.append(tag)
            else:
                self.structure.pop()
        if tag in {"th", "td"} and self.cell is not None:
            self.rows[self.key].append(self.cell.strip())
            self.cell = None
        if tag == "tr":
            self.key = None


class BenchmarkIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "benchmarks.html").read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.html)
        cls.report_html = (ROOT / "benchmarks/swe-v4-astra-fable51-v34.html").read_text()
        cls.report = IndexParser()
        cls.report.feed(cls.report_html)

    def test_structure_and_suite_boundaries(self):
        self.assertEqual(self.page.structure_errors, [])
        self.assertEqual(self.page.structure, [])
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))
        self.assertIn("swe-v4", self.page.ids)
        self.assertIn("archive", self.page.ids)
        self.assertLess(self.html.index('id="swe-v4"'), self.html.index('id="archive"'))
        self.assertLess(self.html.index('id="archive"'), self.html.index('class="report-row"'))

    def test_all_historical_reports_retained(self):
        self.assertEqual(len(self.page.reports), 20)
        self.assertEqual({int(Path(p).name[:2]) for p in self.page.reports}, set(range(1, 21)))

    def test_local_links_and_anchor_targets(self):
        for page in (self.page, self.report):
            self.assertEqual(page.structure_errors, [])
            self.assertEqual(page.structure, [])
            self.assertEqual(len(page.ids), len(set(page.ids)))
            for link in page.links:
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc:
                    continue
                if parsed.path:
                    target = ROOT / unquote(parsed.path).lstrip("/")
                    self.assertTrue(target.is_file(), link)
                    if parsed.fragment and target.suffix == ".html":
                        linked = IndexParser()
                        linked.feed(target.read_text())
                        self.assertIn(parsed.fragment, linked.ids)
                elif parsed.fragment:
                    self.assertIn(parsed.fragment, page.ids)

    def test_no_em_or_en_dashes(self):
        for name in ("benchmarks.html", "benchmarks/swe-v4-astra-fable51-v34.html", "benchmarks-suites.css", "AGENTS.md", "README.md", "index.html", "methodology.html", "leaderboard.html", "llms.txt"):
            text = html.unescape((ROOT / name).read_text())
            self.assertNotIn(chr(0x2014), text, name)
            self.assertNotIn(chr(0x2013), text, name)


if __name__ == "__main__":
    unittest.main()
