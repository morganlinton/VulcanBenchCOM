"""Regression checks for derived data, pricing and publication copy."""

import copy
import json
import unittest

from check_benchmark_index import ROOT
from check_writing import forbidden
from derive_swe_v4_sensitivity import DATA, derive
from verify_swe_v4_costs import verify


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((DATA / "runs.json").read_text())["rows"]
        cls.costs = json.loads((DATA / "costs.json").read_text())

    def test_reproducible_derivatives(self):
        for name, content in derive().items():
            self.assertEqual((DATA / name).read_bytes(), content.encode())

    def test_cost_mutations_are_rejected(self):
        for mutate in (
            lambda c: c["rows"][0].__setitem__("estimated_usd", 0),
            lambda c: c["astra_rates_per_million"].__setitem__("input", 11),
            lambda c: c["rows"][115]["parts"][1]["usage"].__setitem__("inputTokens", 0),
            lambda c: c["groups"][0].__setitem__("mean_usd", 0),
        ):
            changed = copy.deepcopy(self.costs)
            mutate(changed)
            with self.assertRaises(AssertionError):
                verify(changed, self.rows)

    def test_sensitive_bindings_and_intervals(self):
        page = (ROOT / "benchmarks/swe-v4-astra-fable51.html").read_text()
        for r in json.loads((DATA / "sensitivity.json").read_text())["rows"]:
            for value in (f'{r["fable_minus_astra_points"]:+.2f}',
                          f'{r["paired_bootstrap_95_low"]:+.2f} to {r["paired_bootstrap_95_high"]:+.2f}',
                          f'{r["fable_astra_only"]-r["astra_astra_only"]:+.2f}',
                          f'{r["fable_claude_only"]-r["astra_claude_only"]:+.2f}',
                          f'{r["fable_matched_nonfallback"]-r["astra_matched_nonfallback"]:+.2f} (n={r["matched_nonfallback_n"]})'):
                self.assertIn(value, page)

    def test_writing_guard(self):
        for text in (chr(0x2013), chr(0x2014), "&" + "mdash;", "&#" + "8211;"):
            self.assertTrue(forbidden(text))
        self.assertFalse(forbidden("20% Code quality: low to max."))

    def test_current_site_claims(self):
        home = (ROOT / "index.html").read_text()
        self.assertNotIn("No model judges another model", home)
        self.assertNotIn("Memorization cannot help", home)
        self.assertIn("benchmarks/swe-v4-astra-fable51.html", home)
        self.assertNotIn("new eval suite is built", (ROOT / "leaderboard.html").read_text())


if __name__ == "__main__":
    unittest.main()
