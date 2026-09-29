"""Every benchmark report can be shared: a post-to-X link and the image-share script.

share.js adds "Share table" and "Share card" buttons to each report's tables
and model cards. It supports both layouts: numbered reports (.article-head,
table.data) and suite reports (Frontier v4 and Verdict: main h1,
table.suite-results). A new report copied from any template must keep both.
"""

from __future__ import annotations

import re
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = sorted((ROOT / "benchmarks").glob("*.html"))
SCRIPT = re.compile(r'<script src="(?:\.\./|/)share\.js\?v=\d+" defer></script>')


class ShareButtonTests(unittest.TestCase):
    def test_every_report_loads_share_js_once(self):
        self.assertGreater(len(REPORTS), 20)
        for page in REPORTS:
            text = page.read_text()
            with self.subTest(page=page.name):
                self.assertEqual(len(SCRIPT.findall(text)), 1)
                self.assertNotIn("table-share.js", text)

    def test_every_report_links_a_post_to_x_for_itself(self):
        for page in REPORTS:
            text = page.read_text()
            with self.subTest(page=page.name):
                links = re.findall(r'href="(https://x\.com/intent/post\?[^"]+)"', text)
                self.assertTrue(links, "no post-to-X link")
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(links[0].replace("&amp;", "&")).query)
                self.assertEqual(query["url"], [f"https://vulcanbench.com/benchmarks/{page.name}"])
                self.assertTrue(query["text"][0].strip())

    def test_suite_report_posts_name_the_suite(self):
        for page in REPORTS:
            if not page.name.startswith(("swe-v4-", "verdict-")):
                continue
            text = urllib.parse.unquote(page.read_text())
            with self.subTest(page=page.name):
                suite = "Frontier v4" if page.name.startswith("swe-v4-") else "Verdict"
                self.assertRegex(text, rf"intent/post\?text=[^&]*VulcanBench {suite}")

    def test_share_js_handles_both_layouts(self):
        js = (ROOT / "share.js").read_text()
        self.assertIn('"table.data, table.suite-results"', js)
        self.assertIn('".table-scroll, .suite-table-scroll"', js)
        self.assertIn('querySelectorAll("th, td")', js)
        self.assertFalse((ROOT / "table-share.js").exists())


if __name__ == "__main__":
    unittest.main()
