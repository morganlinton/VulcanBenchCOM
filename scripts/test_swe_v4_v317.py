"""Stdlib checks for the v3.17 GPT-6 Sol bundle, its report page, its four cards and the site links to it."""

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
DATA = ROOT / "assets/data/swe-v4-gpt6-sol-v317"
SOL56 = ROOT / "assets/data/swe-v4-sol-v37"
PAGE = ROOT / "benchmarks/swe-v4-gpt6-sol-v317.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-gpt6-sol-v317.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
UNPUBLISHED = [("medium", "legacy-codeccore-binary-parity")]
# Copied byte for byte from the harness (docs/results/swe-v4-gpt6-sol-2026-09 and swe-v4-gpt6-vs-gpt56-2026-09).
CARDS = {
    "swe-v4-gpt6-sol-v317.png": "92423c7e29206441277fc1bef4684aa7058aff156563fb5be21e553b66b262f8",
    "swe-v4-gpt6-sol-v317-economics.png": "bfea7c7f3d00fa1a1acfbf975e11986502480ff393d3daeec7a6152131ae7d36",
    "swe-v4-gpt6-vs-gpt56-sol.png": "d615ec662015a6455c4e0c434bc6fd38b28264f6508c2b041370488a27d87d22",
    "swe-v4-gpt6-vs-gpt56-all.png": "1a87a9cdbff3e9459a9fa18b5b10372ada583b94093d09c083366fc0cca8101f",
}


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


