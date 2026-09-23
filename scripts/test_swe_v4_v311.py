"""Stdlib checks for the v3.11 Devin SWE-2 bundle, its report page and the site links to it."""

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
DATA = ROOT / "assets/data/swe-v4-devin-swe2-v311"
PAGE = ROOT / "benchmarks/swe-v4-devin-swe2-v311.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-devin-swe2-v311.html"
LEVELS = {"swe2": ("medium", "high", "max")}
EFFORTS = LEVELS["swe2"]
PANELS = ("muse",)
FAILED_PANELS = ("grok", "sol")
NAMES = {"swe2": "Devin SWE-2"}
EXCLUDED = [("high", "legacy-cellarcore-binary-parity"), ("high", "legacy-snapcore-binary-parity"),
            ("high", "legacy-vaultcore-binary-parity"), ("max", "legacy-freightcore-binary-parity")]
JUDGED = {"medium": 23, "high": 20, "max": 22}
FINISHED = {"medium": 23, "high": 22, "max": 23}
CARD_SHA256 = "8b938688b63878c60e43249fc8825ab4949d8829dd7a91f0b6bde0861c63f606"
ECONOMICS_CARD_SHA256 = "9104e14b16f252bce3bd3ab85d61b61d99c545078622835d52198c7396ccd4f6"


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.capitalize()


class DevinBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.did_not_finish = cls.runs["did_not_finish"]
        cls.published = [r for r in cls.rows if r["judged"] == "published"]
        cls.groups = {(g["model"], g["effort"]): g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())
        cls.provenance = json.loads((DATA / "provenance.json").read_text())
        with (ROOT / "assets/data/swe-v4-devin-swe2-v311-scores.csv").open(newline="") as source:
            cls.scores = {("swe2", r["effort"]): r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 68)
        self.assertEqual(len(self.did_not_finish), 1)
        self.assertEqual(self.runs["runs_attempted"], 69)
        self.assertEqual(self.runs["runs_finished"], 68)
        self.assertEqual(self.runs["published"], 65)
        self.assertEqual(len(self.published), 65)
        self.assertEqual(self.runs["panel"], ["Muse Spark 1.3"])
        self.assertTrue(all(r["judged_under"] == "code-quality-maintenance-v3.11" for r in self.rows))
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        excluded = [r for r in self.rows if r["judged"] != "published"] + self.did_not_finish
        self.assertEqual(sorted((r["effort"], r["task"]) for r in excluded), sorted(EXCLUDED))
        for r in excluded:
            self.assertTrue(r["judged"].startswith("excluded: "))
            self.assertEqual(r["functional"], 0.0)  # every exclusion is a functional fail
            self.assertGreater(r["duration_s"], 0)
        for r in (r for r in self.rows if r["judged"] != "published"):
            self.assertIn("changed no recognized source file", r["judged"])
            for field in ("automated_quality", "security", "reviewed_score", "intent_recovery", "code_quality",
                          "combined_33", "combined_20_profile", "panels", "passed_quirk_families"):
                self.assertIsNone(r[field], field)
            self.assertGreater(r["raw_tokens"], 0)
        self.assertIn("did not finish", self.did_not_finish[0]["judged"])
        self.assertFalse(self.did_not_finish[0]["finished"])
        redistributed = [r for r in self.published if r["intent_recovery_redistributed"]]
        self.assertEqual([(r["effort"], r["task"]) for r in redistributed], [("high", "legacy-matchcore-order-book-parity")])
        for r in self.published:
            self.assertAlmostEqual(r["reviewed_score"], r["panels"]["muse"]["reviewed_score"], places=9)
            if r["intent_recovery_redistributed"]:
                self.assertIsNone(r["intent_recovery"])
                self.assertEqual(r["passed_quirk_families"], 0)
                self.assertAlmostEqual(r["code_quality"], r["reviewed_score"], places=9)
            else:
                self.assertGreater(r["passed_quirk_families"], 0)
                self.assertAlmostEqual(r["intent_recovery"], r["panels"]["muse"]["intent_recovery"], places=9)
                self.assertAlmostEqual(r["code_quality"], (0.24 * r["reviewed_score"] + 0.09 * r["intent_recovery"]) / 0.33, places=9)
                self.assertGreater(r["panels"]["muse"]["scored_quirks"], 0)
            code_quality = r["code_quality"]
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            self.assertFalse(r["panels"]["muse"]["reviewer_fallback"], r["run_id"])
            self.assertAlmostEqual(r["panels"]["muse"]["reviewed_score"],
                                   (r["panels"]["muse"]["readability"] + r["panels"]["muse"]["maintainability"]) / 2, places=6)
        for r in self.rows:
            self.assertFalse(r["solver_fallback"], r["run_id"])
            # SWE-2 is unpriced: cost is null, never a zero. The credit and ACU counters are measurements, not prices.
            self.assertIsNone(r["estimated_usd"], r["run_id"])
            self.assertIn("no per-token rate", r["pricing_method"])
            self.assertEqual(r["devin_credits"], 0, r["run_id"])
            self.assertEqual(r["devin_acu"], 0.0, r["run_id"])
            self.assertGreater(r["raw_tokens"], 0)
            self.assertEqual(r["raw_tokens"], r["cli_summary_units"])
            self.assertTrue(r["solver_cli_version"].startswith("devin "))
        self.assertEqual(len({(r["model"], r["effort"], r["task"]) for r in self.rows}), 68)

    def test_runs_csv_matches_runs_json(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = list(csv.DictReader(source))
        self.assertEqual(len(csv_rows), 68)
        by_run = {r["run_id"]: r for r in csv_rows}
        for r in self.rows:
            c = by_run[r["run_id"]]
            if r["judged"] == "published":
                self.assertEqual(c["judged"], "published")
                self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], places=3)
                self.assertAlmostEqual(float(c["code_quality"]), r["code_quality"], places=3)
                self.assertAlmostEqual(float(c["muse_reviewed"]), r["panels"]["muse"]["reviewed_score"], places=3)
            else:
                self.assertEqual(c["judged"], "excluded")
                self.assertEqual(c["combined_33"], "")
                self.assertEqual(c["code_quality"], "")
                self.assertEqual(c["muse_intent_recovery"], "")
            self.assertEqual(c["estimated_usd"], "")  # a missing value, not a zero
            self.assertEqual(int(c["devin_credits"]), 0)
            self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), {(m, e) for m in LEVELS for e in LEVELS[m]})
        self.assertEqual(set(self.scores), set(self.groups))
        for key, g in self.groups.items():
            rs = [r for r in self.rows if (r["model"], r["effort"]) == key]
            judged = [r for r in rs if r["judged"] == "published"]
            self.assertEqual(len(rs), FINISHED[key[1]])
            self.assertEqual(g["runs"], FINISHED[key[1]])
            self.assertEqual(g["runs_attempted"], 23)
            self.assertEqual(g["n"], len(judged))
            self.assertEqual(g["n"], JUDGED[key[1]])
            self.assertEqual(g["excluded_runs"], 23 - g["n"])
            scored = [r for r in judged if r["intent_recovery"] is not None]
            self.assertEqual(g["intent_recovery_redistributed_runs"], len(judged) - len(scored))
            for field, values in (("combined_33", [r["combined_33"] for r in judged]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in judged]),
                                  ("code_quality", [r["code_quality"] for r in judged]),
                                  ("reviewed_score", [r["reviewed_score"] for r in judged]),
                                  ("intent_recovery", [r["intent_recovery"] for r in scored]),
                                  ("readability", [r["panels"]["muse"]["readability"] for r in judged]),
                                  ("maintainability", [r["panels"]["muse"]["maintainability"] for r in judged]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]),
                                  ("raw_tokens", [r["raw_tokens"] for r in rs])):
                mean, se = mean_se(values)
                self.assertEqual(g[field]["n"], len(values), (key, field))
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(key, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(key, field))
            self.assertEqual(g["by_panel"]["muse"]["mean"], g["reviewed_score"]["mean"])
            self.assertEqual(g["passed"], sum(r["functional"] == 1 for r in judged))
            # Every excluded run is a fail, so the sweep's pass count equals the judged cell's.
            self.assertEqual(g["passed_all_runs"], g["passed"])
            self.assertIsNone(g["usd"])
            self.assertIsNone(g["usd_total"])
            self.assertEqual(g["cost"], "unavailable")
            self.assertEqual(g["solver_fallback_runs"], 0)
            row = self.scores[key]
            self.assertEqual(row["model"], NAMES["swe2"])
            self.assertEqual(int(row["n"]), g["n"])
            self.assertEqual(int(row["runs_finished"]), g["runs"])
            self.assertEqual(int(row["runs_attempted"]), 23)
            for column, field in (("combined_33", "combined_33"), ("combined_20_profile", "combined_20_profile"), ("code_quality", "code_quality"),
                                  ("readability", "readability"), ("maintainability", "maintainability"), ("intent_recovery", "intent_recovery"),
                                  ("mean_minutes", "minutes")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(key, column))
            self.assertEqual(row["cost_usd"], "unavailable")
            self.assertAlmostEqual(float(row["combined_33_se"]), g["combined_33"]["se"], places=4)
            self.assertAlmostEqual(float(row["code_quality_se"]), g["code_quality"]["se"], places=4)
            self.assertEqual(int(row["passed"]), g["passed"])
        self.assertEqual([self.groups["swe2", e]["passed"] for e in EFFORTS], [15, 15, 21])

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), set(self.groups))
        for key, g in self.groups.items():
            mark = "§" if g["excluded_runs"] else ""
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                        f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}', f'{g["maintainability"]["mean"]:.1f}',
                        f'{g["intent_recovery"]["mean"]:.1f}', f'{g["passed"]}/{g["n"]}{mark}', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows[key][2:], expected, key)
            self.assertEqual(self.page.rows[key][1], label(key[1]))
        g = {e: self.groups["swe2", e] for e in EFFORTS}
        for name, key, d in (("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
                             ("Intent recovery", "intent_recovery", 1)):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e][key]['mean']:.{d}f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        self.assertIn('<th scope="row">Rated by Muse Spark 1.3</th>' + "".join(f"<td>{g[e]['by_panel']['muse']['mean']:.1f}</td>" for e in EFFORTS) + "</tr>", self.page_html)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f"<td>{g[e]['code_quality']['se']:.2f}</td>" for e in EFFORTS), self.page_html)

    def test_across_efforts_table(self):
        g = {e: self.groups["swe2", e] for e in EFFORTS}

        def cells(key, digits):
            return "".join(f"<td>{g[e][key]['mean']:.{digits}f}</td>" for e in EFFORTS)

        for name, html_cells in (("Combined score", cells("combined_33", 2)),
                                 ("Standard error", "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS)),
                                 ("Tasks passed", "".join(f"<td>{g[e]['passed_all_runs']}/23</td>" for e in EFFORTS)),
                                 ("Code quality", cells("code_quality", 2)), ("Human readability", cells("readability", 1)),
                                 ("Minutes per task", cells("minutes", 1)),
                                 ("Cost per task", "<td>unavailable</td><td>unavailable</td><td>unavailable</td>")):
            self.assertIn(f'<th scope="row">{name}</th>{html_cells}</tr>', self.page_html, name)
        comb = [g[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertIn(f'{comb[0]:.2f} at medium, {comb[1]:.2f} at high, {comb[2]:.2f} at Max', self.page_html)
        self.assertIn(f'{comb[0] - comb[1]:.2f} points below medium', self.page_html)
        self.assertIn(f'{comb[2] - comb[0]:.2f} points above medium', self.page_html)
        cq = [g[e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(cq):.2f} to {max(cq):.2f}", self.page_html)
        self.assertIn(f"{min(g[e]['minutes']['mean'] for e in EFFORTS):.1f} to {max(g[e]['minutes']['mean'] for e in EFFORTS):.1f} min", self.page_html)
        self.assertIn(f"climbs {g['max']['readability']['mean'] - g['medium']['readability']['mean']:.1f} points", self.page_html)

    def test_economics_table_and_card(self):
        eg = {r["effort"]: r for r in self.econ["groups"]}
        for e in EFFORTS:
            b = eg[e]
            rs = [r for r in self.rows if r["effort"] == e]
            self.assertEqual(b["n"], len(rs))
            self.assertEqual(b["n"], FINISHED[e])
            self.assertEqual(b["runs_attempted"], 23)
            self.assertIsNone(b["usd"])
            self.assertIsNone(b["usd_total"])
            self.assertEqual(b["cost"], "unavailable")
            self.assertAlmostEqual(b["raw_tokens"]["mean"], statistics.mean(r["raw_tokens"] for r in rs), places=6)
            self.assertAlmostEqual(b["output_tokens"]["mean"], statistics.mean(r["token_usage"]["output_tokens"] for r in rs), places=6)
            self.assertAlmostEqual(b["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=6)
            cells = (f'<td>{b["n"]}</td><td>{b["output_tokens"]["mean"] / 1e3:.0f}K</td><td>{b["raw_tokens_total"] / 1e6:.0f}M</td>'
                     f'<td>{b["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>{b["minutes"]["mean"]:.1f}</td><td>unavailable</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}</tr>', self.page_html, e)
        t = self.econ["totals"]["swe2"]
        self.assertIsNone(t["usd"])
        self.assertEqual(self.econ["cost"], "unavailable")
        self.assertIsNone(self.econ["rates_per_million"])
        self.assertIsNone(self.econ["pricing_verified"])
        self.assertIn("no per-token rate", self.econ["cost_reason"])
        self.assertIn("2026-10-10", self.econ["cost_reason"])
        self.assertEqual(t["raw_tokens"], sum(r["raw_tokens"] for r in self.rows))
        self.assertEqual(t["output_tokens"], sum(r["token_usage"]["output_tokens"] for r in self.rows))
        self.assertEqual(t["runs"], 68)
        self.assertEqual(t["runs_attempted"], 69)
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>68</td>'
                      f'<td>{t["output_tokens"] / t["runs"] / 1e3:.0f}K</td><td>{t["raw_tokens"] / 1e6:,.0f}M</td>'
                      f'<td>{t["raw_tokens"] / t["runs"] / 1e6:.2f}M</td><td>{t["solver_hours"]:.1f} h</td><td>unavailable</td>',
                      self.page_html)
        self.assertIn(f'{t["raw_tokens"] / t["runs"] / 1e6:.2f}M tokens', self.page_html)
        self.assertIn(f'{t["solver_hours"] * 60 / t["runs"]:.1f} minutes per task', self.page_html)
        card = ROOT / "assets/cards/swe-v4-devin-swe2-v311-economics.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), ECONOMICS_CARD_SHA256)

    def test_model_page(self):
        page = (ROOT / "models/devin-swe-2.html").read_text()
        self.assertIn("../benchmarks/swe-v4-devin-swe2-v311.html", page)
        self.assertIn("../benchmarks/swe-v4-devin-swe2-v311.html#cost", page)
        self.assertIn("Cognition", page)
        combined = [self.groups["swe2", e]["combined_33"]["mean"] for e in EFFORTS]
        quality = [self.groups["swe2", e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertIn(f"combined score {combined[0]:.2f} at medium, {combined[1]:.2f} at high and {combined[2]:.2f} at Max", page)
        self.assertIn(f"Code quality {min(quality):.2f} to {max(quality):.2f}", page)
        self.assertIn("Cost is unavailable at every effort level", page)
        self.assertIn("no per-token rate", page)
        self.assertIn("Muse Spark 1.3 alone", page)
        # Every effort level SWE-2 offers is named; there is no other level to show.
        for effort in EFFORTS:
            self.assertIn(effort, page.lower())
        self.assertNotIn(chr(0x2014), html.unescape(page))
        self.assertNotIn(chr(0x2013), html.unescape(page))
        self.assertIn('href="models/devin-swe-2.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="/models/devin-swe-2.html"', self.page_html)

    def test_comparative_claims(self):
        g = {e: self.groups["swe2", e] for e in EFFORTS}
        comb = [g[e]["combined_33"]["mean"] for e in EFFORTS]
        # Medium and high are indistinguishable: within each other's standard errors, and the same pass count.
        self.assertLess(abs(comb[0] - comb[1]), min(g["medium"]["combined_33"]["se"], g["high"]["combined_33"]["se"]))
        self.assertEqual(g["medium"]["passed_all_runs"], g["high"]["passed_all_runs"])
        self.assertEqual(comb[2], max(comb))
        self.assertGreater(g["max"]["passed_all_runs"], g["medium"]["passed_all_runs"] + 5)
        cq = [g[e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertEqual(cq, sorted(cq))
        self.assertLess(max(cq) - min(cq), 5)
        minutes = [g[e]["minutes"]["mean"] for e in EFFORTS]
        self.assertEqual(min(range(3), key=lambda i: minutes[i]), 1)  # high is the fastest level
        self.assertEqual(max(range(3), key=lambda i: minutes[i]), 2)  # max is the slowest
        eg = {r["effort"]: r for r in self.econ["groups"]}
        tokens = [eg[e]["raw_tokens"]["mean"] for e in EFFORTS]
        self.assertEqual(max(range(3), key=lambda i: tokens[i]), 0)  # medium is the heaviest in tokens
        self.assertEqual(min(range(3), key=lambda i: tokens[i]), 1)
        hours = sum(r["duration_s"] for r in self.rows) / 3600
        self.assertIn(f"Summed solver time is {hours:.2f} hours", self.page_html)

    def test_exclusions_are_disclosed(self):
        for text in (self.page_html, (DATA / "README.md").read_text()):
            self.assertIn("65 of 69", text)
        self.assertIn("20 of 23", self.page_html)
        self.assertIn("22 of 23", self.page_html)
        for task in ("cellarcore", "snapcore", "vaultcore", "freightcore"):
            self.assertIn(task, self.page_html, task)
            self.assertIn(task, (DATA / "README.md").read_text(), task)
        population = self.protocols["population"]
        self.assertEqual(population["cells"], {"swe2/high": 20, "swe2/max": 22, "swe2/medium": 23})
        self.assertEqual(len(population["excluded"]), 4)
        for entry in population["excluded"]:
            self.assertNotIn("/Users/", entry["reason"])
            self.assertEqual(entry["functional"], 0.0)
        self.assertEqual(self.protocols["unpublished"], [])
        self.assertTrue(any("20 of its 23 runs" in limit for limit in self.provenance["limits"]))

    def test_single_judge_is_disclosed(self):
        self.assertEqual(set(self.protocols["scored_panel"]), set(PANELS))
        self.assertEqual(set(self.protocols["failed_panels"]), set(FAILED_PANELS))
        self.assertIn("Muse Spark 1.3 alone", self.protocols["single_panel_note"])
        # The abstract, a methods section and a footnote each say it.
        unescaped = html.unescape(self.page_html)
        self.assertIn("a single judge, Muse Spark 1.3", unescaped)
        self.assertIn("One judge, not two.", unescaped)
        self.assertIn("Code quality on this page is one judge's rating.", unescaped)
        self.assertGreaterEqual(unescaped.count("Muse Spark 1.3"), 8)
        for needle in ("gate 16", "Grok 4.6", "GPT-5.6 Sol", "single-panel rule", "invented departures"):
            self.assertIn(needle, unescaped, needle)
        self.assertTrue(any("one judge" in limit for limit in self.provenance["limits"]))

    def test_calibration_and_protocol_record(self):
        panels = self.calibration["panels"]
        self.assertEqual(set(panels), set(PANELS) | set(FAILED_PANELS))
        muse = panels["muse"]
        self.assertTrue(muse["passed"])
        self.assertTrue(muse["scored"])
        self.assertTrue(muse["allowance_used"])
        self.assertEqual(muse["failing_gates"], ["g11_repeatability"])
        self.assertEqual(muse["source"], "runs-code-quality-maintenance-v3.9/calibration-muse.json")
        for judge in FAILED_PANELS:
            record = panels[judge]
            self.assertFalse(record["passed"])
            self.assertFalse(record["scored"])
            self.assertFalse(record["allowance_used"])
            self.assertEqual(record["failing_gates"], ["g16_probe_recovers_documented_intent"])
            self.assertFalse(record["gates"]["g16_probe_recovers_documented_intent"]["passed"])
            self.assertTrue(all(gate["passed"] for name, gate in record["gates"].items() if name != "g16_probe_recovers_documented_intent"))
        for record in panels.values():
            self.assertEqual(record["call_count"], 80)
            self.assertEqual(len(record["gates"]), 20)
            self.assertEqual(record["allowance"], {"max_failing_gates": 1, "max_shortfall": 0.5})
            means = record["control_means"]
            self.assertGreaterEqual(means["0"]["naming"] - means["1"]["naming"], 2)
            self.assertLess(means["5"]["intent"], means["0"]["intent"])
            self.assertLess(means["9"]["verifiability"], means["0"]["verifiability"])
        self.assertIn("<td>passed</td><td>yes</td><td>g11_repeatability</td>", self.page_html)
        self.assertEqual(self.page_html.count("<td>failed</td><td>no</td><td>g16_probe_recovers_documented_intent</td>"), 2)
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.11"})
        self.assertEqual(self.protocols["repeats"], 5)
        self.assertIn("v3.10", self.protocols["amends"])
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("SWE v4", text, name)

    def test_no_price_is_claimed_anywhere(self):
        """SWE-2 has no public rate, so no published file may show a cost figure or call the model free."""
        banned = ("$0", "cost tier Free", "free on Devin", "Free to run", "free to run", "is free", "rates checked",
                  "list rates", "API-equivalent")
        published = [PAGE, ROOT / "models/devin-swe-2.html", DATA / "README.md", DATA / "REPRODUCING.md",
                     ROOT / "assets/data/swe-v4-devin-swe2-v311-scores.csv", DATA / "runs.csv"]
        for path in published:
            text = html.unescape(path.read_text())
            for mark in banned:
                self.assertNotIn(mark, text, f"{path.name}: {mark}")
        # The bundle's JSON may explain why the Free tier is not a rate, but must never carry a cost number.
        for name in ("runs.json", "groups.json", "economics.json", "provenance.json"):
            data = json.loads((DATA / name).read_text())
            self.assertNotIn("$0", json.dumps(data), name)
        for r in self.rows:
            self.assertIsNone(r["estimated_usd"], r["run_id"])
        # The site-wide copy names the report without pricing it. Each of these files lists the Devin entry
        # immediately before the Sol one, so the Devin block is what lies between the two slugs.
        for name in ("benchmarks.html", "index.html", "llms.txt", "feed.xml"):
            text = html.unescape((ROOT / name).read_text())
            start = text.index("swe-v4-devin-swe2-v311")
            end = text.index("swe-v4-sol-v37", start)
            entry = text[start:end]
            self.assertIn("Devin", entry, name)
            self.assertLess(len(entry), 3000, name)  # the slice really is one entry
            for mark in banned:
                self.assertNotIn(mark, entry, f"{name}: {mark}")

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
        card = ROOT / "assets/cards/swe-v4-devin-swe2-v311.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), CARD_SHA256)
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-devin-swe2-v311-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-devin-swe2-v311.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertNotIn("SWE v4", feed_item)
        self.assertIn("VulcanBench Frontier v4", feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn(f"<guid>{URL}</guid>", (ROOT / "feed.xml").read_text())
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-devin-swe2-v311.html"), index.index("swe-v4-sol-v37.html"))
        self.assertIn("assets/cards/swe-v4-devin-swe2-v311.png", index)
        unescaped = html.unescape(self.page_html)
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
            self.assertNotIn(mark, unescaped, mark)


if __name__ == "__main__":
    unittest.main()
