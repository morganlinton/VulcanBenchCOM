"""Stdlib checks for the Claude Fable 5.2 bundle (v3.30.2 and v3.30.3), its report page, its cards, its model page and the site links to them."""

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
DATA = ROOT / "assets/data/swe-v4-fable52-v330"
PAGE = ROOT / "benchmarks/swe-v4-fable52-v330.html"
MODEL_PAGE = ROOT / "models/claude-fable-5-2.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-fable52-v330.html"
MODEL_URL = "https://vulcanbench.com/models/claude-fable-5-2.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "sol")
ENTITIES = ("&" + "mdash;", "&" + "ndash;")  # spelled in parts so this file carries no dash entity
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
# The harness card's per-level table (docs/results/swe-v4-fable52-2026-11/fable52-vs-frontier-efforts.csv), to four places.
CARD = {"low": (91.9176, 0.3929, 80.6272, 4.6335, 1.7239), "medium": (92.2472, 0.4392, 81.4864, 4.2982, 1.7179),
        "high": (92.7612, 0.4336, 82.9509, 7.8015, 2.8564), "extra-high": (93.2460, 0.4481, 84.2475, 14.2008, 4.9895),
        "max": (93.8460, 0.4180, 86.0241, 37.0865, 10.8796)}
# Copied byte for byte from the harness (2400x1350 each), shown at 1600x900.
CARDS = {"fable52-vs-frontier.png": ("swe-v4-fable52-v330.png", "5fc96dc31f01cf7fc2c0c43d5b53de61f3b1180adb4d10871a7552ff16dabe77"),
         "fable52-no-memorization.png": ("swe-v4-fable52-v330-memorization.png", None)}
TWO_RECEIPTS = {("low", "legacy-matchcore-order-book-parity"), ("extra-high", "legacy-reflowcore-binary-parity")}
TOUCHED = ("benchmarks/swe-v4-fable52-v330.html", "models/claude-fable-5-2.html", "models/fable-5-1.html", "benchmarks.html", "index.html",
           "feed.xml", "llms.txt", "README.md", "assets/data/README.md", "assets/data/swe-v4-fable52-v330/README.md",
           "assets/data/swe-v4-fable52-v330/REPRODUCING.md")


def composite(row, code_quality, weight):
    other = (0.5 - weight) / 2
    return 100 * (.5 * row["functional"] + other * row["automated_quality"] + other * row["security"] + weight * code_quality / 100)


def code_quality_of(reviewed, intent):
    return reviewed if intent is None else (0.24 * reviewed + 0.09 * intent) / 0.33


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


