"""Stdlib checks for the DeepSeek V4.1 Flash bundle (v3.27), its report page, its cards, its model page and the site links to them."""

import csv
import hashlib
import json
import re
import statistics
import unittest
from pathlib import Path

from check_benchmark_index import IndexParser
from test_swe_v4_v324 import label, links_resolve, plain

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/swe-v4-deepseek-flash-v327"
PAGE = ROOT / "benchmarks/swe-v4-deepseek-flash-v327.html"
MODEL_PAGE = ROOT / "models/deepseek-v4-1-flash.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-deepseek-flash-v327.html"
MODEL_URL = "https://vulcanbench.com/models/deepseek-v4-1-flash.html"
EFFORTS = ("low", "high", "max")
PANELS = ("muse", "sol")
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
ENTITIES = ("&" + "mdash;", "&" + "ndash;")  # spelled in parts so this file carries no dash entity
RUNS = 69
PASSED = [21, 20, 20]
RATES = (0.15, 0.003, 0.60)  # DeepSeek off-peak list price per million: input cache miss, cache hit, output
# The harness card data (docs/results/swe-v4-deepseek-flash-2026-10/data.json), per level.
CARD = {
    "low": {"combined": 88.65106195760761, "combined_se": 0.6733753879066554, "code_quality": 73.1093511231851, "functional": 98.8404347826087,
            "minutes": 8.054684782608696, "usd": 0.05772682608695652, "billed": 0.10102952173913043, "muse": 64.94565217391305,
            "sol": 74.54710144927536},
    "high": {"combined": 88.60702508361203, "combined_se": 0.9635462101720835, "code_quality": 74.87458193979933, "functional": 97.53608695652174,
             "minutes": 8.659267391304349, "usd": 0.06666321739130435, "billed": 0.06803769565217391, "muse": 68.3876811594203,
             "sol": 76.63043478260869},
    "max": {"combined": 88.35567918168788, "combined_se": 0.9762584445763849, "code_quality": 74.01400806045075, "functional": 97.65695652173913,
            "minutes": 10.596756521739131, "usd": 0.0740565652173913, "billed": 0.07405630434782609, "muse": 67.1195652173913,
            "sol": 74.45652173913044},
}
# Copied byte for byte from the harness (docs/results/swe-v4-deepseek-flash-2026-10/1-summary.png and 2-combined-score.png).
CARDS = (("swe-v4-deepseek-flash-v327.png", "33f583a7be425652b252b1cf218c27d224637ba499e0d7d10cc8615b854f6d28", 1600, 900),
         ("swe-v4-deepseek-flash-v327-combined.png", "564fd17ad6e49f4eb25cdbc5686969883aa63f0fa46dc007059f1692cb6e856f", 1600, 900))
# Published comparator rows: Claude Opus 5.5 (v3.15) and GPT-6.1 Sol (v3.18) bundles.
COMPARATORS = {"opus55": "swe-v4-opus55-v315", "gpt61sol": "swe-v4-gpt61-sol-v318"}
TOUCHED = ("benchmarks/swe-v4-deepseek-flash-v327.html", "models/deepseek-v4-1-flash.html", "models/deepseek-v4-flash.html", "benchmarks.html",
           "index.html", "feed.xml", "llms.txt", "leaderboard.html", "README.md", "assets/data/README.md",
           "assets/data/swe-v4-deepseek-flash-v327/README.md", "assets/data/swe-v4-deepseek-flash-v327/REPRODUCING.md",
           "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v327.py")


class FlashBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), RUNS)
        self.assertEqual((self.runs["published"], self.runs["timeouts"]), (69, 0))
        self.assertEqual(len({(r["effort"], r["task"]) for r in self.rows}), RUNS)
        for r in self.rows:
            self.assertEqual(r["judged"], "published")
            self.assertEqual(r["judged_under"], "code-quality-maintenance-v3.27")
            self.assertTrue(r["finished"] and r["duration_s"] < 10800)
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            self.assertEqual((r["solver_cli_version"], r["requested_model"], r["model_identity"]),
                             ("DeepSeek Harness 0.2.1-rc.2", "deepseek-flash", "harness-recorded"))
            self.assertEqual(r["source_tag"], "bench/2026-10-20-deepseek-dsh-frontier-v4")
            u = r["token_usage"]
            self.assertEqual(u["uncached_input_tokens"], u["input_tokens"] - u["cached_input_tokens"])
            self.assertEqual(r["raw_tokens"], u["input_tokens"] + u["output_tokens"])
            listed = (u["uncached_input_tokens"] * RATES[0] + u["cached_input_tokens"] * RATES[1] + u["output_tokens"] * RATES[2]) / 1e6
            self.assertAlmostEqual(r["list_usd"], listed, delta=5e-7)  # the harness stores it to six places
            self.assertGreaterEqual(r["billed_usd"], r["list_usd"] - 1e-5)  # peak hours only ever double a call
            if r["peak_calls"] == 0:
                self.assertAlmostEqual(r["billed_usd"], r["list_usd"], delta=1e-5)
            else:
                self.assertGreater(r["billed_usd"], r["list_usd"])
            self.assertIn(r["unmetered_title_calls"], (0, 1))
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
            code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            combined = 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100)
            self.assertAlmostEqual(r["combined_33"], combined, places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"]
                                                                    + .20 * code_quality / 100), places=9)
            for p in PANELS:
                alone = (0.24 * r["panels"][p]["reviewed_score"] + 0.09 * r["panels"][p]["intent_recovery"]) / 0.33
                self.assertAlmostEqual(r["combined_single_judge"][p], 100 * (.5 * r["functional"] + .085 * r["automated_quality"]
                                                                             + .085 * r["security"] + .33 * alone / 100), places=9)
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e) for e in EFFORTS], [23, 23, 23])
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e and r["peak_calls"]) for e in EFFORTS], [14, 1, 0])
        self.assertEqual(sum(r["unmetered_title_calls"] for r in self.rows), 66)
        self.assertEqual(sum(r["attempts_without_usage"] for r in self.rows), 3)

    def test_runs_csv_and_scores_csv(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), RUNS)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            self.assertAlmostEqual(float(c["list_usd"]), r["list_usd"], delta=5.1e-7)
            self.assertAlmostEqual(float(c["billed_usd"]), r["billed_usd"], delta=5.1e-7)
            self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], delta=5.1e-5)
            self.assertEqual(c["judged"], "published")
        with (ROOT / "assets/data/swe-v4-deepseek-flash-v327-scores.csv").open(newline="") as source:
            scores = {r["effort"]: r for r in csv.DictReader(source)}
        self.assertEqual(set(scores), set(EFFORTS))  # DeepSeek's API offers no medium or extra-high
        for e, g in self.groups.items():
            self.assertAlmostEqual(float(scores[e]["combined_33"]), g["combined_33"]["mean"], places=4)
            self.assertAlmostEqual(float(scores[e]["mean_list_usd"]), g["usd"]["mean"], places=6)
            self.assertAlmostEqual(float(scores[e]["mean_billed_usd"]), g["billed_usd"]["mean"], places=6)
            self.assertEqual(int(scores[e]["passed_of_23"]), g["passed_all_runs"])

    def test_groups_match_runs_and_card(self):
        self.assertEqual(list(self.groups), list(EFFORTS))
        for i, e in enumerate(EFFORTS):
            g = self.groups[e]
            rs = [r for r in self.rows if r["effort"] == e]
            self.assertEqual((g["runs"], g["n"], g["timeouts"]), (23, 23, 0))
            self.assertEqual(g["passed_all_runs"], PASSED[i])
            self.assertEqual(g["passed"], sum(r["functional"] == 1 for r in rs))
            for field, values in (("combined_33", [r["combined_33"] for r in rs]), ("code_quality", [r["code_quality"] for r in rs]),
                                  ("usd", [r["list_usd"] for r in rs]), ("billed_usd", [r["billed_usd"] for r in rs])):
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(values), places=9)
                self.assertAlmostEqual(g[field]["se"], statistics.stdev(values) / len(values) ** .5, places=9)
            self.assertAlmostEqual(g["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=9)
            c = CARD[e]
            for field, value in (("combined", g["combined_33"]["mean"]), ("combined_se", g["combined_33"]["se"]), ("code_quality", g["code_quality"]["mean"]),
                                 ("functional", g["functional"]["mean"]), ("minutes", g["minutes"]["mean"]), ("usd", g["usd"]["mean"]),
                                 ("billed", g["billed_usd"]["mean"]), ("muse", g["by_panel"]["muse"]["mean"]), ("sol", g["by_panel"]["sol"]["mean"])):
                self.assertAlmostEqual(value, c[field], places=9, msg=(e, field))
        self.assertEqual([round(self.groups[e]["combined_33"]["mean"], 2) for e in EFFORTS], [88.65, 88.61, 88.36])
        self.assertEqual([round(self.groups[e]["combined_33"]["se"], 2) for e in EFFORTS], [0.67, 0.96, 0.98])
        self.assertEqual([round(self.groups[e]["code_quality"]["mean"], 1) for e in EFFORTS], [73.1, 74.9, 74.0])
        self.assertEqual([f'{self.groups[e]["minutes"]["mean"]:.2f}' for e in EFFORTS], ["8.05", "8.66", "10.60"])
        self.assertEqual([f'{self.groups[e]["usd"]["mean"]:.4f}' for e in EFFORTS], ["0.0577", "0.0667", "0.0741"])
        self.assertEqual([f'{self.groups[e]["billed_usd"]["mean"]:.4f}' for e in EFFORTS], ["0.1010", "0.0680", "0.0741"])
        gaps = [self.groups[e]["by_panel"]["sol"]["mean"] - self.groups[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
        self.assertEqual([round(x, 1) for x in gaps], [9.6, 8.2, 7.3])
        self.assertEqual(round(statistics.mean(gaps)), 8)
        t = self.econ["totals"]["dsflash"]
        self.assertEqual((t["runs"], f'{t["list_usd"]:.2f}', f'{t["billed_usd"]:.2f}'), (RUNS, "4.56", "5.59"))
        self.assertEqual(self.econ["rates_per_million_off_peak"]["deepseek-flash"], {"input": 0.15, "cached_input": 0.003, "output": 0.60})
        self.assertEqual(self.econ["alias"]["deepseek-flash"], "DeepSeek-V4.1-Flash-1017")

    def test_judges_and_protocol(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertEqual(record["taken_under"], "code-quality-maintenance-v3.27")
            self.assertTrue(record["passed"])
            self.assertFalse(record["allowance_used"])
            self.assertEqual(record["failing_gates"], [])
            self.assertEqual(record["call_count"], 80)
        p = self.protocols
        self.assertEqual(set(p["scored_panel"]), set(PANELS))
        self.assertEqual(p["scored_panel"]["muse"]["model"], "muse-spark-1.3")
        self.assertEqual((p["scored_panel"]["sol"]["model"], p["scored_panel"]["sol"]["effort"], p["scored_panel"]["sol"]["codex_version"]),
                         ("gpt-6.1-sol", "medium", "0.159.0"))
        v320 = json.loads((ROOT / "assets/data/swe-v4-grok47-cursor-v320/judge-protocols.json").read_text())
        for key in ("rubric", "system", "probe_instruction", "match_instruction", "schemas", "weights", "seed", "repeats", "gate_allowance"):
            self.assertEqual(p[key], v320[key], key)
        self.assertEqual(p["scored_panel"]["muse"]["binary_sha256"], v320["scored_panel"]["muse"]["binary_sha256"])
        self.assertEqual(p["scored_panel"]["sol"]["binary_sha256"], v320["scored_panel"]["sol"]["binary_sha256"])
        self.assertIn("out of usage", p["seat"])
        self.assertEqual(p["counted_calls"], {q: {"calibration": 80, "match": 69, "pairwise": 6, "primary": 69, "probe": 69, "repeat": 3} for q in PANELS})
        self.assertEqual(p["second_attempts"], {"muse": 2, "sol": 10})
        self.assertEqual(len(p["operator_recoveries"]), 6)
        self.assertTrue(all(r["panel"] == "sol" and r["stage"] == "match" for r in p["operator_recoveries"]))
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), *ENTITIES, "/Users/", "/home/", "/private/", "/var/folders/", "SWE v4",
                         "no model on the board"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("ultra", text.lower(), name)


class FlashPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.econ = {g["effort"]: g for g in json.loads((DATA / "economics.json").read_text())["groups"]}

    def section(self, start, end):
        return plain(self.page_html[self.page_html.index(f'id="{start}"'):self.page_html.index(f'id="{end}"')])

    def test_no_placeholders_left(self):
        left = {name: (ROOT / name).read_text().count(PLACEHOLDER) for name in TOUCHED}
        self.assertEqual({name: n for name, n in left.items() if n}, {})

    def test_structure_writing_and_links(self):
        for markup in (self.page_html, MODEL_PAGE.read_text()):
            parser = IndexParser()
            parser.feed(markup)
            text = plain(markup)
            self.assertEqual(parser.structure_errors, [])
            self.assertEqual(parser.structure, [])
            self.assertEqual(len(parser.ids), len(set(parser.ids)))
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra", "no model on the board", "no model on this board"):
                self.assertNotIn(mark, text, mark)
            for entity in ENTITIES:
                self.assertNotIn(entity, markup)
        links_resolve(self, self.page)
        model = IndexParser()
        model.feed(MODEL_PAGE.read_text())
        for link in model.links:  # relative links on the model page resolve from models/
            if "://" in link or link.startswith(("#", "mailto:")):
                continue
            self.assertTrue((ROOT / "models" / link.split("#")[0].split("?")[0]).resolve().is_file(), link)
        self.assertIn(f'<link rel="canonical" href="{URL}">', self.page_html)
        self.assertIn("intent/post?text=DeepSeek%20V4.1%20Flash%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertIn("Morgan Linton", self.text)
        self.assertNotIn(".pdf", self.page_html)
        self.assertNotIn("/analysis/", self.page_html)  # no Analysis page for this report
        for target in ("https://github.com/morganlinton/VulcanBench", "https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md",
                       "https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/deepseek_harness.py"):
            self.assertIn(f'href="{target}"', self.page_html)

    def test_tables_match_the_bundle(self):
        g, c = self.groups, self.econ
        self.assertEqual(set(self.page.rows), {("dsflash", e) for e in EFFORTS})
        for i, e in enumerate(EFFORTS):
            row = self.page.rows["dsflash", e]
            self.assertEqual(row[1:5], [label(e), f'{g[e]["combined_33"]["mean"]:.2f}', f'{g[e]["combined_33"]["se"]:.2f}',
                                        f'{g[e]["combined_20_profile"]["mean"]:.2f}'])
            self.assertEqual(row[5:9], [f'{g[e]["code_quality"]["mean"]:.2f}', f'{g[e]["readability"]["mean"]:.1f}',
                                        f'{g[e]["maintainability"]["mean"]:.1f}', f'{g[e]["intent_recovery"]["mean"]:.1f}'])
            self.assertEqual(row[-3:], ["23/23", f'{g[e]["passed_all_runs"]}/23', f'{g[e]["minutes"]["mean"]:.1f}'])
            cells = (f'<td>23</td><td>${c[e]["usd"]["mean"]:.4f}</td><td>${c[e]["usd"]["se"]:.4f}</td><td>${c[e]["billed_usd"]["mean"]:.4f}</td>'
                     f'<td>{c[e]["runs_with_peak_calls"]}</td><td>${c[e]["usd_total"]:.2f}</td><td>${c[e]["billed_usd_total"]:.2f}</td>'
                     f'<td>{c[e]["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>{c[e]["output_tokens"]["mean"] / 1e3:.1f}K</td>'
                     f'<td>{c[e]["minutes"]["mean"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}', self.page_html, e)
        self.assertIn('<th scope="row">Combined score</th>' + "".join(f'<td>{g[e]["combined_33"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Tasks passed</th>' + "".join(f"<td>{p}/23</td>" for p in PASSED), self.page_html)
        self.assertIn('<th scope="row">Hidden behaviours fixed</th>' + "".join(f'<td>{g[e]["hidden_behaviours_fixed"]}/231</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">Minutes per task</th>' + "".join(f'<td>{g[e]["minutes"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">$ per task (list)</th>' + "".join(f'<td>${g[e]["usd"]["mean"]:.4f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">$ per task (billed)</th>' + "".join(f'<td>${g[e]["billed_usd"]["mean"]:.4f}</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">Rated by Muse Spark 1.3</th>' + "".join(f'<td>{g[e]["by_panel"]["muse"]["mean"]:.1f}</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">Rated by GPT-6.1 Sol</th>' + "".join(f'<td>{g[e]["by_panel"]["sol"]["mean"]:.1f}</td>' for e in EFFORTS),
                      self.page_html)
        judges = self.section("judges", "run-notes")
        for e in EFFORTS:
            for p in PANELS:
                self.assertIn(f'{g[e]["combined_single_judge"][p]["mean"]:.2f}', judges, (e, p))

    def test_comparison_matches_the_published_bundles(self):
        for key, bundle in COMPARATORS.items():
            groups = {x["effort"]: x for x in json.loads((ROOT / "assets/data" / bundle / "groups.json").read_text()) if x["model"] == key}
            econ = {x["effort"]: x for x in json.loads((ROOT / "assets/data" / bundle / "economics.json").read_text())["groups"] if x["model"] == key}
            for e in EFFORTS:
                g, x = groups[e], econ[e]
                passed = g.get("passed_all_runs", g["passed"])
                judged = f'{g["n"]}' + ("*" if g["n"] < 23 else "")
                cells = (f'<td>{label(e)}</td><td>{g["combined_33"]["mean"]:.2f}</td><td>{g["combined_33"]["se"]:.2f}</td><td>{judged}</td>'
                         f'<td>{passed}/23</td><td>{x["minutes"]["mean"]:.1f}</td><td>${x["usd"]["mean"]:.2f}</td>')
                row = self.page_html[self.page_html.index(f'data-compare="{key}-{e}"'):]
                self.assertIn(cells, row[:row.index("</tr>")], (key, e))
        for e in EFFORTS:
            row = self.page_html[self.page_html.index(f'data-compare="dsflash-{e}"'):]
            g = self.groups[e]
            self.assertIn(f'<td>{g["combined_33"]["mean"]:.2f}</td><td>{g["combined_33"]["se"]:.2f}</td><td>23</td><td>{g["passed_all_runs"]}/23</td>'
                          f'<td>{g["minutes"]["mean"]:.1f}</td><td>${g["usd"]["mean"]:.3f}</td>', row[:row.index("</tr>")])
        comparison = self.section("comparison", "cost")
        for needle in ("highest combined score of the three", "behind Opus 5.5", "essentially level with GPT-6.1 Sol", "5.3, 5.0 and 6.2 times",
                       "29, 49 and 118 times", "not calibrated against each other", "judges a column it is shown beside", "22 judged runs"):
            self.assertIn(needle, comparison, needle)

    def test_required_disclosures(self):
        cost = self.section("cost", "board")
        for needle in ("API key", "off-peak", "$0.15", "$0.003", "$0.60", "01:00 to 04:00 and 06:00 to 10:00 UTC", "2x", "14 of the 23 Low runs",
                       "$4.56", "$5.59", "66 of the 69 runs", "not priced", "well under a cent"):
            self.assertIn(needle, cost, needle)
        board = self.section("board", "code-quality")
        for needle in ("ranks 22nd of the board’s 70", "23rd and 24th", "not calibrated against each other", "pick Low"):
            self.assertIn(needle, board, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("Muse Spark 1.3", "GPT-6.1 Sol", "Grok 4.6", "Cursor", "out of usage", "as protocol v3.20 did for Grok 4.7",
                       "byte-identical backup", "judges a column it is shown beside", "about 8 points above", "9.6 at Low, 8.2 at High and 7.3 at Max",
                       "passed every gate with no allowance used", "Six of Sol’s answer-key matches"):
            self.assertIn(needle, judges, needle)
        notes = self.section("run-notes", "reproduce")
        for needle in ("deepseek-flash", "DeepSeek-V4.1-Flash-1017", "harness-recorded", "@deepseek-ai/dsh", "MIT", "0.2.1-rc.2",
                       "developer preview", "headless", "install tree", "outer sandbox", "Web tools were off", "session’s log",
                       "OpenTelemetry", "owner’s choice", "task content still reaches DeepSeek", "no medium", "paused the sweep twice",
                       "rerun", "26 to 27.0.1", "13 Low runs", "No hash bridge", "No timeouts, no overlapping jobs"):
            self.assertIn(needle, notes, needle)
        self.assertIn("never compared with Routine v1 Code quality", self.text)

    def test_cards_pinned(self):
        for name, sha, width, height in CARDS:
            data = (ROOT / "assets/cards" / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), sha)
            self.assertEqual((int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")), (width, height))
            self.assertIn(f'src="/assets/cards/{name}" width="{width}" height="{height}"', self.page_html)
        self.assertIn('<meta property="og:image" content="https://vulcanbench.com/assets/cards/swe-v4-deepseek-flash-v327.png">', self.page_html)
        self.assertIn('<meta property="og:image:height" content="900">', self.page_html)


class FlashSiteTests(unittest.TestCase):
    def test_model_page_links_report(self):
        markup = MODEL_PAGE.read_text()
        self.assertIn('href="../benchmarks/swe-v4-deepseek-flash-v327.html"', markup)
        self.assertIn(f'<link rel="canonical" href="{MODEL_URL}">', markup)
        for value in ("88.65", "88.61", "88.36", "21, 20 and 20 of 23", "22nd of 70"):
            self.assertIn(value, markup, value)
        self.assertIn('href="deepseek-v4-flash.html"', markup)
        self.assertIn('href="deepseek-v4-1-flash.html"', (ROOT / "models/deepseek-v4-flash.html").read_text())

    def test_site_references(self):
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "models/deepseek-v4-1-flash.html"):
            self.assertIn("swe-v4-deepseek-flash-v327.html", (ROOT / name).read_text(), name)
        self.assertIn('href="models/deepseek-v4-1-flash.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn("swe-v4-deepseek-flash-v327/", (ROOT / "assets/data/README.md").read_text())
        sitemap = (ROOT / "sitemap.xml").read_text()
        for page_url in (URL, MODEL_URL):
            self.assertIn(f"<loc>{page_url}</loc>", sitemap)
        item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in i)
        self.assertIn("VulcanBench Frontier v4", item)
        self.assertIn("23 Oct 2026", item)
        self.assertNotIn(chr(0x2014), item)
        leaderboard = (ROOT / "leaderboard.html").read_text()
        self.assertIn('<a href="benchmarks/swe-v4-deepseek-flash-v327.html">DeepSeek V4.1 Flash</a>', leaderboard)
        self.assertEqual(len(re.findall(r'data-model="dsflash" data-effort="[a-z-]+" data-best', leaderboard)), 3)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-deepseek-flash-v327.html"), index.index("swe-v4-musewonder-full-v326.html"))


if __name__ == "__main__":
    unittest.main()
