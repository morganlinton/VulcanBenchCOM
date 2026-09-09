"""Stdlib checks for the v3.4 neutral-panel bundle, its report page and the site links to it."""

import csv
import hashlib
import html
import json
import statistics
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

from check_benchmark_index import IndexParser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/swe-v4-astra-fable51-v34"
PAGE = ROOT / "benchmarks/swe-v4-astra-fable51-v34.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-astra-fable51-v34.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
CARD_SHA256 = "81015c5ac4e1055ce4fa5896a4a9416494ba9ac0f8fed0aacada7b245ac96dbb"


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


class NeutralPanelBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.groups = {(g["model"], g["effort"]): g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        with (ROOT / "assets/data/swe-v4-astra-fable51-v34-scores.csv").open(newline="") as source:
            cls.scores = {("astra" if r["model"] == "GPT-6 Astra" else "fable", r["effort"]): r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 230)
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        for r in self.rows:
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
            code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            for p in PANELS:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"],
                                       (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
        self.assertEqual(sum(r["solver_fallback"] for r in self.rows), 11)
        self.assertEqual(len({(r["model"], r["effort"], r["task"]) for r in self.rows}), 230)

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), {(m, e) for m in ("astra", "fable") for e in EFFORTS})
        self.assertEqual(set(self.scores), set(self.groups))
        for key, g in self.groups.items():
            rs = [r for r in self.rows if (r["model"], r["effort"]) == key]
            self.assertEqual(len(rs), 23)
            self.assertEqual(g["n"], 23)
            for field, values in (("combined_33", [r["combined_33"] for r in rs]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in rs]),
                                  ("code_quality", [r["code_quality"] for r in rs]),
                                  ("reviewed_score", [r["reviewed_score"] for r in rs]),
                                  ("intent_recovery", [r["intent_recovery"] for r in rs]),
                                  ("readability", [statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in rs]),
                                  ("maintainability", [statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in rs]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs])):
                mean, se = mean_se(values)
                self.assertAlmostEqual(g[field]["mean"], mean, places=9, msg=(key, field))
                self.assertAlmostEqual(g[field]["se"], se, places=9, msg=(key, field))
            for p in PANELS:
                self.assertAlmostEqual(g["by_panel"][p]["mean"], statistics.mean(r["panels"][p]["reviewed_score"] for r in rs), places=9)
            self.assertEqual(g["passed"], sum(r["functional"] == 1 for r in rs))
            self.assertEqual(g["solver_fallback_runs"], sum(r["solver_fallback"] for r in rs))
            row = self.scores[key]
            for column, field in (("combined_33", "combined_33"), ("combined_20_profile", "combined_20_profile"), ("code_quality", "code_quality"),
                                  ("readability", "readability"), ("maintainability", "maintainability"), ("intent_recovery", "intent_recovery"),
                                  ("mean_minutes", "minutes")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(key, column))
            self.assertAlmostEqual(float(row["combined_33_se"]), g["combined_33"]["se"], places=4)
            self.assertAlmostEqual(float(row["code_quality_se"]), g["code_quality"]["se"], places=4)

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), set(self.groups))
        for key, g in self.groups.items():
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                        f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}', f'{g["maintainability"]["mean"]:.1f}',
                        f'{g["intent_recovery"]["mean"]:.1f}', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows[key][2:], expected, key)
        a, f = self.groups["astra", "max"], self.groups["fable", "max"]
        for label, value in (("Code quality", f'<td>{a["code_quality"]["mean"]:.2f}</td><td>{f["code_quality"]["mean"]:.2f}</td><td>{f["code_quality"]["mean"] - a["code_quality"]["mean"]:+.2f}</td>'),
                             ("Human readability", f'<td>{a["readability"]["mean"]:.1f}</td><td>{f["readability"]["mean"]:.1f}</td><td>{f["readability"]["mean"] - a["readability"]["mean"]:+.1f}</td>'),
                             ("Maintainability", f'<td>{a["maintainability"]["mean"]:.1f}</td><td>{f["maintainability"]["mean"]:.1f}</td><td>{f["maintainability"]["mean"] - a["maintainability"]["mean"]:+.1f}</td>'),
                             ("Intent recovery", f'<td>{a["intent_recovery"]["mean"]:.1f}</td><td>{f["intent_recovery"]["mean"]:.1f}</td><td>{f["intent_recovery"]["mean"] - a["intent_recovery"]["mean"]:+.1f}</td>'),
                             ("Rated by Muse Spark 1.3", f'<td>{a["by_panel"]["muse"]["mean"]:.1f}</td><td>{f["by_panel"]["muse"]["mean"]:.1f}</td><td>{f["by_panel"]["muse"]["mean"] - a["by_panel"]["muse"]["mean"]:+.1f}</td>'),
                             ("Rated by Grok 4.6", f'<td>{a["by_panel"]["grok"]["mean"]:.1f}</td><td>{f["by_panel"]["grok"]["mean"]:.1f}</td><td>{f["by_panel"]["grok"]["mean"] - a["by_panel"]["grok"]["mean"]:+.1f}</td>'),
                             ("Standard error of Code quality", f'<td>{a["code_quality"]["se"]:.2f}</td><td>{f["code_quality"]["se"]:.2f}</td>')):
            self.assertIn(f'<th scope="row">{label}</th>{value}', self.page_html, label)

    def test_across_efforts_table(self):
        def cells(model, key, digits):
            return "".join(f"<td>{self.groups[model, e][key]['mean']:.{digits}f}</td>" for e in EFFORTS)

        def diffs(key):
            return "".join(f"<td>{round(self.groups['fable', e][key]['mean'], 2) - round(self.groups['astra', e][key]['mean'], 2):+.2f}</td>" for e in EFFORTS)

        for label, html_cells in (("Astra combined score", cells("astra", "combined_33", 2)), ("Fable 5.1 combined score", cells("fable", "combined_33", 2)),
                                  ("Fable minus Astra, combined", diffs("combined_33")), ("Astra Code quality", cells("astra", "code_quality", 2)),
                                  ("Fable 5.1 Code quality", cells("fable", "code_quality", 2)), ("Fable minus Astra, Code quality", diffs("code_quality")),
                                  ("Astra minutes per task", cells("astra", "minutes", 1)), ("Fable 5.1 minutes per task", cells("fable", "minutes", 1))):
            self.assertIn(f'<th scope="row">{label}</th>{html_cells}', self.page_html, label)
        low, high = self.groups["astra", "low"], self.groups["astra", "max"]
        self.assertIn(f'Astra {low["combined_33"]["mean"]:.2f} to {high["combined_33"]["mean"]:.2f}', self.page_html)

    def test_comparative_claims(self):
        for effort in EFFORTS:
            a, f = self.groups["astra", effort], self.groups["fable", effort]
            self.assertGreater(f["combined_33"]["mean"], a["combined_33"]["mean"], effort)
            self.assertGreater(f["combined_20_profile"]["mean"], a["combined_20_profile"]["mean"], effort)
            self.assertGreater(f["code_quality"]["mean"], a["code_quality"]["mean"], effort)
            self.assertLess(a["minutes"]["mean"], f["minutes"]["mean"], effort)
            for p in PANELS:
                self.assertGreater(f["by_panel"][p]["mean"], a["by_panel"][p]["mean"], (effort, p))
        best = max(self.groups.values(), key=lambda g: g["combined_33"]["mean"])
        self.assertEqual((best["model"], best["effort"]), ("fable", "max"))
        self.assertEqual(max(self.groups.values(), key=lambda g: g["code_quality"]["mean"])["model"], "fable")
        self.assertEqual(f'{sum(r["duration_s"] for r in self.rows) / 3600:.2f}', "70.75")

    def test_calibration_and_protocol_record(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertEqual(record["failing_gates"], [])
            self.assertFalse(record["allowance_used"])
            self.assertEqual(record["call_count"], 80)
            self.assertTrue(all(gate["passed"] for gate in record["gates"].values()))
            self.assertEqual(len(record["gates"]), 20)
            means = record["control_means"]
            self.assertGreaterEqual(means["0"]["naming"] - means["1"]["naming"], 2)
            self.assertGreaterEqual(means["0"]["presentation"] - means["1"]["presentation"], 2)
        self.assertFalse(self.calibration["glm"]["passed"])
        self.assertEqual(self.calibration["glm"]["failing_gates"], ["g01_validity"])
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.4", "grok": "code-quality-maintenance-v3.3"})
        self.assertEqual(set(self.protocols["scored_panel"]), set(PANELS))
        self.assertEqual(self.protocols["repeats"], 5)
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/"):
                self.assertNotIn(mark, text, name)

    def test_page_card_links_and_site_references(self):
        self.assertEqual(self.page.structure_errors, [])
        self.assertEqual(self.page.structure, [])
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))
        for link in self.page.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            if parsed.path:
                target = ROOT / unquote(parsed.path).lstrip("/")
                self.assertTrue(target.is_file(), link)
            elif parsed.fragment:
                self.assertIn(parsed.fragment, self.page.ids)
        card = ROOT / "assets/cards/swe-v4-astra-fable51-v34.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), CARD_SHA256)
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-astra-fable51-v34-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "methodology.html", "leaderboard.html"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-astra-fable51-v34.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = (ROOT / "feed.xml").read_text().split("<item>")[1]
        self.assertIn(URL, feed_item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn(f"<guid>{URL}</guid>", (ROOT / "feed.xml").read_text())
        self.assertNotIn(chr(0x2014), html.unescape(self.page_html))
        self.assertNotIn(chr(0x2013), html.unescape(self.page_html))


if __name__ == "__main__":
    unittest.main()
