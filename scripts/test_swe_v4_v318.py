"""Stdlib checks for the v3.18 GPT-6.1 Sol bundle, its report page, its three cards and the site links to it."""

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
DATA = ROOT / "assets/data/swe-v4-gpt61-sol-v318"
SOL6 = ROOT / "assets/data/swe-v4-gpt6-sol-v317"
SOL56 = ROOT / "assets/data/swe-v4-sol-v37"
PAGE = ROOT / "benchmarks/swe-v4-gpt61-sol-v318.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-gpt61-sol-v318.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
ONE_PANEL = [("medium", "legacy-paddockcore-binary-parity")]
# Copied byte for byte from the harness (docs/results/swe-v4-gpt61-sol-2026-09 and swe-v4-gpt6-vs-gpt56-2026-09).
CARDS = {
    "swe-v4-gpt61-sol-v318.png": "679399afa0574aed0ce9e1f148499b5bbcc55eabfa50ceb87b62225946929576",
    "swe-v4-gpt61-sol-v318-economics.png": "3564f3b6f0f7ce0528bac19afcc85ae6fda301d8c8c53d461413f923633c803b",
    "swe-v4-sol-family-combined.png": "da186dea5e46af6fd3411b063fcf02f6d6f60051a016706fa776aeb65d756bf0",
}


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


def load(bundle, model):
    groups = {g["effort"]: g for g in json.loads((bundle / "groups.json").read_text()) if g["model"] == model}
    econ = {g["effort"]: g for g in json.loads((bundle / "economics.json").read_text())["groups"] if g["model"] == model}
    return groups, econ


