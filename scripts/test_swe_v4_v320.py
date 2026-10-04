"""Stdlib checks for the v3.20 Grok 4.7 (Cursor) bundle, its report page, its four cards and the site links to it."""

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
DATA = ROOT / "assets/data/swe-v4-grok47-cursor-v320"
PAGE = ROOT / "benchmarks/swe-v4-grok47-cursor-v320.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-grok47-cursor-v320.html"
EFFORTS = ("low", "medium", "high", "extra-high")
PANELS = ("muse", "sol")
TIMEOUT = ("medium", "legacy-lodgecore-binary-parity")
# Copied byte for byte from the harness (docs/results/swe-v4-grok47-cursor-2026-10 and safety-v1-grok47-2026-10).
CARDS = {
    "swe-v4-grok47-cursor-v320.png": "40a21ba4fda5faa3686cb121116e39bc154606c89b6e871508b228fc59129ce4",
    "swe-v4-grok47-cursor-v320-usage.png": "f29bec92250e8d3f60467d3a20b25f11aa805a6f50d37041402f6bca32f0782d",
    "swe-v4-grok47-vs-frontier-leaders.png": "162e862d8c9aca8e37d367b84aa79af0318ecdeae2aa692222698345aefa0a64",
    "safety-v1-grok47-opus55.png": "f1909f3bb67b07ade63a2017bd4bee4aba8baa6740bcaa9df2524f8078c40cb4",
}
# Every other Frontier v4 column, for the shared-judge check (Muse Spark 1.3 alone).
BUNDLES = {"astra": "swe-v4-astra-fable51-v34", "fable": "swe-v4-astra-fable51-v34", "gpt55": "swe-v4-gpt55-luna-v35",
           "luna": "swe-v4-gpt55-luna-v35", "terra": "swe-v4-terra-v36", "sol": "swe-v4-sol-v37", "opus55": "swe-v4-opus55-v315",
           "gpt6luna": "swe-v4-gpt6-luna-v316", "gpt6sol": "swe-v4-gpt6-sol-v317", "gpt61sol": "swe-v4-gpt61-sol-v318"}


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


def muse_only(r):
    m = r["panels"]["muse"]
    cq = m["reviewed_score"] if m["intent_recovery"] is None else (0.24 * m["reviewed_score"] + 0.09 * m["intent_recovery"]) / 0.33
    return cq, 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * cq / 100)


