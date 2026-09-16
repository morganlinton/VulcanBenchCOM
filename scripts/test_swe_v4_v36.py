"""Stdlib checks for the v3.6 GPT-5.6 Terra bundle, its report page and the site links to it."""

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
DATA = ROOT / "assets/data/swe-v4-terra-v36"
PAGE = ROOT / "benchmarks/swe-v4-terra-v36.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-terra-v36.html"
LEVELS = {"terra": ("low", "medium", "high", "extra-high", "max")}
EFFORTS = LEVELS["terra"]
PANELS = ("muse", "grok")
NAMES = {"terra": "GPT-5.6 Terra"}
EXPECTED = {("terra", "max"): 22}
CARD_SHA256 = "9fc260a33dbc9b60629aca8c500922e1d86853e127ead944754bc85dabf25286"
ECONOMICS_CARD_SHA256 = "586294b967cec175c660f91f345eb78c1995563d7efc25971e662b35a37f0bfe"


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


class TerraBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.groups = {(g["model"], g["effort"]): g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())
        with (ROOT / "assets/data/swe-v4-terra-v36-scores.csv").open(newline="") as source:
            cls.scores = {("terra", r["effort"]): r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 114)
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        redistributed = 0
        for r in self.rows:
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            if r["intent_recovery_redistributed"]:
                redistributed += 1
                self.assertIsNone(r["intent_recovery"])
                self.assertEqual(r["passed_quirk_families"], 0)
                self.assertTrue(all(r["panels"][p]["intent_recovery"] is None and r["panels"][p]["scored_quirks"] == 0 for p in PANELS))
                code_quality = reviewed
            else:
                intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
                self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
                code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            self.assertFalse(r["solver_fallback"], r["run_id"])
            for p in PANELS:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"],
                                       (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
            usage, rate = r["token_usage"], self.econ["rates_per_million"][r["model"]]
            cached = min(usage["cached_input_tokens"], usage["input_tokens"])
            priced = ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6
            self.assertAlmostEqual(r["estimated_usd"], priced, places=5, msg=r["run_id"])
            self.assertGreater(r["raw_tokens"], 0)
        self.assertEqual(redistributed, 2)
        self.assertEqual(len({(r["model"], r["effort"], r["task"]) for r in self.rows}), 114)
        self.assertEqual(sorted((r["effort"], r["task"]) for r in self.rows if r["intent_recovery_redistributed"]),
                         [("high", "legacy-schedcore-binary-parity"), ("low", "legacy-granarycore-binary-parity")])
        for r in self.rows:
            self.assertIn("frozen_record_usd", r)
            self.assertGreater(r["frozen_record_usd"], r["estimated_usd"], r["run_id"])

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), {(m, e) for m in LEVELS for e in LEVELS[m]})
        self.assertEqual(set(self.scores), set(self.groups))
        for key, g in self.groups.items():
            rs = [r for r in self.rows if (r["model"], r["effort"]) == key]
            scored = [r for r in rs if r["intent_recovery"] is not None]
            self.assertEqual(len(rs), EXPECTED.get(key, 23))
            self.assertEqual(g["n"], EXPECTED.get(key, 23))
            self.assertEqual(g["intent_recovery_redistributed_runs"], len(rs) - len(scored))
            for field, values in (("combined_33", [r["combined_33"] for r in rs]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in rs]),
                                  ("code_quality", [r["code_quality"] for r in rs]),
                                  ("reviewed_score", [r["reviewed_score"] for r in rs]),
                                  ("intent_recovery", [r["intent_recovery"] for r in scored]),
                                  ("readability", [statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in rs]),
                                  ("maintainability", [statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in rs]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]),
                                  ("usd", [r["estimated_usd"] for r in rs]),
                                  ("raw_tokens", [r["raw_tokens"] for r in rs])):
                mean, se = mean_se(values)
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(key, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(key, field))
            for p in PANELS:
                self.assertAlmostEqual(g["by_panel"][p]["mean"], statistics.mean(r["panels"][p]["reviewed_score"] for r in rs), places=9)
            self.assertEqual(g["passed"], sum(r["functional"] == 1 for r in rs))
            self.assertEqual(g["solver_fallback_runs"], 0)
            row = self.scores[key]
            for column, field in (("combined_33", "combined_33"), ("combined_20_profile", "combined_20_profile"), ("code_quality", "code_quality"),
                                  ("readability", "readability"), ("maintainability", "maintainability"), ("intent_recovery", "intent_recovery"),
                                  ("mean_minutes", "minutes")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(key, column))
            self.assertAlmostEqual(float(row["combined_33_se"]), g["combined_33"]["se"], places=4)
            self.assertAlmostEqual(float(row["code_quality_se"]), g["code_quality"]["se"], places=4)
            self.assertEqual(int(row["passed"]), g["passed"])
            self.assertEqual(int(row["intent_recovery_redistributed_runs"]), g["intent_recovery_redistributed_runs"])

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), set(self.groups))
        for key, g in self.groups.items():
            star = "*" if g["intent_recovery_redistributed_runs"] else ""
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                        f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}', f'{g["maintainability"]["mean"]:.1f}',
                        f'{g["intent_recovery"]["mean"]:.1f}{star}', f'{g["passed"]}/{g["n"]}', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows[key][2:], expected, key)
            self.assertEqual(self.page.rows[key][1], label(key[1]))
        g = {e: self.groups["terra", e] for e in EFFORTS}
        for name, key, d in (("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
                             ("Intent recovery", "intent_recovery", 1)):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e][key]['mean']:.{d}f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        for name, p in (("Rated by Muse Spark 1.3", "muse"), ("Rated by Grok 4.6", "grok")):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e]['by_panel'][p]['mean']:.1f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f"<td>{g[e]['code_quality']['se']:.2f}</td>" for e in EFFORTS), self.page_html)

    def test_across_efforts_table(self):
        g = {e: self.groups["terra", e] for e in EFFORTS}
        econ = json.loads((DATA / "economics.json").read_text())
        eg = {r["effort"]: r for r in econ["groups"]}

        def cells(key, digits):
            return "".join(f"<td>{g[e][key]['mean']:.{digits}f}</td>" for e in EFFORTS)

        for name, html_cells in (("Combined score", cells("combined_33", 2)), ("Standard error", "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS)),
                                 ("Tasks passed", "".join(f"<td>{g[e]['passed']}/{g[e]['n']}</td>" for e in EFFORTS)),
                                 ("Code quality", cells("code_quality", 2)), ("Human readability", cells("readability", 1)),
                                 ("Minutes per task", cells("minutes", 1)), ("API-equivalent $ per task", "".join(f"<td>${eg[e]['usd']['mean']:.2f}</td>" for e in EFFORTS))):
            self.assertIn(f'<th scope="row">{name}</th>{html_cells}</tr>', self.page_html, name)
        comb = [g[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertEqual(comb, sorted(comb))
        self.assertIn(f'{min(comb):.2f} at Low to {max(comb):.2f} at Max', self.page_html)

    def test_economics_table_and_card(self):
        econ = json.loads((DATA / "economics.json").read_text())
        eg = {r["effort"]: r for r in econ["groups"]}
        for e in EFFORTS:
            b = eg[e]
            rs = [r for r in self.rows if r["effort"] == e]
            self.assertEqual(b["n"], len(rs))
            self.assertAlmostEqual(b["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs), places=9)
            self.assertAlmostEqual(b["usd_total"], sum(r["estimated_usd"] for r in rs), places=6)
            self.assertAlmostEqual(b["raw_tokens"]["mean"], statistics.mean(r["raw_tokens"] for r in rs), places=6)
            cells = (f'<td>{b["n"]}</td><td>${b["usd"]["mean"]:.2f}</td><td>${b["usd_total"]:.2f}</td>'
                     f'<td>{b["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>{b["minutes"]["mean"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}</tr>', self.page_html, e)
        t = econ["totals"]["terra"]
        self.assertAlmostEqual(t["usd"], sum(r["estimated_usd"] for r in self.rows), places=6)
        self.assertEqual(t["raw_tokens"], sum(r["raw_tokens"] for r in self.rows))
        self.assertEqual(t["runs"], 114)
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>114</td><td>${t["usd"] / 114:.2f}</td><td>${t["usd"]:,.2f}</td>', self.page_html)
        self.assertEqual(f'{t["usd"]:.2f}', "142.73")
        self.assertEqual(econ["rates_per_million"], {"terra": {"input": 2.0, "cached_input": 0.2, "output": 12.0}})
        usd = [eg[e]["usd"]["mean"] for e in EFFORTS]
        index = (ROOT / "benchmarks.html").read_text()
        self.assertIn(f"${min(usd):.2f} to ${max(usd):.2f} per task", index)
        card = ROOT / "assets/cards/swe-v4-terra-v36-economics.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), ECONOMICS_CARD_SHA256)

    def test_model_pages(self):
        page = (ROOT / "models/gpt-5-6-terra.html").read_text()
        self.assertIn("../benchmarks/swe-v4-terra-v36.html", page)
        combined = [self.groups["terra", e]["combined_33"]["mean"] for e in EFFORTS]
        quality = [self.groups["terra", e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertIn(f"combined score {min(combined):.2f} to {max(combined):.2f}", page)
        self.assertIn(f"Code quality {min(quality):.2f} to {max(quality):.2f}", page)
        self.assertNotIn(chr(0x2014), html.unescape(page))
        self.assertIn('href="models/gpt-5-6-terra.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="/models/gpt-5-6-terra.html"', self.page_html)

    def test_comparative_claims(self):
        g = {e: self.groups["terra", e] for e in EFFORTS}
        comb = [g[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertEqual(comb, sorted(comb))
        self.assertEqual([g[e]["combined_20_profile"]["mean"] for e in EFFORTS], sorted(g[e]["combined_20_profile"]["mean"] for e in EFFORTS))
        self.assertEqual([g[e]["passed"] for e in EFFORTS], [2, 5, 11, 14, 22])
        self.assertEqual(g["max"]["passed"], g["max"]["n"])
        cq = [g[e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertLess(max(cq) - min(cq), 3)
        for e in EFFORTS:
            self.assertLess(abs(g[e]["by_panel"]["muse"]["mean"] - g[e]["by_panel"]["grok"]["mean"]), 3.5, e)
        self.assertLess(g["max"]["minutes"]["mean"], g["extra-high"]["minutes"]["mean"])
        econ = json.loads((DATA / "economics.json").read_text())
        eg = {r["effort"]: r for r in econ["groups"]}
        self.assertLess(eg["max"]["usd"]["mean"], eg["extra-high"]["usd"]["mean"])
        self.assertEqual(max(eg.values(), key=lambda r: r["usd"]["mean"])["effort"], "extra-high")
        self.assertGreater(g["max"]["intent_recovery"]["mean"], g["low"]["intent_recovery"]["mean"])
        hours = sum(r["duration_s"] for r in self.rows) / 3600
        self.assertIn(f"Summed solver time is {hours:.2f} hours", self.page_html)

    def test_calibration_and_protocol_record(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertEqual(record["call_count"], 80)
            self.assertEqual(len(record["gates"]), 20)
            self.assertEqual(record["allowance"], {"max_failing_gates": 1, "max_shortfall": 0.5})
            means = record["control_means"]
            self.assertGreaterEqual(means["0"]["naming"] - means["1"]["naming"], 2)
            self.assertGreaterEqual(means["0"]["presentation"] - means["1"]["presentation"], 1.5)
            self.assertLessEqual(means["0"]["presentation"] - means["1"]["presentation"], 2.3)
            self.assertGreater(means["2"]["presentation"] - means["1"]["presentation"], 0.5)
            self.assertLessEqual(means["2"]["naming"] - means["1"]["naming"], 0.25)
            self.assertLess(means["5"]["intent"], means["0"]["intent"])
            self.assertLess(means["9"]["verifiability"], means["0"]["verifiability"])
        muse, grok = self.calibration["muse"], self.calibration["grok"]
        self.assertTrue(muse["allowance_used"])
        self.assertEqual(muse["failing_gates"], ["g11_repeatability"])
        self.assertFalse(muse["gates"]["g11_repeatability"]["passed"])
        self.assertLessEqual(muse["gates"]["g11_repeatability"]["shortfall"], 0.5)
        self.assertEqual(sum(not gate["passed"] for gate in muse["gates"].values()), 1)
        self.assertFalse(grok["allowance_used"])
        self.assertEqual(grok["failing_gates"], [])
        self.assertTrue(all(gate["passed"] for gate in grok["gates"].values()))
        self.assertIn(f'yes, g11 by {muse["gates"]["g11_repeatability"]["shortfall"]:.2f}', self.page_html)
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.6", "grok": "code-quality-maintenance-v3.6"})
        self.assertEqual(set(self.protocols["scored_panel"]), set(PANELS))
        self.assertEqual(self.protocols["repeats"], 5)
        self.assertEqual(self.protocols["population"]["excluded"], [])
        self.assertEqual([(m["effort"], m["task"]) for m in self.protocols["missing"]], [("max", "legacy-paddockcore-binary-parity")])
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
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
        card = ROOT / "assets/cards/swe-v4-terra-v36.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), CARD_SHA256)
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-terra-v36-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "leaderboard.html"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-terra-v36.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn(f"<guid>{URL}</guid>", (ROOT / "feed.xml").read_text())
        self.assertNotIn(chr(0x2014), html.unescape(self.page_html))
        self.assertNotIn(chr(0x2013), html.unescape(self.page_html))


if __name__ == "__main__":
    unittest.main()
