"""Stdlib checks for the Gemini 4 Neon bundle (v3.32), its report page, its card, its model page and the site links to them."""

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
DATA = ROOT / "assets/data/swe-v4-gemini4-neon-v332"
PAGE = ROOT / "benchmarks/swe-v4-gemini4-neon-v332.html"
MODEL_PAGE = ROOT / "models/gemini-4-neon.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-gemini4-neon-v332.html"
MODEL_URL = "https://vulcanbench.com/models/gemini-4-neon.html"
EFFORTS = ("low", "medium", "high", "extra-high")  # Antigravity offers no Max level for Neon
PANELS = ("muse", "grok")
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
ENTITIES = ("&" + "mdash;", "&" + "ndash;")  # spelled in parts so this file carries no dash entity
RUNS = 92
# Gemini 4 Neon list rates per million tokens, checked 2026-11-19.
RATES = {"input": 3.00, "cached_input": 0.15, "output": 15.00}
TOOLS = ("read_file", "write_file", "edit_file", "run_command")
# The harness card's per-level table (docs/results/swe-v4-gemini4-neon-2026-11/gemini4neon-vs-frontier-efforts.csv), to four places.
CARD = {"low": (84.3209, 1.0948, 66.1494, 5.1269, 0.7322), "medium": (87.4833, 0.4919, 67.8718, 5.8511, 0.9181),
        "high": (87.8685, 0.4601, 69.0667, 6.4493, 1.1913), "extra-high": (87.7024, 0.5109, 68.6887, 10.1158, 1.8036)}
# Copied byte for byte from the harness (docs/results/swe-v4-gemini4-neon-2026-11/gemini4neon-vs-frontier.png, 2400x1350), shown at 1600x900.
CARD_PNG = ("swe-v4-gemini4-neon-v332.png", "bdf9d8dd129518b6297252e5a854a8c47e01bc7e342dd8e9abea14cd721bfad9", 2400, 1350)
# Comparators on the page and the card: published board rows.
COMPARATORS = {"opus55": "Opus 5.5", "gpt62sol": "GPT-6.2 Sol"}
UNPUBLISHED = {("low", "legacy-codeccore-binary-parity"): "submission-048", ("extra-high", "legacy-codeccore-binary-parity"): "submission-069"}
LOW_PARTIAL = ("cellarcore", "hedgecore", "lodgecore", "matchcore", "quotacore", "tallycore")
TOUCHED = ("benchmarks/swe-v4-gemini4-neon-v332.html", "models/gemini-4-neon.html", "benchmarks.html", "index.html", "feed.xml", "llms.txt",
           "leaderboard.html", "README.md", "assets/data/README.md", "assets/data/swe-v4-gemini4-neon-v332/README.md",
           "assets/data/swe-v4-gemini4-neon-v332/REPRODUCING.md", "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v332.py")


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


