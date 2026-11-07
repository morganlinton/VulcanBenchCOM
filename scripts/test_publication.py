"""Regression checks for publication copy and the writing guard."""

import re
import unittest

from check_benchmark_index import ROOT
from check_writing import forbidden


class PublicationTests(unittest.TestCase):
    def test_writing_guard(self):
        for text in (chr(0x2013), chr(0x2014), "&" + "mdash;", "&#" + "8211;"):
            self.assertTrue(forbidden(text))
        self.assertFalse(forbidden("33% Code quality: low to max."))

    def test_current_site_claims(self):
        home = (ROOT / "index.html").read_text()
        self.assertNotIn("No model judges another model", home)
        self.assertNotIn("Memorization cannot help", home)
        self.assertIn("benchmarks/swe-v4-astra-fable51-v34.html", (ROOT / "benchmarks.html").read_text())
        self.assertNotIn("benchmarks/swe-v4-astra-fable51.html", home)
        self.assertNotIn("new eval suite is built", (ROOT / "leaderboard.html").read_text())

    def test_every_page_links_the_eval_suite_builder(self):
        # The masthead nav is copied into every page; the old For teams page is gone and only vercel.json may name it.
        for page in ROOT.rglob("*.html"):
            if ".git" in page.parts or "node_modules" in page.parts:
                continue
            text = page.read_text()
            self.assertNotIn("benchmark-your-stack", text, page)
            self.assertNotIn("For teams", text, page)
            self.assertRegex(text, r'href="(\.\./|/)?eval-suite-builder\.html"[^>]*>Eval suite builder</a>', page)
        self.assertIn("benchmark-your-stack", (ROOT / "vercel.json").read_text())

    def test_eval_suite_builder_page_posts_to_the_waitlist_function(self):
        page = (ROOT / "eval-suite-builder.html").read_text()
        self.assertIn('action="/api/waitlist"', page)
        self.assertIn('name="email"', page)
        self.assertIn("VulcanBench Frontier v4", page)
        self.assertNotIn("SWE v4", page)
        function = (ROOT / "api" / "waitlist.js").read_text()
        self.assertIn("BLOB_READ_WRITE_TOKEN", function)
        self.assertIn('access: "private"', function)

    def test_home_lists_the_five_newest_reports(self):
        # The home page shows the five newest Benchmarks entries, newest first; Benchmarks carries every report.
        home = (ROOT / "index.html").read_text()
        index = (ROOT / "benchmarks.html").read_text()
        newest = re.findall(r'<h3 id="[^"]+"><a href="(benchmarks/[^"]+)"', index)[:5]
        self.assertEqual(re.findall(r'<a class="report-row" href="(benchmarks/[^"]+)"', home), newest)


if __name__ == "__main__":
    unittest.main()
