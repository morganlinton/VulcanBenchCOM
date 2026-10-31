"""Stdlib checks for the GPT-6.1 Terra bundle (v3.29), its report page, its card, its model page and the site links to them."""

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
DATA = ROOT / "assets/data/swe-v4-gpt61-terra-v329"
PAGE = ROOT / "benchmarks/swe-v4-gpt61-terra-v329.html"
MODEL_PAGE = ROOT / "models/gpt-6-1-terra.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-gpt61-terra-v329.html"
MODEL_URL = "https://vulcanbench.com/models/gpt-6-1-terra.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
ENTITIES = ("&" + "mdash;", "&" + "ndash;")  # spelled in parts so this file carries no dash entity
RUNS = 115
PASSED = [13, 12, 15, 16, 23]
# GPT-6.1 Terra list rates per million tokens, checked 2026-10-26.
RATES = {"input": 1.00, "cached_input": 0.05, "output": 5.00}
# The harness card's per-level table (docs/results/swe-v4-gpt61-terra-2026-10/terra-vs-frontier-card-efforts.csv), to four places.
CARD = {"low": (74.9479, 3.9008, 66.5532, 2.7847, 0.1139), "medium": (80.0953, 2.6116, 67.2941, 3.1121, 0.1388),
        "high": (79.1898, 3.3765, 69.9617, 3.2048, 0.1283), "extra-high": (83.6751, 2.0925, 70.9415, 4.9492, 0.2405),
        "max": (89.9973, 0.3927, 76.5928, 6.8775, 0.3564)}
# Copied byte for byte from the harness (docs/results/swe-v4-gpt61-terra-2026-10/terra-vs-frontier-card.png, 2400x1350), shown at 1600x900.
CARD_PNG = ("swe-v4-gpt61-terra-v329.png", "3e48b441fdae393290908a359146be2690d422bfb36947da8bd9214121638c42", 2400, 1350)
# Published comparator rows: Claude Opus 5.5 (v3.15), GPT-6.1 Sol (v3.18) and GPT-6 Astra (v3.4) bundles, and GPT-5.6 Terra (v3.6).
COMPARATORS = {"opus55": "swe-v4-opus55-v315", "gpt61sol": "swe-v4-gpt61-sol-v318", "astra": "swe-v4-astra-fable51-v34"}
PREVIOUS = ("terra", "swe-v4-terra-v36")
RECOVERED = ("max", "legacy-settlecore-binary-parity")
NOTICES = {("extra-high", "legacy-hedgecore-binary-parity"), ("extra-high", "legacy-pacecore-binary-parity"),
           ("extra-high", "legacy-tallycore-binary-parity")}
TOUCHED = ("benchmarks/swe-v4-gpt61-terra-v329.html", "models/gpt-6-1-terra.html", "models/gpt-5-6-terra.html", "benchmarks.html", "index.html",
           "feed.xml", "llms.txt", "leaderboard.html", "README.md", "assets/data/README.md", "assets/data/swe-v4-gpt61-terra-v329/README.md",
           "assets/data/swe-v4-gpt61-terra-v329/REPRODUCING.md", "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v329.py")


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