class Gemini4NeonBundleTests(unittest.TestCase):
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
        self.assertEqual((self.runs["published"], self.runs["unpublished"], self.runs["timeouts"]), (90, 2, 0))
        for r in self.rows:
            key = (r["effort"], r["task"])
            self.assertTrue(r["finished"] and r["duration_s"] < 10800)
            self.assertEqual(r["functional"] == 1, r["hidden_behaviours_fixed"] == r["hidden_behaviours"])
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            self.assertEqual((r["solver_cli_version"], r["requested_model"], r["reported_model"], r["model_identity"]),
                             ("1.5.12", "gemini-4-neon", "gemini-4-neon", "harness-recorded"))
            self.assertEqual(r["requested_effort"], "xhigh" if r["effort"] == "extra-high" else r["effort"])
            self.assertEqual(r["source_tag"], "bench/2026-11-20-gemini4-neon-frontier-v4")
            self.assertEqual(set(r["tool_calls_by_tool"]), set(TOOLS))
            self.assertEqual(sum(r["tool_calls_by_tool"].values()), r["tool_calls"])
            u = r["token_usage"]
            self.assertEqual(u["uncached_input_tokens"], u["input_tokens"] - u["cached_input_tokens"])
            self.assertEqual(r["raw_tokens"], u["input_tokens"] + u["output_tokens"])
            self.assertLessEqual(u["reasoning_output_tokens"], u["output_tokens"])  # thinking is part of output
            self.assertAlmostEqual(r["estimated_usd"], priced(u), delta=1e-5)
            if key in UNPUBLISHED:
                self.assertTrue(r["judged"].startswith("unpublished: Grok 4.6's intent probe returned malformed JSON"))
                self.assertEqual(r["functional"], 1)
                for field in ("reviewed_score", "intent_recovery", "code_quality", "combined_33", "combined_20_profile", "panels",
                              "intent_recovery_redistributed"):
                    self.assertIsNone(r[field], field)
                self.assertEqual(r["combined_single_judge"], {p: None for p in PANELS})
                continue
            self.assertEqual((r["judged"], r["judged_under"]), ("published", "code-quality-maintenance-v3.32"))
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            intents = [r["panels"][p]["intent_recovery"] for p in PANELS if r["panels"][p]["intent_recovery"] is not None]
            intent = statistics.mean(intents) if intents else None
            self.assertEqual(r["intent_recovery_redistributed"], intent is None)
            cq = code_quality(reviewed, intent)
            self.assertAlmostEqual(r["code_quality"], cq, places=9)
            self.assertAlmostEqual(r["combined_33"], combined(r, cq), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], combined(r, cq, 0.20), places=9)
            for p in PANELS:
                alone = code_quality(r["panels"][p]["reviewed_score"], r["panels"][p]["intent_recovery"])
                self.assertAlmostEqual(r["combined_single_judge"][p], combined(r, alone), places=9)
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e) for e in EFFORTS], [23] * 4)
        self.assertFalse(any(r["intent_recovery_redistributed"] for r in self.rows))
        partial = sorted(r["task"].removeprefix("legacy-").split("-")[0] for r in self.rows if r["functional"] < 1)
        self.assertEqual(partial, list(LOW_PARTIAL))
        self.assertTrue(all(r["effort"] == "low" for r in self.rows if r["functional"] < 1))
        self.assertEqual(sum(r["tool_calls"] for r in self.rows), 2455)

    def test_runs_csv_and_scores_csv(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), RUNS)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            unpublished = (r["effort"], r["task"]) in UNPUBLISHED
            self.assertEqual(c["judged"], "unpublished" if unpublished else "published")
            self.assertEqual(c["combined_33"] == "", unpublished)
            if not unpublished:
                self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], delta=5.1e-5)
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], delta=5.1e-7)
            self.assertEqual((int(c["raw_tokens"]), int(c["tool_calls"])), (r["raw_tokens"], r["tool_calls"]))
        with (ROOT / "assets/data/swe-v4-gemini4-neon-v332-scores.csv").open(newline="") as source:
            scores = {r["effort"]: r for r in csv.DictReader(source)}
        self.assertEqual(list(scores), list(EFFORTS))
        for e, g in self.groups.items():
            self.assertAlmostEqual(float(scores[e]["combined_33"]), g["combined_33"]["mean"], places=4)
            self.assertEqual((int(scores[e]["n"]), int(scores[e]["passed_of_23"])), (g["n"], g["passed_all_runs"]))
            self.assertAlmostEqual(float(scores[e]["mean_usd"]), g["usd"]["mean"], places=6)

    def test_groups_match_runs_and_card(self):
        self.assertEqual(list(self.groups), list(EFFORTS))
        for e in EFFORTS:
            g = self.groups[e]
            rs = [r for r in self.rows if r["effort"] == e]
            judged = [r for r in rs if r["judged"] == "published"]
            unpublished = 1 if e in ("low", "extra-high") else 0
            self.assertEqual((g["runs"], g["n"], g["timeouts"], g["unpublished_runs"], g["one_panel_runs"]), (23, 23 - unpublished, 0, unpublished, 0))
            self.assertEqual(g["passed_all_runs"], 17 if e == "low" else 23)
            for field in ("combined_33", "code_quality"):
                values = [r[field] for r in judged]
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(values), places=9)
                self.assertAlmostEqual(g[field]["se"], statistics.stdev(values) / len(values) ** .5, places=9)
            self.assertAlmostEqual(g["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=9)
            self.assertAlmostEqual(g["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs), places=9)
            values = (g["combined_33"]["mean"], g["combined_33"]["se"], g["code_quality"]["mean"], g["minutes"]["mean"], g["usd"]["mean"])
            for value, expected in zip(values, CARD[e]):
                self.assertAlmostEqual(value, expected, delta=5e-5, msg=e)
        self.assertEqual([round(self.groups[e]["combined_33"]["mean"], 2) for e in EFFORTS], [84.32, 87.48, 87.87, 87.70])
        self.assertEqual([self.groups[e]["hidden_behaviours_fixed"] for e in EFFORTS], [220, 231, 231, 231])
        self.assertEqual([f'{self.groups[e]["raw_tokens"]["mean"] / 1e6:.2f}' for e in EFFORTS], ["0.91", "1.10", "1.44", "2.45"])
        self.assertEqual([self.groups[e]["quota_refused_attempts"] for e in EFFORTS], [0, 10, 8, 22])
        gaps = [self.groups[e]["by_panel"]["grok"]["mean"] - self.groups[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
        self.assertEqual((round(min(gaps), 1), round(max(gaps), 1)), (3.1, 6.8))
        t = self.econ["totals"]["neon"]
        self.assertEqual((t["runs"], round(t["usd"], 2), t["raw_tokens"]), (RUNS, 106.84, 135653416))
        self.assertEqual(self.econ["rates_per_million"]["neon"], RATES)

    def test_judges_and_protocol(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertEqual(record["taken_under"], "code-quality-maintenance-v3.32")
            self.assertTrue(record["passed"])
            self.assertEqual(record["call_count"], 80)
        self.assertEqual((self.calibration["muse"]["allowance_used"], self.calibration["muse"]["failing_gates"]), (True, ["g11_repeatability"]))
        self.assertAlmostEqual(self.calibration["muse"]["gates"]["g11_repeatability"]["shortfall"], 0.02, places=9)
        self.assertEqual((self.calibration["grok"]["allowance_used"], self.calibration["grok"]["failing_gates"]), (False, []))
        p = self.protocols
        self.assertEqual((p["scored_panel"]["muse"]["model"], p["scored_panel"]["grok"]["model"]), ("muse-spark-1.3", "cursor-grok-4.6-medium"))
        v324 = json.loads((ROOT / "assets/data/swe-v4-haiku55-v324/judge-protocols.json").read_text())
        self.assertEqual(p["scored_panel"], v324["scored_panel"])
        for key in ("rubric", "system", "probe_instruction", "match_instruction", "schemas", "weights", "seed", "repeats", "gate_allowance"):
            self.assertEqual(p[key], v324[key], key)
        calls = {q: {"calibration": 80, "primary": 92, "repeat": 4, "pairwise": 8, "probe": 92, "match": 92} for q in PANELS}
        calls["grok"]["match"] = 90
        self.assertEqual(p["counted_calls"], calls)
        self.assertEqual(p["second_attempts"], {"muse": 2, "grok": 7})
        self.assertEqual(p["display_name"]["accepted_renames_recorded"], 364)
        self.assertEqual((p["one_panel"], p["operator_recoveries"], p["quota_stops"]), ([], [], []))
        self.assertEqual({(u["effort"], u["task"]): u["submission"] for u in p["unpublished"]}, UNPUBLISHED)
        for u in p["unpublished"]:
            self.assertEqual((u["panel"], u["stage"], u["functional"]), ("grok", "probe", 1))
            self.assertEqual(set(u["malformed_attempts"]), {"1", "2"})
            self.assertIn("invalidate_unrecoverable_probe", u["rule"])
        window = p["judging_window_utc"]
        self.assertTrue(window["first_muse_call_completed"].startswith("2026-11-21T14:58"))
        self.assertTrue(window["last_muse_call_completed"].startswith("2026-11-21T18:24"))
        self.assertIn("bench/2026-11-21-gemini4-neon-judging-v332-recovery", window["recovery"])
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), chr(0), *ENTITIES, "/Users/", "/home/", "/private/", "/var/folders/", "SWE v4",
                         "no model on the board", "no model on this board"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("ultra", text.lower(), name)


class Gemini4NeonPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.rows = json.loads((DATA / "runs.json").read_text())["rows"]

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
        self.assertIn("intent/post?text=Gemini%204%20Neon%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertEqual(self.page_html.count('<script src="/share.js?v=2" defer></script>'), 1)
        self.assertIn("Morgan Linton", self.text)
        self.assertNotIn(".pdf", self.page_html)
        self.assertNotIn("analysis.html", self.page_html)
        for target in ("https://github.com/morganlinton/VulcanBench", "https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md",
                       "https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/antigravity_cli.py",
                       "https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md"):
            self.assertIn(f'href="{target}"', self.page_html)

    def test_tables_match_the_bundle(self):
        g = self.groups
        self.assertEqual(set(self.page.rows), {("neon", e) for e in EFFORTS})
        for e in EFFORTS:
            row = self.page.rows["neon", e]
            self.assertEqual(row[1:5], [label(e), f'{g[e]["combined_33"]["mean"]:.2f}', f'{g[e]["combined_33"]["se"]:.2f}',
                                        f'{g[e]["combined_20_profile"]["mean"]:.2f}'])
            self.assertEqual(row[5:9], [f'{g[e]["code_quality"]["mean"]:.2f}', f'{g[e]["readability"]["mean"]:.1f}',
                                        f'{g[e]["maintainability"]["mean"]:.1f}', f'{g[e]["intent_recovery"]["mean"]:.1f}'])
            self.assertEqual(row[-3:], [f'{g[e]["n"]}/23', f'{g[e]["passed_all_runs"]}/23', f'{g[e]["minutes"]["mean"]:.1f}'])
            cells = (f'<td>23</td><td>${g[e]["usd"]["mean"]:.2f}</td><td>${g[e]["usd_total"]:.2f}</td><td>{g[e]["raw_tokens"]["mean"] / 1e6:.2f}M</td>'
                     f'<td>{g[e]["output_tokens"]["mean"] / 1e3:.1f}K</td><td>{g[e]["reasoning_output_tokens_median"] / 1e3:.1f}K</td>'
                     f'<td>{100 * g[e]["cached_input_share"]["mean"]:.1f}%</td><td>{g[e]["minutes"]["mean"]:.1f}</td><td>{g[e]["minutes_median"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}', self.page_html, e)
        total = sum(g[e]["usd_total"] for e in EFFORTS)
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>92</td><td>${total / RUNS:.2f}</td><td>${total:.2f}</td>', self.page_html)
        self.assertIn('<th scope="row">Combined score</th>' + "".join(f'<td>{g[e]["combined_33"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Judged runs</th>' + "".join(f'<td>{g[e]["n"]}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Tasks passed</th>' + "".join(f'<td>{g[e]["passed_all_runs"]}/23</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Hidden behaviours fixed</th>' + "".join(f'<td>{g[e]["hidden_behaviours_fixed"]}/231</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">API-equivalent $ per task</th>' + "".join(f'<td>${g[e]["usd"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        for p, name in (("muse", "Muse Spark 1.3"), ("grok", "Grok 4.6")):
            self.assertIn(f'<th scope="row">Rated by {name}</th>' + "".join(f'<td>{g[e]["by_panel"][p]["mean"]:.1f}</td>' for e in EFFORTS),
                          self.page_html)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f'<td>{g[e]["code_quality"]["se"]:.2f}</td>' for e in EFFORTS),
                      self.page_html)
        judges = self.section("judges", "run-notes")
        for e in EFFORTS:
            for p in PANELS:
                self.assertIn(f'{g[e]["combined_single_judge"][p]["mean"]:.2f}', judges, (e, p))
        notes = plain(self.page_html[self.page_html.index('id="results"'):self.page_html.index('id="comparison"')])
        for e in EFFORTS:  # the four-factor note averages every run, the unpublished one included
            rs = [r for r in self.rows if r["effort"] == e]
            for factor in ("functional", "automated_quality", "security"):
                self.assertIn(f'{statistics.mean(100 * r[factor] for r in rs):.2f}', notes, (e, factor))

    def test_comparison_matches_the_board(self):
        board = board_rows()
        for key, name in {"neon": "Gemini 4 Neon", **COMPARATORS}.items():
            for e in EFFORTS:  # only the levels all three share
                b = board[name, e]
                star = "*" if key == "opus55" and int(b["n"]) < 23 else ""
                cells = (f'<td>{label(e)}</td><td>{float(b["combined_33"]):.2f}</td><td>{float(b["combined_33_se"]):.2f}</td><td>{b["n"]}{star}</td>'
                         f'<td>{b["passed"]}/23</td><td>{float(b["mean_minutes"]):.1f}</td>'
                         f'<td>{float(b["mean_raw_tokens"]) / 1e6:.2f}M</td><td>${float(b["mean_usd"]):.2f}</td><td>{float(b["code_quality"]):.2f}</td>')
                row = self.page_html[self.page_html.index(f'data-compare="{key}-{e}"'):]
                self.assertIn(cells, row[:row.index("</tr>")], (key, e))
        self.assertNotIn('data-compare="neon-max"', self.page_html)
        self.assertNotIn('data-compare="opus55-max"', self.page_html)
        self.assertNotIn('data-compare="gpt62sol-max"', self.page_html)
        comparison = self.section("comparison", "low")
        for needle in ("3.0 to 3.4 points", "1.0 to 1.5 points", "4.1 at Low", "both models pass 17 tasks", "same rubric", "Harnesses differ",
                       "no Max level", "$0.73 to $1.80"):
            self.assertIn(needle, comparison, needle)

    def test_required_disclosures(self):
        results = plain(self.page_html[self.page_html.index('id="results"'):self.page_html.index('id="comparison"')])
        for needle in ("Low and Extra-high codeccore have no Code quality score", "invalidate_unrecoverable_probe", "not valid JSON",
                       "v3.7", "v3.17", "rather than score the runs from Muse alone", "Both runs passed every hidden test"):
            self.assertIn(needle, results, needle)
        low = self.section("low", "cost")
        for task in LOW_PARTIAL:
            self.assertIn(task, low)
        board = self.section("board", "code-quality")
        for needle in ("ranks 43rd of the board’s 95", "Low 60th, Medium 46th, High 43rd and Extra-high 45th", "pick Medium",
                       "not calibrated against each other", "††† footnote"):
            self.assertIn(needle, board, needle)
        cost = self.section("cost", "board")
        for needle in ("$3.00 input, $0.15 cached input and $15.00 output", "2026-11-19", "not subscription charges", "$106.84", "40.8K",
                       "2,455", "not billed twice"):
            self.assertIn(needle, cost, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("Muse Spark 1.3", "Grok 4.6", "2026.10.01-e373342", "Neither lab is Google", "one-gate allowance", "g11", "0.02 short",
                       "368 counted calls", "364 selected", "second attempt on 2 calls", "Grok on 7", "Grok 4.6 Medium", "14:58 to 21:19 UTC",
                       "02:19 UTC", "no benchmark run overlapped"):
            self.assertIn(needle, judges, needle)
        notes = self.section("run-notes", "reproduce")
        for needle in ("gemini-4-neon", "1.5.12", "Google AI Pro", "no Max level", "custom main agent", "web search tool", "verbatim",
                       "40 attempts", "four of them at Extra-high cut off mid-task", "nine hours", "bench/2026-11-20-gemini4-neon-frontier-v4",
                       "heredocs", "1.6.1", "read-only", "environment variable", "No timeouts", "19.0 minutes"):
            self.assertIn(needle, notes, needle)
        self.assertIn("never compared with Routine v1 Code quality", self.text)
        self.assertIn("thinking text", self.text)

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
        self.assertEqual(provenance["gemini4neon-vs-frontier.png"], sha)


class Gemini4NeonSiteTests(unittest.TestCase):
    def test_model_page_links_report(self):
        markup = MODEL_PAGE.read_text()
        self.assertIn('href="../benchmarks/swe-v4-gemini4-neon-v332.html"', markup)
        self.assertIn(f'<link rel="canonical" href="{MODEL_URL}">', markup)
        self.assertIn("Model results &middot; Google", markup)
        for value in ("84.32", "87.48", "87.87", "87.70", "17 of 23 tasks passed at Low", "43rd of 95", "$106.84"):
            self.assertIn(value, markup, value)

    def test_site_references(self):
        for name in ("benchmarks.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "index.html", "models/gemini-4-neon.html"):
            self.assertIn("swe-v4-gemini4-neon-v332.html", (ROOT / name).read_text(), name)
        self.assertIn('href="models/gemini-4-neon.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn("swe-v4-gemini4-neon-v332/", (ROOT / "assets/data/README.md").read_text())
        sitemap = (ROOT / "sitemap.xml").read_text()
        for page_url in (URL, MODEL_URL):
            self.assertIn(f"<loc>{page_url}</loc>", sitemap)
        item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in i)
        self.assertIn("VulcanBench Frontier v4", item)
        self.assertIn("21 Nov 2026", item)
        self.assertNotIn(chr(0x2014), item)
        leaderboard = (ROOT / "leaderboard.html").read_text()
        self.assertIn('<a href="benchmarks/swe-v4-gemini4-neon-v332.html">Gemini 4 Neon</a>', leaderboard)
        self.assertEqual(len(re.findall(r'"key":"neon","effort":"[a-z-]+"', leaderboard)), 4)
        self.assertIn('"neon":"#A142F4"', leaderboard.replace(" ", ""))
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-gemini4-neon-v332.html"), index.index("swe-v4-gpt62-sol-v331.html"))


if __name__ == "__main__":
    unittest.main()
