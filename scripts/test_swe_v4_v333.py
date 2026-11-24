"""Stdlib checks for the GPT-6.2 Astra bundle (v3.33), its report page, its card, its model page and the site links to them."""

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
DATA = ROOT / "assets/data/swe-v4-gpt62-astra-v333"
PAGE = ROOT / "benchmarks/swe-v4-gpt62-astra-v333.html"
MODEL_PAGE = ROOT / "models/gpt-6-2-astra.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-gpt62-astra-v333.html"
MODEL_URL = "https://vulcanbench.com/models/gpt-6-2-astra.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
ENTITIES = ("&" + "mdash;", "&" + "ndash;")  # spelled in parts so this file carries no dash entity
RUNS = 115
# GPT-6.2 Astra list rates per million tokens, checked 2026-11-22 (standard tier, short context).
RATES = {"input": 8.00, "cached_input": 0.40, "output": 40.00}
# The harness card's per-level table (docs/results/swe-v4-gpt62-astra-2026-11/gpt62astra-vs-gpt6astra-efforts.csv), to four places:
# combined, its standard error, Code quality, minutes and $ per task.
CARD = {"low": (87.6795, 0.4439, 67.2658, 1.7200, 0.5213), "medium": (88.8873, 0.3333, 70.6517, 2.3597, 0.6662),
        "high": (89.2617, 0.3057, 72.8829, 3.6110, 0.9965), "extra-high": (89.0531, 0.3556, 72.9785, 5.6665, 1.3000),
        "max": (89.4201, 0.4111, 74.5314, 14.0366, 2.4157)}
# Copied byte for byte from the harness (docs/results/swe-v4-gpt62-astra-2026-11/gpt62astra-vs-gpt6astra.png, 2400x1350), shown at 1600x900.
CARD_PNG = ("swe-v4-gpt62-astra-v333.png", "e56a27c4e71a8e653c85f335c09b4d6bbbe14581656e2eda657ec008601e8593", 2400, 1350)
# The comparator on the page and the card: GPT-6 Astra's published board rows; GPT-6.2 Sol shares the Codex build.
PREVIOUS = ("gpt6astra", "GPT-6 Astra")
SIBLING = ("gpt62sol", "GPT-6.2 Sol")
TOUCHED = ("benchmarks/swe-v4-gpt62-astra-v333.html", "models/gpt-6-2-astra.html", "models/gpt-6-astra.html", "benchmarks.html", "index.html",
           "feed.xml", "llms.txt", "leaderboard.html", "README.md", "assets/data/README.md", "assets/data/swe-v4-gpt62-astra-v333/README.md",
           "assets/data/swe-v4-gpt62-astra-v333/REPRODUCING.md", "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v333.py")


def code_quality(reviewed, intent):
    return reviewed if intent is None else (0.24 * reviewed + 0.09 * intent) / 0.33


def combined(r, cq, weight=0.33):
    other = (0.5 - weight) / 2
    return 100 * (.5 * r["functional"] + other * r["automated_quality"] + other * r["security"] + weight * cq / 100)


def priced(u):
    return ((u["input_tokens"] - u["cached_input_tokens"]) * RATES["input"] + u["cached_input_tokens"] * RATES["cached_input"]
            + u["output_tokens"] * RATES["output"]) / 1e6


def board_rows():
    with (ROOT / "assets/data/swe-v4-board.csv").open(newline="") as source:
        return {(r["model"], r["effort"]): r for r in csv.DictReader(source)}


