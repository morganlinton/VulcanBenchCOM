"""Stdlib checks for the v3.16 GPT-6 Luna bundle, its report page and the site links to it."""

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
DATA = ROOT / "assets/data/swe-v4-gpt6-luna-v316"
PAGE = ROOT / "benchmarks/swe-v4-gpt6-luna-v316.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-gpt6-luna-v316.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
TIMEOUTS = [("extra-high", "legacy-depotcore-binary-parity"), ("extra-high", "legacy-paddockcore-binary-parity"),
            ("max", "legacy-cellarcore-binary-parity"), ("max", "legacy-depotcore-binary-parity"),
            ("max", "legacy-lodgecore-binary-parity"), ("max", "legacy-paddockcore-binary-parity")]
CARD_SHA256 = "f8e8e6481eca32b7f5c401a22905ab86c69b733d15baf29c955cb9ed9f535dca"
ECONOMICS_CARD_SHA256 = "455e54800f0a61210605fd80cc139cae6392711e2fe262fc1a2b0306268cf08b"
COMPARISON_CARD_SHA256 = "6c2fc0cedf14782629fb658f72b4f566588be1f83515dae6577ac5452a840c1c"  # GPT-6 Luna vs. GPT-5.6 Luna, make_gpt6_vs_gpt56_cards.py


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


