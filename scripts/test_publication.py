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

    def test_home_lists_the_five_newest_reports(self):
        # The home page shows the five newest Benchmarks entries, newest first; Benchmarks carries every report.
        home = (ROOT / "index.html").read_text()
        index = (ROOT / "benchmarks.html").read_text()
        newest = re.findall(r'<h3 id="[^"]+"><a href="(benchmarks/[^"]+)"', index)[:5]
        self.assertEqual(re.findall(r'<a class="report-row" href="(benchmarks/[^"]+)"', home), newest)


if __name__ == "__main__":
    unittest.main()
