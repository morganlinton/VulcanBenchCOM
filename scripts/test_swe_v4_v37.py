"""Stdlib checks for the v3.7 GPT-5.6 Sol bundle, its report page and the site links to it."""

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
DATA = ROOT / "assets/data/swe-v4-sol-v37"
PAGE = ROOT / "benchmarks/swe-v4-sol-v37.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-sol-v37.html"
LEVELS = {"sol": ("low", "medium", "high", "extra-high", "max")}
EFFORTS = LEVELS["sol"]
PANELS = ("muse", "grok")
NAMES = {"sol": "GPT-5.6 Sol"}
UNPUBLISHED = [("max", "legacy-codeccore-binary-parity")]
CARD_SHA256 = "6c6cba2bf5d1636082db71afb193fbf1d9b925f600f18089cceb49a4ff0e8b1b"
ECONOMICS_CARD_SHA256 = "c7156544e958ab1f3a52a063350d24732576ce0ffeaf44603f3bc7f4b6410c8a"


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


class SolBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.published = [r for r in cls.rows if r["judged"] == "published"]
        cls.groups = {(g["model"], g["effort"]): g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())
        cls.provenance = json.loads((DATA / "provenance.json").read_text())
        with (ROOT / "assets/data/swe-v4-sol-v37-scores.csv").open(newline="") as source:
            cls.scores = {("sol", r["effort"]): r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 115)
        self.assertEqual(self.runs["published"], 114)
        self.assertEqual(len(self.published), 114)
        self.assertTrue(all(r["judged_under"] == "code-quality-maintenance-v3.7" for r in self.rows))
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        unpublished = [r for r in self.rows if r["judged"] != "published"]
        self.assertEqual([(r["effort"], r["task"]) for r in unpublished], UNPUBLISHED)
        for r in unpublished:
            self.assertTrue(r["judged"].startswith("unpublished: "))
            self.assertIn("no recovery rule accepts", r["judged"])
            for field in ("reviewed_score", "intent_recovery", "intent_recovery_redistributed", "code_quality", "combined_33", "combined_20_profile", "panels"):
                self.assertIsNone(r[field], field)
            self.assertEqual(r["functional"], 1.0)  # the run passed its tests
            self.assertGreater(r["estimated_usd"], 0)
            self.assertGreater(r["duration_s"], 0)
        for r in self.published:
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            self.assertFalse(r["intent_recovery_redistributed"])
            self.assertGreater(r["passed_quirk_families"], 0)
            intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
            self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
            code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            for p in PANELS:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertGreater(r["panels"][p]["scored_quirks"], 0)
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"],
                                       (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
        for r in self.rows:
            self.assertFalse(r["solver_fallback"], r["run_id"])
            usage, rate = r["token_usage"], self.econ["rates_per_million"][r["model"]]
            cached = min(usage["cached_input_tokens"], usage["input_tokens"])
            priced = ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6
            self.assertAlmostEqual(r["estimated_usd"], priced, places=5, msg=r["run_id"])
            self.assertGreater(r["raw_tokens"], 0)
        self.assertEqual(len({(r["model"], r["effort"], r["task"]) for r in self.rows}), 115)

    def test_runs_csv_matches_runs_json(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = list(csv.DictReader(source))
        self.assertEqual(len(csv_rows), 115)
        by_run = {r["run_id"]: r for r in csv_rows}
        for r in self.rows:
            c = by_run[r["run_id"]]
            if r["judged"] == "published":
                self.assertEqual(c["judged"], "published")
                self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], places=3)
                self.assertAlmostEqual(float(c["code_quality"]), r["code_quality"], places=3)
                self.assertAlmostEqual(float(c["muse_intent_recovery"]), r["panels"]["muse"]["intent_recovery"], places=3)
            else:
                self.assertEqual(c["judged"], "unpublished")
                self.assertEqual(c["combined_33"], "")
                self.assertEqual(c["code_quality"], "")
                self.assertEqual(c["grok_intent_recovery"], "")
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], places=6)
            self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), {(m, e) for m in LEVELS for e in LEVELS[m]})
        self.assertEqual(set(self.scores), set(self.groups))
        for key, g in self.groups.items():
            rs = [r for r in self.rows if (r["model"], r["effort"]) == key]
            judged = [r for r in rs if r["judged"] == "published"]
            self.assertEqual(len(rs), 23)
            self.assertEqual(g["runs"], 23)
            self.assertEqual(g["n"], len(judged))
            self.assertEqual(g["n"], 22 if key == ("sol", "max") else 23)
            self.assertEqual(g["unpublished_runs"], 23 - g["n"])
            self.assertEqual(g["intent_recovery_redistributed_runs"], 0)
            for field, values in (("combined_33", [r["combined_33"] for r in judged]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in judged]),
                                  ("code_quality", [r["code_quality"] for r in judged]),
                                  ("reviewed_score", [r["reviewed_score"] for r in judged]),
                                  ("intent_recovery", [r["intent_recovery"] for r in judged]),
                                  ("readability", [statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in judged]),
                                  ("maintainability", [statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in judged]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]),
                                  ("usd", [r["estimated_usd"] for r in rs]),
                                  ("raw_tokens", [r["raw_tokens"] for r in rs])):
                mean, se = mean_se(values)
                self.assertEqual(g[field]["n"], len(values), (key, field))
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(key, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(key, field))
            for p in PANELS:
                self.assertAlmostEqual(g["by_panel"][p]["mean"], statistics.mean(r["panels"][p]["reviewed_score"] for r in judged), places=9)
            self.assertEqual(g["passed"], sum(r["functional"] == 1 for r in judged))
            self.assertEqual(g["passed_all_runs"], sum(r["functional"] == 1 for r in rs))
            self.assertEqual(g["solver_fallback_runs"], 0)
            row = self.scores[key]
            self.assertEqual(int(row["n"]), g["n"])
            self.assertEqual(int(row["runs"]), 23)
            for column, field in (("combined_33", "combined_33"), ("combined_20_profile", "combined_20_profile"), ("code_quality", "code_quality"),
                                  ("readability", "readability"), ("maintainability", "maintainability"), ("intent_recovery", "intent_recovery"),
                                  ("mean_minutes", "minutes")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(key, column))
            self.assertAlmostEqual(float(row["combined_33_se"]), g["combined_33"]["se"], places=4)
            self.assertAlmostEqual(float(row["code_quality_se"]), g["code_quality"]["se"], places=4)
            self.assertEqual(int(row["passed"]), g["passed"])
        self.assertEqual(self.groups["sol", "max"]["passed"], 21)
        self.assertEqual(self.groups["sol", "max"]["passed_all_runs"], 22)

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), set(self.groups))
        for key, g in self.groups.items():
            mark = "§" if g["unpublished_runs"] else ""
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                        f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}', f'{g["maintainability"]["mean"]:.1f}',
                        f'{g["intent_recovery"]["mean"]:.1f}', f'{g["passed"]}/{g["n"]}{mark}', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows[key][2:], expected, key)
            self.assertEqual(self.page.rows[key][1], label(key[1]))
        g = {e: self.groups["sol", e] for e in EFFORTS}
        for name, key, d in (("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
                             ("Intent recovery", "intent_recovery", 1)):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e][key]['mean']:.{d}f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        for name, p in (("Rated by Muse Spark 1.3", "muse"), ("Rated by Grok 4.6", "grok")):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e]['by_panel'][p]['mean']:.1f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f"<td>{g[e]['code_quality']['se']:.2f}</td>" for e in EFFORTS), self.page_html)

    def test_across_efforts_table(self):
        g = {e: self.groups["sol", e] for e in EFFORTS}
        eg = {r["effort"]: r for r in self.econ["groups"]}

        def cells(key, digits):
            return "".join(f"<td>{g[e][key]['mean']:.{digits}f}</td>" for e in EFFORTS)

        for name, html_cells in (("Combined score", cells("combined_33", 2)), ("Standard error", "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS)),
                                 ("Tasks passed", "".join(f"<td>{g[e]['passed']}/{g[e]['n']}</td>" for e in EFFORTS)),
                                 ("Code quality", cells("code_quality", 2)), ("Human readability", cells("readability", 1)),
                                 ("Minutes per task", cells("minutes", 1)), ("API-equivalent $ per task", "".join(f"<td>${eg[e]['usd']['mean']:.2f}</td>" for e in EFFORTS))):
            self.assertIn(f'<th scope="row">{name}</th>{html_cells}</tr>', self.page_html, name)
        comb = [g[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertEqual(comb, sorted(comb))
        self.assertIn(f'{min(comb):.2f} at Low to {max(comb):.2f} at Max', self.page_html)
        self.assertIn(f"{comb[1] - comb[0]:.1f} points from Low to Medium, then {comb[2] - comb[1]:.1f} to High, {comb[3] - comb[2]:.1f} to Extra-high and {comb[4] - comb[3]:.1f} to Max", self.page_html)
        cq = [g[e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertIn(f"{min(cq):.2f} to {max(cq):.2f}", self.page_html)
        self.assertIn(f"{min(g[e]['minutes']['mean'] for e in EFFORTS):.1f} to {max(g[e]['minutes']['mean'] for e in EFFORTS):.1f} min", self.page_html)

    def test_economics_table_and_card(self):
        eg = {r["effort"]: r for r in self.econ["groups"]}
        for e in EFFORTS:
            b = eg[e]
            rs = [r for r in self.rows if r["effort"] == e]
            self.assertEqual(b["n"], len(rs))
            self.assertEqual(b["n"], 23)
            self.assertAlmostEqual(b["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs), places=9)
            self.assertAlmostEqual(b["usd_total"], sum(r["estimated_usd"] for r in rs), places=6)
            self.assertAlmostEqual(b["raw_tokens"]["mean"], statistics.mean(r["raw_tokens"] for r in rs), places=6)
            self.assertAlmostEqual(b["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=6)
            cells = (f'<td>{b["n"]}</td><td>${b["usd"]["mean"]:.2f}</td><td>${b["usd_total"]:.2f}</td>'
                     f'<td>{b["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>{b["minutes"]["mean"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}</tr>', self.page_html, e)
        t = self.econ["totals"]["sol"]
        self.assertAlmostEqual(t["usd"], sum(r["estimated_usd"] for r in self.rows), places=6)
        self.assertEqual(t["raw_tokens"], sum(r["raw_tokens"] for r in self.rows))
        self.assertEqual(t["runs"], 115)
        self.assertIn(f'<tr data-econ-effort="sweep"><th scope="row">Full sweep</th><td>115</td><td>${t["usd"] / 115:.2f}</td><td>${t["usd"]:,.2f}</td>'
                      f'<td>{t["raw_tokens"] / 1e6:,.0f}M</td><td>{t["solver_hours"]:.1f} h</td>', self.page_html)
        self.assertEqual(self.econ["rates_per_million"], {"sol": {"input": 4.0, "cached_input": 0.4, "output": 20.0}})
        usd = [eg[e]["usd"]["mean"] for e in EFFORTS]
        index = (ROOT / "benchmarks.html").read_text()
        self.assertIn(f"${min(usd):.2f} to ${max(usd):.2f} per task", index)
        self.assertEqual(max(eg.values(), key=lambda r: r["usd"]["mean"])["effort"], "high")
        card = ROOT / "assets/cards/swe-v4-sol-v37-economics.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), ECONOMICS_CARD_SHA256)

    def test_model_pages(self):
        page = (ROOT / "models/gpt-5-6-sol.html").read_text()
        self.assertIn("../benchmarks/swe-v4-sol-v37.html", page)
        self.assertIn("../benchmarks/swe-v4-sol-v37.html#cost", page)
        self.assertLess(page.index("swe-v4-sol-v37.html"), page.index("08-kimi-k3.html"))
        combined = [self.groups["sol", e]["combined_33"]["mean"] for e in EFFORTS]
        quality = [self.groups["sol", e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertIn(f"combined score {min(combined):.2f} to {max(combined):.2f}", page)
        self.assertIn(f"Code quality {min(quality):.2f} to {max(quality):.2f}", page)
        eg = {r["effort"]: r for r in self.econ["groups"]}
        usd = [eg[e]["usd"]["mean"] for e in EFFORTS]
        self.assertIn(f"${min(usd):.2f} to ${max(usd):.2f} per task", page)
        self.assertIn(f'${self.econ["totals"]["sol"]["usd"]:,.2f}', page)
        self.assertNotIn(chr(0x2014), html.unescape(page))
        self.assertNotIn(chr(0x2013), html.unescape(page))
        self.assertIn('href="models/gpt-5-6-sol.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="/models/gpt-5-6-sol.html"', self.page_html)

    def test_comparative_claims(self):
        g = {e: self.groups["sol", e] for e in EFFORTS}
        comb = [g[e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertEqual(comb, sorted(comb))
        self.assertEqual([g[e]["combined_20_profile"]["mean"] for e in EFFORTS], sorted(g[e]["combined_20_profile"]["mean"] for e in EFFORTS))
        self.assertEqual([g[e]["passed"] for e in EFFORTS], [6, 12, 20, 21, 21])
        self.assertGreater(comb[1] - comb[0], 10)  # the Low to Medium step carries most of the range
        self.assertLess(comb[4] - comb[2], 1.5)  # High, Extra-high and Max sit within 1.5 points
        cq = [g[e]["code_quality"]["mean"] for e in EFFORTS]
        self.assertLess(max(cq) - min(cq), 3.5)
        for e in EFFORTS:
            self.assertLess(abs(g[e]["by_panel"]["muse"]["mean"] - g[e]["by_panel"]["grok"]["mean"]), 4.0, e)
            self.assertGreater(g[e]["by_panel"]["grok"]["mean"], g[e]["by_panel"]["muse"]["mean"], e)
        minutes = [g[e]["minutes"]["mean"] for e in EFFORTS]
        self.assertEqual(max(range(5), key=lambda i: minutes[i]), 2)  # High is the slowest level
        eg = {r["effort"]: r for r in self.econ["groups"]}
        self.assertEqual(max(eg.values(), key=lambda r: r["usd"]["mean"])["effort"], "high")
        self.assertLess(eg["max"]["usd"]["mean"], eg["high"]["usd"]["mean"])
        self.assertLess(eg["extra-high"]["usd"]["mean"], eg["max"]["usd"]["mean"])
        self.assertGreater(g["high"]["intent_recovery"]["mean"], g["low"]["intent_recovery"]["mean"])
        hours = sum(r["duration_s"] for r in self.rows) / 3600
        self.assertIn(f"Summed solver time is {hours:.2f} hours", self.page_html)

    def test_unpublished_row_is_disclosed(self):
        for text in (self.page_html, (DATA / "README.md").read_text(), (ROOT / "assets/data/swe-v4-sol-v37-scores.csv").read_text()):
            self.assertIn("22", text)
        self.assertIn("judged on 22 of 23 tasks", self.page_html)
        self.assertIn('memo = record[31:46].rstrip(".",")', html.unescape(self.page_html))
        self.assertIn('memo = record[31:46].rstrip(".,")', html.unescape(self.page_html))
        self.assertIn("22 of 23", (DATA / "README.md").read_text())
        self.assertEqual(len(self.protocols["unpublished"]), 1)
        finding = self.protocols["unpublished"][0]
        self.assertEqual((finding["effort"], finding["task"], finding["panel"], finding["stage"]), ("max", "legacy-codeccore-binary-parity", "grok", "probe"))
        self.assertEqual(finding["unsupported_excerpts"]["1"], finding["unsupported_excerpts"]["2"])
        self.assertTrue(any("22 of its 23 runs" in limit for limit in self.provenance["limits"]))
        self.assertIn("v3.7/calls/grok/probe/submission-023/operator-invalid.json", self.provenance["source_artifacts_sha256"])

    def test_calibration_and_protocol_record(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertFalse(record["allowance_used"])
            self.assertEqual(record["failing_gates"], [])
            self.assertTrue(all(gate["passed"] for gate in record["gates"].values()))
            self.assertEqual(record["call_count"], 80)
            self.assertEqual(len(record["gates"]), 20)
            self.assertEqual(record["allowance"], {"max_failing_gates": 1, "max_shortfall": 0.5})
            means = record["control_means"]
            self.assertGreaterEqual(means["0"]["naming"] - means["1"]["naming"], 2)
            self.assertGreaterEqual(means["0"]["presentation"] - means["1"]["presentation"], 2.0)
            self.assertLessEqual(means["0"]["presentation"] - means["1"]["presentation"], 2.15)
            self.assertGreater(means["2"]["presentation"] - means["1"]["presentation"], 0.5)
            self.assertLessEqual(means["2"]["naming"] - means["1"]["naming"], 0.35)
            self.assertLess(means["5"]["intent"], means["0"]["intent"])
            self.assertLess(means["9"]["verifiability"], means["0"]["verifiability"])
        self.assertIn("<td>passed</td><td>no</td><td>none</td>", self.page_html)
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.7", "grok": "code-quality-maintenance-v3.7"})
        self.assertEqual(set(self.protocols["scored_panel"]), set(PANELS))
        self.assertEqual(self.protocols["repeats"], 5)
        self.assertEqual(self.protocols["population"]["excluded"], [])
        self.assertEqual(self.protocols["population"]["missing"], [])
        self.assertEqual(self.protocols["population"]["cells"], {f"sol/{e}": 23 for e in EFFORTS})
        self.assertIn("v3.6.1", self.protocols["amends"])
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("SWE v4", text, name)

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
        card = ROOT / "assets/cards/swe-v4-sol-v37.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), CARD_SHA256)
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-sol-v37-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "leaderboard.html", "README.md"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-sol-v37.html", text, name)
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
        self.assertLess(index.index("swe-v4-sol-v37.html"), index.index("swe-v4-terra-v36.html"))
        self.assertIn("assets/cards/swe-v4-sol-v37.png", index)
        unescaped = html.unescape(self.page_html)
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
            self.assertNotIn(mark, unescaped, mark)


if __name__ == "__main__":
    unittest.main()