class Fable52BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.record["rows"]
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 115)
        self.assertEqual({(r["effort"], r["task"]) for r in self.rows}, {(e, t) for e in EFFORTS for t in {r["task"] for r in self.rows}})
        for r in self.rows:
            p = r["panels"]
            reviewed = statistics.mean(p[q]["reviewed_score"] for q in PANELS)
            intent = statistics.mean(p[q]["intent_recovery"] for q in PANELS)
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
            cq = code_quality_of(reviewed, intent)
            self.assertAlmostEqual(r["code_quality"], cq, places=9)
            self.assertAlmostEqual(r["combined_33"], composite(r, cq, 0.33), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], composite(r, cq, 0.20), places=9)
            for q in PANELS:
                self.assertAlmostEqual(r["combined_single_judge"][q],
                                       composite(r, code_quality_of(p[q]["reviewed_score"], p[q]["intent_recovery"]), 0.33), places=9)
            self.assertEqual(r["functional"], 1)
            self.assertEqual(r["hidden_behaviours_fixed"], r["hidden_behaviours"])
            self.assertEqual(r["integrity_audit"]["web"], "no_web")
            self.assertEqual((r["integrity_audit"]["benchmark_data_paths"], r["integrity_audit"]["answer_key_paths"]), (0, 0))
            self.assertFalse(r["integrity_audit"]["contaminated"])
            self.assertEqual(r["replies_by_model"], {"claude-fable-5-2": r["replies_by_model"]["claude-fable-5-2"]})
            self.assertFalse(r["solver_fallback"])
            self.assertEqual(r["solver_cli_version"], "2.1.321 (Claude Code)")
            self.assertEqual(r["result_receipts"], 2 if (r["effort"], r["task"]) in TWO_RECEIPTS else 1)
            u = r["token_usage"]
            self.assertEqual(r["raw_tokens"], u["input_tokens"] + u["cache_read_tokens"] + u["cache_creation_tokens"] + u["output_tokens"])
            self.assertLess(u["thinking_tokens"], u["output_tokens"])
            self.assertLess(r["duration_s"], 10800)
            self.assertEqual(r["judged_under"], "code-quality-maintenance-v3.30.3" if r["effort"] == "max" else "code-quality-maintenance-v3.30.2")

    def test_groups_match_runs_and_card(self):
        self.assertEqual(list(self.groups), list(EFFORTS))
        for e in EFFORTS:
            rs = [r for r in self.rows if r["effort"] == e]
            g = self.groups[e]
            for key, field in (("combined_33", "combined_33"), ("code_quality", "code_quality")):
                mean, se = mean_se(r[field] for r in rs)
                self.assertAlmostEqual(g[key]["mean"], mean, places=9)
                self.assertAlmostEqual(g[key]["se"], se, places=9)
            self.assertAlmostEqual(g["usd"]["mean"], statistics.mean(r["estimated_usd"] for r in rs), places=9)
            self.assertAlmostEqual(g["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=9)
            self.assertEqual(g["passed_all_runs"], 23)
            combined, se, cq, minutes, usd = CARD[e]
            self.assertEqual((round(g["combined_33"]["mean"], 4), round(g["combined_33"]["se"], 4), round(g["code_quality"]["mean"], 4)), (combined, se, cq))
            self.assertEqual((round(g["minutes"]["mean"], 4), round(g["usd"]["mean"], 4)), (minutes, usd))
        self.assertEqual(round(sum(r["estimated_usd"] for r in self.rows), 2), 509.85)
        with (DATA / "card-table.csv").open() as fh:
            card = {(r["model"], r["effort"]): r for r in csv.DictReader(fh)}
        for e in EFFORTS:
            self.assertEqual(card["fable52", e]["judges"], "muse+sol")
            self.assertEqual(card["astra", e]["judges"], "muse+grok")
            self.assertAlmostEqual(float(card["fable52", e]["combined"]), self.groups[e]["combined_33"]["mean"], places=4)

    def test_csvs(self):
        with (DATA / "runs.csv").open() as fh:
            flat = list(csv.DictReader(fh))
        self.assertEqual(len(flat), 115)
        for row, r in zip(flat, self.rows):
            self.assertEqual((row["effort"], row["task"], row["run_id"]), (r["effort"], r["task"], r["run_id"]))
            self.assertEqual(row["combined_33"], f'{r["combined_33"]:.4f}')
            self.assertEqual(row["thinking_tokens"], str(r["token_usage"]["thinking_tokens"]))
        with (ROOT / "assets/data/swe-v4-fable52-v330-scores.csv").open() as fh:
            scores = list(csv.DictReader(fh))
        self.assertEqual([s["effort"] for s in scores], list(EFFORTS))
        for s in scores:
            g = self.groups[s["effort"]]
            self.assertEqual(s["combined_33"], f'{g["combined_33"]["mean"]:.4f}')
            self.assertEqual(s["mean_usd"], f'{g["usd"]["mean"]:.6f}')
            self.assertEqual(s["passed_of_23"], "23")

    def test_judges_calibration_and_recoveries(self):
        calibration = json.loads((DATA / "calibration.json").read_text())
        self.assertTrue(calibration["muse"]["passed"] and calibration["sol"]["passed"])
        self.assertEqual((calibration["muse"]["failing_gates"], calibration["sol"]["failing_gates"]), ([], []))
        self.assertFalse(calibration["muse"]["allowance_used"] or calibration["sol"]["allowance_used"])
        self.assertEqual(calibration["muse"]["taken_under"], "code-quality-maintenance-v3.30")
        self.assertEqual(calibration["sol"]["taken_under"], "code-quality-maintenance-v3.30.2")
        self.assertFalse(calibration["grok_failed"]["passed"])
        self.assertEqual(calibration["grok_failed"]["failing_gates"], ["g14_pair_2_1"])
        protocols = json.loads((DATA / "judge-protocols.json").read_text())
        self.assertEqual(set(protocols["protocols"]), {"v3.30.2", "v3.30.3"})
        recoveries = [rec for c in protocols["calls"].values() for rec in c["operator_recoveries"]]
        self.assertEqual(sum(rec["rule"] == "recover_one_based_indexes" for rec in recoveries), 12)
        self.assertEqual(sum(rec["panel"] == "muse" for rec in recoveries), 1)
        self.assertEqual(protocols["calls"]["v3.30.2"]["sol_counted_calls"],
                         {"calibration": 80, "match": 92, "pairwise": 8, "primary": 92, "probe": 92, "repeat": 4})
        self.assertEqual(protocols["calls"]["v3.30.3"]["sol_counted_calls"], {"match": 23, "primary": 23, "probe": 23, "repeat": 1})

    def test_no_dashes_or_host_paths(self):
        for p in [*DATA.iterdir(), ROOT / "assets/data/swe-v4-fable52-v330-scores.csv"]:
            text = p.read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/private/", "/var/folders/", "SWE v4"):
                self.assertNotIn(mark, text, (p.name, mark))


class Fable52PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}

    def section(self, start, end):
        return plain(self.page_html[self.page_html.index(f'id="{start}"'):self.page_html.index(f'id="{end}"')])

    def test_structure_writing_and_links(self):
        for name in TOUCHED:
            markup = (ROOT / name).read_text()
            for entity in ENTITIES:
                self.assertNotIn(entity, markup, name)
        for markup in (self.page_html, MODEL_PAGE.read_text()):
            parser = IndexParser()
            parser.feed(markup)
            text = plain(markup)
            self.assertEqual(parser.structure_errors, [])
            self.assertEqual(parser.structure, [])
            self.assertEqual(len(parser.ids), len(set(parser.ids)))
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
                self.assertNotIn(mark, text, mark)
        links_resolve(self, self.page)
        model = IndexParser()
        model.feed(MODEL_PAGE.read_text())
        for link in model.links:
            if "://" in link or link.startswith(("#", "mailto:")):
                continue
            self.assertTrue((ROOT / "models" / link.split("#")[0].split("?")[0]).resolve().is_file(), link)
        self.assertIn(f'<link rel="canonical" href="{URL}">', self.page_html)
        self.assertIn('href="/reports.html"', self.page_html)
        for target in ("https://github.com/morganlinton/vulcanbench-fable52-traces", "/reports/01-how-claude-fable-5-2-thinks.html",
                       "https://github.com/morganlinton/VulcanBench/blob/main/docs/results/swe-v4-fable52-2026-11/README.md",
                       "https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md"):
            self.assertIn(f'href="{target}"', self.page_html)
        self.assertNotIn("data-backup", self.page_html)

    def test_tables_match_the_bundle(self):
        g = self.groups
        self.assertEqual(set(self.page.rows), {("fable52", e) for e in EFFORTS})
        for e in EFFORTS:
            row = self.page.rows["fable52", e]
            self.assertEqual(row[1:5], [label(e), f'{g[e]["combined_33"]["mean"]:.2f}', f'{g[e]["combined_33"]["se"]:.2f}',
                                        f'{g[e]["combined_20_profile"]["mean"]:.2f}'])
            self.assertEqual(row[5:9], [f'{g[e]["code_quality"]["mean"]:.2f}', f'{g[e]["readability"]["mean"]:.1f}',
                                        f'{g[e]["maintainability"]["mean"]:.1f}', f'{g[e]["intent_recovery"]["mean"]:.1f}'])
            self.assertEqual(row[-3:], ["23/23", "23/23", f'{g[e]["minutes"]["mean"]:.1f}'])
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th><td>23</td><td>${g[e]["usd"]["mean"]:.2f}</td>'
                          f'<td>${g[e]["usd_total"]:.2f}</td>', self.page_html)
        self.assertIn('<th scope="row">Combined score</th>' + "".join(f'<td>{g[e]["combined_33"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Tasks passed</th>' + "<td>23/23</td>" * 5, self.page_html)
        with (DATA / "card-table.csv").open() as fh:
            card = {(r["model"], r["effort"]): r for r in csv.DictReader(fh)}
        for m in ("fable51", "opus55"):
            self.assertIn(f'<tr data-matched="combined-{m}">', self.page_html)
            row = self.page_html[self.page_html.index(f'data-matched="combined-{m}"'):].split("</tr>")[0]
            self.assertEqual(re.findall(r"<td>([^<]+)</td>", row), [f'{float(card[m, e]["combined"]):.2f}' for e in EFFORTS])
        with (DATA / "muse-like-for-like.csv").open() as fh:
            muse = {(r["model"], r["effort"]): r for r in csv.DictReader(fh)}
        for m in ("fable52", "fable51", "opus55", "astra"):
            row = self.page_html[self.page_html.index(f'data-muse="combined-{m}"'):].split("</tr>")[0]
            self.assertEqual(re.findall(r"<td>([^<]+)</td>", row), [f'{float(muse[m, e]["muse_combined"]):.2f}' for e in EFFORTS])
        for key, bundle, model in (("fable51", "swe-v4-astra-fable51-v34", "fable"), ("opus55", "swe-v4-opus55-v315", "opus55"),
                                   ("astra", "swe-v4-astra-fable51-v34", "astra")):
            groups = {x["effort"]: x for x in json.loads((ROOT / "assets/data" / bundle / "groups.json").read_text()) if x["model"] == model}
            for e in EFFORTS:
                row = self.page_html[self.page_html.index(f'data-compare="{key}-{e}"'):].split("</tr>")[0]
                self.assertEqual(re.findall(r"<td>([^<]+)</td>", row)[1], f'{groups[e]["combined_33"]["mean"]:.2f}', (key, e))

    def test_required_disclosures(self):
        for needle in ("Grok 4.6, the usual second judge, failed its calibration exam", "the first column", "solved all 115"):
            self.assertIn(needle, self.text, needle)
        panels = self.section("panels", "behaviour")
        for needle in ("comparison-only rounds v3.30.4 and v3.30.5", "for this comparison only", "board keeps", "0.08 ahead of Opus 5.5",
                       "GPT-6.1 Sol shares its lab", "0.7 to 2.0 points", "correctness, speed and cost"):
            self.assertIn(needle, panels, needle)
        self.assertIn("Report 01", self.section("behaviour", "memorization"))
        memo = self.section("memorization", "cost")
        for needle in ("5.6%", "4.4% to 5.7%", "115 of 115", "did not remember"):
            self.assertIn(needle, memo, needle)
        cost = self.section("cost", "board")
        for needle in ("$509.85", "two receipts", "recorded no thinking tokens", "Grading is unaffected", "not subscription charges"):
            self.assertIn(needle, cost, needle)
        board = self.section("board", "code-quality")
        for needle in ("Max ranks 1st", "86 model and effort columns", "Extra-high 2nd, High 4th, Medium 7th and Low 10th", "not calibrated against each other"):
            self.assertIn(needle, board, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("g14_pair_2_1", "judged nothing", "recover_one_based_indexes", "Twelve", "re-wrapped", "v3.27", "Neither judge"):
            self.assertIn(needle, judges, needle)
        notes = self.section("run-notes", "reproduce")
        for needle in ("--thinking-display summarized", "usage limit", "bench/2026-11-09-fable52-frontier-v4", "2.1.321", "xhigh",
                       "second result receipt", "refusal fallback"):
            self.assertIn(needle, notes, needle)
        self.assertIn("never compared with Routine v1 Code quality", self.text)

    def test_cards_pinned(self):
        provenance = json.loads((DATA / "provenance.json").read_text())["source_artifacts_sha256"]
        for source, (name, sha) in CARDS.items():
            data = (ROOT / "assets/cards" / name).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            self.assertEqual(provenance[source], digest)
            if sha:
                self.assertEqual(digest, sha)
            self.assertEqual((int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")), (2400, 1350))
            self.assertIn(f'src="/assets/cards/{name}" width="1600" height="900"', self.page_html)
        self.assertIn('<meta property="og:image" content="https://vulcanbench.com/assets/cards/swe-v4-fable52-v330.png">', self.page_html)


class Fable52SiteTests(unittest.TestCase):
    def test_model_page_links_report(self):
        markup = MODEL_PAGE.read_text()
        self.assertIn('href="../benchmarks/swe-v4-fable52-v330.html"', markup)
        self.assertIn('href="https://github.com/morganlinton/vulcanbench-fable52-traces"', markup)
        self.assertIn('href="../reports/01-how-claude-fable-5-2-thinks.html"', markup)
        self.assertIn(f'<link rel="canonical" href="{MODEL_URL}">', markup)
        for value in ("91.92", "92.25", "92.76", "93.25", "93.85", "80.63 to 86.02", "$509.85"):
            self.assertIn(value, markup, value)
        self.assertIn('href="claude-fable-5-2.html"', (ROOT / "models/fable-5-1.html").read_text())

    def test_site_references(self):
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "models/claude-fable-5-2.html"):
            self.assertIn("swe-v4-fable52-v330.html", (ROOT / name).read_text(), name)
        self.assertIn('href="models/claude-fable-5-2.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn("swe-v4-fable52-v330/", (ROOT / "assets/data/README.md").read_text())
        sitemap = (ROOT / "sitemap.xml").read_text()
        for page_url in (URL, MODEL_URL):
            self.assertIn(f"<loc>{page_url}</loc>", sitemap)
        item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in i)
        self.assertIn("13 Nov 2026", item)
        self.assertNotIn(chr(0x2014), item)
        leaderboard = (ROOT / "leaderboard.html").read_text()
        self.assertIn('<a href="benchmarks/swe-v4-fable52-v330.html">Claude Fable 5.2</a>', leaderboard)
        self.assertEqual(len(re.findall(r'"key":"fable52","effort":"[a-z-]+"', leaderboard)), 5)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-fable52-v330.html"), index.index("swe-v4-gpt61-terra-v329.html"))


if __name__ == "__main__":
    unittest.main()
