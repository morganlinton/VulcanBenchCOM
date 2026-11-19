"""Stdlib checks for the GPT-6.2 Sol bundle (v3.31), its report page, its card, its model page and the site links to them."""

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
DATA = ROOT / "assets/data/swe-v4-gpt62-sol-v331"
PAGE = ROOT / "benchmarks/swe-v4-gpt62-sol-v331.html"
MODEL_PAGE = ROOT / "models/gpt-6-2-sol.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-gpt62-sol-v331.html"
MODEL_URL = "https://vulcanbench.com/models/gpt-6-2-sol.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
ENTITIES = ("&" + "mdash;", "&" + "ndash;")  # spelled in parts so this file carries no dash entity
RUNS = 115
# GPT-6.2 Sol list rates per million tokens, checked 2026-11-17 (the same as GPT-6.1 Sol).
RATES = {"input": 2.00, "cached_input": 0.10, "output": 10.00}
# The harness card's per-level table (docs/results/swe-v4-gpt62-sol-2026-11/gpt62sol-vs-frontier-efforts.csv), to four places.
CARD = {"low": (88.4360, 0.3481, 70.3077, 2.7553, 0.2331), "medium": (88.9414, 0.4667, 71.7819, 4.3516, 0.3254),
        "high": (88.8619, 0.3263, 71.4348, 5.1436, 0.4065), "extra-high": (89.0059, 0.4319, 71.9079, 8.2172, 0.4586),
        "max": (88.7438, 0.4027, 71.0646, 11.2644, 0.5493)}
# Copied byte for byte from the harness (docs/results/swe-v4-gpt62-sol-2026-11/gpt62sol-vs-frontier.png, 2400x1350), shown at 1600x900.
CARD_PNG = ("swe-v4-gpt62-sol-v331.png", "38b5ada9bbb5b283f4103d86f6e36884b6ae227357cc0a73b27401599d928ab9", 2400, 1350)
# Comparators on the page and the card: published board rows.
COMPARATORS = {"fable52": "Fable 5.2", "opus55": "Opus 5.5", "gpt61sol": "GPT-6.1 Sol"}
PREVIOUS = ("gpt61sol", "swe-v4-gpt61-sol-v318")
ONE_PANEL = ("low", "legacy-granarycore-binary-parity")
TOUCHED = ("benchmarks/swe-v4-gpt62-sol-v331.html", "models/gpt-6-2-sol.html", "models/gpt-6-1-sol.html", "benchmarks.html", "index.html",
           "feed.xml", "llms.txt", "leaderboard.html", "README.md", "assets/data/README.md", "assets/data/swe-v4-gpt62-sol-v331/README.md",
           "assets/data/swe-v4-gpt62-sol-v331/REPRODUCING.md", "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v331.py")


def code_quality(reviewed, intent):
    return reviewed if intent is None else (0.24 * reviewed + 0.09 * intent) / 0.33


def combined(r, cq, weight=0.33):
    other = (0.5 - weight) / 2
    return 100 * (.5 * r["functional"] + other * r["automated_quality"] + other * r["security"] + weight * cq / 100)


def priced(u):
    return ((u["input_tokens"] - u["cached_input_tokens"]) * RATES["input"] + u["cached_input_tokens"] * RATES["cached_input"]
            + u["output_tokens"] * RATES["output"]) / 1e6


def load(bundle, key):
    groups = {x["effort"]: x for x in json.loads((ROOT / "assets/data" / bundle / "groups.json").read_text()) if x["model"] == key}
    econ = {x["effort"]: x for x in json.loads((ROOT / "assets/data" / bundle / "economics.json").read_text())["groups"] if x["model"] == key}
    return groups, econ


def board_rows():
    with (ROOT / "assets/data/swe-v4-board.csv").open(newline="") as source:
        return {(r["model"], r["effort"]): r for r in csv.DictReader(source)}


