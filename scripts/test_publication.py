"""Regression checks for publication copy and the writing guard."""

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
        self.assertIn("benchmarks/swe-v4-astra-fable51-v34.html", home)
        self.assertNotIn("benchmarks/swe-v4-astra-fable51.html", home)
        self.assertNotIn("new eval suite is built", (ROOT / "leaderboard.html").read_text())


if __name__ == "__main__":
    unittest.main()