class GPT6SolBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.published = [r for r in cls.rows if r["judged"] == "published"]
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())
        cls.provenance = json.loads((DATA / "provenance.json").read_text())
        with (ROOT / "assets/data/swe-v4-gpt6-sol-v317-scores.csv").open(newline="") as source:
            cls.scores = {r["effort"]: r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 115)
        self.assertEqual((self.runs["published"], self.runs["unpublished"]), (114, 1))
        self.assertEqual(len(self.published), 114)
        self.assertTrue(all(r["judged_under"] == "code-quality-maintenance-v3.17" for r in self.rows))
        self.assertTrue(all(r["finished"] and r["duration_s"] < 10800 for r in self.rows))  # no timeouts
        self.assertTrue(all(r["solver_cli_version"] == "codex-cli 0.155.0" for r in self.rows))
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        unpublished = [r for r in self.rows if r["judged"] != "published"]
        self.assertEqual([(r["effort"], r["task"]) for r in unpublished], UNPUBLISHED)
        for r in unpublished:
            self.assertTrue(r["judged"].startswith("unpublished: "))
            self.assertLess(r["functional"], 1)  # it failed its tests, so it is a failed task either way
            for field in ("reviewed_score", "intent_recovery", "code_quality", "combined_33", "combined_20_profile", "panels"):
                self.assertIsNone(r[field], field)
            self.assertGreater(r["estimated_usd"], 0)  # still priced
        for r in self.rows:
            usage, rate = r["token_usage"], self.econ["rates_per_million"][r["model"]]
            cached = min(usage["cached_input_tokens"], usage["input_tokens"])
            priced = ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6
            self.assertAlmostEqual(r["estimated_usd"], priced, places=5, msg=r["run_id"])
            self.assertGreater(r["raw_tokens"], 0)
        for r in self.published:
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            self.assertFalse(r["intent_recovery_redistributed"])  # every judged run passed at least one quirk family
            self.assertGreater(r["passed_quirk_families"], 0)
            intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
            self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
            code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            for p in PANELS:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"],
                                       (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
        self.assertFalse(any(r["solver_fallback"] for r in self.rows))
        self.assertEqual(len({(r["effort"], r["task"]) for r in self.rows}), 115)

    def test_runs_csv_matches_runs_json(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = list(csv.DictReader(source))
        self.assertEqual(len(csv_rows), 115)
        by_run = {r["run_id"]: r for r in csv_rows}
        for r in self.rows:
            c = by_run[r["run_id"]]
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], places=6)
            self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])
            if r["judged"] == "published":
                self.assertEqual(c["judged"], "published")
                self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], places=3)
                self.assertAlmostEqual(float(c["code_quality"]), r["code_quality"], places=3)
            else:
                self.assertEqual(c["judged"], "unpublished")
                for column in ("combined_33", "code_quality", "grok_intent_recovery", "muse_reviewed"):
                    self.assertEqual(c[column], "", column)

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), set(EFFORTS))
        self.assertEqual(set(self.scores), set(EFFORTS))
        for effort, g in self.groups.items():
            rs = [r for r in self.rows if r["effort"] == effort]
            judged = [r for r in rs if r["judged"] == "published"]
            self.assertEqual((len(rs), g["runs"]), (23, 23))
            self.assertEqual(g["n"], len(judged))
            self.assertEqual(g["unpublished_runs"], 23 - g["n"])
            for field, values in (("combined_33", [r["combined_33"] for r in judged]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in judged]),
                                  ("code_quality", [r["code_quality"] for r in judged]),
                                  ("reviewed_score", [r["reviewed_score"] for r in judged]),
                                  ("intent_recovery", [r["intent_recovery"] for r in judged]),
                                  ("readability", [statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged]),
                                  ("maintainability", [statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]),
                                  ("minutes_judged_runs", [r["duration_s"] / 60 for r in judged]),
                                  ("usd", [r["estimated_usd"] for r in rs]),
                                  ("raw_tokens", [r["raw_tokens"] for r in rs])):
                mean, se = mean_se(values)
                self.assertEqual(g[field]["n"], len(values), (effort, field))
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(effort, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(effort, field))
            self.assertEqual(g["passed_all_runs"], sum(r["functional"] == 1 for r in rs))
            self.assertEqual(g["passed"], g["passed_all_runs"])
            row = self.scores[effort]
            self.assertEqual((int(row["n"]), int(row["runs"])), (g["n"], 23))
            for column, field in (("combined_33", "combined_33"), ("combined_20_profile", "combined_20_profile"), ("code_quality", "code_quality"),
                                  ("readability", "readability"), ("maintainability", "maintainability"), ("intent_recovery", "intent_recovery"),
                                  ("mean_minutes", "minutes"), ("mean_usd", "usd")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(effort, column))
            self.assertEqual(int(row["passed_of_23"]), g["passed_all_runs"])
        g = self.groups
        self.assertEqual([g[e]["n"] for e in EFFORTS], [23, 22, 23, 23, 23])
        self.assertEqual([g[e]["passed_all_runs"] for e in EFFORTS], [4, 13, 15, 18, 19])
        self.assertEqual([round(g[e]["combined_33"]["mean"], 2) for e in EFFORTS], [67.62, 80.60, 82.83, 85.94, 86.82])
        self.assertEqual([round(g[e]["code_quality"]["mean"], 2) for e in EFFORTS], [62.53, 66.79, 70.09, 70.77, 70.78])
        self.assertEqual([round(g[e]["minutes"]["mean"], 1) for e in EFFORTS], [13.0, 17.5, 23.8, 20.9, 24.5])
        self.assertEqual(round(g["medium"]["minutes_judged_runs"]["mean"], 1), 17.9)  # the score card's runtime bar
        self.assertEqual([g[e]["intent_recovery_redistributed_runs"] for e in EFFORTS], [0, 0, 0, 0, 0])

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), {("gpt6sol", e) for e in EFFORTS})
        for effort, g in self.groups.items():
            judged = f'{g["n"]}/23' + ("&Vert;" if effort == "medium" else "")
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                        f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}', f'{g["maintainability"]["mean"]:.1f}',
                        f'{g["intent_recovery"]["mean"]:.1f}', html.unescape(judged), f'{g["passed_all_runs"]}/23', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows["gpt6sol", effort][2:], expected, effort)
            self.assertEqual(self.page.rows["gpt6sol", effort][1], label(effort))
        g = self.groups
        for name, key, d in (("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
                             ("Intent recovery", "intent_recovery", 1)):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e][key]['mean']:.{d}f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        for name, p in (("Rated by Muse Spark 1.3", "muse"), ("Rated by Grok 4.6", "grok")):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e]['by_panel'][p]['mean']:.1f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f"<td>{g[e]['code_quality']['se']:.2f}</td>" for e in EFFORTS), self.page_html)
        self.assertIn("&Vert;Medium is judged on 22 of 23 tasks.", self.page_html)

    def test_across_efforts_table(self):
        g = self.groups
        eg = {r["effort"]: r for r in self.econ["groups"]}

        def cells(key, digits):
            return "".join(f"<td>{g[e][key]['mean']:.{digits}f}</td>" for e in EFFORTS)

        for name, html_cells in (("Combined score", cells("combined_33", 2)),
                                 ("Standard error", "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS)),
                                 ("Judged runs", "".join(f"<td>{g[e]['n']}</td>" for e in EFFORTS)),
                                 ("Tasks passed", "".join(f"<td>{g[e]['passed_all_runs']}/23</td>" for e in EFFORTS)),
                                 ("Code quality", cells("code_quality", 2)), ("Human readability", cells("readability", 1)),
                                 ("Minutes per task", cells("minutes", 1)),
                                 ("API-equivalent $ per task", "".join(f"<td>${eg[e]['usd']['mean']:.2f}</td>" for e in EFFORTS))):
            self.assertIn(f'<th scope="row">{name}</th>{html_cells}</tr>', self.page_html, name)
        comb = [g[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertEqual(comb, sorted(comb))
        self.assertIn(f"{comb[0]:.2f} at Low to {comb[4]:.2f} at Max", self.page_html)
        self.assertIn(f"{comb[1] - comb[0]:.1f} points from Low to Medium, then {comb[2] - comb[1]:.1f} to High, {comb[3] - comb[2]:.1f} to Extra-high and {comb[4] - comb[3]:.1f} to Max", self.page_html)
        cq = [g[e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(cq):.2f} to {max(cq):.2f}", self.page_html)
        minutes = [g[e]["minutes"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(minutes):.1f} to {max(minutes):.1f} min", self.page_html)
        self.assertIn(f"71.23 to 89.19", self.page_html)
        self.assertEqual((f"{g['low']['combined_20_profile']['mean']:.2f}", f"{g['max']['combined_20_profile']['mean']:.2f}"), ("71.23", "89.19"))
        # Every effort level appears; the page never leads with Max alone.
        for e in EFFORTS:
            self.assertIn(f"<td>{label(e)}</td>", self.page_html)

    def test_economics_table_and_totals(self):
        eg = {r["effort"]: r for r in self.econ["groups"]}
        for e in EFFORTS:
            b = eg[e]
            rs = [r for r in self.rows if r["effort"] == e]
            self.assertEqual(b["n"], 23)
            self.assertAlmostEqual(b["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs), places=9)
            self.assertAlmostEqual(b["usd_total"], sum(r["estimated_usd"] for r in rs), places=6)
            self.assertAlmostEqual(b["raw_tokens"]["mean"], statistics.mean(r["raw_tokens"] for r in rs), places=6)
            self.assertAlmostEqual(b["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=6)
            cells = (f'<td>23</td><td>${b["usd"]["mean"]:.2f}</td><td>${b["usd_total"]:.2f}</td>'
                     f'<td>{b["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>{b["minutes"]["mean"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}</tr>', self.page_html, e)
        t = self.econ["totals"]["gpt6sol"]
        self.assertAlmostEqual(t["usd"], sum(r["estimated_usd"] for r in self.rows), places=6)
        self.assertEqual(t["raw_tokens"], sum(r["raw_tokens"] for r in self.rows))
        self.assertEqual(t["runs"], 115)
        self.assertEqual((f'{t["usd"]:.2f}', f'{t["usd"] / 115:.2f}'), ("221.38", "1.93"))
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>115</td><td>${t["usd"] / 115:.2f}</td><td>${t["usd"]:,.2f}</td>'
                      f'<td>{t["raw_tokens"] / 1e6:,.0f}M</td><td>{t["solver_hours"]:.1f} h</td>', self.page_html)
        self.assertEqual(self.econ["rates_per_million"], {"gpt6sol": {"input": 2.0, "cached_input": 0.2, "output": 10.0}})
        self.assertEqual(self.econ["pricing_verified"], "2026-09-25")
        self.assertIn("$2.00 input, $0.20 cached input and $10.00 output per million tokens", self.page_html)
        self.assertIn("no long-context premium applies", self.page_html)

    def test_gpt56_sol_comparison(self):
        sol = [r for r in json.loads((SOL56 / "runs.json").read_text())["rows"] if r["model"] == "sol"]
        sol_groups = {g["effort"]: g for g in json.loads((SOL56 / "groups.json").read_text()) if g["model"] == "sol"}
        sol_econ = {g["effort"]: g for g in json.loads((SOL56 / "economics.json").read_text())["groups"] if g["model"] == "sol"}
        eg = {r["effort"]: r for r in self.econ["groups"]}
        g = self.groups
        passed = [sum(r["functional"] == 1 for r in sol if r["effort"] == e) for e in EFFORTS]
        self.assertEqual(passed, [6, 12, 20, 21, 22])
        combined = [sol_groups[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertEqual([round(c, 2) for c in combined], [69.05, 82.56, 85.76, 86.47, 87.18])
        self.assertEqual(sol_groups["max"]["n"], 22)
        rows = {"passed-sol": "".join(f"<td>{n}/23</td>" for n in passed),
                "combined-sol": "".join(f"<td>{c:.2f}</td>" for c in combined),
                "se-sol": "".join(f"<td>{sol_groups[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS),
                "cq-sol": "".join(f"<td>{sol_groups[e]['code_quality']['mean']:.2f}</td>" for e in EFFORTS),
                "minutes-sol": "".join(f"<td>{sol_econ[e]['minutes']['mean']:.1f}</td>" for e in EFFORTS),
                "usd-sol": "".join(f"<td>${sol_econ[e]['usd']['mean']:.2f}</td>" for e in EFFORTS),
                "tokens-sol": "".join(f"<td>{sol_econ[e]['raw_tokens']['mean'] / 1e6:.2f}M</td>" for e in EFFORTS),
                "passed-gpt6sol": "".join(f"<td>{g[e]['passed_all_runs']}/23</td>" for e in EFFORTS),
                "combined-gpt6sol": "".join(f"<td>{g[e]['combined_33']['mean']:.2f}</td>" for e in EFFORTS),
                "se-gpt6sol": "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS),
                "cq-gpt6sol": "".join(f"<td>{g[e]['code_quality']['mean']:.2f}</td>" for e in EFFORTS),
                "minutes-gpt6sol": "".join(f"<td>{g[e]['minutes']['mean']:.1f}</td>" for e in EFFORTS),
                "usd-gpt6sol": "".join(f"<td>${eg[e]['usd']['mean']:.2f}</td>" for e in EFFORTS),
                "tokens-gpt6sol": "".join(f"<td>{eg[e]['raw_tokens']['mean'] / 1e6:.2f}M</td>" for e in EFFORTS)}
        for key, cells in rows.items():
            start = self.page_html.index(f'<tr data-compare="{key}">')
            self.assertIn(cells + "</tr>", self.page_html[start:start + 400], key)
        # The claims in the prose: behind at every level, within one SE at the top two, slower everywhere, dearer from Medium up.
        gaps = [sol_groups[e]["combined_33"]["mean"] - g[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertTrue(all(gap > 0 for gap in gaps))
        self.assertIn(f"by {gaps[0]:.2f} points at Low, {gaps[1]:.2f} at Medium, {gaps[2]:.2f} at High, {gaps[3]:.2f} at Extra-high and "
                      f"{gaps[4]:.2f} at Max", self.page_html)
        for e in ("extra-high", "max"):
            gap = sol_groups[e]["combined_33"]["mean"] - g[e]["combined_33"]["mean"]
            self.assertLess(gap, min(sol_groups[e]["combined_33"]["se"], g[e]["combined_33"]["se"]))
        self.assertTrue(all(g[e]["minutes"]["mean"] > sol_econ[e]["minutes"]["mean"] for e in EFFORTS))
        ratios = [eg[e]["usd"]["mean"] / sol_econ[e]["usd"]["mean"] for e in EFFORTS]
        self.assertLess(ratios[0], 1)
        self.assertTrue(all(r > 1 for r in ratios[1:]))
        self.assertEqual((round(100 * (ratios[2] - 1)), round(100 * (ratios[4] - 1))), (14, 42))
        tokens = [eg[e]["raw_tokens"]["mean"] / sol_econ[e]["raw_tokens"]["mean"] for e in EFFORTS]
        self.assertEqual((f"{min(tokens):.1f}", f"{max(tokens):.1f}"), ("1.8", "3.9"))
        self.assertIn("1.8 to 3.9 times the raw tokens per task", self.page_html)
        speed = [g[e]["minutes"]["mean"] / sol_econ[e]["minutes"]["mean"] for e in EFFORTS]
        self.assertEqual((f"{speed[0]:.1f}", f"{speed[4]:.1f}"), ("1.3", "2.1"))

    def test_model_pages(self):
        page = (ROOT / "models/gpt-6-sol.html").read_text()
        self.assertIn("../benchmarks/swe-v4-gpt6-sol-v317.html", page)
        self.assertIn("../benchmarks/swe-v4-gpt6-sol-v317.html#cost", page)
        self.assertIn('href="gpt-5-6-sol.html"', page)
        self.assertIn('href="gpt-6-luna.html"', page)
        self.assertIn('href="gpt-6-sol.html"', (ROOT / "models/gpt-5-6-sol.html").read_text())
        self.assertIn('href="gpt-6-sol.html"', (ROOT / "models/gpt-6-luna.html").read_text())
        self.assertIn('<link rel="canonical" href="https://vulcanbench.com/models/gpt-6-sol.html">', page)
        self.assertNotIn("Luna across", page)
        g = self.groups
        for e in EFFORTS:
            self.assertIn(f"{g[e]['combined_33']['mean']:.2f} at {label(e)}", page)
        self.assertIn(f'${self.econ["totals"]["gpt6sol"]["usd"]:,.2f}', page)
        for text in (page, (ROOT / "models/gpt-5-6-sol.html").read_text(), (ROOT / "models/gpt-6-luna.html").read_text()):
            self.assertNotIn(chr(0x2014), html.unescape(text))
            self.assertNotIn(chr(0x2013), html.unescape(text))
        self.assertIn('href="models/gpt-6-sol.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="/models/gpt-6-sol.html"', self.page_html)

    def test_every_level_everywhere_scores_appear(self):
        for name in ("benchmarks.html", "index.html", "feed.xml", "llms.txt", "models/gpt-6-sol.html", "leaderboard.html",
                     "assets/data/swe-v4-gpt6-sol-v317/README.md"):
            text = (ROOT / name).read_text()
            for figure in ("67.62", "80.60", "82.83", "85.94", "86.82"):
                self.assertIn(figure, text, (name, figure))

    def test_calibration_and_protocol_record(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertFalse(record["allowance_used"])
            self.assertEqual(record["failing_gates"], [])
            self.assertTrue(all(g["passed"] for g in record["gates"].values()))
            self.assertEqual(record["call_count"], 80)
            self.assertEqual(len(record["gates"]), 20)
            self.assertEqual(record["allowance"], {"max_failing_gates": 1, "max_shortfall": 0.5})
        self.assertEqual(self.page_html.count("<td>code-quality-maintenance-v3.17</td><td>80</td><td>passed</td><td>no</td><td>none</td>"), 2)
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.17", "grok": "code-quality-maintenance-v3.17"})
        self.assertEqual(self.protocols["repeats"], 5)
        population = self.protocols["population"]
        self.assertEqual((population["excluded"], population["missing"]), ([], []))
        self.assertEqual(population["cells"], {f"gpt6sol/{e}": 23 for e in EFFORTS})
        self.assertIn("v3.16", self.protocols["amends"])
        [finding] = self.protocols["unpublished"]
        self.assertEqual((finding["effort"], finding["task"], finding["panel"], finding["stage"]), ("medium", "legacy-codeccore-binary-parity", "grok", "probe"))
        self.assertEqual(set(finding["malformed_attempts"]), {"1"})
        self.assertEqual(set(finding["unsupported_excerpts"]), {"2"})
        [recovery] = self.protocols["operator_recoveries"]
        self.assertEqual((recovery["effort"], recovery["task"], recovery["rule"], recovery["removed"]),
                         ("high", "legacy-payrollcore-binary-parity", "recover_trailing_braces", "\n}"))
        self.assertAlmostEqual(recovery["reviewed_score"], 79.1667, places=4)
        payroll = next(r for r in self.rows if r["effort"] == "high" and r["task"] == "legacy-payrollcore-binary-parity")
        self.assertAlmostEqual(payroll["panels"]["grok"]["reviewed_score"], recovery["reviewed_score"], places=9)
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("SWE v4", text, name)
            self.assertNotIn("ultra", text.lower(), name)

    def test_run_disclosures(self):
        text = html.unescape(self.page_html)
        section = text[text.index('id="run-notes"'):text.index('id="reproduce"')]
        for needle in ("Codex CLI 0.155.0", "0.153.4", "refuses GPT-6 models on a ChatGPT account", "stray closing brace", "79.17",
                       "every normal check", "Medium codeccore had no valid answer", "22 of 23",
                       "September 28, 00:31 PDT, to September 29, 14:53 PDT", "GPT-6 Luna's Code quality judging, September 28, 00:32 to 14:32 PDT",
                       "wall-clock speed figures", "at capacity", "the retry is the counted run", "GPT-6.1 Sol", "One attempt per task and level"):
            self.assertIn(needle, section, needle)
        self.assertTrue(any("22 of its 23 runs" in limit for limit in self.provenance["limits"]))
        self.assertTrue(any("at capacity" in limit for limit in self.provenance["limits"]))
        self.assertTrue(any("GPT-6 Luna's v3.16 judging" in limit for limit in self.provenance["limits"]))

    def test_cards_are_pinned_and_placed(self):
        for name, sha in CARDS.items():
            self.assertEqual(hashlib.sha256((ROOT / "assets/cards" / name).read_bytes()).hexdigest(), sha, name)
            self.assertIn(f'href="/assets/cards/{name}" download', self.page_html, name)
            self.assertIn(f'src="/assets/cards/{name}"', self.page_html, name)
        sol = self.page_html[self.page_html.index('id="gpt56-sol"'):self.page_html.index('id="gpt6-family"')]
        self.assertIn('src="/assets/cards/swe-v4-gpt6-vs-gpt56-sol.png"', sol)
        family = self.page_html[self.page_html.index('id="gpt6-family"'):self.page_html.index('id="code-quality"')]
        self.assertIn('src="/assets/cards/swe-v4-gpt6-vs-gpt56-all.png"', family)
        self.assertIn("71.94 and 67.26", family)  # GPT-6 Luna's timeouts-as-0 figures stay beside its judged ones

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
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-gpt6-sol-v317-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "leaderboard.html", "README.md"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-gpt6-sol-v317.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertNotIn("SWE v4", feed_item)
        self.assertIn("VulcanBench Frontier v4", feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn("<loc>https://vulcanbench.com/models/gpt-6-sol.html</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn(f"<guid>{URL}</guid>", (ROOT / "feed.xml").read_text())
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-gpt6-sol-v317.html"), index.index("swe-v4-gpt6-luna-v316.html"))
        self.assertIn("assets/cards/swe-v4-gpt6-sol-v317.png", index)
        home = (ROOT / "index.html").read_text()
        self.assertLess(home.index("swe-v4-gpt6-sol-v317.html"), home.index("swe-v4-gpt6-luna-v316.html"))
        unescaped = html.unescape(self.page_html)
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
            self.assertNotIn(mark, unescaped, mark)
        self.assertIn('class="how-it-works"', self.page_html)
        self.assertIn("share.js", self.page_html)
        self.assertIn("intent/post?text=GPT-6%20Sol%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)


if __name__ == "__main__":
    unittest.main()