class GPT6LunaBundleTests(unittest.TestCase):
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
        with (ROOT / "assets/data/swe-v4-gpt6-luna-v316-scores.csv").open(newline="") as source:
            cls.scores = {r["effort"]: r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 115)
        self.assertEqual((self.runs["published"], self.runs["timeouts"]), (109, 6))
        self.assertEqual(len(self.published), 109)
        self.assertTrue(all(r["judged_under"] == "code-quality-maintenance-v3.16" for r in self.rows))
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        timeouts = [r for r in self.rows if r["judged"] != "published"]
        self.assertEqual([(r["effort"], r["task"]) for r in timeouts], TIMEOUTS)
        for r in timeouts:
            self.assertTrue(r["judged"].startswith("timeout: "))
            self.assertFalse(r["finished"])
            self.assertEqual(r["functional"], 0.0)
            self.assertEqual(r["combined_timeouts_zero"], 0.0)
            self.assertGreaterEqual(r["duration_s"], 10800)
            for field in ("reviewed_score", "intent_recovery", "code_quality", "combined_33", "combined_20_profile", "panels",
                          "raw_tokens", "token_usage", "estimated_usd"):
                self.assertIsNone(r[field], field)  # unpriced, never $0
        redistributed = 0
        for r in self.published:
            self.assertTrue(r["finished"])
            self.assertEqual(r["solver_cli_version"], "codex-cli 0.155.0")
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            if r["intent_recovery_redistributed"]:
                redistributed += 1
                self.assertEqual(r["passed_quirk_families"], 0)
                self.assertIsNone(r["intent_recovery"])
                code_quality = reviewed
            else:
                self.assertGreater(r["passed_quirk_families"], 0)
                intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
                self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
                code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            self.assertEqual(r["combined_timeouts_zero"], r["combined_33"])
            for p in PANELS:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"],
                                       (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
            usage, rate = r["token_usage"], self.econ["rates_per_million"][r["model"]]
            cached = min(usage["cached_input_tokens"], usage["input_tokens"])
            priced = ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6
            self.assertAlmostEqual(r["estimated_usd"], priced, places=5, msg=r["run_id"])
            self.assertGreater(r["raw_tokens"], 0)
        self.assertEqual(redistributed, 14)
        self.assertFalse(any(r["solver_fallback"] for r in self.rows))
        self.assertEqual(len({(r["effort"], r["task"]) for r in self.rows}), 115)

    def test_runs_csv_matches_runs_json(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = list(csv.DictReader(source))
        self.assertEqual(len(csv_rows), 115)
        by_run = {r["run_id"]: r for r in csv_rows}
        for r in self.rows:
            c = by_run[r["run_id"]]
            self.assertAlmostEqual(float(c["combined_timeouts_zero"]), r["combined_timeouts_zero"], places=3)
            if r["judged"] == "published":
                self.assertEqual(c["judged"], "published")
                self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], places=3)
                self.assertAlmostEqual(float(c["code_quality"]), r["code_quality"], places=3)
                self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], places=6)
                self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])
            else:
                self.assertEqual((c["judged"], c["finished"]), ("timeout", "False"))
                for column in ("combined_33", "code_quality", "estimated_usd", "raw_tokens", "grok_intent_recovery"):
                    self.assertEqual(c[column], "", column)

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), set(EFFORTS))
        self.assertEqual(set(self.scores), set(EFFORTS))
        for effort, g in self.groups.items():
            rs = [r for r in self.rows if r["effort"] == effort]
            judged = [r for r in rs if r["judged"] == "published"]
            scored = [r for r in judged if r["intent_recovery"] is not None]
            priced = [r for r in rs if r["estimated_usd"] is not None]
            self.assertEqual((len(rs), g["runs"]), (23, 23))
            self.assertEqual(g["n"], len(judged))
            self.assertEqual(g["timeouts"], 23 - g["n"])
            self.assertEqual(g["priced_runs"], len(priced))
            for field, values in (("combined_33", [r["combined_33"] for r in judged]),
                                  ("combined_timeouts_zero", [r["combined_timeouts_zero"] for r in rs]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in judged]),
                                  ("code_quality", [r["code_quality"] for r in judged]),
                                  ("reviewed_score", [r["reviewed_score"] for r in judged]),
                                  ("intent_recovery", [r["intent_recovery"] for r in scored]),
                                  ("readability", [statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged]),
                                  ("maintainability", [statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]),
                                  ("usd", [r["estimated_usd"] for r in priced]),
                                  ("raw_tokens", [r["raw_tokens"] for r in priced])):
                mean, se = mean_se(values)
                self.assertEqual(g[field]["n"], len(values), (effort, field))
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(effort, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(effort, field))
            # The timeouts-as-0 figure is the judged sum over all 23 runs.
            self.assertAlmostEqual(g["combined_timeouts_zero"]["mean"], g["combined_33"]["mean"] * g["n"] / 23, places=9)
            self.assertEqual(g["passed_all_runs"], sum(r["functional"] == 1 for r in rs))
            self.assertEqual(g["passed"], g["passed_all_runs"])
            row = self.scores[effort]
            self.assertEqual((int(row["n"]), int(row["runs"]), int(row["timeouts"])), (g["n"], 23, g["timeouts"]))
            for column, field in (("combined_33", "combined_33"), ("combined_timeouts_zero", "combined_timeouts_zero"),
                                  ("combined_20_profile", "combined_20_profile"), ("code_quality", "code_quality"), ("readability", "readability"),
                                  ("maintainability", "maintainability"), ("intent_recovery", "intent_recovery"), ("mean_minutes_all_runs", "minutes")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(effort, column))
            self.assertAlmostEqual(float(row["combined_timeouts_zero_se"]), g["combined_timeouts_zero"]["se"], places=4)
            self.assertEqual(int(row["passed_of_23"]), g["passed_all_runs"])
        g = self.groups
        self.assertEqual([g[e]["n"] for e in EFFORTS], [23, 23, 23, 21, 19])
        self.assertEqual([g[e]["timeouts"] for e in EFFORTS], [0, 0, 0, 2, 4])
        self.assertEqual([g[e]["passed_all_runs"] for e in EFFORTS], [0, 0, 2, 11, 12])
        self.assertEqual([round(g[e]["combined_33"]["mean"], 2) for e in EFFORTS], [40.83, 45.72, 57.35, 78.79, 81.42])
        self.assertEqual([round(g[e]["combined_timeouts_zero"]["mean"], 2) for e in EFFORTS], [40.83, 45.72, 57.35, 71.94, 67.26])
        self.assertEqual([round(g[e]["code_quality"]["mean"], 2) for e in EFFORTS], [65.84, 69.33, 66.40, 71.49, 71.51])
        self.assertEqual([round(g[e]["minutes"]["mean"], 1) for e in EFFORTS], [5.6, 3.6, 15.6, 52.6, 60.5])
        self.assertEqual([g[e]["intent_recovery_redistributed_runs"] for e in EFFORTS], [10, 3, 1, 0, 0])

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), {("gpt6luna", e) for e in EFFORTS})
        for effort, g in self.groups.items():
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_timeouts_zero"]["mean"]:.2f}',
                        f'{g["combined_20_profile"]["mean"]:.2f}', f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}',
                        f'{g["maintainability"]["mean"]:.1f}', f'{g["intent_recovery"]["mean"]:.1f}', f'{g["n"]}/23',
                        f'{g["passed_all_runs"]}/23', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows["gpt6luna", effort][2:], expected, effort)
            self.assertEqual(self.page.rows["gpt6luna", effort][1], label(effort))
        g = self.groups
        for name, key, d in (("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
                             ("Intent recovery", "intent_recovery", 1)):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e][key]['mean']:.{d}f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        for name, p in (("Rated by Muse Spark 1.3", "muse"), ("Rated by Grok 4.6", "grok")):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e]['by_panel'][p]['mean']:.1f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f"<td>{g[e]['code_quality']['se']:.2f}</td>" for e in EFFORTS), self.page_html)

    def test_across_efforts_table(self):
        g = self.groups
        eg = {r["effort"]: r for r in self.econ["groups"]}

        def cells(key, digits):
            return "".join(f"<td>{g[e][key]['mean']:.{digits}f}</td>" for e in EFFORTS)

        for name, html_cells in (("Combined score, judged runs", cells("combined_33", 2)),
                                 ("Combined score, timeouts counted as 0", cells("combined_timeouts_zero", 2)),
                                 ("Standard error, judged runs", "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS)),
                                 ("Judged runs", "".join(f"<td>{g[e]['n']}</td>" for e in EFFORTS)),
                                 ("Tasks passed", "".join(f"<td>{g[e]['passed_all_runs']}/23</td>" for e in EFFORTS)),
                                 ("Runs stopped at the 3-hour bound", "".join(f"<td>{g[e]['timeouts']}</td>" for e in EFFORTS)),
                                 ("Code quality", cells("code_quality", 2)), ("Human readability", cells("readability", 1)),
                                 ("Minutes per task", cells("minutes", 1)),
                                 ("API-equivalent $ per task", "".join(f"<td>${eg[e]['usd']['mean']:.3f}</td>" for e in EFFORTS))):
            self.assertIn(f'<th scope="row">{name}</th>{html_cells}</tr>', self.page_html, name)
        comb = [g[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertEqual(comb, sorted(comb))
        self.assertIn(f"{comb[0]:.2f} at Low to {comb[4]:.2f} at Max", self.page_html)
        self.assertIn(f"{comb[1] - comb[0]:.1f} points from Low to Medium, then {comb[2] - comb[1]:.1f} to High, {comb[3] - comb[2]:.1f} to Extra-high and {comb[4] - comb[3]:.1f} to Max", self.page_html)
        zero = [g[e]["combined_timeouts_zero"]["mean"] for e in EFFORTS]
        self.assertLess(zero[4], zero[3])  # with timeouts as 0, Max falls below Extra-high
        self.assertIn(f"{zero[3]:.2f} at Extra-high and {zero[4]:.2f} at Max", self.page_html)
        cq = [g[e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(cq):.2f} to {max(cq):.2f}", self.page_html)
        minutes = [g[e]["minutes"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(minutes):.1f} to {max(minutes):.1f} min", self.page_html)

    def test_economics_table_and_card(self):
        eg = {r["effort"]: r for r in self.econ["groups"]}
        for e in EFFORTS:
            b = eg[e]
            rs = [r for r in self.rows if r["effort"] == e]
            priced = [r for r in rs if r["estimated_usd"] is not None]
            self.assertEqual((b["n"], b["runs"], b["unpriced_timeouts"]), (len(priced), 23, 23 - len(priced)))
            self.assertAlmostEqual(b["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in priced), places=9)
            self.assertAlmostEqual(b["usd_total"], sum(r["estimated_usd"] for r in priced), places=6)
            self.assertAlmostEqual(b["raw_tokens"]["mean"], statistics.mean(r["raw_tokens"] for r in priced), places=6)
            self.assertAlmostEqual(b["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=6)
            cells = (f'<td>{b["n"]}</td><td>${b["usd"]["mean"]:.3f}</td><td>${b["usd_total"]:.2f}</td>'
                     f'<td>{b["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>{b["minutes"]["mean"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}</tr>', self.page_html, e)
        t = self.econ["totals"]["gpt6luna"]
        priced = [r for r in self.rows if r["estimated_usd"] is not None]
        self.assertAlmostEqual(t["usd"], sum(r["estimated_usd"] for r in priced), places=6)
        self.assertEqual(t["raw_tokens"], sum(r["raw_tokens"] for r in priced))
        self.assertEqual((t["runs"], t["priced_runs"], t["unpriced_timeouts"]), (115, 109, 6))
        self.assertEqual(f'{t["usd"]:.2f}', "7.26")
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>109</td><td>${t["usd"] / 109:.3f}</td><td>${t["usd"]:,.2f}</td>'
                      f'<td>{t["raw_tokens"] / 1e6:,.0f}M</td><td>{t["solver_hours"]:.1f} h</td>', self.page_html)
        self.assertEqual(self.econ["rates_per_million"], {"gpt6luna": {"input": 0.1, "cached_input": 0.01, "output": 0.5}})
        self.assertEqual(self.econ["pricing_verified"], "2026-09-25")
        self.assertEqual(len(self.econ["unpriced"]), 6)
        self.assertIn("unpriced, not $0", self.page_html)
        self.assertIn("no long-context premium applies", self.page_html)
        card = ROOT / "assets/cards/swe-v4-gpt6-luna-v316-economics.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), ECONOMICS_CARD_SHA256)

    def test_gpt56_luna_comparison(self):
        luna = json.loads((ROOT / "assets/data/swe-v4-gpt55-luna-v35/runs.json").read_text())["rows"]
        luna = [r for r in luna if r["model"] == "luna"]
        luna_groups = {g["effort"]: g for g in json.loads((ROOT / "assets/data/swe-v4-gpt55-luna-v35/groups.json").read_text()) if g["model"] == "luna"}
        luna_econ = {g["effort"]: g for g in json.loads((ROOT / "assets/data/swe-v4-gpt55-luna-v35/economics.json").read_text())["groups"] if g["model"] == "luna"}
        passed = [sum(r["functional"] == 1 for r in luna if r["effort"] == e) for e in EFFORTS]
        self.assertEqual(passed, [0, 1, 9, 13, 19])
        self.assertIn('<th scope="row">Tasks passed, GPT-5.6 Luna</th>' + "".join(f"<td>{n}/23</td>" for n in passed), self.page_html)
        self.assertIn('<th scope="row">Combined, GPT-5.6 Luna</th>' + "".join(f"<td>{luna_groups[e]['combined_33']['mean']:.2f}</td>" for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">$ per task, GPT-5.6 Luna</th>' + "".join(f"<td>${luna_econ[e]['usd']['mean']:.3f}</td>" for e in EFFORTS), self.page_html)
        for name, source in (("GPT-6 Luna", self.rows), ("GPT-5.6 Luna", luna)):
            medians = [statistics.median(r["duration_s"] / 60 for r in source if r["effort"] == e) for e in EFFORTS]
            self.assertIn(f'<th scope="row">Median minutes, {name}</th>' + "".join(f"<td>{m:.1f}</td>" for m in medians), self.page_html)
        mine = statistics.median(r["duration_s"] / 60 for r in self.rows if r["effort"] == "medium")
        theirs = statistics.median(r["duration_s"] / 60 for r in luna if r["effort"] == "medium")
        self.assertIn(f"median {mine:.1f} minutes", self.page_html)
        self.assertIn(f"against {theirs:.1f} minutes", self.page_html)
        out_mine = statistics.median(r["token_usage"]["output_tokens"] for r in self.rows if r["effort"] == "medium")
        out_theirs = statistics.median(r["token_usage"]["output_tokens"] for r in luna if r["effort"] == "medium")
        self.assertIn(f"{out_mine:,.0f} output tokens, against {theirs:.1f} minutes and {out_theirs:,.0f}", self.page_html)
        self.assertFalse(any(r.get("finished") is False for r in luna))
        slow = [r for r in luna if r["duration_s"] > 10800]
        self.assertEqual([(r["effort"], r["task"], r["functional"]) for r in slow], [("max", "legacy-paddockcore-binary-parity", 1.0)])
        self.assertIn(f"took {slow[0]['duration_s'] / 60:.0f} minutes", self.page_html)

    def test_model_pages(self):
        page = (ROOT / "models/gpt-6-luna.html").read_text()
        self.assertIn("../benchmarks/swe-v4-gpt6-luna-v316.html", page)
        self.assertIn("../benchmarks/swe-v4-gpt6-luna-v316.html#cost", page)
        self.assertIn('href="gpt-5-6-luna.html"', page)
        self.assertIn('href="gpt-6-luna.html"', (ROOT / "models/gpt-5-6-luna.html").read_text())
        self.assertIn('<link rel="canonical" href="https://vulcanbench.com/models/gpt-6-luna.html">', page)
        g = self.groups
        for e in EFFORTS:
            self.assertIn(f"{g[e]['combined_33']['mean']:.2f} at {label(e)}", page)
        self.assertIn(f"gives {g['extra-high']['combined_timeouts_zero']['mean']:.2f} at Extra-high and {g['max']['combined_timeouts_zero']['mean']:.2f} at Max", page)
        self.assertIn(f'${self.econ["totals"]["gpt6luna"]["usd"]:,.2f}', page)
        for text in (page, (ROOT / "models/gpt-5-6-luna.html").read_text()):
            self.assertNotIn(chr(0x2014), html.unescape(text))
            self.assertNotIn(chr(0x2013), html.unescape(text))
        self.assertIn('href="models/gpt-6-luna.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="/models/gpt-6-luna.html"', self.page_html)

    def test_both_figures_everywhere_scores_appear(self):
        for name in ("benchmarks.html", "index.html", "feed.xml", "llms.txt", "models/gpt-6-luna.html", "leaderboard.html",
                     "assets/data/swe-v4-gpt6-luna-v316/README.md"):
            text = (ROOT / name).read_text()
            for figure in ("78.79", "81.42", "71.94", "67.26"):
                self.assertIn(figure, text, (name, figure))

    def test_calibration_and_protocol_record(self):
        failing = {"muse": ("g11_repeatability", 0.06), "grok": ("g04_formatting_is_presentation", 0.10)}
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertTrue(record["allowance_used"])
            gate, shortfall = failing[judge]
            self.assertEqual(record["failing_gates"], [gate])
            self.assertAlmostEqual(record["gates"][gate]["shortfall"], shortfall, places=9)
            self.assertEqual(sum(not g["passed"] for g in record["gates"].values()), 1)
            self.assertEqual(record["call_count"], 80)
            self.assertEqual(len(record["gates"]), 20)
            self.assertEqual(record["allowance"], {"max_failing_gates": 1, "max_shortfall": 0.5})
        self.assertIn("<td>passed</td><td>yes</td><td>gate 11, repeatability, short by 0.06</td>", self.page_html)
        self.assertIn("<td>passed</td><td>yes</td><td>gate 4, formatting is presentation, short by 0.10</td>", self.page_html)
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.16", "grok": "code-quality-maintenance-v3.16"})
        self.assertEqual(self.protocols["repeats"], 5)
        population = self.protocols["population"]
        self.assertEqual(population["missing"] if "missing" in population else [], [])
        self.assertEqual([(e["effort"], e["task"]) for e in population["excluded"]], TIMEOUTS)
        self.assertEqual(population["cells"], {"gpt6luna/low": 23, "gpt6luna/medium": 23, "gpt6luna/high": 23, "gpt6luna/extra-high": 21, "gpt6luna/max": 19})
        self.assertIn("v3.15", self.protocols["amends"])
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("SWE v4", text, name)
            self.assertNotIn("ultra", text.lower(), name)

    def test_run_disclosures(self):
        text = html.unescape(self.page_html)
        for needle in ("Codex CLI 0.155.0", "0.153.4", "about 88 idle minutes", "The retry is the counted run", "GPT-6 Sol solver sweep",
                       "00:32 to 14:32 PDT", "One attempt per task and level", "Six runs hit the flat 3-hour task bound"):
            self.assertIn(needle, text, needle)
        for e, task in TIMEOUTS:
            short = task.replace("legacy-", "").replace("-binary-parity", "")
            self.assertIn(f'<tr data-timeout="{e}/{short}"><th scope="row">{label(e)}</th><td>{short}</td><td>180.0</td>', self.page_html)
        self.assertTrue(any("21 of its 23 runs" in limit and "19 of its 23" in limit for limit in self.provenance["limits"]))

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
        card = ROOT / "assets/cards/swe-v4-gpt6-luna-v316.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), CARD_SHA256)
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-gpt6-luna-v316-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "leaderboard.html", "README.md"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-gpt6-luna-v316.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertNotIn("SWE v4", feed_item)
        self.assertIn("VulcanBench Frontier v4", feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn("<loc>https://vulcanbench.com/models/gpt-6-luna.html</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn(f"<guid>{URL}</guid>", (ROOT / "feed.xml").read_text())
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-gpt6-luna-v316.html"), index.index("swe-v4-opus55-v315.html"))
        self.assertIn("assets/cards/swe-v4-gpt6-luna-v316.png", index)
        home = (ROOT / "index.html").read_text()
        self.assertLess(home.index("swe-v4-gpt6-luna-v316.html"), home.index("swe-v4-opus55-v315.html"))
        unescaped = html.unescape(self.page_html)
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
            self.assertNotIn(mark, unescaped, mark)
        self.assertIn('class="how-it-works"', self.page_html)


class ComparisonCardTests(unittest.TestCase):
    def test_comparison_card_is_pinned_and_placed(self):
        card = ROOT / "assets/cards/swe-v4-gpt6-vs-gpt56-luna.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), COMPARISON_CARD_SHA256)
        page = (ROOT / "benchmarks/swe-v4-gpt6-luna-v316.html").read_text()
        section = page[page.index('id="gpt56-luna"') : page.index('id="code-quality"')]
        self.assertIn('src="/assets/cards/swe-v4-gpt6-vs-gpt56-luna.png"', section)
        self.assertIn('href="/assets/cards/swe-v4-gpt6-vs-gpt56-luna.png" download', page)


if __name__ == "__main__":
    unittest.main()