class TerraBundleTests(unittest.TestCase):
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
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            self.assertEqual((r["solver_cli_version"], r["requested_model"], r["model_identity"]), ("codex-cli 0.159.0", "gpt-6.1-terra", "requested-only"))
            self.assertEqual(r["requested_effort"], "xhigh" if r["effort"] == "extra-high" else r["effort"])
            self.assertEqual(r["source_tag"], "bench/2026-10-27-gpt61-terra-frontier-v4")
            self.assertEqual((r["judged"], r["judged_under"], r["scored_panels"]), ("published", "code-quality-maintenance-v3.29", list(PANELS)))
            self.assertEqual(r["codex_notices"], ["model_metadata_fallback"] if key in NOTICES else [])
            self.assertEqual(r["operator_recovery"] is not None, key == RECOVERED)
            u = r["token_usage"]
            self.assertEqual(u["uncached_input_tokens"], u["input_tokens"] - u["cached_input_tokens"])
            self.assertEqual(r["raw_tokens"], u["input_tokens"] + u["output_tokens"])
            self.assertAlmostEqual(r["estimated_usd"], priced(u), delta=1e-5)
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
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e) for e in EFFORTS], [23] * 5)
        self.assertEqual(sorted((r["effort"], r["task"]) for r in self.rows if r["intent_recovery_redistributed"]),
                         [("low", "legacy-granarycore-binary-parity"), ("low", "legacy-paddockcore-binary-parity"),
                          ("medium", "legacy-granarycore-binary-parity")])
        settle = next(r for r in self.rows if (r["effort"], r["task"]) == RECOVERED)
        self.assertIn("recover_escaped_excerpts", settle["operator_recovery"])
        self.assertEqual((round(settle["combined_33"], 2), round(settle["code_quality"], 2)), (91.11, 80.30))
        self.assertTrue(all(r["functional"] == 1 for r in self.rows if r["codex_notices"]))

    def test_runs_csv_and_scores_csv(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), RUNS)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], delta=5.1e-5)
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], delta=5.1e-7)
            self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])
            self.assertEqual(c["codex_notices"], "+".join(r["codex_notices"]))
        with (ROOT / "assets/data/swe-v4-gpt61-terra-v329-scores.csv").open(newline="") as source:
            scores = {r["effort"]: r for r in csv.DictReader(source)}
        self.assertEqual(list(scores), list(EFFORTS))
        for e, g in self.groups.items():
            self.assertAlmostEqual(float(scores[e]["combined_33"]), g["combined_33"]["mean"], places=4)
            self.assertEqual(int(scores[e]["passed_of_23"]), g["passed_all_runs"])
            self.assertAlmostEqual(float(scores[e]["mean_usd"]), g["usd"]["mean"], places=6)

    def test_groups_match_runs_and_card(self):
        self.assertEqual(list(self.groups), list(EFFORTS))
        for i, e in enumerate(EFFORTS):
            g = self.groups[e]
            rs = [r for r in self.rows if r["effort"] == e]
            self.assertEqual((g["runs"], g["n"], g["timeouts"], g["unpublished_runs"]), (23, 23, 0, 0))
            self.assertEqual(g["passed_all_runs"], PASSED[i])
            self.assertEqual(g["passed_all_runs"], sum(r["functional"] == 1 for r in rs))
            for field in ("combined_33", "code_quality"):
                values = [r[field] for r in rs]
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(values), places=9)
                self.assertAlmostEqual(g[field]["se"], statistics.stdev(values) / len(values) ** .5, places=9)
            self.assertAlmostEqual(g["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=9)
            self.assertAlmostEqual(g["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs), places=9)
            self.assertEqual(g["codex_notice_runs"], 3 if e == "extra-high" else 0)
            values = (g["combined_33"]["mean"], g["combined_33"]["se"], g["code_quality"]["mean"], g["minutes"]["mean"], g["usd"]["mean"])
            for value, expected in zip(values, CARD[e]):
                self.assertAlmostEqual(value, expected, delta=5e-5, msg=e)
        self.assertEqual([round(self.groups[e]["combined_33"]["mean"], 2) for e in EFFORTS], [74.95, 80.10, 79.19, 83.68, 90.00])
        self.assertEqual([self.groups[e]["hidden_behaviours_fixed"] for e in EFFORTS], [170, 188, 176, 205, 231])
        self.assertEqual([f'{self.groups[e]["raw_tokens"]["mean"] / 1e6:.2f}' for e in EFFORTS], ["0.77", "0.98", "0.90", "2.15", "2.38"])
        self.assertEqual([round(self.groups[e]["security"]["mean"], 2) for e in EFFORTS], [100.00, 99.57, 99.57, 93.48, 88.26])
        gaps = [self.groups[e]["by_panel"]["grok"]["mean"] - self.groups[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
        self.assertEqual((round(min(gaps), 1), round(max(gaps), 1)), (1.8, 3.3))
        t = self.econ["totals"]["gpt61terra"]
        self.assertEqual((t["runs"], round(t["usd"], 2), t["raw_tokens"]), (RUNS, 22.49, 165263467))
        self.assertEqual(self.econ["rates_per_million"]["gpt61terra"], RATES)

    def test_judges_and_protocol(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertEqual(record["taken_under"], "code-quality-maintenance-v3.29")
            self.assertTrue(record["passed"])
            self.assertEqual(record["call_count"], 80)
        self.assertEqual((self.calibration["muse"]["allowance_used"], self.calibration["muse"]["failing_gates"]), (True, ["g11_repeatability"]))
        self.assertAlmostEqual(self.calibration["muse"]["gates"]["g11_repeatability"]["shortfall"], 0.26, places=9)
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
        self.assertEqual(p["second_attempts"], {"muse": 12, "grok": 4})
        self.assertEqual(p["display_name"]["accepted_renames_recorded"], 440)
        self.assertEqual(p["unpublished"], [])
        (recovery,) = p["operator_recoveries"]
        self.assertEqual((recovery["panel"], recovery["stage"], recovery["submission"], recovery["effort"], recovery["task"], recovery["rule"]),
                         ("muse", "probe", "submission-011", *RECOVERED, "recover_escaped_excerpts"))
        self.assertEqual((recovery["source_attempt"], recovery["respelled_excerpts"]), (1, 1))
        self.assertIn("PR #239", recovery["owner_decision"])
        window = p["judging_window_utc"]
        self.assertEqual(len(window["recovery_calls_completed"]), 1)
        self.assertTrue(window["recovery_calls_completed"][0].startswith("2026-10-30T22:58"))
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), chr(0), *ENTITIES, "/Users/", "/home/", "/private/", "/var/folders/", "SWE v4",
                         "no model on the board", "no model on this board"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("ultra", text.lower(), name)


class TerraPageTests(unittest.TestCase):
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
        self.assertIn("intent/post?text=GPT-6.1%20Terra%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertIn("Morgan Linton", self.text)
        self.assertNotIn(".pdf", self.page_html)
        for target in ("https://github.com/morganlinton/VulcanBench", "https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md",
                       "https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/cli_agents.py",
                       "https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md",
                       "https://github.com/morganlinton/vulcanbench-gpt61-terra-traces"):
            self.assertIn(f'href="{target}"', self.page_html)

    def test_tables_match_the_bundle(self):
        g = self.groups
        self.assertEqual(set(self.page.rows), {("gpt61terra", e) for e in EFFORTS})
        for i, e in enumerate(EFFORTS):
            row = self.page.rows["gpt61terra", e]
            self.assertEqual(row[1:5], [label(e), f'{g[e]["combined_33"]["mean"]:.2f}', f'{g[e]["combined_33"]["se"]:.2f}',
                                        f'{g[e]["combined_20_profile"]["mean"]:.2f}'])
            self.assertEqual(row[5:9], [f'{g[e]["code_quality"]["mean"]:.2f}', f'{g[e]["readability"]["mean"]:.1f}',
                                        f'{g[e]["maintainability"]["mean"]:.1f}', f'{g[e]["intent_recovery"]["mean"]:.1f}'])
            self.assertEqual(row[-3:], ["23/23", f"{PASSED[i]}/23", f'{g[e]["minutes"]["mean"]:.1f}'])
            cells = (f'<td>23</td><td>${g[e]["usd"]["mean"]:.2f}</td><td>${g[e]["usd_total"]:.2f}</td><td>{g[e]["raw_tokens"]["mean"] / 1e6:.2f}M</td>'
                     f'<td>{g[e]["output_tokens"]["mean"] / 1e3:.1f}K</td><td>{g[e]["reasoning_output_tokens_median"] / 1e3:.1f}K</td>'
                     f'<td>{100 * g[e]["cached_input_share"]["mean"]:.1f}%</td><td>{g[e]["minutes"]["mean"]:.1f}</td><td>{g[e]["minutes_median"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}', self.page_html, e)
        total = sum(g[e]["usd_total"] for e in EFFORTS)
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>115</td><td>${total / RUNS:.2f}</td><td>${total:.2f}</td>', self.page_html)
        self.assertIn('<th scope="row">Combined score</th>' + "".join(f'<td>{g[e]["combined_33"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Judged runs</th>' + "<td>23</td>" * 5, self.page_html)
        self.assertIn('<th scope="row">Tasks passed</th>' + "".join(f"<td>{p}/23</td>" for p in PASSED), self.page_html)
        self.assertIn('<th scope="row">Hidden behaviours fixed</th>' + "".join(f'<td>{g[e]["hidden_behaviours_fixed"]}/231</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">API-equivalent $ per task</th>' + "".join(f'<td>${g[e]["usd"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Rated by Muse Spark 1.3</th>' + "".join(f'<td>{g[e]["by_panel"]["muse"]["mean"]:.1f}</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">Rated by Grok 4.6</th>' + "".join(f'<td>{g[e]["by_panel"]["grok"]["mean"]:.1f}</td>' for e in EFFORTS),
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

    def test_comparison_matches_the_published_bundles(self):
        rows = {"gpt61terra": load("swe-v4-gpt61-terra-v329", "gpt61terra")}
        rows.update({key: load(bundle, key) for key, bundle in COMPARATORS.items()})
        for key, (groups, econ) in rows.items():
            for e in EFFORTS:
                g, x = groups[e], econ[e]
                judged = f'{g["n"]}' + ("*" if g["n"] < 23 else "")
                cells = (f'<td>{label(e)}</td><td>{g["combined_33"]["mean"]:.2f}</td><td>{g["combined_33"]["se"]:.2f}</td><td>{judged}</td>'
                         f'<td>{g.get("passed_all_runs", g["passed"])}/23</td><td>{x["minutes"]["mean"]:.1f}</td>'
                         f'<td>{x["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>${x["usd"]["mean"]:.2f}</td><td>{g["code_quality"]["mean"]:.2f}</td>')
                row = self.page_html[self.page_html.index(f'data-compare="{key}-{e}"'):]
                self.assertIn(cells, row[:row.index("</tr>")], (key, e))
        comparison = self.section("comparison", "terra-family")
        for needle in ("catches the three frontier columns", "90.22", "89.30", "88.35", "cheapest and the fastest of the four at every level",
                       "$8.75", "37.5", "half of GPT-6.1 Sol’s", "same rubric", "Harnesses differ"):
            self.assertIn(needle, comparison, needle)
        new, new_econ = rows["gpt61terra"]
        old, old_econ = load(*PREVIOUS[::-1])
        family = self.page_html[self.page_html.index('id="terra-family"'):self.page_html.index('id="cost"')]
        for metric, key, cell in (("combined", "gpt61terra", lambda e: f'{new[e]["combined_33"]["mean"]:.2f}'),
                                  ("combined", "terra", lambda e: f'{old[e]["combined_33"]["mean"]:.2f}'),
                                  ("passed", "gpt61terra", lambda e: f'{new[e]["passed_all_runs"]}/23'),
                                  ("passed", "terra", lambda e: f'{old[e].get("passed_all_runs", old[e]["passed"])}/23'),
                                  ("cq", "gpt61terra", lambda e: f'{new[e]["code_quality"]["mean"]:.2f}'),
                                  ("cq", "terra", lambda e: f'{old[e]["code_quality"]["mean"]:.2f}'),
                                  ("usd", "gpt61terra", lambda e: f'${new_econ[e]["usd"]["mean"]:.2f}'),
                                  ("usd", "terra", lambda e: f'${old_econ[e]["usd"]["mean"]:.2f}'),
                                  ("minutes", "gpt61terra", lambda e: f'{new_econ[e]["minutes"]["mean"]:.1f}'),
                                  ("minutes", "terra", lambda e: f'{old_econ[e]["minutes"]["mean"]:.1f}')):
            row = family[family.index(f'data-family="{metric}-{key}"'):]
            self.assertIn("".join(f"<td>{cell(e)}</td>" for e in EFFORTS), row[:row.index("</tr>")], (metric, key))
        gains = [new[e]["combined_33"]["mean"] - old[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertTrue(all(x > 0 for x in gains))
        for x in gains:
            self.assertIn(f"{x:.2f}", plain(family))

    def test_required_disclosures(self):
        results = plain(self.page_html[self.page_html.index('id="results"'):self.page_html.index('id="comparison"')])
        for needle in ("Max settlecore is published through a recovery", "recover_escaped_excerpts", "\\0", "\\x00", "114 of the 115 runs",
                       "October 29", "harness PR #239", "89.95 on 22 runs to 90.00 on 23", "Three runs (Low granarycore and paddockcore, Medium granarycore)",
                       "Security is the one factor that falls with effort"):
            self.assertIn(needle, results, needle)
        board = self.section("board", "code-quality")
        for needle in ("ranks 16th of the board’s 80", "Low 62nd, Medium 56th, High 57th, Extra-high 49th, Max 16th", "Of the 17 priced columns scoring 89 or more",
                       "all pick Max", "not calibrated against each other", "** footnote"):
            self.assertIn(needle, board, needle)
        cost = self.section("cost", "board")
        for needle in ("$1.00 input, $0.05 cached input and $5.00 output", "2026-10-26", "not subscription charges", "$22.49", "14.5K"):
            self.assertIn(needle, cost, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("Muse Spark 1.3", "Grok 4.6", "2026.10.01-e373342", "Neither lab is OpenAI", "one-gate allowance", "g11", "0.26 short",
                       "440 counted calls", "second attempt on 12 calls", "Grok on 4", "Grok 4.6 Medium", "22:58 UTC"):
            self.assertIn(needle, judges, needle)
        notes = self.section("run-notes", "reproduce")
        for needle in ("gpt-6.1-terra", "October 26, 2026", "requested", "0.159.0", "workspace-write", "xhigh", "hedgecore, pacecore and tallycore",
                       "fallback metadata", "bench/2026-10-27-gpt61-terra-frontier-v4", "No timeouts", "19.5 minutes", "15:14 to 23:16 UTC"):
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
        self.assertEqual(provenance["terra-vs-frontier-card.png"], sha)


class TerraSiteTests(unittest.TestCase):
    def test_model_page_links_report(self):
        markup = MODEL_PAGE.read_text()
        self.assertIn('href="../benchmarks/swe-v4-gpt61-terra-v329.html"', markup)
        self.assertIn('href="https://github.com/morganlinton/vulcanbench-gpt61-terra-traces"', markup)
        self.assertIn(f'<link rel="canonical" href="{MODEL_URL}">', markup)
        for value in ("74.95", "80.10", "79.19", "83.68", "90.00", "13, 12, 15, 16 and 23 of 23", "16th of 80", "$22.49"):
            self.assertIn(value, markup, value)
        self.assertIn('href="gpt-6-1-terra.html"', (ROOT / "models/gpt-5-6-terra.html").read_text())

    def test_site_references(self):
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "models/gpt-6-1-terra.html"):
            self.assertIn("swe-v4-gpt61-terra-v329.html", (ROOT / name).read_text(), name)
        self.assertIn('href="models/gpt-6-1-terra.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn("swe-v4-gpt61-terra-v329/", (ROOT / "assets/data/README.md").read_text())
        sitemap = (ROOT / "sitemap.xml").read_text()
        for page_url in (URL, MODEL_URL):
            self.assertIn(f"<loc>{page_url}</loc>", sitemap)
        item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in i)
        self.assertIn("VulcanBench Frontier v4", item)
        self.assertIn("30 Oct 2026", item)
        self.assertNotIn(chr(0x2014), item)
        leaderboard = (ROOT / "leaderboard.html").read_text()
        self.assertIn('<a href="benchmarks/swe-v4-gpt61-terra-v329.html">GPT-6.1 Terra</a>', leaderboard)
        self.assertEqual(len(re.findall(r'"key":"gpt61terra","effort":"[a-z-]+"', leaderboard)), 5)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-gpt61-terra-v329.html"), index.index("swe-v4-beam-v328.html"))


if __name__ == "__main__":
    unittest.main()