class GPT61SolBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())
        cls.provenance = json.loads((DATA / "provenance.json").read_text())
        with (ROOT / "assets/data/swe-v4-gpt61-sol-v318-scores.csv").open(newline="") as source:
            cls.scores = {r["effort"]: r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def scored_mean(self, r, key):
        return statistics.mean(r["panels"][p][key] for p in r["scored_panels"])

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 115)
        self.assertEqual((self.runs["published"], self.runs["unpublished"], self.runs["one_panel"]), (115, 0, 1))
        self.assertTrue(all(r["judged_under"] == "code-quality-maintenance-v3.18" for r in self.rows))
        self.assertTrue(all(r["finished"] and r["duration_s"] < 10800 for r in self.rows))  # no timeouts
        self.assertTrue(all(r["solver_cli_version"] == "codex-cli 0.159.0" for r in self.rows))
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        one_panel = [r for r in self.rows if r["judged"] != "published"]
        self.assertEqual([(r["effort"], r["task"]) for r in one_panel], ONE_PANEL)
        [single] = one_panel
        self.assertTrue(single["judged"].startswith("published from Muse Spark 1.3 alone"))
        self.assertEqual(single["scored_panels"], ["muse"])
        self.assertFalse(single["panels"]["grok"]["scored"])
        for field in ("reviewed_score", "readability", "maintainability", "intent_recovery"):
            self.assertIsNone(single["panels"]["grok"][field], field)  # Grok's unused probe answer is not published
        self.assertAlmostEqual(single["code_quality"], 54.0043, places=4)
        self.assertEqual(single["functional"], 1.0)
        self.assertTrue(all(r["scored_panels"] == list(PANELS) for r in self.rows if r is not single))
        for r in self.rows:
            usage, rate = r["token_usage"], self.econ["rates_per_million"][r["model"]]
            cached = min(usage["cached_input_tokens"], usage["input_tokens"])
            priced = ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6
            self.assertAlmostEqual(r["estimated_usd"], priced, places=5, msg=r["run_id"])
            self.assertGreater(r["raw_tokens"], 0)
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            reviewed = self.scored_mean(r, "reviewed_score")
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            self.assertFalse(r["intent_recovery_redistributed"])  # every run passed at least one quirk family
            self.assertGreater(r["passed_quirk_families"], 0)
            intent = self.scored_mean(r, "intent_recovery")
            self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
            code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            for p in r["scored_panels"]:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"],
                                       (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
            self.assertLessEqual(r["hidden_behaviours_fixed"], r["hidden_behaviours"])
            self.assertEqual(r["functional"] == 1, r["hidden_behaviours_fixed"] == r["hidden_behaviours"], r["run_id"])
        self.assertFalse(any(r["solver_fallback"] for r in self.rows))
        self.assertEqual(sorted((r["effort"], r["task"]) for r in self.rows if r["evidence_rebuilt_from_index_diff"]),
                         [("low", "legacy-cellarcore-binary-parity"), ("low", "legacy-payrollcore-binary-parity"), ("medium", "legacy-lodgecore-binary-parity")])
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
            self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], places=3)
            self.assertAlmostEqual(float(c["code_quality"]), r["code_quality"], places=3)
            self.assertEqual(int(c["hidden_behaviours_fixed"]), r["hidden_behaviours_fixed"])
            self.assertEqual(c["scored_panels"], "+".join(r["scored_panels"]))
            if r["judged"] == "published":
                self.assertEqual(c["judged"], "published")
            else:
                self.assertEqual(c["judged"], "published, one panel")
                for column in ("grok_reviewed", "grok_intent_recovery"):
                    self.assertEqual(c[column], "", column)

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), set(EFFORTS))
        self.assertEqual(set(self.scores), set(EFFORTS))
        for effort, g in self.groups.items():
            rs = [r for r in self.rows if r["effort"] == effort]
            self.assertEqual((len(rs), g["runs"], g["n"]), (23, 23, 23))
            for field, values in (("combined_33", [r["combined_33"] for r in rs]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in rs]),
                                  ("code_quality", [r["code_quality"] for r in rs]),
                                  ("reviewed_score", [r["reviewed_score"] for r in rs]),
                                  ("intent_recovery", [r["intent_recovery"] for r in rs]),
                                  ("readability", [self.scored_mean(r, "readability") for r in rs]),
                                  ("maintainability", [self.scored_mean(r, "maintainability") for r in rs]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]),
                                  ("usd", [r["estimated_usd"] for r in rs]),
                                  ("raw_tokens", [r["raw_tokens"] for r in rs])):
                mean, se = mean_se(values)
                self.assertEqual(g[field]["n"], len(values), (effort, field))
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(effort, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(effort, field))
            for p in PANELS:
                values = [r["panels"][p]["reviewed_score"] for r in rs if r["panels"][p]["scored"]]
                self.assertEqual(g["by_panel"][p]["n"], len(values))
                self.assertAlmostEqual(g["by_panel"][p]["mean"], statistics.mean(values), places=9)
            self.assertEqual(g["passed_all_runs"], sum(r["functional"] == 1 for r in rs))
            self.assertEqual(g["hidden_behaviours_fixed"], sum(r["hidden_behaviours_fixed"] for r in rs))
            self.assertEqual(g["hidden_behaviours"], 231)
            row = self.scores[effort]
            self.assertEqual((int(row["n"]), int(row["runs"])), (23, 23))
            for column, field in (("combined_33", "combined_33"), ("combined_20_profile", "combined_20_profile"), ("code_quality", "code_quality"),
                                  ("readability", "readability"), ("maintainability", "maintainability"), ("intent_recovery", "intent_recovery"),
                                  ("mean_minutes", "minutes"), ("mean_usd", "usd")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(effort, column))
            self.assertEqual(int(row["passed_of_23"]), g["passed_all_runs"])
            self.assertEqual(int(row["hidden_behaviours_fixed_of_231"]), g["hidden_behaviours_fixed"])
        g = self.groups
        self.assertEqual([g[e]["by_panel"]["grok"]["n"] for e in EFFORTS], [23, 22, 23, 23, 23])
        self.assertEqual([g[e]["passed_all_runs"] for e in EFFORTS], [20, 22, 23, 23, 23])
        self.assertEqual([g[e]["hidden_behaviours_fixed"] for e in EFFORTS], [225, 228, 231, 231, 231])
        self.assertEqual([round(g[e]["combined_33"]["mean"], 2) for e in EFFORTS], [86.22, 86.44, 88.23, 88.78, 88.35])
        self.assertEqual([round(g[e]["code_quality"]["mean"], 2) for e in EFFORTS], [70.79, 70.25, 73.67, 74.99, 73.80])
        self.assertEqual([round(g[e]["minutes"]["mean"], 1) for e in EFFORTS], [6.9, 10.6, 10.2, 15.4, 14.5])
        self.assertEqual([g[e]["intent_recovery_redistributed_runs"] for e in EFFORTS], [0, 0, 0, 0, 0])
        self.assertNotIn("card_intent_recovery", g["medium"])
        self.assertEqual(round(g["medium"]["intent_recovery"]["mean"], 2), 78.59)

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), {("gpt61sol", e) for e in EFFORTS})
        for effort, g in self.groups.items():
            judged = "23/23" + ("*" if effort == "medium" else "")
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                        f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}', f'{g["maintainability"]["mean"]:.1f}',
                        f'{g["intent_recovery"]["mean"]:.1f}', judged, f'{g["passed_all_runs"]}/23', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows["gpt61sol", effort][2:], expected, effort)
            self.assertEqual(self.page.rows["gpt61sol", effort][1], label(effort))
        g = self.groups
        for name, key, d in (("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
                             ("Intent recovery", "intent_recovery", 1)):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e][key]['mean']:.{d}f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        for name, p in (("Rated by Muse Spark 1.3", "muse"), ("Rated by Grok 4.6", "grok")):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e]['by_panel'][p]['mean']:.1f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f"<td>{g[e]['code_quality']['se']:.2f}</td>" for e in EFFORTS), self.page_html)
        self.assertIn("*Medium paddockcore is scored from Muse Spark 1.3 alone.", self.page_html)
        self.assertIn("<code>self.standing[pony] += 2</code>", self.page_html)
        self.assertIn("(Code quality 54.00, combined 80.76)", self.page_html)

    def test_across_efforts_table(self):
        g = self.groups
        eg = {r["effort"]: r for r in self.econ["groups"]}

        def cells(key, digits):
            return "".join(f"<td>{g[e][key]['mean']:.{digits}f}</td>" for e in EFFORTS)

        for name, html_cells in (("Combined score", cells("combined_33", 2)),
                                 ("Standard error", "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS)),
                                 ("Judged runs", "".join(f"<td>{g[e]['n']}</td>" for e in EFFORTS)),
                                 ("Tasks passed", "".join(f"<td>{g[e]['passed_all_runs']}/23</td>" for e in EFFORTS)),
                                 ("Hidden behaviours fixed", "".join(f"<td>{g[e]['hidden_behaviours_fixed']}/231</td>" for e in EFFORTS)),
                                 ("Code quality", cells("code_quality", 2)), ("Human readability", cells("readability", 1)),
                                 ("Minutes per task", cells("minutes", 1)),
                                 ("API-equivalent $ per task", "".join(f"<td>${eg[e]['usd']['mean']:.2f}</td>" for e in EFFORTS))):
            self.assertIn(f'<th scope="row">{name}</th>{html_cells}</tr>', self.page_html, name)
        comb = {e: g[e]["combined_33"]["mean"] for e in EFFORTS}
        best = max(comb, key=comb.get)
        self.assertEqual(best, "extra-high")
        self.assertIn(f"{comb['low']:.2f} at Low to {comb[best]:.2f} at Extra-high", self.page_html)
        self.assertIn(f"Low is {comb[best] - comb['low']:.2f} points below the best level", self.page_html)
        self.assertIn(f"within {max(comb[e] for e in ('high', 'extra-high', 'max')) - min(comb[e] for e in ('high', 'extra-high', 'max')):.2f} points of each other",
                      self.page_html)
        cq = [g[e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(cq):.2f} to {max(cq):.2f}", self.page_html)
        minutes = [g[e]["minutes"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(minutes):.1f} to {max(minutes):.1f} min", self.page_html)
        profile = [g[e]["combined_20_profile"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(profile):.2f} to {max(profile):.2f}", self.page_html)
        # Every effort level appears; the page never leads with Max alone.
        for e in EFFORTS:
            self.assertIn(f"<td>{label(e)}</td>", self.page_html)

    def test_ceiling_section(self):
        text = html.unescape(self.page_html)
        section = text[text.index('id="ceiling"'):text.index('id="cost"')]
        for needle in ("no longer separates GPT-6.1 Sol's top levels on correctness", "all 231 tested behaviours", "integrity audit is clean on all 115 runs",
                       "knowledge cutoff of April 30, 2026", "August 2026", "saturation-pruning rule", "planned follow-up"):
            self.assertIn(needle, section, needle)
        g = self.groups
        eg = {r["effort"]: r for r in self.econ["groups"]}
        self.assertIn(f"Extra-high scores {g['extra-high']['combined_33']['mean'] - g['high']['combined_33']['mean']:.2f} points above High", section)
        self.assertIn(f"costs {round(100 * (eg['extra-high']['usd']['mean'] / eg['high']['usd']['mean'] - 1))}% more per task", section)
        self.assertIn(f"Max is {g['extra-high']['combined_33']['mean'] - g['max']['combined_33']['mean']:.2f} points below Extra-high at "
                      f"{round(100 * (eg['max']['usd']['mean'] / eg['extra-high']['usd']['mean'] - 1))}% more", section)

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
        t = self.econ["totals"]["gpt61sol"]
        self.assertAlmostEqual(t["usd"], sum(r["estimated_usd"] for r in self.rows), places=6)
        self.assertEqual(t["raw_tokens"], sum(r["raw_tokens"] for r in self.rows))
        self.assertEqual(t["runs"], 115)
        self.assertEqual((f'{t["usd"]:.2f}', f'{t["usd"] / 115:.2f}'), ("44.33", "0.39"))
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>115</td><td>${t["usd"] / 115:.2f}</td><td>${t["usd"]:,.2f}</td>'
                      f'<td>{t["raw_tokens"] / 1e6:,.0f}M</td><td>{t["solver_hours"]:.1f} h</td>', self.page_html)
        self.assertEqual(self.econ["rates_per_million"], {"gpt61sol": {"input": 2.0, "cached_input": 0.1, "output": 10.0}})
        self.assertEqual(self.econ["pricing_verified"], "2026-09-29")
        self.assertIn("$2.00 input, $0.10 cached input and $10.00 output per million tokens", self.page_html)
        self.assertIn("no long-context premium applies", self.page_html)
        self.assertIn(f"about {t['raw_tokens'] / 115 / 1e6:.1f}M raw tokens per task", self.page_html)

    def test_three_generations_of_sol(self):
        g = self.groups
        eg = {r["effort"]: r for r in self.econ["groups"]}
        s6, e6 = load(SOL6, "gpt6sol")
        s56, e56 = load(SOL56, "sol")
        rows = {}
        for key, groups, econ in (("gpt61sol", g, eg), ("gpt6sol", s6, e6), ("sol", s56, e56)):
            rows[f"combined-{key}"] = "".join(f"<td>{groups[e]['combined_33']['mean']:.2f}</td>" for e in EFFORTS)
            rows[f"passed-{key}"] = "".join(f"<td>{groups[e]['passed_all_runs']}/23</td>" for e in EFFORTS)
            rows[f"cq-{key}"] = "".join(f"<td>{groups[e]['code_quality']['mean']:.2f}</td>" for e in EFFORTS)
            rows[f"usd-{key}"] = "".join(f"<td>${econ[e]['usd']['mean']:.2f}</td>" for e in EFFORTS)
            rows[f"minutes-{key}"] = "".join(f"<td>{econ[e]['minutes']['mean']:.1f}</td>" for e in EFFORTS)
        for key, cells in rows.items():
            start = self.page_html.index(f'<tr data-compare="{key}">')
            self.assertIn(cells + "</tr>", self.page_html[start:start + 400], key)
        # The table matches the harness card's own table (sol-family-combined-efforts.csv), checked at export.
        for other, oe in ((s6, e6), (s56, e56)):
            for e in EFFORTS:
                self.assertGreater(g[e]["combined_33"]["mean"], other[e]["combined_33"]["mean"], e)
                self.assertGreater(g[e]["passed_all_runs"], other[e]["passed_all_runs"], e)
                self.assertLess(eg[e]["usd"]["mean"], oe[e]["usd"]["mean"], e)
                self.assertGreater(g[e]["code_quality"]["mean"], other[e]["code_quality"]["mean"], e)
        self.assertEqual([round(s6[e]["combined_33"]["mean"], 2) for e in EFFORTS], [67.62, 80.60, 82.83, 85.94, 86.82])
        self.assertEqual([round(s56[e]["combined_33"]["mean"], 2) for e in EFFORTS], [69.05, 82.56, 85.76, 86.47, 87.18])
        lead6 = [g[e]["combined_33"]["mean"] - s6[e]["combined_33"]["mean"] for e in EFFORTS]
        lead56 = [g[e]["combined_33"]["mean"] - s56[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertIn(f"largest at Low ({lead6[0]:.2f} and {lead56[0]:.2f} points) and smallest at Max ({lead6[4]:.2f} and {lead56[4]:.2f})", self.page_html)
        frac6 = [eg[e]["usd"]["mean"] / e6[e]["usd"]["mean"] for e in EFFORTS]
        frac56 = [eg[e]["usd"]["mean"] / e56[e]["usd"]["mean"] for e in EFFORTS]
        self.assertIn(f"{round(100 * min(frac6))}% to {round(100 * max(frac6))}% of GPT-6 Sol's price per task and "
                      f"{round(100 * min(frac56))}% to {round(100 * max(frac56))}% of GPT-5.6 Sol's", self.page_html)
        slower = [e for e in EFFORTS if eg[e]["minutes"]["mean"] > e56[e]["minutes"]["mean"]]
        self.assertEqual(slower, ["extra-high", "max"])
        self.assertTrue(all(eg[e]["minutes"]["mean"] < e6[e]["minutes"]["mean"] for e in EFFORTS))

    def test_board_context(self):
        # The page describes the board as published on October 1, 2026: columns added later (Grok 4.7) are set aside and ranks recounted.
        later = {"grok47cursor"}
        board = [dict(r) for r in json.loads((ROOT / "assets/data/swe-v4-board.json").read_text())["columns"] if r["key"] not in later]
        for rank, r in enumerate(board, 1):
            r["rank"] = rank
        mine = {r["effort"]: r for r in board if r["key"] == "gpt61sol"}
        self.assertEqual((mine["extra-high"]["rank"], mine["max"]["rank"], mine["high"]["rank"], len(board)), (13, 14, 15, 49))
        above = [r for r in board if r["rank"] < 13]
        self.assertEqual({r["key"] for r in above}, {"fable", "opus55", "astra", "terra"})
        self.assertEqual(sorted(r["effort"] for r in above if r["key"] == "opus55"), ["extra-high", "high", "max", "medium"])
        leaders = {(r["key"], r["effort"]): r for r in board}
        best = mine["extra-high"]["combined"]
        for key, effort in (("fable", "max"), ("opus55", "high"), ("astra", "max")):
            self.assertIn(f"{leaders[key, effort]['combined'] - best:.2f}", self.page_html)
        top = [r for r in board if r["combined"] >= 88]
        self.assertEqual(len(top), 16)
        self.assertEqual(sorted(top, key=lambda r: r["usd"])[:3], sorted([mine["high"], mine["extra-high"], mine["max"]], key=lambda r: r["usd"]))
        others = [r["usd"] for r in top if r["key"] != "gpt61sol"]
        self.assertIn(f"${min(others):.2f} to ${max(others):.2f} for the rest", self.page_html)

    def test_model_pages(self):
        page = (ROOT / "models/gpt-6-1-sol.html").read_text()
        self.assertIn("../benchmarks/swe-v4-gpt61-sol-v318.html", page)
        self.assertIn("../benchmarks/swe-v4-gpt61-sol-v318.html#cost", page)
        self.assertIn("../benchmarks/swe-v4-gpt61-sol-v318.html#sol-family", page)
        self.assertIn('href="gpt-6-sol.html"', page)
        self.assertIn('href="gpt-5-6-sol.html"', page)
        self.assertIn('href="gpt-6-1-sol.html"', (ROOT / "models/gpt-6-sol.html").read_text())
        self.assertIn('href="gpt-6-1-sol.html"', (ROOT / "models/gpt-5-6-sol.html").read_text())
        self.assertIn('<link rel="canonical" href="https://vulcanbench.com/models/gpt-6-1-sol.html">', page)
        g = self.groups
        for e in EFFORTS:
            self.assertIn(f"{g[e]['combined_33']['mean']:.2f} at {label(e)}", page)
        self.assertIn(f'${self.econ["totals"]["gpt61sol"]["usd"]:,.2f}', page)
        for text in (page, (ROOT / "models/gpt-6-sol.html").read_text(), (ROOT / "models/gpt-5-6-sol.html").read_text()):
            self.assertNotIn(chr(0x2014), html.unescape(text))
            self.assertNotIn(chr(0x2013), html.unescape(text))
        self.assertIn('href="models/gpt-6-1-sol.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="/models/gpt-6-1-sol.html"', self.page_html)

    def test_every_level_everywhere_scores_appear(self):
        for name in ("benchmarks.html", "index.html", "feed.xml", "llms.txt", "models/gpt-6-1-sol.html", "leaderboard.html",
                     "assets/data/swe-v4-gpt61-sol-v318/README.md"):
            text = (ROOT / name).read_text()
            for figure in ("86.22", "86.44", "88.23", "88.78", "88.35"):
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
        self.assertEqual(self.page_html.count("<td>code-quality-maintenance-v3.18</td><td>80</td><td>passed</td><td>no</td><td>none</td>"), 2)
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.18", "grok": "code-quality-maintenance-v3.18"})
        self.assertEqual(self.protocols["repeats"], 5)
        population = self.protocols["population"]
        self.assertEqual((population["excluded"], population["missing"]), ([], []))
        self.assertEqual(population["cells"], {f"gpt61sol/{e}": 23 for e in EFFORTS})
        self.assertIn("v3.17", self.protocols["amends"])
        self.assertEqual(self.protocols["unpublished"], [])
        [finding] = self.protocols["one_panel"]
        self.assertEqual((finding["effort"], finding["task"], finding["invalid_panel"], finding["stage"], finding["rule"], finding["scored_from"]),
                         ("medium", "legacy-paddockcore-binary-parity", "grok", "primary", "invalidate_unrecoverable_primary", "muse"))
        self.assertAlmostEqual(finding["code_quality"], 54.0043, places=4)
        [recovery] = self.protocols["operator_recoveries"]
        self.assertEqual((recovery["effort"], recovery["task"], recovery["panel"], recovery["stage"], recovery["rule"], recovery["source_attempt"]),
                         ("high", "legacy-codeccore-binary-parity", "muse", "probe", "recover_escaped_excerpts", 2))
        self.assertEqual(len(self.protocols["evidence_rebuilds"]), 3)
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("SWE v4", text, name)
            self.assertNotIn("ultra", text.lower(), name)

    def test_run_disclosures(self):
        text = html.unescape(self.page_html)
        section = text[text.index('id="run-notes"'):text.index('id="reproduce"')]
        for needle in ("Codex CLI 0.159.0", "0.155.0, 0.157.0 and 0.158.0 refuse GPT-6.1 Sol on a ChatGPT account",
                       "September 29, 19:18 PDT, to September 30, 17:21 PDT", "first 11.5 hours, to September 30, 06:51 PDT",
                       "GPT-6 Sol's v3.17 Code quality judging", "wall-clock speed figures", "Three evidence rebuilds", "binary",
                       "JSON-escaping slip", "High codeccore", "Medium paddockcore", "v3.14 precedent",
                       "September 30, 20:58 PDT, to October 1, 06:01 PDT", "06:04 to 12:52 PDT", "One attempt per task and level"):
            self.assertIn(needle, section, needle)
        limits = " ".join(self.provenance["limits"])
        for needle in ("Muse Spark 1.3 alone", "recover_escaped_excerpts", "binary", "06:51 PDT"):
            self.assertIn(needle, limits, needle)

    def test_cards_are_pinned_and_placed(self):
        for name, sha in CARDS.items():
            self.assertEqual(hashlib.sha256((ROOT / "assets/cards" / name).read_bytes()).hexdigest(), sha, name)
            self.assertIn(f'href="/assets/cards/{name}" download', self.page_html, name)
            self.assertIn(f'src="/assets/cards/{name}"', self.page_html, name)
        family = self.page_html[self.page_html.index('id="sol-family"'):self.page_html.index('id="board"')]
        self.assertIn('src="/assets/cards/swe-v4-sol-family-combined.png"', family)
        self.assertNotIn("78.4", self.page_html)

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
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-gpt61-sol-v318-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "leaderboard.html", "README.md"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-gpt61-sol-v318.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertNotIn("SWE v4", feed_item)
        self.assertIn("VulcanBench Frontier v4", feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn("<loc>https://vulcanbench.com/models/gpt-6-1-sol.html</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn(f"<guid>{URL}</guid>", (ROOT / "feed.xml").read_text())
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-gpt61-sol-v318.html"), index.index("swe-v4-gpt6-sol-v317.html"))
        self.assertIn("assets/cards/swe-v4-gpt61-sol-v318.png", index)
        home = (ROOT / "index.html").read_text()
        self.assertLess(home.index("swe-v4-gpt61-sol-v318.html"), home.index("swe-v4-gpt6-sol-v317.html"))
        unescaped = html.unescape(self.page_html)
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
            self.assertNotIn(mark, unescaped, mark)
        self.assertIn('class="how-it-works"', self.page_html)
        self.assertIn("share.js", self.page_html)
        self.assertIn("intent/post?text=GPT-6.1%20Sol%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)



class LeadersCardTests(unittest.TestCase):
    """GPT-6.1 Sol beside Claude Opus 5.5 and GPT-6 Astra (harness make_frontier_leaders_card.py and _quality_card.py)."""

    CARDS = {
        "swe-v4-gpt61sol-opus55-astra.png": "173462b61f7c02352b1563c4cf22a2975c4010b882228c56de8db367af38a66a",
        "swe-v4-gpt61sol-opus55-astra-quality.png": "17f7dc916c07bac8c5a70a95d383d79ff86d3a2d748e5fe950870017d28e518e",
    }

    def test_leaders_cards_are_pinned_and_placed_in_the_board_section(self):
        page = (ROOT / "benchmarks/swe-v4-gpt61-sol-v318.html").read_text()
        section = page[page.index('id="board"') : page.index('id="code-quality"')]
        for name, digest in self.CARDS.items():
            self.assertEqual(hashlib.sha256((ROOT / "assets/cards" / name).read_bytes()).hexdigest(), digest)
            self.assertIn(f'src="/assets/cards/{name}"', section)
            self.assertIn(f'href="/assets/cards/{name}" download', page)


if __name__ == "__main__":
    unittest.main()
