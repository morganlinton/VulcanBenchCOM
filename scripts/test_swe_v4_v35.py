"""Stdlib checks for the v3.5 GPT-5.5 versus Luna bundle, its report page and the site links to it."""

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
DATA = ROOT / "assets/data/swe-v4-gpt55-luna-v35"
PAGE = ROOT / "benchmarks/swe-v4-gpt55-luna-v35.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-gpt55-luna-v35.html"
LEVELS = {"gpt55": ("low", "medium", "high", "extra-high"), "luna": ("low", "medium", "high", "extra-high", "max")}
EFFORTS = LEVELS["luna"]
SHARED = LEVELS["gpt55"]
PANELS = ("muse", "grok")
NAMES = {"gpt55": "GPT-5.5", "luna": "GPT-5.6 Luna"}
CARD_SHA256 = "82fe91c5b2b0b03b6f545aa896af4cc72ba247f189677c82f7e54407c7228de0"
ECONOMICS_CARD_SHA256 = "a089c961e77280fa40493b12061a75240415e06f679e4a8269ebf12f4cfd6391"


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


class Gpt55LunaBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.groups = {(g["model"], g["effort"]): g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())
        with (ROOT / "assets/data/swe-v4-gpt55-luna-v35-scores.csv").open(newline="") as source:
            cls.scores = {("gpt55" if r["model"] == "GPT-5.5" else "luna", r["effort"]): r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 207)
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        redistributed = 0
        for r in self.rows:
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            if r["intent_recovery_redistributed"]:
                redistributed += 1
                self.assertIsNone(r["intent_recovery"])
                self.assertEqual(r["passed_quirk_families"], 0)
                self.assertTrue(all(r["panels"][p]["intent_recovery"] is None and r["panels"][p]["scored_quirks"] == 0 for p in PANELS))
                code_quality = reviewed
            else:
                intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
                self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
                code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            self.assertFalse(r["solver_fallback"], r["run_id"])
            for p in PANELS:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"],
                                       (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
            usage, rate = r["token_usage"], self.econ["rates_per_million"][r["model"]]
            cached = min(usage["cached_input_tokens"], usage["input_tokens"])
            priced = ((usage["input_tokens"] - cached) * rate["input"] + cached * rate["cached_input"] + usage["output_tokens"] * rate["output"]) / 1e6
            self.assertAlmostEqual(r["estimated_usd"], priced, places=5, msg=r["run_id"])
            self.assertGreater(r["raw_tokens"], 0)
        self.assertEqual(redistributed, 10)
        self.assertEqual(len({(r["model"], r["effort"], r["task"]) for r in self.rows}), 207)

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), {(m, e) for m in LEVELS for e in LEVELS[m]})
        self.assertEqual(set(self.scores), set(self.groups))
        for key, g in self.groups.items():
            rs = [r for r in self.rows if (r["model"], r["effort"]) == key]
            scored = [r for r in rs if r["intent_recovery"] is not None]
            self.assertEqual(len(rs), 23)
            self.assertEqual(g["n"], 23)
            self.assertEqual(g["intent_recovery_redistributed_runs"], len(rs) - len(scored))
            for field, values in (("combined_33", [r["combined_33"] for r in rs]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in rs]),
                                  ("code_quality", [r["code_quality"] for r in rs]),
                                  ("reviewed_score", [r["reviewed_score"] for r in rs]),
                                  ("intent_recovery", [r["intent_recovery"] for r in scored]),
                                  ("readability", [statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in rs]),
                                  ("maintainability", [statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in rs]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]),
                                  ("usd", [r["estimated_usd"] for r in rs]),
                                  ("raw_tokens", [r["raw_tokens"] for r in rs])):
                mean, se = mean_se(values)
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(key, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(key, field))
            for p in PANELS:
                self.assertAlmostEqual(g["by_panel"][p]["mean"], statistics.mean(r["panels"][p]["reviewed_score"] for r in rs), places=9)
            self.assertEqual(g["passed"], sum(r["functional"] == 1 for r in rs))
            self.assertEqual(g["solver_fallback_runs"], 0)
            row = self.scores[key]
            for column, field in (("combined_33", "combined_33"), ("combined_20_profile", "combined_20_profile"), ("code_quality", "code_quality"),
                                  ("readability", "readability"), ("maintainability", "maintainability"), ("intent_recovery", "intent_recovery"),
                                  ("mean_minutes", "minutes")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(key, column))
            self.assertAlmostEqual(float(row["combined_33_se"]), g["combined_33"]["se"], places=4)
            self.assertAlmostEqual(float(row["code_quality_se"]), g["code_quality"]["se"], places=4)
            self.assertEqual(int(row["passed"]), g["passed"])
            self.assertEqual(int(row["intent_recovery_redistributed_runs"]), g["intent_recovery_redistributed_runs"])

    def test_page_tables_match_groups(self):
        self.assertEqual(set(self.page.rows), set(self.groups))
        for key, g in self.groups.items():
            star = "*" if g["intent_recovery_redistributed_runs"] else ""
            expected = [f'{g["combined_33"]["mean"]:.2f}', f'{g["combined_33"]["se"]:.2f}', f'{g["combined_20_profile"]["mean"]:.2f}',
                        f'{g["code_quality"]["mean"]:.2f}', f'{g["readability"]["mean"]:.1f}', f'{g["maintainability"]["mean"]:.1f}',
                        f'{g["intent_recovery"]["mean"]:.1f}{star}', f'{g["passed"]}/23', f'{g["minutes"]["mean"]:.1f}']
            self.assertEqual(self.page.rows[key][2:], expected, key)
            self.assertEqual(self.page.rows[key][1], label(key[1]))
        a, f = self.groups["gpt55", "extra-high"], self.groups["luna", "max"]
        for name, value in (("Code quality", f'<td>{a["code_quality"]["mean"]:.2f}</td><td>{f["code_quality"]["mean"]:.2f}</td><td>{round(f["code_quality"]["mean"], 2) - round(a["code_quality"]["mean"], 2):+.2f}</td>'),
                            ("Human readability", f'<td>{a["readability"]["mean"]:.1f}</td><td>{f["readability"]["mean"]:.1f}</td><td>{round(f["readability"]["mean"], 1) - round(a["readability"]["mean"], 1):+.1f}</td>'),
                            ("Maintainability", f'<td>{a["maintainability"]["mean"]:.1f}</td><td>{f["maintainability"]["mean"]:.1f}</td><td>{round(f["maintainability"]["mean"], 1) - round(a["maintainability"]["mean"], 1):+.1f}</td>'),
                            ("Intent recovery", f'<td>{a["intent_recovery"]["mean"]:.1f}</td><td>{f["intent_recovery"]["mean"]:.1f}</td><td>{round(f["intent_recovery"]["mean"], 1) - round(a["intent_recovery"]["mean"], 1):+.1f}</td>'),
                            ("Rated by Muse Spark 1.3", f'<td>{a["by_panel"]["muse"]["mean"]:.1f}</td><td>{f["by_panel"]["muse"]["mean"]:.1f}</td><td>{round(f["by_panel"]["muse"]["mean"], 1) - round(a["by_panel"]["muse"]["mean"], 1):+.1f}</td>'),
                            ("Rated by Grok 4.6", f'<td>{a["by_panel"]["grok"]["mean"]:.1f}</td><td>{f["by_panel"]["grok"]["mean"]:.1f}</td><td>{round(f["by_panel"]["grok"]["mean"], 1) - round(a["by_panel"]["grok"]["mean"], 1):+.1f}</td>'),
                            ("Standard error of Code quality", f'<td>{a["code_quality"]["se"]:.2f}</td><td>{f["code_quality"]["se"]:.2f}</td>')):
            self.assertIn(f'<th scope="row">{name}</th>{value}', self.page_html, name)

    def test_across_efforts_table(self):
        def cells(model, key, digits):
            out = "".join(f"<td>{self.groups[model, e][key]['mean']:.{digits}f}</td>" for e in LEVELS[model])
            return out + ("<td>no level</td>" if model == "gpt55" else "")

        def diffs(key):
            return "".join(f"<td>{round(self.groups['luna', e][key]['mean'], 2) - round(self.groups['gpt55', e][key]['mean'], 2):+.2f}</td>" for e in SHARED) + "<td></td>"

        def passed(model):
            return "".join(f"<td>{self.groups[model, e]['passed']}/23</td>" for e in LEVELS[model]) + ("<td>no level</td>" if model == "gpt55" else "")

        for name, html_cells in (("GPT-5.5 combined score", cells("gpt55", "combined_33", 2)), ("Luna combined score", cells("luna", "combined_33", 2)),
                                 ("Luna minus GPT-5.5, combined", diffs("combined_33")), ("GPT-5.5 tasks passed", passed("gpt55")), ("Luna tasks passed", passed("luna")),
                                 ("GPT-5.5 Code quality", cells("gpt55", "code_quality", 2)), ("Luna Code quality", cells("luna", "code_quality", 2)),
                                 ("Luna minus GPT-5.5, Code quality", diffs("code_quality")),
                                 ("GPT-5.5 minutes per task", cells("gpt55", "minutes", 1)), ("Luna minutes per task", cells("luna", "minutes", 1))):
            self.assertIn(f'<th scope="row">{name}</th>{html_cells}', self.page_html, name)
        gpt = [self.groups["gpt55", e]["combined_33"]["mean"] for e in SHARED]
        luna = [self.groups["luna", e]["combined_33"]["mean"] for e in EFFORTS]
        self.assertIn(f'GPT-5.5 {min(gpt):.2f} to {max(gpt):.2f} &middot; Luna {min(luna):.2f} to {max(luna):.2f}', self.page_html)
        self.assertIn(f'{self.groups["luna", "low"]["intent_recovery_redistributed_runs"]} of 23 Luna Low runs', self.page_html)

    def test_economics_table_and_card(self):
        eg = {(r["model"], r["effort"]): r for r in self.econ["groups"]}
        for e in EFFORTS:
            b = eg["luna", e]
            rs = [r for r in self.rows if r["effort"] == e]
            self.assertAlmostEqual(b["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs if r["model"] == "luna"), places=9)
            self.assertAlmostEqual(b["raw_tokens"]["mean"], statistics.mean(r["raw_tokens"] for r in rs if r["model"] == "luna"), places=6)
            if e == "max":
                cells = f'<td>no level</td><td>${b["usd"]["mean"]:.2f}</td><td></td><td></td><td>{b["raw_tokens"]["mean"] / 1e6:.2f}M</td><td></td><td>{b["minutes"]["mean"]:.1f}</td>'
            else:
                a = eg["gpt55", e]
                self.assertAlmostEqual(a["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs if r["model"] == "gpt55"), places=9)
                self.assertLess(b["usd"]["mean"], a["usd"]["mean"], e)
                cells = (f'<td>${a["usd"]["mean"]:.2f}</td><td>${b["usd"]["mean"]:.2f}</td><td>{a["usd"]["mean"] / b["usd"]["mean"]:.1f}x</td>'
                         f'<td>{a["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>{b["raw_tokens"]["mean"] / 1e6:.2f}M</td>'
                         f'<td>{a["minutes"]["mean"]:.1f}</td><td>{b["minutes"]["mean"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}</tr>', self.page_html, e)
        t = self.econ["totals"]
        for m in LEVELS:
            self.assertAlmostEqual(t[m]["usd"], sum(r["estimated_usd"] for r in self.rows if r["model"] == m), places=6)
            self.assertEqual(t[m]["raw_tokens"], sum(r["raw_tokens"] for r in self.rows if r["model"] == m))
            self.assertEqual(t[m]["runs"], sum(1 for r in self.rows if r["model"] == m))
        self.assertEqual((t["gpt55"]["runs"], t["luna"]["runs"]), (92, 115))
        self.assertIn(f'<th scope="row">Full sweeps, 92 and 115 runs</th><td>${t["gpt55"]["usd"]:,.2f}</td><td>${t["luna"]["usd"]:,.2f}</td>', self.page_html)
        self.assertEqual(f'{t["gpt55"]["usd"]:.2f}', "305.04")
        self.assertEqual(f'{t["luna"]["usd"]:.2f}', "23.70")
        ratios = [eg["gpt55", e]["usd"]["mean"] / eg["luna", e]["usd"]["mean"] for e in SHARED]
        self.assertIn(f"{min(ratios):.1f} to {max(ratios):.1f} times less per task", self.page_html)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertIn(f"Luna costs {min(ratios):.0f} to {max(ratios):.0f} times less per task", index)
        card = ROOT / "assets/cards/swe-v4-gpt55-luna-v35-economics.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), ECONOMICS_CARD_SHA256)

    def test_model_pages(self):
        for slug, model in (("gpt-5-5", "gpt55"), ("gpt-5-6-luna", "luna")):
            page = (ROOT / f"models/{slug}.html").read_text()
            self.assertIn("../benchmarks/swe-v4-gpt55-luna-v35.html", page)
            combined = [self.groups[model, e]["combined_33"]["mean"] for e in LEVELS[model]]
            quality = [self.groups[model, e]["code_quality"]["mean"] for e in LEVELS[model]]
            self.assertIn(f"combined score {min(combined):.2f} to {max(combined):.2f}", page)
            self.assertIn(f"Code quality {min(quality):.2f} to {max(quality):.2f}", page)
            self.assertNotIn(chr(0x2014), html.unescape(page))
            self.assertIn(f'href="models/{slug}.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="/models/gpt-5-5.html"', self.page_html)
        self.assertIn('href="/models/gpt-5-6-luna.html"', self.page_html)

    def test_comparative_claims(self):
        g = self.groups
        for effort in ("low", "medium"):
            self.assertGreater(g["gpt55", effort]["combined_33"]["mean"], g["luna", effort]["combined_33"]["mean"], effort)
            self.assertGreater(g["gpt55", effort]["combined_20_profile"]["mean"], g["luna", effort]["combined_20_profile"]["mean"], effort)
            self.assertLess(g["luna", effort]["minutes"]["mean"], g["gpt55", effort]["minutes"]["mean"], effort)
        for effort in ("high", "extra-high"):
            gap = g["luna", effort]["combined_33"]["mean"] - g["gpt55", effort]["combined_33"]["mean"]
            self.assertGreater(gap, 0, effort)
            self.assertLess(gap, min(g["luna", effort]["combined_33"]["se"], g["gpt55", effort]["combined_33"]["se"]), effort)
            self.assertGreater(g["luna", effort]["combined_20_profile"]["mean"], g["gpt55", effort]["combined_20_profile"]["mean"], effort)
            self.assertGreater(g["luna", effort]["minutes"]["mean"], g["gpt55", effort]["minutes"]["mean"], effort)
        for effort in SHARED:
            self.assertGreater(g["luna", effort]["code_quality"]["mean"], g["gpt55", effort]["code_quality"]["mean"], effort)
            self.assertGreater(g["luna", effort]["readability"]["mean"], g["gpt55", effort]["readability"]["mean"], effort)
            for p in PANELS:
                self.assertGreater(g["luna", effort]["by_panel"][p]["mean"], g["gpt55", effort]["by_panel"][p]["mean"], (effort, p))
            if effort != "low":
                self.assertLess(g["luna", effort]["code_quality"]["mean"] - g["gpt55", effort]["code_quality"]["mean"], 3, effort)
        best = max(g.values(), key=lambda x: x["combined_33"]["mean"])
        self.assertEqual((best["model"], best["effort"]), ("luna", "max"))
        self.assertEqual(g["luna", "max"]["passed"], 19)
        self.assertEqual([g["gpt55", e]["passed"] for e in SHARED], [1, 3, 7, 11])
        self.assertEqual([g["luna", e]["passed"] for e in EFFORTS], [0, 1, 9, 13, 19])
        self.assertGreater(g["gpt55", "extra-high"]["readability"]["mean"], g["luna", "max"]["readability"]["mean"])
        self.assertGreater(g["luna", "max"]["intent_recovery"]["mean"], g["gpt55", "extra-high"]["intent_recovery"]["mean"])
        for p in PANELS:
            self.assertGreater(g["gpt55", "extra-high"]["by_panel"][p]["mean"], g["luna", "max"]["by_panel"][p]["mean"], p)
        hours = sum(r["duration_s"] for r in self.rows) / 3600
        self.assertIn(f"Summed solver time is {hours:.2f} hours", self.page_html)

    def test_calibration_and_protocol_record(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertEqual(record["call_count"], 80)
            self.assertEqual(len(record["gates"]), 20)
            self.assertEqual(record["allowance"], {"max_failing_gates": 1, "max_shortfall": 0.5})
            means = record["control_means"]
            self.assertGreaterEqual(means["0"]["naming"] - means["1"]["naming"], 2)
            self.assertGreaterEqual(means["0"]["presentation"] - means["1"]["presentation"], 1.9)
            self.assertGreater(means["2"]["presentation"], means["1"]["presentation"])
            self.assertLessEqual(means["2"]["naming"], means["1"]["naming"])
            self.assertLess(means["5"]["intent"], means["0"]["intent"])
            self.assertLess(means["9"]["verifiability"], means["0"]["verifiability"])
        muse, grok = self.calibration["muse"], self.calibration["grok"]
        self.assertTrue(muse["allowance_used"])
        self.assertEqual(muse["failing_gates"], ["g11_repeatability"])
        self.assertFalse(muse["gates"]["g11_repeatability"]["passed"])
        self.assertLessEqual(muse["gates"]["g11_repeatability"]["shortfall"], 0.5)
        self.assertEqual(sum(not gate["passed"] for gate in muse["gates"].values()), 1)
        self.assertFalse(grok["allowance_used"])
        self.assertEqual(grok["failing_gates"], [])
        self.assertTrue(all(gate["passed"] for gate in grok["gates"].values()))
        self.assertIn(f'yes, g11 by {muse["gates"]["g11_repeatability"]["shortfall"]:.2f}', self.page_html)
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.5", "grok": "code-quality-maintenance-v3.5"})
        self.assertEqual(set(self.protocols["scored_panel"]), set(PANELS))
        self.assertEqual(self.protocols["repeats"], 5)
        self.assertEqual(self.protocols["population"]["excluded"], [])
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/"):
                self.assertNotIn(mark, text, name)

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
        card = ROOT / "assets/cards/swe-v4-gpt55-luna-v35.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), CARD_SHA256)
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-gpt55-luna-v35-report.pdf").stat().st_size, 100_000)
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "leaderboard.html"):
            text = html.unescape((ROOT / name).read_text())
            self.assertIn("swe-v4-gpt55-luna-v35.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn(f"<guid>{URL}</guid>", (ROOT / "feed.xml").read_text())
        self.assertNotIn(chr(0x2014), html.unescape(self.page_html))
        self.assertNotIn(chr(0x2013), html.unescape(self.page_html))


if __name__ == "__main__":
    unittest.main()
