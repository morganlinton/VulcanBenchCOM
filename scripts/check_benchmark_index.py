"""Static, dependency-free checks for the suite-separated benchmark index."""

import csv
import hashlib
import html
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EFFORTS = {"low", "medium", "high", "extra-high", "max"}


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
        cls.report_html = (ROOT / "benchmarks/swe-v4-astra-fable51.html").read_text()
        cls.report = IndexParser()
        cls.report.feed(cls.report_html)
        with (ROOT / "assets/data/swe-v4-astra-fable51-scores.csv").open(newline="") as source:
            cls.scores = list(csv.DictReader(source))
        with (ROOT / "assets/data/swe-v4-astra-fable51-costs.csv").open(newline="") as source:
            cls.costs = {(r["model"], r["effort"]): r for r in csv.DictReader(source)}

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

    def test_exact_user_selected_card(self):
        card = ROOT / "assets/cards/swe-v4-astra-fable51.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(),
                         "138c96d9fdffab4845d1b373c035b71d180272a9901fcb98bb7ad04ef8dd84b3")

    def test_no_em_or_en_dashes(self):
        for name in ("benchmarks.html", "benchmarks/swe-v4-astra-fable51.html", "benchmarks-suites.css", "AGENTS.md", "README.md", "index.html", "methodology.html", "leaderboard.html", "llms.txt"):
            text = html.unescape((ROOT / name).read_text())
            self.assertNotIn(chr(0x2014), text, name)
            self.assertNotIn(chr(0x2013), text, name)

    def test_every_displayed_result_matches_sources(self):
        expected_keys = {(model, effort) for model in ("astra", "fable") for effort in EFFORTS}
        self.assertEqual(set(self.report.rows), expected_keys)
        self.assertEqual(set(self.costs), expected_keys)
        self.assertEqual(len(self.scores), 10)
        for row in self.scores:
            model = "astra" if row["model"] == "GPT-6 Astra" else "fable"
            key = (model, row["effort"])
            cost = self.costs[key]
            self.assertEqual(int(row["n"]), 23)
            self.assertEqual(int(cost["n"]), 23)
            actual = self.report.rows[key][2:]
            expected = [f'{float(row["combined"]):.2f}%',
                        f'{float(row["code_quality"]):.2f}',
                        f'{float(row["mean_minutes"]):.1f}',
                        f'{int(row["raw_tokens"]) / 23 / 1e6:.2f}M',
                        f'${float(cost["mean_usd"]):.2f}']
            self.assertEqual(actual, expected, key)
            weighted = sum(float(row[field]) * weight for field, weight in
                           (("functional", .50), ("automated_quality", .15),
                            ("security", .15), ("code_quality", .20)))
            self.assertAlmostEqual(weighted, float(row["combined"]), delta=.01)
            self.assertAlmostEqual(float(cost["mean_usd"]) * 23, float(cost["total_usd"]))

    def test_cost_totals_and_comparative_claims(self):
        totals = {model: sum(float(r["total_usd"]) for (m, _), r in self.costs.items() if m == model)
                  for model in ("astra", "fable")}
        self.assertEqual(f'{totals["astra"]:.2f}', "225.04")
        self.assertEqual(f'{totals["fable"]:,.2f}', "1,159.10")
        upper = sum(float(r["long_context_upper_total_usd"])
                    for (m, _), r in self.costs.items() if m == "astra")
        self.assertEqual(f"{upper:.2f}", "419.42")
        for effort in EFFORTS:
            self.assertLess(float(self.costs["astra", effort]["long_context_upper_mean_usd"]),
                            float(self.costs["fable", effort]["mean_usd"]))
            astra, fable = [next(r for r in self.scores if r["effort"] == effort
                               and (r["model"] == "GPT-6 Astra") == (m == "astra"))
                            for m in ("astra", "fable")]
            self.assertLess(float(astra["mean_minutes"]), float(fable["mean_minutes"]))
        best = max(self.scores, key=lambda r: float(r["combined"]))
        self.assertEqual((best["model"], best["effort"]), ("Fable 5.1 with fallbacks", "max"))
        self.assertEqual(sum(int(r["solver_fallback_runs"]) for r in self.scores), 11)


if __name__ == "__main__":
    unittest.main()