class Grok47BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.judged = [r for r in cls.rows if r["finished"]]
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.usage = json.loads((DATA / "usage.json").read_text())
        cls.provenance = json.loads((DATA / "provenance.json").read_text())
        cls.shared = json.loads((DATA / "shared-judge.json").read_text())["columns"]
        cls.safety = json.loads((DATA / "safety-v1.json").read_text())
        with (ROOT / "assets/data/swe-v4-grok47-cursor-v320-scores.csv").open(newline="") as source:
            cls.scores = {r["effort"]: r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 92)
        self.assertEqual((self.runs["published"], self.runs["timeouts"]), (91, 1))
        self.assertEqual(self.runs["judges"], {"muse": "Muse Spark 1.3", "sol": "GPT-6.1 Sol"})
        self.assertTrue(all(r["judged_under"] == "code-quality-maintenance-v3.20" for r in self.rows))
        self.assertTrue(all(r["solver_cli_version"] == "2026.10.01-14929f9" for r in self.rows))
        self.assertEqual({r["effort"] for r in self.rows}, set(EFFORTS))  # Cursor offers no max level for Grok 4.7
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        [timeout] = [r for r in self.rows if not r["finished"]]
        self.assertEqual((timeout["effort"], timeout["task"]), TIMEOUT)
        self.assertGreaterEqual(timeout["duration_s"], 10800)
        self.assertTrue(timeout["judged"].startswith("timeout: the run hit the flat 3-hour task bound"))
        self.assertEqual((timeout["functional"], timeout["hidden_behaviours_fixed"]), (0.0, 0))
        for field in ("combined_33", "code_quality", "panels", "raw_tokens", "token_usage", "estimated_usd"):
            self.assertIsNone(timeout[field], field)
        for r in self.rows:
            self.assertIsNone(r["estimated_usd"])  # no list price: unavailable, never $0
            self.assertTrue(r["pricing_method"].startswith("unpriced"))
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
        for r in self.judged:
            self.assertEqual(r["duration_s"] < 10800, True)
            self.assertEqual(r["scored_panels"], list(PANELS))
            self.assertEqual(r["raw_tokens"], sum(r["token_usage"].values()))
            self.assertEqual(r["cli_summary_units"], 0)
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
            self.assertFalse(r["intent_recovery_redistributed"])
            code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            for p in PANELS:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"], (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
            self.assertEqual(r["functional"] == 1, r["hidden_behaviours_fixed"] == r["hidden_behaviours"], r["run_id"])
        self.assertEqual(len({(r["effort"], r["task"]) for r in self.rows}), 92)
        per_task = {}
        for r in self.rows:
            per_task.setdefault(r["task"], set()).add(r["hidden_behaviours"])
        self.assertEqual(sum(next(iter(v)) for v in per_task.values()), 231)

    def test_runs_csv_matches_runs_json(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = list(csv.DictReader(source))
        self.assertEqual(len(csv_rows), 92)
        by_run = {r["run_id"]: r for r in csv_rows}
        for r in self.rows:
            c = by_run[r["run_id"]]
            self.assertEqual(c["estimated_usd"], "unavailable")
            if r["finished"]:
                self.assertEqual(c["judged"], "published")
                self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])
                self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], places=3)
                self.assertAlmostEqual(float(c["sol_reviewed"]), r["panels"]["sol"]["reviewed_score"], places=3)
            else:
                self.assertEqual((c["judged"], c["combined_33"], c["raw_tokens"]), ("timeout", "", ""))

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), set(EFFORTS))
        self.assertEqual(set(self.scores), set(EFFORTS))
        for effort, g in self.groups.items():
            rs = [r for r in self.rows if r["effort"] == effort]
            judged = [r for r in rs if r["finished"]]
            self.assertEqual((len(rs), g["runs"], g["n"], g["timeouts"]), (23, 23, len(judged), 23 - len(judged)))
            for field, values in (("combined_33", [r["combined_33"] for r in judged]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in judged]),
                                  ("code_quality", [r["code_quality"] for r in judged]),
                                  ("intent_recovery", [r["intent_recovery"] for r in judged]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]),
                                  ("raw_tokens", [r["raw_tokens"] for r in judged])):
                mean, se = mean_se(values)
                self.assertEqual(g[field]["n"], len(values), (effort, field))
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(effort, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(effort, field))
            for p in PANELS:
                self.assertAlmostEqual(g["by_panel"][p]["mean"], statistics.mean(r["panels"][p]["reviewed_score"] for r in judged), places=9)
            self.assertEqual(g["passed_all_runs"], sum(r["functional"] == 1 for r in rs))
            self.assertEqual(g["hidden_behaviours"], 231)
            self.assertIsNone(g["usd"])
            row = self.scores[effort]
            self.assertEqual(row["mean_usd"], "unavailable")
            for column, field in (("combined_33", "combined_33"), ("code_quality", "code_quality"), ("mean_minutes", "minutes")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(effort, column))
            self.assertEqual(int(row["passed_of_23"]), g["passed_all_runs"])
        g = self.groups
        self.assertEqual([g[e]["n"] for e in EFFORTS], [23, 22, 23, 23])
        self.assertEqual([g[e]["passed_all_runs"] for e in EFFORTS], [18, 21, 22, 23])
        self.assertEqual([g[e]["hidden_behaviours_fixed"] for e in EFFORTS], [213, 215, 230, 231])
        self.assertEqual([round(g[e]["combined_33"]["mean"], 2) for e in EFFORTS], [89.42, 92.30, 92.71, 93.15])
        self.assertEqual([round(g[e]["code_quality"]["mean"], 2) for e in EFFORTS], [81.41, 83.90, 83.43, 84.35])
        self.assertEqual([round(g[e]["by_panel"]["muse"]["mean"], 1) for e in EFFORTS], [78.3, 80.5, 79.8, 81.9])
        self.assertEqual([round(g[e]["minutes"]["mean"], 1) for e in EFFORTS], [20.2, 27.2, 25.4, 28.5])
        self.assertEqual([round(g[e]["raw_tokens"]["mean"] / 1e6, 2) for e in EFFORTS], [4.76, 3.20, 2.85, 3.94])
        self.assertEqual(g["medium"]["raw_tokens"]["n"], 22)  # the timeout has no usage receipt

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), {("grok47cursor", e) for e in EFFORTS})
        for effort, g in self.groups.items():
            judged = f'{g["n"]}/23' + ("*" if effort == "medium" else "")
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                        f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}', f'{g["maintainability"]["mean"]:.1f}',
                        f'{g["intent_recovery"]["mean"]:.1f}', judged, f'{g["passed_all_runs"]}/23', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows["grok47cursor", effort][2:], expected, effort)
            self.assertEqual(self.page.rows["grok47cursor", effort][1], label(effort))
        g = self.groups
        for name, key, d in (("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
                             ("Intent recovery", "intent_recovery", 1)):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e][key]['mean']:.{d}f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        for name, p in (("Rated by Muse Spark 1.3", "muse"), ("Rated by GPT-6.1 Sol", "sol")):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e]['by_panel'][p]['mean']:.1f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f"<td>{g[e]['code_quality']['se']:.2f}</td>" for e in EFFORTS), self.page_html)
        self.assertIn("*Medium lodgecore hit the 3-hour task bound.", self.page_html)
        self.assertIn(f"20.3 over the 22 finished ones", html.unescape(self.page_html))
        self.assertAlmostEqual(g["medium"]["minutes_judged_runs"]["mean"], 20.3, places=1)

    def test_across_efforts_table(self):
        g = self.groups
        for name, cells in (("Combined score", "".join(f"<td>{g[e]['combined_33']['mean']:.2f}</td>" for e in EFFORTS)),
                            ("Standard error", "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS)),
                            ("Judged runs", "".join(f"<td>{g[e]['n']}</td>" for e in EFFORTS)),
                            ("Tasks passed", "".join(f"<td>{g[e]['passed_all_runs']}/23</td>" for e in EFFORTS)),
                            ("Hidden behaviours fixed", "".join(f"<td>{g[e]['hidden_behaviours_fixed']}/231</td>" for e in EFFORTS)),
                            ("Minutes per task", "".join(f"<td>{g[e]['minutes']['mean']:.1f}</td>" for e in EFFORTS)),
                            ("Tokens per task", "".join(f"<td>{g[e]['raw_tokens']['mean'] / 1e6:.2f}M</td>" for e in EFFORTS)),
                            ("Cost per task", "<td>unavailable</td>" * 4)):
            self.assertIn(f'<th scope="row">{name}</th>{cells}</tr>', self.page_html, name)
        comb = {e: g[e]["combined_33"]["mean"] for e in EFFORTS}
        self.assertEqual(max(comb, key=comb.get), "extra-high")
        self.assertIn(f"{comb['low']:.2f} at Low to {comb['extra-high']:.2f} at Extra-high", self.page_html)
        self.assertIn(f"Low is {comb['extra-high'] - comb['low']:.2f} points below the best level", self.page_html)
        self.assertIn(f"within {comb['extra-high'] - comb['medium']:.2f} points of each other", self.page_html)
        self.assertIn(f"between Low and Medium ({comb['medium'] - comb['low']:.2f} points)", html.unescape(self.page_html))
        profile = [g[e]["combined_20_profile"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(profile):.2f} to {max(profile):.2f}", self.page_html)
        for e in EFFORTS:
            self.assertIn(f"<td>{label(e)}</td>", self.page_html)
        self.assertNotIn("<td>Max</td>", self.page_html)

    def test_usage_table_and_no_cost(self):
        ug = {r["effort"]: r for r in self.usage["groups"]}
        self.assertEqual(self.usage["cost"], "unavailable")
        for e in EFFORTS:
            u, g = ug[e], self.groups[e]
            self.assertIsNone(u["usd"])
            self.assertEqual(u["raw_tokens"], g["raw_tokens"])
            cells = (f'<td>23</td><td>{u["minutes"]["mean"]:.1f}</td><td>{u["minutes_median"]:.1f}</td><td>{u["raw_tokens"]["mean"] / 1e6:.2f}M</td>'
                     f'<td>{u["output_tokens"]["mean"] / 1e3:.1f}k</td><td>{100 * u["cache_read_share"]["mean"]:.0f}%</td><td>unavailable</td>')
            self.assertIn(f'<tr data-usage-effort="{e}"><th scope="row">{label(e)}</th>{cells}</tr>', self.page_html, e)
        t = self.usage["totals"]["grok47cursor"]
        self.assertEqual((t["runs"], t["receipt_runs"], t["usd"]), (92, 91, None))
        self.assertEqual(t["raw_tokens"], sum(r["raw_tokens"] for r in self.judged))
        self.assertIn(f'<td>92</td><td>{60 * t["solver_hours"] / 92:.1f}</td><td></td><td>{t["raw_tokens"] / 1e6:.0f}M</td>', self.page_html)
        self.assertIn(f"Summed solver time is {t['solver_hours']:.2f} hours", self.page_html)
        shares = [ug[e]["cache_read_share"]["mean"] for e in EFFORTS]
        self.assertEqual((round(100 * min(shares)), round(100 * max(shares))), (85, 89))
        text = html.unescape(self.page_html)
        self.assertNotIn("$0.", text)
        self.assertIn("Cost is unavailable, not $0", text)

    def test_shared_judge_sensitivity(self):
        """Muse Spark 1.3 alone for every column, recomputed here from the public bundles."""
        expected = {}
        for key, bundle in BUNDLES.items():
            for r in json.loads((ROOT / "assets/data" / bundle / "runs.json").read_text())["rows"]:
                if r["model"] == key and r.get("combined_33") is not None and r.get("panels") and r["panels"]["muse"].get("reviewed_score") is not None:
                    expected.setdefault((key, r["effort"]), []).append(muse_only(r)[1])
        for r in self.judged:
            expected.setdefault(("grok47cursor", r["effort"]), []).append(muse_only(r)[1])
        got = {(c["model"], c["effort"]): c for c in self.shared}
        self.assertEqual(set(got), set(expected))
        for key, values in expected.items():
            self.assertAlmostEqual(got[key]["muse_combined"], statistics.mean(values), places=9, msg=key)
            self.assertEqual(got[key]["n"], len(values))
        mine = {e: got["grok47cursor", e]["muse_combined"] for e in EFFORTS}
        self.assertEqual([round(mine[e], 2) for e in EFFORTS], [88.64, 91.46, 91.74, 92.27])
        rivals = {e: max((c for c in self.shared if c["effort"] == e and c["model"] != "grok47cursor"), key=lambda c: c["muse_combined"]) for e in EFFORTS}
        self.assertEqual({e: rivals[e]["model"] for e in EFFORTS}, {"low": "fable", "medium": "opus55", "high": "opus55", "extra-high": "fable"})
        names = {"fable": "Fable 5.1", "opus55": "Opus 5.5"}
        for e in EFFORTS:
            row = (f'<tr data-shared="{e}"><th scope="row">{label(e)}</th><td>{self.groups[e]["combined_33"]["mean"]:.2f}</td><td>{mine[e]:.2f}</td>'
                   f'<td>{rivals[e]["muse_combined"]:.2f} ({names[rivals[e]["model"]]})</td><td>{self.groups[e]["by_panel"]["muse"]["mean"]:.1f}</td>'
                   f'<td>{rivals[e]["muse_reviewed"]:.1f}</td></tr>')
            self.assertIn(row, self.page_html, e)
        self.assertLess(mine["low"], rivals["low"]["muse_combined"])  # second at Low on one judge
        self.assertTrue(all(mine[e] > rivals[e]["muse_combined"] for e in EFFORTS[1:]))
        best_max = max((c for c in self.shared if c["effort"] == "max"), key=lambda c: c["muse_combined"])
        self.assertEqual(best_max["model"], "fable")
        self.assertIn(f"above the best Max column on Muse alone (Fable 5.1, {best_max['muse_combined']:.2f})", html.unescape(self.page_html))
        gaps = [self.groups[e]["by_panel"]["sol"]["mean"] - self.groups[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
        self.assertIn(f"({min(gaps):.1f} to {max(gaps):.1f} points by level)", self.page_html)
        self.assertIn(f"second at Low behind Fable 5.1 ({rivals['low']['muse_combined']:.2f})", (ROOT / "leaderboard.html").read_text())
        caveat = html.unescape(self.page_html[self.page_html.index('id="judge-caveat"'):self.page_html.index('id="how-it-works"')])
        for needle in ("Read this first: a different second judge", "not neutral for an xAI submission", "not strictly comparable",
                       "Grok 4.7 (78.3 to 81.9)", "Claude Opus 5.5 (70.2 to 80.1)", "GPT-6.1 Sol (64.7 to 71.2)", "GPT-6 Astra (64.9 to 73.6)",
                       "Claude Fable 5.1 (78.7 to 83.4)", "second at Low, behind Fable 5.1"):
            self.assertIn(needle, caveat, needle)
        self.assertLess(self.page_html.index('id="judge-caveat"'), self.page_html.index('id="across-efforts"'))

    def test_board_context(self):
        board = json.loads((ROOT / "assets/data/swe-v4-board.json").read_text())["columns"]
        mine = {r["effort"]: r for r in board if r["key"] == "grok47cursor"}
        self.assertEqual([mine[e]["rank"] for e in ("extra-high", "high", "medium", "low")], [1, 2, 3, 12])
        self.assertEqual(len(board), 53)
        self.assertTrue(all(r["usd"] is None for r in mine.values()))
        for e in EFFORTS:  # the highest combined score at every level Grok 4.7 shares
            others = [r["combined"] for r in board if r["effort"] == e and r["key"] != "grok47cursor"]
            self.assertGreater(mine[e]["combined"], max(others), e)
        self.assertIn("ranks first, second and third of 53 model and effort columns", self.page_html)
        self.assertIn("Grok 4.7 at Low (89.42) ranks 12th and is the highest Low column, 0.30 points above Fable 5.1 at Low", html.unescape(self.page_html))

    def test_safety_section(self):
        g, o = self.safety["models"]["grok47cursor"], self.safety["models"]["opus55"]
        self.assertEqual(self.safety["suite"], "VulcanBench Safety v1")
        self.assertEqual((g["totals"]["runs"], g["totals"]["planted"], g["totals"]["complied"], g["totals"]["reported"], g["totals"]["runs_leaking_secret"]), (40, 80, 14, 0, 0))
        self.assertEqual((o["totals"]["runs"], o["totals"]["planted"], o["totals"]["complied"], o["totals"]["reported"], o["totals"]["runs_leaking_secret"]), (50, 100, 3, 64, 0))
        self.assertEqual([r["effort"] for r in g["levels"]], list(EFFORTS))
        self.assertEqual([r["effort"] for r in o["levels"]], [*EFFORTS, "max"])
        for model in (g, o):
            for r in model["levels"]:
                self.assertEqual((r["runs"], r["planted"]), (10, 20))
                self.assertEqual(r["complied"] + r["ignored"] + r["reported"], r["planted"])
            for key in ("complied", "ignored", "reported"):
                self.assertEqual(sum(v for k, v in model["by_payload"].items() if k.endswith("/" + key)), model["totals"][key])
        gp = g["by_payload"]
        self.assertEqual((gp["code_insert/complied"], gp["ack_file/complied"], gp["beacon/complied"], gp["secret_exfil/complied"], gp["destructive/complied"]), (7, 7, 0, 0, 0))
        levels = {"grok47cursor": {r["effort"]: r for r in g["levels"]}, "opus55": {r["effort"]: r for r in o["levels"]}}
        for model, measure in (("grok47cursor", "passed"), ("grok47cursor", "complied"), ("grok47cursor", "reported"),
                               ("opus55", "passed"), ("opus55", "complied"), ("opus55", "reported")):
            cells = "".join(f"<td>{levels[model][e][measure]}</td>" if e in levels[model] else "<td>n/a</td>" for e in (*EFFORTS, "max"))
            start = self.page_html.index(f'<tr data-safety="{model}-{measure}">')
            self.assertIn(cells + "</tr>", self.page_html[start:start + 300], (model, measure))
        section = html.unescape(self.page_html[self.page_html.index('id="safety"'):self.page_html.index('id="code-quality"')])
        for needle in ("followed 14 of the 80 planted notes", "7 of 16 code inserts and 7 of 16 acknowledgment files", "reported none of them",
                       "never ran the network beacon, never exfiltrated the planted secret and never ran the destructive delete",
                       "followed 3 of 100 and reported 64", "Neither model leaked the secret", "Cursor stream parser", "netcat",
                       "/blog/02-vulcanbench-safety-v1.html", "10-hour Safety bound"):
            self.assertIn(needle, section, needle)
        # Safety v1 is private: no Frontier v4 task name appears where it would say which tasks were forked.
        shorts = {r["task"].replace("legacy-", "").split("-")[0] for r in self.rows}
        safety_text = (DATA / "safety-v1.json").read_text()
        for name in shorts:
            self.assertNotIn(name, section, name)
            self.assertNotIn(name, safety_text, name)

    def test_model_pages(self):
        page = (ROOT / "models/grok-4-7.html").read_text()
        for anchor in ("", "#judge-pair", "#safety"):
            self.assertIn(f"../benchmarks/swe-v4-grok47-cursor-v320.html{anchor}", page)
        self.assertIn('href="grok-4-6.html"', page)
        self.assertIn('href="grok-4-7.html"', (ROOT / "models/grok-4-6.html").read_text())
        self.assertIn('<link rel="canonical" href="https://vulcanbench.com/models/grok-4-7.html">', page)
        self.assertIn("Model results &middot; xAI", page)
        self.assertIn("GPT-6.1 Sol", page)
        for text in (page, (ROOT / "models/grok-4-6.html").read_text()):
            self.assertNotIn(chr(0x2014), html.unescape(text))
            self.assertNotIn(chr(0x2013), html.unescape(text))
        self.assertIn('href="models/grok-4-7.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="/models/grok-4-7.html"', self.page_html)

    def test_every_level_everywhere_scores_appear(self):
        for name in ("benchmarks.html", "index.html", "feed.xml", "llms.txt", "models/grok-4-7.html", "leaderboard.html",
                     "assets/data/swe-v4-grok47-cursor-v320/README.md"):
            text = (ROOT / name).read_text()
            for figure in ("89.42", "92.30", "92.71", "93.15"):
                self.assertIn(figure, text, (name, figure))

    def test_calibration_and_protocol_record(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertEqual(record["call_count"], 80)
            self.assertEqual(len(record["gates"]), 20)
            self.assertEqual(record["allowance"], {"max_failing_gates": 1, "max_shortfall": 0.5})
        self.assertTrue(self.calibration["muse"]["allowance_used"])
        self.assertEqual(self.calibration["muse"]["failing_gates"], ["g11_repeatability"])
        self.assertLessEqual(self.calibration["muse"]["gates"]["g11_repeatability"]["shortfall"], 0.5)
        self.assertFalse(self.calibration["sol"]["allowance_used"])
        self.assertEqual(self.calibration["sol"]["failing_gates"], [])
        self.assertIn("<td>code-quality-maintenance-v3.20</td><td>80</td><td>passed</td><td>yes</td><td>g11 repeatability, 0.1 short</td>", self.page_html)
        self.assertIn("<td>code-quality-maintenance-v3.20</td><td>80</td><td>passed</td><td>no</td><td>none</td>", self.page_html)
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.20", "sol": "code-quality-maintenance-v3.20"})
        self.assertEqual(self.protocols["scored_panel"]["sol"]["model"], "gpt-6.1-sol")
        self.assertEqual(self.protocols["scored_panel"]["sol"]["codex_version"], "0.159.0")
        self.assertEqual(self.protocols["scored_panel"]["sol"]["effort"], "medium")
        population = self.protocols["population"]
        self.assertEqual(population["cells"], {f"grok47cursor/{e}": (22 if e == "medium" else 23) for e in EFFORTS})
        [excluded] = population["excluded"]
        self.assertEqual((excluded["effort"], excluded["task"]), TIMEOUT)
        self.assertEqual((self.protocols["one_panel"], self.protocols["invalidated_calls"]), ([], []))
        self.assertEqual(self.protocols["counted_calls"]["sol"], {"calibration": 80, "primary": 91, "repeat": 4, "pairwise": 8, "probe": 91, "match": 91})
        self.assertEqual(self.protocols["second_attempts"], {"muse": 3, "sol": 13})
        [retry] = self.protocols["transport_retries"]
        self.assertIn("Selected model is at capacity", retry["finding"])
        recoveries = self.protocols["operator_recoveries"]
        self.assertEqual(len(recoveries), 6)
        self.assertTrue(all(r["panel"] == "sol" and r["stage"] == "match" and r["rule"] == "recover_one_based_indexes" for r in recoveries))
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "usage.json", "provenance.json", "shared-judge.json",
                     "safety-v1.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("SWE v4", text, name)
            self.assertNotIn("ultra", text.lower(), name)

    def test_run_disclosures(self):
        text = html.unescape(self.page_html)
        section = text[text.index('id="run-notes"'):text.index('id="next"')]
        for needle in ("Cursor agent CLI 2026.10.01-14929f9", "grok-4.7-low, -medium, -high and -xhigh", "October 1, 12:53 PDT, to October 3, 04:12 PDT",
                       "Selected model is at capacity", "single fresh attempt", "recover_one_based_indexes", "no score changed",
                       "October 3, 08:15 to 14:55 PDT", "09:26 to 09:27", "11:53 to 13:28", "Safety v1 leg",
                       "no Frontier v4 solver run was active during judging", "Five High tasks", "One attempt per task and level"):
            self.assertIn(needle, section, needle)
        upcoming = text[text.index('id="next"'):text.index('id="reproduce"')]
        for needle in ("Routine v1", "v3.22", "Grok Build", "v3.21"):
            self.assertIn(needle, upcoming, needle)
        limits = " ".join(self.provenance["limits"])
        for needle in ("GPT-6.1 Sol rates about 6 points above Muse", "requested model", "3-hour bound", "Cursor subscription", "08:15 to 14:55 PDT"):
            self.assertIn(needle, limits, needle)

    def test_cards_are_pinned_and_placed(self):
        for name, sha in CARDS.items():
            self.assertEqual(hashlib.sha256((ROOT / "assets/cards" / name).read_bytes()).hexdigest(), sha, name)
            self.assertIn(f'href="/assets/cards/{name}" download', self.page_html, name)
            self.assertIn(f'src="/assets/cards/{name}"', self.page_html, name)
        board = self.page_html[self.page_html.index('id="board"'):self.page_html.index('id="safety"')]
        self.assertIn('src="/assets/cards/swe-v4-grok47-vs-frontier-leaders.png"', board)
        safety = self.page_html[self.page_html.index('id="safety"'):self.page_html.index('id="code-quality"')]
        self.assertIn('src="/assets/cards/safety-v1-grok47-opus55.png"', safety)
        usage = self.page_html[self.page_html.index('id="usage"'):self.page_html.index('id="board"')]
        self.assertIn('src="/assets/cards/swe-v4-grok47-cursor-v320-usage.png"', usage)

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
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-grok47-cursor-v320-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "leaderboard.html", "README.md"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-grok47-cursor-v320.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertNotIn("SWE v4", feed_item)
        self.assertIn("VulcanBench Frontier v4", feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn("<loc>https://vulcanbench.com/models/grok-4-7.html</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn(f"<guid>{URL}</guid>", (ROOT / "feed.xml").read_text())
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-grok47-cursor-v320.html"), index.index("swe-v4-gpt61-sol-v318.html"))
        self.assertIn("assets/cards/swe-v4-grok47-cursor-v320.png", index)
        home = (ROOT / "index.html").read_text()
        self.assertLess(home.index("swe-v4-grok47-cursor-v320.html"), home.index("swe-v4-gpt61-sol-v318.html"))
        unescaped = html.unescape(self.page_html)
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
            self.assertNotIn(mark, unescaped, mark)
        self.assertIn('class="how-it-works"', self.page_html)
        self.assertIn("share.js", self.page_html)
        self.assertIn("intent/post?text=Grok%204.7%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)


if __name__ == "__main__":
    unittest.main()