class GPT62AstraBundleTests(unittest.TestCase):
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
        self.assertEqual(len({(r["effort"], r["task"]) for r in self.rows}), RUNS)
        self.assertEqual((self.runs["published"], self.runs["unpublished"], self.runs["timeouts"]), (RUNS, 0, 0))
        for r in self.rows:
            self.assertTrue(r["finished"] and r["duration_s"] < 10800)
            self.assertEqual(r["functional"], 1)
            self.assertEqual(r["hidden_behaviours_fixed"], r["hidden_behaviours"])
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            self.assertEqual((r["solver_cli_version"], r["requested_model"], r["model_identity"]), ("codex-cli 0.166.0", "gpt-6.2-astra", "requested-only"))
            self.assertEqual(r["requested_effort"], "xhigh" if r["effort"] == "extra-high" else r["effort"])
            self.assertEqual(r["source_tag"], "bench/2026-11-22-gpt62-astra-frontier-v4")
            self.assertEqual((r["judged"], r["judged_under"], r["scored_panels"]), ("published", "code-quality-maintenance-v3.33", list(PANELS)))
            self.assertNotIn("one_panel_note", r)
            self.assertEqual(r["codex_notices"], [])
            u = r["token_usage"]
            self.assertEqual(u["uncached_input_tokens"], u["input_tokens"] - u["cached_input_tokens"])
            self.assertEqual(r["raw_tokens"], u["input_tokens"] + u["output_tokens"])
            self.assertAlmostEqual(r["estimated_usd"], priced(u), delta=1e-5)
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
            self.assertFalse(r["intent_recovery_redistributed"])
            cq = code_quality(reviewed, intent)
            self.assertAlmostEqual(r["code_quality"], cq, places=9)
            self.assertAlmostEqual(r["combined_33"], combined(r, cq), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], combined(r, cq, 0.20), places=9)
            for p in PANELS:
                alone = code_quality(r["panels"][p]["reviewed_score"], r["panels"][p]["intent_recovery"])
                self.assertAlmostEqual(r["combined_single_judge"][p], combined(r, alone), places=9)
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e) for e in EFFORTS], [23] * 5)
        # The security scan's low-severity findings grow with effort; none is medium or high severity.
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e and r["security"] < 1) for e in EFFORTS], [2, 6, 13, 18, 21])
        self.assertEqual({r["security"] for r in self.rows}, {1.0, 0.9, 0.85})
        longest = max(self.rows, key=lambda r: r["duration_s"])
        self.assertEqual((longest["effort"], longest["task"], round(longest["duration_s"] / 60, 1)), ("max", "legacy-quotacore-binary-parity", 18.4))
        self.assertTrue(min(r["started_at"] for r in self.rows).startswith("2026-11-23T02:08"))
        self.assertTrue(max(r["finished_at"] for r in self.rows).startswith("2026-11-23T12:38"))

    def test_runs_csv_and_scores_csv(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), RUNS)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], delta=5.1e-5)
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], delta=5.1e-7)
            self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])
            self.assertEqual(c["scored_panels"], "muse+grok")
            self.assertNotEqual(c["combined_grok_only"], "")
        with (ROOT / "assets/data/swe-v4-gpt62-astra-v333-scores.csv").open(newline="") as source:
            scores = {r["effort"]: r for r in csv.DictReader(source)}
        self.assertEqual(list(scores), list(EFFORTS))
        for e, g in self.groups.items():
            self.assertAlmostEqual(float(scores[e]["combined_33"]), g["combined_33"]["mean"], places=4)
            self.assertEqual(int(scores[e]["passed_of_23"]), g["passed_all_runs"])
            self.assertAlmostEqual(float(scores[e]["mean_usd"]), g["usd"]["mean"], places=6)

    def test_groups_match_runs_and_card(self):
        self.assertEqual(list(self.groups), list(EFFORTS))
        for e in EFFORTS:
            g = self.groups[e]
            rs = [r for r in self.rows if r["effort"] == e]
            self.assertEqual((g["runs"], g["n"], g["timeouts"], g["unpublished_runs"], g["one_panel_runs"]), (23, 23, 0, 0, 0))
            self.assertEqual(g["passed_all_runs"], 23)
            self.assertEqual((g["by_panel"]["muse"]["n"], g["by_panel"]["grok"]["n"]), (23, 23))
            for field in ("combined_33", "code_quality"):
                values = [r[field] for r in rs]
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(values), places=9)
                self.assertAlmostEqual(g[field]["se"], statistics.stdev(values) / len(values) ** .5, places=9)
            self.assertAlmostEqual(g["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=9)
            self.assertAlmostEqual(g["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs), places=9)
            self.assertEqual(g["codex_notice_runs"], 0)
            values = (g["combined_33"]["mean"], g["combined_33"]["se"], g["code_quality"]["mean"], g["minutes"]["mean"], g["usd"]["mean"])
            for value, expected in zip(values, CARD[e]):
                self.assertAlmostEqual(value, expected, delta=5e-5, msg=e)
        self.assertEqual([round(self.groups[e]["combined_33"]["mean"], 2) for e in EFFORTS], [87.68, 88.89, 89.26, 89.05, 89.42])
        self.assertEqual([round(self.groups[e]["code_quality"]["mean"], 2) for e in EFFORTS], [67.27, 70.65, 72.88, 72.98, 74.53])
        self.assertEqual([self.groups[e]["hidden_behaviours_fixed"] for e in EFFORTS], [231] * 5)
        self.assertEqual([f'{self.groups[e]["raw_tokens"]["mean"] / 1e6:.2f}' for e in EFFORTS], ["0.36", "0.51", "0.78", "0.97", "1.31"])
        self.assertEqual([round(self.groups[e]["security"]["mean"], 2) for e in EFFORTS], [99.13, 97.39, 94.35, 91.96, 90.87])
        self.assertEqual([round(self.groups[e]["automated_quality"]["mean"], 2) for e in EFFORTS], [83.01, 85.81, 84.60, 84.16, 83.54])
        gaps = [self.groups[e]["by_panel"]["grok"]["mean"] - self.groups[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
        self.assertTrue(all(x > 0 for x in gaps))
        self.assertEqual((round(gaps[0], 1), round(min(gaps[1:]), 1), round(max(gaps[1:]), 1)), (4.5, 0.2, 2.1))
        t = self.econ["totals"]["gpt62astra"]
        self.assertEqual((t["runs"], round(t["usd"], 2), t["raw_tokens"], round(t["solver_hours"], 2)), (RUNS, 135.69, 90489772, 10.50))
        self.assertEqual(self.econ["rates_per_million"]["gpt62astra"], RATES)
        self.assertEqual(self.econ["pricing_verified"], "2026-11-22")

    def test_judges_and_protocol(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertEqual(record["taken_under"], "code-quality-maintenance-v3.33")
            self.assertTrue(record["passed"])
            self.assertEqual(record["call_count"], 80)
            self.assertEqual((record["allowance_used"], record["failing_gates"]), (False, []))
            self.assertEqual(len(record["gates"]), 20)
            self.assertTrue(all(g["passed"] for g in record["gates"].values()))
        p = self.protocols
        self.assertEqual(set(p["scored_panel"]), set(PANELS))
        self.assertEqual((p["scored_panel"]["muse"]["model"], p["scored_panel"]["grok"]["model"]), ("muse-spark-1.3", "cursor-grok-4.6-medium"))
        v324 = json.loads((ROOT / "assets/data/swe-v4-haiku55-v324/judge-protocols.json").read_text())
        self.assertEqual(p["scored_panel"], v324["scored_panel"])
        for key in ("rubric", "system", "probe_instruction", "match_instruction", "schemas", "weights", "seed", "repeats", "gate_allowance"):
            self.assertEqual(p[key], v324[key], key)
        self.assertEqual(p["counted_calls"], {q: {"calibration": 80, "primary": 115, "repeat": 5, "pairwise": 10, "probe": 115, "match": 115}
                                              for q in PANELS})
        self.assertEqual(p["second_attempts"], {"muse": 9, "grok": 7})
        self.assertEqual(p["second_attempt_causes"], {"muse": {"Unsupported evidence excerpt": 7, "JSON syntax error": 2},
                                                      "grok": {"Unsupported evidence excerpt": 6, "JSON syntax error": 1}})
        self.assertEqual(p["display_name"]["accepted_renames_recorded"], 440)
        self.assertEqual((p["unpublished"], p["operator_recoveries"], p["one_panel"], p["quota_stops"]), ([], [], [], None))
        self.assertEqual(p["round"], {"tag": "bench/2026-11-23-gpt62-astra-judging-v333", "commit": "dc7f85611daaef1e7649556e3323fc24d6cc62ff"})
        self.assertEqual(p["judge_pins"]["cursor_version"]["version"], "2026.10.01-e373342")
        window = p["judging_window_utc"]
        self.assertEqual(window["chain"], "2026-11-23T15:25Z to 2026-11-24T03:13Z, from the operator's chain log")
        self.assertTrue(window["first_muse_call_completed"].startswith("2026-11-23T15:26"))
        self.assertTrue(window["last_muse_call_completed"].startswith("2026-11-23T20:43"))
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), chr(0), *ENTITIES, "/Users/", "/home/", "/private/", "/var/folders/", "SWE v4",
                         "no model on the board", "no model on this board"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("ultra", text.lower(), name)
        provenance = json.loads((DATA / "provenance.json").read_text())["source_artifacts_sha256"]
        self.assertFalse(any("operator-invalid" in k for k in provenance))


class GPT62AstraPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}

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
        self.assertIn("intent/post?text=GPT-6.2%20Astra%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertIn("Morgan Linton", self.text)
        self.assertNotIn(".pdf", self.page_html)
        self.assertEqual(self.page_html.count("https://github.com/morganlinton/vulcanbench-gpt62-astra-traces"), 2)  # resource tile and withheld note
        for target in ("https://github.com/morganlinton/VulcanBench", "https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md",
                       "https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/cli_agents.py",
                       "https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md"):
            self.assertIn(f'href="{target}"', self.page_html)

    def test_tables_match_the_bundle(self):
        g = self.groups
        self.assertEqual(set(self.page.rows), {("gpt62astra", e) for e in EFFORTS})
        for e in EFFORTS:
            row = self.page.rows["gpt62astra", e]
            self.assertEqual(row[1:5], [label(e), f'{g[e]["combined_33"]["mean"]:.2f}', f'{g[e]["combined_33"]["se"]:.2f}',
                                        f'{g[e]["combined_20_profile"]["mean"]:.2f}'])
            self.assertEqual(row[5:9], [f'{g[e]["code_quality"]["mean"]:.2f}', f'{g[e]["readability"]["mean"]:.1f}',
                                        f'{g[e]["maintainability"]["mean"]:.1f}', f'{g[e]["intent_recovery"]["mean"]:.1f}'])
            self.assertEqual(row[-3:], ["23/23", "23/23", f'{g[e]["minutes"]["mean"]:.1f}'])
            cells = (f'<td>23</td><td>${g[e]["usd"]["mean"]:.2f}</td><td>${g[e]["usd_total"]:.2f}</td><td>{g[e]["raw_tokens"]["mean"] / 1e6:.2f}M</td>'
                     f'<td>{g[e]["output_tokens"]["mean"] / 1e3:.1f}K</td><td>{g[e]["reasoning_output_tokens_median"] / 1e3:.1f}K</td>'
                     f'<td>{100 * g[e]["cached_input_share"]["mean"]:.1f}%</td><td>{g[e]["minutes"]["mean"]:.1f}</td><td>{g[e]["minutes_median"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}', self.page_html, e)
        total = sum(g[e]["usd_total"] for e in EFFORTS)
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>115</td><td>${total / RUNS:.2f}</td><td>${total:.2f}</td>', self.page_html)
        self.assertIn('<th scope="row">Combined score</th>' + "".join(f'<td>{g[e]["combined_33"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Judged runs</th>' + "<td>23</td>" * 5, self.page_html)
        self.assertIn('<th scope="row">Tasks passed</th>' + "<td>23/23</td>" * 5, self.page_html)
        self.assertIn('<th scope="row">Hidden behaviours fixed</th>' + "<td>231/231</td>" * 5, self.page_html)
        self.assertIn('<th scope="row">API-equivalent $ per task</th>' + "".join(f'<td>${g[e]["usd"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        for panel, name in (("muse", "Muse Spark 1.3"), ("grok", "Grok 4.6")):
            self.assertIn(f'<th scope="row">Rated by {name}</th>' + "".join(f'<td>{g[e]["by_panel"][panel]["mean"]:.1f}</td>' for e in EFFORTS),
                          self.page_html)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f'<td>{g[e]["code_quality"]["se"]:.2f}</td>' for e in EFFORTS),
                      self.page_html)
        judges = self.section("judges", "run-notes")
        for e in EFFORTS:
            for p in PANELS:
                self.assertIn(f'{g[e]["combined_single_judge"][p]["mean"]:.2f}', judges, (e, p))
        notes = plain(self.page_html[self.page_html.index('id="results"'):self.page_html.index('id="comparison"')])
        for e in EFFORTS:
            for factor in ("functional", "automated_quality", "security"):
                self.assertIn(f'{g[e][factor]["mean"]:.2f}', notes, (e, factor))

    def test_comparison_matches_the_board_and_bundles(self):
        board = board_rows()
        for key, name in (("gpt62astra", "GPT-6.2 Astra"), PREVIOUS):
            for e in EFFORTS:
                b = board[name, e]
                judged = b["n"] + ("*" if int(b["n"]) < 23 else "")
                cells = (f'<td>{label(e)}</td><td>{float(b["combined_33"]):.2f}</td><td>{float(b["combined_33_se"]):.2f}</td><td>{judged}</td>'
                         f'<td>{b["passed"]}/23</td><td>{float(b["mean_minutes"]):.1f}</td>'
                         f'<td>{float(b["mean_raw_tokens"]) / 1e6:.2f}M</td><td>${float(b["mean_usd"]):.2f}</td><td>{float(b["code_quality"]):.2f}</td>')
                row = self.page_html[self.page_html.index(f'data-compare="{key}-{e}"'):]
                self.assertIn(cells, row[:row.index("</tr>")], (key, e))
        self.assertEqual(board["GPT-6 Astra", "low"]["passed"], "22")
        new = {e: board["GPT-6.2 Astra", e] for e in EFFORTS}
        old = {e: board["GPT-6 Astra", e] for e in EFFORTS}
        comparison = self.section("comparison", "gpt62-sol")
        diffs = [float(new[e]["combined_33"]) - float(old[e]["combined_33"]) for e in EFFORTS]
        self.assertEqual([f"{abs(x):.2f}" for x in diffs], ["0.25", "1.16", "1.10", "0.11", "0.12"])
        for x in diffs:
            self.assertIn(f"{abs(x):.2f}", comparison)
        self.assertTrue(all(float(new[e]["mean_usd"]) < float(old[e]["mean_usd"]) for e in EFFORTS))
        self.assertTrue(all(float(new[e]["code_quality"]) < float(old[e]["code_quality"]) for e in EFFORTS))
        for e in EFFORTS:
            self.assertIn(f'${float(new[e]["mean_usd"]):.2f} against ${float(old[e]["mean_usd"]):.2f}', comparison, e)
            self.assertIn(f'{float(old[e]["code_quality"]) - float(new[e]["code_quality"]):.2f}', comparison, e)
        for needle in ("0.153.4", "v3.4", "passed 22 at Low", "paddockcore", "eleven weeks apart", "long-context upper bound", "same rubric"):
            self.assertIn(needle, comparison, needle)
        v34 = {g["effort"]: g for g in json.loads((ROOT / "assets/data/swe-v4-astra-fable51-v34/groups.json").read_text()) if g["model"] == "astra"}
        factors = self.page_html[self.page_html.index('id="comparison"'):self.page_html.index('id="gpt62-sol"')]
        for metric, key, cell in (("lint", "gpt62astra", lambda e: f'{self.groups[e]["automated_quality"]["mean"]:.2f}'),
                                  ("lint", "gpt6astra", lambda e: f'{v34[e]["automated_quality"]["mean"]:.2f}'),
                                  ("security", "gpt62astra", lambda e: f'{self.groups[e]["security"]["mean"]:.2f}'),
                                  ("security", "gpt6astra", lambda e: f'{v34[e]["security"]["mean"]:.2f}')):
            row = factors[factors.index(f'data-factor="{metric}-{key}"'):]
            self.assertIn("".join(f"<td>{cell(e)}</td>" for e in EFFORTS), row[:row.index("</tr>")], (metric, key))
        sol = {e: board[SIBLING[1], e] for e in EFFORTS}
        family = self.page_html[self.page_html.index('id="gpt62-sol"'):self.page_html.index('id="cost"')]
        for metric, column, fmt in (("combined", "combined_33", "{:.2f}"), ("cq", "code_quality", "{:.2f}"), ("usd", "mean_usd", "${:.2f}"),
                                    ("minutes", "mean_minutes", "{:.1f}")):
            for key, source in (("gpt62astra", new), (SIBLING[0], sol)):
                row = family[family.index(f'data-family="{metric}-{key}"'):]
                self.assertIn("".join(f"<td>{fmt.format(float(source[e][column]))}</td>" for e in EFFORTS), row[:row.index("</tr>")], (metric, key))
        ratios = [float(new[e]["mean_usd"]) / float(sol[e]["mean_usd"]) for e in EFFORTS]
        self.assertEqual((f"{min(ratios):.1f}", f"{max(ratios):.1f}"), ("2.0", "4.4"))
        for needle in ("0.76 points ahead at Low", "0.68 ahead at Max", "3.47 points at Max", "2.0 to 4.4 times"):
            self.assertIn(needle, plain(family), needle)

    def test_required_disclosures(self):
        results = plain(self.page_html[self.page_html.index('id="results"'):self.page_html.index('id="comparison"')])
        for needle in ("Every run is scored by both judges", "Sixteen calls", "100.00 at every level", "bandit", "no medium or high severity",
                       "2 runs at Low, 6 at Medium, 13 at High, 18 at Extra-high and 21 at Max"):
            self.assertIn(needle, results, needle)
        board = self.section("board", "code-quality")
        for needle in ("ranks 23rd of the board’s 100", "Low 50th, Medium 32nd, High 25th, Extra-high 29th, Max 23rd", "89.4202 against 89.4201",
                       "Of the 26 priced columns scoring 89 or more", "fourth cheapest", "critical effort suggestion picks Medium",
                       "routine and rough suggestions pick Low", "not calibrated against each other", "‡‡‡ footnote"):
            self.assertIn(needle, board, needle)
        cost = self.section("cost", "board")
        for needle in ("$8.00 input, $0.40 cached input and $40.00 output", "2026-11-22", "not subscription charges", "$135.69", "21.2K",
                       "272K", "no long-context premium is modelled"):
            self.assertIn(needle, cost, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("Muse Spark 1.3", "Grok 4.6", "2026.10.01-e373342", "Neither lab is OpenAI", "all 20 gates without the one-gate allowance",
                       "440 counted calls", "all 440 of them selected", "second attempt on 9 calls", "Grok on 7", "seven unsupported excerpts",
                       "six unsupported excerpts", "No call stopped on a usage limit", "Grok 4.6 Medium", "November 23", "15:25 UTC", "03:13 UTC"):
            self.assertIn(needle, judges, needle)
        notes = self.section("run-notes", "reproduce")
        for needle in ("gpt-6.2-astra", "requested", "0.166.0", "prolite", "workspace-write", "xhigh", "bench/2026-11-22-gpt62-astra-frontier-v4",
                       "No timeouts", "18.4 minutes", "02:08 to 12:38 UTC"):
            self.assertIn(needle, notes, needle)
        self.assertIn("never compared with Routine v1 Code quality", self.text)

    def test_card_pinned(self):
        name, sha, width, height = CARD_PNG
        data = (ROOT / "assets/cards" / name).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), sha)
        self.assertEqual((int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")), (width, height))
        self.assertIn(f'src="/assets/cards/{name}" width="1600" height="900"', self.page_html)  # 16:9, shown at the feature-card size
        self.assertIn(f'<meta property="og:image" content="https://vulcanbench.com/assets/cards/{name}">', self.page_html)
        self.assertIn(f'<meta property="og:image:width" content="{width}">', self.page_html)
        self.assertIn(f'<meta property="og:image:height" content="{height}">', self.page_html)
        provenance = json.loads((DATA / "provenance.json").read_text())["source_artifacts_sha256"]
        self.assertEqual(provenance["gpt62astra-vs-gpt6astra.png"], sha)


class GPT62AstraSiteTests(unittest.TestCase):
    def test_model_page_links_report(self):
        markup = MODEL_PAGE.read_text()
        self.assertIn('href="../benchmarks/swe-v4-gpt62-astra-v333.html"', markup)
        self.assertIn(f'<link rel="canonical" href="{MODEL_URL}">', markup)
        for value in ("87.68", "88.89", "89.26", "89.05", "89.42", "Every task passed at every level", "23rd of 100", "$135.69"):
            self.assertIn(value, markup, value)
        self.assertIn('href="gpt-6-astra.html"', markup)
        self.assertIn('href="gpt-6-2-astra.html"', (ROOT / "models/gpt-6-astra.html").read_text())

    def test_site_references(self):
        for name in ("benchmarks.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "index.html", "models/gpt-6-2-astra.html"):
            self.assertIn("swe-v4-gpt62-astra-v333.html", (ROOT / name).read_text(), name)
        self.assertIn('href="models/gpt-6-2-astra.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn("swe-v4-gpt62-astra-v333/", (ROOT / "assets/data/README.md").read_text())
        sitemap = (ROOT / "sitemap.xml").read_text()
        for page_url in (URL, MODEL_URL):
            self.assertIn(f"<loc>{page_url}</loc>", sitemap)
        item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in i)
        self.assertIn("VulcanBench Frontier v4", item)
        self.assertIn("24 Nov 2026", item)
        self.assertNotIn(chr(0x2014), item)
        leaderboard = (ROOT / "leaderboard.html").read_text()
        self.assertIn('<a href="benchmarks/swe-v4-gpt62-astra-v333.html">GPT-6.2 Astra</a>', leaderboard)
        self.assertEqual(len(re.findall(r'"key":"gpt62astra","effort":"[a-z-]+"', leaderboard)), 5)
        self.assertIn("21 models &middot; 100 model&times;effort columns &middot; 2267 runs", leaderboard)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-gpt62-astra-v333.html"), index.index("swe-v4-gemini4-neon-v332.html"))
        home = (ROOT / "index.html").read_text()
        self.assertLess(home.index("swe-v4-gpt62-astra-v333.html"), home.index("swe-v4-gemini4-neon-v332.html"))


if __name__ == "__main__":
    unittest.main()