class GPT62SolBundleTests(unittest.TestCase):
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
            key = (r["effort"], r["task"])
            self.assertTrue(r["finished"] and r["duration_s"] < 10800)
            self.assertEqual(r["functional"], 1)
            self.assertEqual(r["hidden_behaviours_fixed"], r["hidden_behaviours"])
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            self.assertEqual((r["solver_cli_version"], r["requested_model"], r["model_identity"]), ("codex-cli 0.166.0", "gpt-6.2-sol", "requested-only"))
            self.assertEqual(r["requested_effort"], "xhigh" if r["effort"] == "extra-high" else r["effort"])
            self.assertEqual(r["source_tag"], "bench/2026-11-17-gpt62-sol-frontier-v4")
            valid = ["muse"] if key == ONE_PANEL else list(PANELS)
            self.assertEqual((r["judged"], r["judged_under"], r["scored_panels"]), ("published", "code-quality-maintenance-v3.31", valid))
            self.assertEqual(r["one_panel_note"] is not None, key == ONE_PANEL)
            self.assertEqual(r["codex_notices"], [])
            u = r["token_usage"]
            self.assertEqual(u["uncached_input_tokens"], u["input_tokens"] - u["cached_input_tokens"])
            self.assertEqual(r["raw_tokens"], u["input_tokens"] + u["output_tokens"])
            self.assertAlmostEqual(r["estimated_usd"], priced(u), delta=1e-5)
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in valid)
            intents = [r["panels"][p]["intent_recovery"] for p in valid if r["panels"][p]["intent_recovery"] is not None]
            intent = statistics.mean(intents) if intents else None
            self.assertEqual(r["intent_recovery_redistributed"], intent is None)
            cq = code_quality(reviewed, intent)
            self.assertAlmostEqual(r["code_quality"], cq, places=9)
            self.assertAlmostEqual(r["combined_33"], combined(r, cq), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], combined(r, cq, 0.20), places=9)
            for p in PANELS:
                if p in valid:
                    alone = code_quality(r["panels"][p]["reviewed_score"], r["panels"][p]["intent_recovery"])
                    self.assertAlmostEqual(r["combined_single_judge"][p], combined(r, alone), places=9)
                else:
                    self.assertIsNone(r["combined_single_judge"][p])
                    self.assertIsNone(r["panels"][p]["reviewed_score"])
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e) for e in EFFORTS], [23] * 5)
        self.assertFalse(any(r["intent_recovery_redistributed"] for r in self.rows))
        granary = next(r for r in self.rows if (r["effort"], r["task"]) == ONE_PANEL)
        self.assertEqual((round(granary["combined_33"], 2), round(granary["code_quality"], 2)), (85.62, 65.50))

    def test_runs_csv_and_scores_csv(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), RUNS)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], delta=5.1e-5)
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], delta=5.1e-7)
            self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])
            self.assertEqual(c["scored_panels"], "+".join(r["scored_panels"]))
            self.assertEqual(c["combined_grok_only"] == "", (r["effort"], r["task"]) == ONE_PANEL)
        with (ROOT / "assets/data/swe-v4-gpt62-sol-v331-scores.csv").open(newline="") as source:
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
            self.assertEqual((g["runs"], g["n"], g["timeouts"], g["unpublished_runs"]), (23, 23, 0, 0))
            self.assertEqual(g["passed_all_runs"], 23)
            self.assertEqual(g["one_panel_runs"], 1 if e == "low" else 0)
            self.assertEqual(g["by_panel"]["grok"]["n"], 22 if e == "low" else 23)
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
        self.assertEqual([round(self.groups[e]["combined_33"]["mean"], 2) for e in EFFORTS], [88.44, 88.94, 88.86, 89.01, 88.74])
        self.assertEqual([self.groups[e]["hidden_behaviours_fixed"] for e in EFFORTS], [231] * 5)
        self.assertEqual([f'{self.groups[e]["raw_tokens"]["mean"] / 1e6:.2f}' for e in EFFORTS], ["0.77", "1.05", "1.30", "1.31", "1.31"])
        self.assertEqual([round(self.groups[e]["security"]["mean"], 2) for e in EFFORTS], [99.78, 99.78, 100.00, 99.35, 100.00])
        gaps = [self.groups[e]["by_panel"]["grok"]["mean"] - self.groups[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
        self.assertEqual((round(min(gaps), 1), round(max(gaps), 1)), (0.5, 5.9))
        t = self.econ["totals"]["gpt62sol"]
        self.assertEqual((t["runs"], round(t["usd"], 2), t["raw_tokens"]), (RUNS, 45.38, 131730354))
        self.assertEqual(self.econ["rates_per_million"]["gpt62sol"], RATES)

    def test_judges_and_protocol(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertEqual(record["taken_under"], "code-quality-maintenance-v3.31")
            self.assertTrue(record["passed"])
            self.assertEqual(record["call_count"], 80)
        self.assertEqual((self.calibration["muse"]["allowance_used"], self.calibration["muse"]["failing_gates"]), (True, ["g11_repeatability"]))
        self.assertAlmostEqual(self.calibration["muse"]["gates"]["g11_repeatability"]["shortfall"], 0.1, places=9)
        self.assertEqual((self.calibration["grok"]["allowance_used"], self.calibration["grok"]["failing_gates"]), (False, []))
        p = self.protocols
        self.assertEqual(set(p["scored_panel"]), set(PANELS))
        self.assertEqual((p["scored_panel"]["muse"]["model"], p["scored_panel"]["grok"]["model"]), ("muse-spark-1.3", "cursor-grok-4.6-medium"))
        v324 = json.loads((ROOT / "assets/data/swe-v4-haiku55-v324/judge-protocols.json").read_text())
        self.assertEqual(p["scored_panel"], v324["scored_panel"])
        for key in ("rubric", "system", "probe_instruction", "match_instruction", "schemas", "weights", "seed", "repeats", "gate_allowance"):
            self.assertEqual(p[key], v324[key], key)
        self.assertEqual(p["counted_calls"], {q: {"calibration": 80, "primary": 115, "repeat": 5, "pairwise": 10, "probe": 115, "match": 115}
                                              for q in PANELS})
        self.assertEqual(p["second_attempts"], {"muse": 8, "grok": 4})
        self.assertEqual(p["display_name"]["accepted_renames_recorded"], 439)
        self.assertEqual((p["unpublished"], p["operator_recoveries"]), ([], []))
        (one,) = p["one_panel"]
        self.assertEqual((one["submission"], one["effort"], one["task"], one["invalid_panel"], one["stage"], one["rule"], one["scored_from"]),
                         ("submission-069", *ONE_PANEL, "grok", "primary", "invalidate_unrecoverable_primary", "muse"))
        self.assertEqual(one["owner_decision"], "2026-09-23 (v3.14 precedent)")
        quota = p["quota_stops"]
        self.assertEqual((quota["panel"], quota["stage"], quota["call"], quota["archived_attempts"]), ("grok", "calibration", "control-7-r2", 5))
        window = p["judging_window_utc"]
        self.assertTrue(window["first_muse_call_completed"].startswith("2026-11-19T00:05"))
        self.assertTrue(window["last_muse_call_completed"].startswith("2026-11-19T07:27"))
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), chr(0), *ENTITIES, "/Users/", "/home/", "/private/", "/var/folders/", "SWE v4",
                         "no model on the board", "no model on this board"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("ultra", text.lower(), name)


class GPT62SolPageTests(unittest.TestCase):
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
        self.assertIn("intent/post?text=GPT-6.2%20Sol%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertIn("Morgan Linton", self.text)
        self.assertNotIn(".pdf", self.page_html)
        for target in ("https://github.com/morganlinton/VulcanBench", "https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md",
                       "https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/cli_agents.py",
                       "https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md"):
            self.assertIn(f'href="{target}"', self.page_html)

    def test_tables_match_the_bundle(self):
        g = self.groups
        self.assertEqual(set(self.page.rows), {("gpt62sol", e) for e in EFFORTS})
        for e in EFFORTS:
            row = self.page.rows["gpt62sol", e]
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
        self.assertIn('<th scope="row">Rated by Muse Spark 1.3</th>' + "".join(f'<td>{g[e]["by_panel"]["muse"]["mean"]:.1f}</td>' for e in EFFORTS),
                      self.page_html)
        grok = [f'{g[e]["by_panel"]["grok"]["mean"]:.1f}' + (" (22)" if e == "low" else "") for e in EFFORTS]
        self.assertIn('<th scope="row">Rated by Grok 4.6</th>' + "".join(f"<td>{v}</td>" for v in grok), self.page_html)
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
        for key, name in {"gpt62sol": "GPT-6.2 Sol", **COMPARATORS}.items():
            for e in EFFORTS:
                b = board[name, e]
                judged = b["n"] + ("*" if int(b["n"]) < 23 else "")
                cq = f'{float(b["code_quality"]):.2f}' + ("&dagger;" if key == "fable52" else "")
                cells = (f'<td>{label(e)}</td><td>{float(b["combined_33"]):.2f}</td><td>{float(b["combined_33_se"]):.2f}</td><td>{judged}</td>'
                         f'<td>{b["passed"]}/23</td><td>{float(b["mean_minutes"]):.1f}</td>'
                         f'<td>{float(b["mean_raw_tokens"]) / 1e6:.2f}M</td><td>${float(b["mean_usd"]):.2f}</td><td>{cq}</td>')
                row = self.page_html[self.page_html.index(f'data-compare="{key}-{e}"'):]
                self.assertIn(cells, row[:row.index("</tr>")], (key, e))
        comparison = self.section("comparison", "sol-family")
        for needle in ("first on the board", "3.3 to 5.1 points", "5 to 20 times", "91.09 to 92.78", "87.75 to 88.65", "same rubric",
                       "Harnesses differ", "not strictly comparable"):
            self.assertIn(needle, comparison, needle)
        new = {e: self.groups[e] for e in EFFORTS}
        old, old_econ = load(*PREVIOUS[::-1])
        family = self.page_html[self.page_html.index('id="sol-family"'):self.page_html.index('id="cost"')]
        for metric, key, cell in (("combined", "gpt62sol", lambda e: f'{new[e]["combined_33"]["mean"]:.2f}'),
                                  ("combined", "gpt61sol", lambda e: f'{old[e]["combined_33"]["mean"]:.2f}'),
                                  ("passed", "gpt62sol", lambda e: f'{new[e]["passed_all_runs"]}/23'),
                                  ("passed", "gpt61sol", lambda e: f'{old[e].get("passed_all_runs", old[e]["passed"])}/23'),
                                  ("cq", "gpt62sol", lambda e: f'{new[e]["code_quality"]["mean"]:.2f}'),
                                  ("cq", "gpt61sol", lambda e: f'{old[e]["code_quality"]["mean"]:.2f}'),
                                  ("usd", "gpt62sol", lambda e: f'${new[e]["usd"]["mean"]:.2f}'),
                                  ("usd", "gpt61sol", lambda e: f'${old_econ[e]["usd"]["mean"]:.2f}'),
                                  ("minutes", "gpt62sol", lambda e: f'{new[e]["minutes"]["mean"]:.1f}'),
                                  ("minutes", "gpt61sol", lambda e: f'{old_econ[e]["minutes"]["mean"]:.1f}')):
            row = family[family.index(f'data-family="{metric}-{key}"'):]
            self.assertIn("".join(f"<td>{cell(e)}</td>" for e in EFFORTS), row[:row.index("</tr>")], (metric, key))
        gains = [new[e]["combined_33"]["mean"] - old[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertTrue(all(x > 0 for x in gains))
        for x in gains:
            self.assertIn(f"{x:.2f}", plain(family))

    def test_required_disclosures(self):
        results = plain(self.page_html[self.page_html.index('id="results"'):self.page_html.index('id="comparison"')])
        for needle in ("Low granarycore is scored by one judge", "invalidate_unrecoverable_primary", "September 23", "Muse Spark 1.3 alone",
                       "Medium paddockcore", "85.62", "65.50", "100.00 at every level"):
            self.assertIn(needle, results, needle)
        board = self.section("board", "code-quality")
        for needle in ("ranks 27th of the board’s 91", "Low 34th, Medium 28th, High 29th, Extra-high 27th, Max 31st",
                       "Of the 23 priced columns scoring 89 or more", "all pick Low", "not calibrated against each other", "*** footnote"):
            self.assertIn(needle, board, needle)
        cost = self.section("cost", "board")
        for needle in ("$2.00 input, $0.10 cached input and $10.00 output", "2026-11-17", "not subscription charges", "$45.38", "12.8K"):
            self.assertIn(needle, cost, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("Muse Spark 1.3", "Grok 4.6", "2026.10.01-e373342", "Neither lab is OpenAI", "one-gate allowance", "g11", "0.1 short",
                       "failed one gate of the same exam", "440 counted calls", "439 selected calls", "second attempt on 8 calls", "Grok on 4",
                       "usage limit", "free plan", "quota rule", "Grok 4.6 Medium", "00:04 UTC", "13:39 UTC"):
            self.assertIn(needle, judges, needle)
        notes = self.section("run-notes", "reproduce")
        for needle in ("gpt-6.2-sol", "November 17, 2026", "requested", "0.166.0", "0.165.0", "prolite", "workspace-write", "xhigh",
                       "bench/2026-11-17-gpt62-sol-frontier-v4", "No timeouts", "23.6 minutes", "00:34 to 12:44 UTC"):
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
        self.assertEqual(provenance["gpt62sol-vs-frontier.png"], sha)


class GPT62SolSiteTests(unittest.TestCase):
    def test_model_page_links_report(self):
        markup = MODEL_PAGE.read_text()
        self.assertIn('href="../benchmarks/swe-v4-gpt62-sol-v331.html"', markup)
        self.assertIn(f'<link rel="canonical" href="{MODEL_URL}">', markup)
        for value in ("88.44", "88.94", "88.86", "89.01", "88.74", "Every task passed at every level", "27th of 91", "$45.38"):
            self.assertIn(value, markup, value)
        self.assertIn('href="gpt-6-2-sol.html"', (ROOT / "models/gpt-6-1-sol.html").read_text())

    def test_site_references(self):
        for name in ("benchmarks.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "index.html", "models/gpt-6-2-sol.html"):
            self.assertIn("swe-v4-gpt62-sol-v331.html", (ROOT / name).read_text(), name)
        self.assertIn('href="models/gpt-6-2-sol.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn("swe-v4-gpt62-sol-v331/", (ROOT / "assets/data/README.md").read_text())
        sitemap = (ROOT / "sitemap.xml").read_text()
        for page_url in (URL, MODEL_URL):
            self.assertIn(f"<loc>{page_url}</loc>", sitemap)
        item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in i)
        self.assertIn("VulcanBench Frontier v4", item)
        self.assertIn("19 Nov 2026", item)
        self.assertNotIn(chr(0x2014), item)
        leaderboard = (ROOT / "leaderboard.html").read_text()
        self.assertIn('<a href="benchmarks/swe-v4-gpt62-sol-v331.html">GPT-6.2 Sol</a>', leaderboard)
        self.assertEqual(len(re.findall(r'"key":"gpt62sol","effort":"[a-z-]+"', leaderboard)), 5)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-gpt62-sol-v331.html"), index.index("swe-v4-fable52-v330.html"))


if __name__ == "__main__":
    unittest.main()
