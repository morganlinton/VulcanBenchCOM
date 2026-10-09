"""Stdlib checks for the v3.23 Claude Sonnet 5.5 bundle, its report page, its cards and the site links to it.

The page, model page and link tests run as soon as the page exists. The bundle tests run once
scripts/export_swe_v4_v323_evidence.py has written assets/data/swe-v4-sonnet55-v323/groups.json;
test_bundle_is_exported and test_no_placeholders_left fail until the page is filled from it.
"""

import csv
import hashlib
import html
import json
import re
import statistics
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

from check_benchmark_index import IndexParser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/swe-v4-sonnet55-v323"
OPUS = ROOT / "assets/data/swe-v4-opus55-v315"
FABLE = ROOT / "assets/data/swe-v4-astra-fable51-v34"
PAGE = ROOT / "benchmarks/swe-v4-sonnet55-v323.html"
MODEL_PAGE = ROOT / "models/claude-sonnet-5-5.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-sonnet55-v323.html"
FRONTIER = ROOT / "benchmarks/swe-v4-sonnet55-vs-frontier.html"
FRONTIER_URL = "https://vulcanbench.com/benchmarks/swe-v4-sonnet55-vs-frontier.html"
SOL = ROOT / "assets/data/swe-v4-gpt61-sol-v318"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
BUNDLE_READY = (DATA / "groups.json").is_file()
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
# Sweep facts fixed before judging (harness DECISIONS.md, 2026-10-07; run summaries).
PASSED = [15, 17, 20, 22, 23]
HIDDEN = [214, 219, 223, 230, 231]
MINUTES = ["20.0", "20.8", "14.8", "21.6", "38.0"]
USD = ["2.88", "3.00", "2.39", "3.38", "5.52"]
CLI_VERSIONS = {"low": {"2.1.291": 21, "2.1.292": 2}, "medium": {"2.1.292": 23}, "high": {"2.1.292": 23},
                "extra-high": {"2.1.292": 22, "2.1.293": 1}, "max": {"2.1.293": 23}}
# Copied byte for byte from the harness (docs/results/swe-v4-sonnet55-2026-10) once final; pin their hashes here.
CARDS = {
    "swe-v4-sonnet55-v323.png": "2cb7c84978ba7257690983c743c347ad9cd277b0a71e935eee0bb1babd2577bd",
    "swe-v4-sonnet55-vs-claude.png": "6c1dca1cfefbbe8157800758cdccd0e2e9a73889427acf07a3155f5df21a2ee2",
}
# Files that carry Sonnet 5.5 copy and must be free of placeholders before merge.
TOUCHED = ("benchmarks/swe-v4-sonnet55-v323.html", "benchmarks/swe-v4-sonnet55-vs-frontier.html", "models/claude-opus-5-5.html", "models/gpt-6-1-sol.html", "models/claude-sonnet-5-5.html", "benchmarks.html", "index.html", "feed.xml", "llms.txt",
           "leaderboard.html", "assets/data/README.md", "assets/data/swe-v4-sonnet55-v323/README.md",
           "assets/data/swe-v4-sonnet55-v323/REPRODUCING.md", "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v323.py")


def mean_se(values):
    values = list(values)
    return statistics.mean(values), statistics.stdev(values) / len(values) ** 0.5


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


def plain(markup):
    """Visible text: tags dropped, entities decoded."""
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def text_of(name):
    return html.unescape((ROOT / name).read_text())


class SonnetPageTests(unittest.TestCase):
    """Checks that need only the page and the site files."""

    @classmethod
    def setUpClass(cls):
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)

    def section(self, start, end):
        return plain(self.page_html[self.page_html.index(f'id="{start}"'):self.page_html.index(f'id="{end}"')])

    def test_bundle_is_exported(self):
        self.assertTrue(BUNDLE_READY, "run scripts/export_swe_v4_v323_evidence.py once the v3.23 summary.json exists")

    def test_no_placeholders_left(self):
        left = {name: (ROOT / name).read_text().count(PLACEHOLDER) for name in TOUCHED}
        self.assertEqual({name: n for name, n in left.items() if n}, {}, "fill every TBD placeholder from the v3.23 summary before merging")

    def test_structure_and_writing(self):
        self.assertEqual(self.page.structure_errors, [])
        self.assertEqual(self.page.structure, [])
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
            self.assertNotIn(mark, self.text, mark)
        self.assertIn('class="how-it-works"', self.page_html)
        self.assertIn("share.js", self.page_html)
        self.assertIn("intent/post?text=Claude%20Sonnet%205.5%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertEqual(set(self.page.rows), {("sonnet55", e) for e in EFFORTS})
        for fragment in [link for link in self.page.links if link.startswith("#")]:
            self.assertIn(fragment[1:], self.page.ids)

    def test_required_disclosures(self):
        run_notes = self.section("run-notes", "reproduce")
        # 1. Before the tagged-worktree rule: no source block, older hash format, verified content, the bridge, the .pyc check.
        for needle in ("tagged-worktree rule", "no source block", "__pycache__", "identical to the frozen suite lock",
                       "docs/judging/task-hash-bridge-sonnet55.json", "All 107 cached .pyc files", "byte-identical to compiling the starting source"):
            self.assertIn(needle, run_notes, needle)
        # 2. Judge settings and versions: originals recovered, settings identical, Muse same binary, Cursor version moved.
        judges = self.section("judges", "run-notes")
        for needle in ("Judge settings and versions", "recovered from the owner\u2019s private backup", "b82da598", "1d80e097",
                       "settings used in v3.23 are identical to them", "same binary as every earlier round (sha256 match)",
                       "hashes only Cursor\u2019s launcher script", "never fixed the version", "October 7 at 14:43 PDT",
                       "Cursor CLI 2026.10.01-e373342", "2026.09.02-c22c1a3", "model id", "\u201cGrok 4.6 Medium\u201d where the frozen settings say \u201cCursor Grok 4.6 Medium\u201d", "439 times",
                       "passed calibration under v3.23"):
            self.assertIn(needle, judges, needle)
        for stale in ("rebuilt", "re-pinned", "cannot be shown", "were lost", "erased"):
            self.assertNotIn(stale, self.text, stale)
        # 3. Claude Code version mix.
        for needle in ("Low ran 21 tasks on 2.1.291 and 2 on 2.1.292", "Medium and High ran on 2.1.292",
                       "Extra-high ran 22 tasks on 2.1.292 and its last, paddockcore, on 2.1.293", "Max ran on 2.1.293",
                       "Earlier Claude columns used older Claude Code releases"):
            self.assertIn(needle, run_notes, needle)
        # 4. Frontier Code quality is L1 plus L2, never compared with Routine v1.
        self.assertIn("never compared with Routine v1 Code quality", self.text)
        # 5. Combined score formula.
        self.assertIn("50% functional correctness + 8.5% lint and complexity + 8.5% security + 33% Code quality", self.text)
        self.assertIn("100 × (0.50F + 0.085Q + 0.085S + 0.33C / 100)", self.text)
        # Calibration under v3.23, both with the one-gate allowance.
        self.assertIn("<td>code-quality-maintenance-v3.23</td><td>80</td><td>passed</td><td>yes</td><td>g11_repeatability, short by 0.02</td>", self.page_html)
        self.assertIn("<td>code-quality-maintenance-v3.23</td><td>80</td><td>passed</td><td>yes</td><td>g04_formatting_is_presentation, short by 0.10</td>",
                      self.page_html)
        # Refusal fallback on, never used; cost source.
        for needle in ("Refusal fallback on, never used", "every reply in every run came from claude-sonnet-5-5", "cli_reported_cost_usd",
                       "two cache-read prices", "$0.20 per million in its table", "($0.10)"):
            self.assertIn(needle, self.text, needle)

    def test_sweep_facts(self):
        for e, passed, hidden, minutes in zip(EFFORTS, PASSED, HIDDEN, MINUTES):
            row = self.page.rows["sonnet55", e]
            self.assertEqual(row[1], label(e))
            self.assertEqual(row[-2:], [f"{passed}/23", minutes])
        self.assertIn('<th scope="row">Tasks passed</th>' + "".join(f"<td>{p}/23</td>" for p in PASSED) + "</tr>", self.page_html)
        self.assertIn('<th scope="row">Hidden behaviours fixed</th>' + "".join(f"<td>{h}/231</td>" for h in HIDDEN) + "</tr>", self.page_html)
        self.assertIn('<th scope="row">Minutes per task</th>' + "".join(f"<td>{m}</td>" for m in MINUTES) + "</tr>", self.page_html)
        self.assertIn('<th scope="row">$ per task (Claude Code)</th>' + "".join(f"<td>${u}</td>" for u in USD) + "</tr>", self.page_html)
        for value in ("0.652 (&plusmn;0.102)", "0.739 (&plusmn;0.094)", "0.870 (&plusmn;0.072)", "0.957 (&plusmn;0.043)", "$394.77", "$3.43 per task"):
            self.assertIn(value, self.page_html, value)
        self.assertIn("October 6, 06:49 PDT, to October 8, 03:38 PDT", self.text)

    def test_comparison_rows_match_published_bundles(self):
        o = {g["effort"]: g for g in json.loads((OPUS / "groups.json").read_text())}
        eo = {g["effort"]: g for g in json.loads((OPUS / "economics.json").read_text())["groups"]}
        f = {g["effort"]: g for g in json.loads((FABLE / "groups.json").read_text()) if g["model"] == "fable"}
        ef = {g["effort"]: g for g in json.loads((FABLE / "economics.json").read_text())["groups"] if g["model"] == "fable"}
        rows = {"combined-opus55": [f'{o[e]["combined_33"]["mean"]:.2f}' for e in EFFORTS],
                "combined-fable": [f'{f[e]["combined_33"]["mean"]:.2f}' for e in EFFORTS],
                "passed-opus55": [f'{o[e]["passed_all_runs"]}/23' for e in EFFORTS],
                "passed-fable": [f'{f[e]["passed"]}/23' for e in EFFORTS],
                "cq-opus55": [f'{o[e]["code_quality"]["mean"]:.2f}' for e in EFFORTS],
                "cq-fable": [f'{f[e]["code_quality"]["mean"]:.2f}' for e in EFFORTS],
                "usd-opus55": [f'${eo[e]["usd"]["mean"]:.2f}' for e in EFFORTS],
                "usd-fable": [f'${ef[e]["usd"]["mean"]:.2f}' for e in EFFORTS],
                "usd-sonnet55": [f"${u}" for u in USD],
                "minutes-opus55": [f'{eo[e]["minutes"]["mean"]:.1f}' for e in EFFORTS],
                "minutes-fable": [f'{ef[e]["minutes"]["mean"]:.1f}' for e in EFFORTS],
                "minutes-sonnet55": MINUTES,
                "passed-sonnet55": [f"{p}/23" for p in PASSED]}
        for key, cells in rows.items():
            start = self.page_html.index(f'<tr data-compare="{key}">')
            self.assertIn("".join(f"<td>{c}</td>" for c in cells) + "</tr>", self.page_html[start:start + 400], key)

    def test_model_pages_and_site_references(self):
        page = MODEL_PAGE.read_text()
        self.assertIn('<link rel="canonical" href="https://vulcanbench.com/models/claude-sonnet-5-5.html">', page)
        for anchor in ("", "#cost", "#compared"):
            self.assertIn(f"../benchmarks/swe-v4-sonnet55-v323.html{anchor}", page)
        self.assertIn('href="claude-sonnet-5.html"', page)
        self.assertIn('href="claude-opus-5-5.html"', page)
        self.assertIn('href="claude-sonnet-5-5.html"', (ROOT / "models/claude-sonnet-5.html").read_text())
        self.assertIn('href="claude-sonnet-5-5.html"', (ROOT / "models/claude-opus-5-5.html").read_text())
        self.assertIn('href="/models/claude-sonnet-5-5.html"', self.page_html)
        self.assertIn('href="models/claude-sonnet-5-5.html"', (ROOT / "benchmarks.html").read_text())
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "leaderboard.html", "README.md"):
            text = text_of(name)
            self.assertIn("swe-v4-sonnet55-v323.html", text, name)
            if name != "feed.xml":  # feed.xml keeps historical item text as published
                self.assertNotIn(chr(0x2014), text, name)
                self.assertNotIn(chr(0x2013), text, name)
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in item)
        self.assertNotIn(chr(0x2014), feed_item)
        self.assertNotIn("SWE v4", feed_item)
        self.assertIn("VulcanBench Frontier v4", feed_item)
        self.assertIn(f"<loc>{URL}</loc>", (ROOT / "sitemap.xml").read_text())
        self.assertIn("<loc>https://vulcanbench.com/models/claude-sonnet-5-5.html</loc>", (ROOT / "sitemap.xml").read_text())
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-sonnet55-v323.html"), index.index("swe-v4-grok47-cursor-v320.html"))
        home = (ROOT / "index.html").read_text()
        self.assertLess(home.index("swe-v4-sonnet55-v323.html"), home.index("swe-v4-grok47-cursor-v320.html"))

    def test_page_links_resolve(self):
        # Fails until the export, the PDF render and the two cards are in place.
        for link in self.page.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            self.assertTrue((ROOT / unquote(parsed.path).lstrip("/")).is_file(), link)


def published(bundle, model):
    groups = {g["effort"]: g for g in json.loads((bundle / "groups.json").read_text()) if g["model"] == model}
    econ = {g["effort"]: g for g in json.loads((bundle / "economics.json").read_text())["groups"] if g["model"] == model}
    return groups, econ


class FrontierComparisonTests(unittest.TestCase):
    """The three-model page: Opus 5.5 and GPT-6.1 Sol rows are final and must equal their bundles."""

    @classmethod
    def setUpClass(cls):
        cls.page_html = FRONTIER.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)

    def section(self, start, end):
        return plain(self.page_html[self.page_html.index(f'id="{start}"'):self.page_html.index(f'id="{end}"')])

    def test_structure_and_writing(self):
        self.assertEqual(self.page.structure_errors, [])
        self.assertEqual(self.page.structure, [])
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra"):
            self.assertNotIn(mark, self.text, mark)
        self.assertIn(f'<link rel="canonical" href="{FRONTIER_URL}">', self.page_html)
        self.assertIn("VulcanBench Frontier v4", self.text)
        self.assertIn("intent/post?text=Claude%20Sonnet%205.5%20vs%20Claude%20Opus%205.5%20vs%20GPT-6.1%20Sol%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertIn('src="/assets/cards/swe-v4-sonnet55-vs-frontier.png"', self.page_html)
        for fragment in [link for link in self.page.links if link.startswith("#")]:
            self.assertIn(fragment[1:], self.page.ids)

    def test_rows_for_every_model_and_level(self):
        self.assertEqual(set(self.page.rows), {(m, e) for m in ("sonnet55", "opus55", "gpt61sol") for e in EFFORTS})
        for (key, bundle, model) in (("opus55", OPUS, "opus55"), ("gpt61sol", SOL, "gpt61sol")):
            groups, econ = published(bundle, model)
            for e in EFFORTS:
                g, c = groups[e], econ[e]
                expected = [label(e), f'{g["combined_33"]["mean"]:.2f}', f'\u00b1{g["combined_33"]["se"]:.2f}', str(g["n"]),
                            f'{g["code_quality"]["mean"]:.2f}', f'{g["passed_all_runs"]}/23', f'${c["usd"]["mean"]:.2f}', f'{c["minutes"]["mean"]:.1f}']
                self.assertEqual(self.page.rows[key, e][1:], expected, (key, e))
        for e, passed, usd, minutes in zip(EFFORTS, PASSED, USD, MINUTES):
            row = self.page.rows["sonnet55", e]
            self.assertEqual(row[1], label(e))
            self.assertEqual(row[-3:], [f"{passed}/23", f"${usd}", minutes], e)

    def test_findings_state_the_final_facts(self):
        findings = self.section("findings", "by-level")
        for needle in ("Sonnet 5.5 15, 17, 20, 22, 23", "Opus 5.5 17, 23, 22, 22, 21", "GPT-6.1 Sol 20, 22, 23, 23, 23",
                       "Sonnet 5.5 $2.39 to $5.52", "Opus 5.5 $1.70 to $8.75", "GPT-6.1 Sol $0.31 to $0.46",
                       "$394.77", "$475.33", "$44.33"):
            self.assertIn(needle, findings, needle)
        _, so = published(SOL, "gpt61sol")
        _, oe = published(OPUS, "opus55")
        ratios = [float(u) / so[e]["usd"]["mean"] for e, u in zip(EFFORTS, USD)]
        self.assertEqual((round(min(ratios)), round(max(ratios))), (7, 12))
        self.assertIn(f"{round(min(ratios))} to {round(max(ratios))} times less than Sonnet 5.5", findings)
        versus_opus = [float(u) / oe[e]["usd"]["mean"] for e, u in zip(EFFORTS, USD)]
        self.assertEqual(round(100 * (versus_opus[0] - 1)), 70)
        self.assertIn(f"{round(100 * (1 - max(versus_opus[2:])))}% to {round(100 * (1 - min(versus_opus[2:])))}% less from High up", findings)

    def test_fallback_row_matches_the_opus_bundle(self):
        _, econ = published(OPUS, "opus55")
        cells = "".join(f'<td>{econ[e]["solver_fallback_runs"]} of 23 runs, {econ[e]["opus48_reply_share_pct"]:.1f}% of replies</td>' for e in EFFORTS)
        self.assertIn(cells + "</tr>", self.page_html)
        self.assertIn('<tr data-fallback="sonnet55"><th scope="row">Claude Sonnet 5.5</th>' + "<td>none</td>" * 5, self.page_html)

    def test_methods_and_caveats(self):
        caveats = self.section("caveats", "data")
        for needle in ("same 23 Frontier v4 tasks", "Muse Spark 1.3 (Meta) and Grok 4.6 (xAI), neutral for both Anthropic and OpenAI",
                       "protocol v3.23", "v3.15", "v3.18", "Separate judging sessions",
                       "Claude Code\u2019s own list-price total", "API-equivalent at list prices", "token ledger", "ChatGPT Pro subscription",
                       "Claude Code 2.1.291 to 2.1.293", "Claude Code 2.1.280", "Codex 0.159.0", "harness confounded",
                       "refusal fallback on", "never used it", "Codex has no fallback", "tagged-worktree rule", "task hash bridge",
                       "identical to the original v3.3 and v3.4 protocols", "Cursor CLI (2026.10.01)", "(2026.09.02)",
                       "Opus 5.5 at High is judged on 22 of 23", "paddockcore, scored from Muse Spark 1.3 alone"):
            self.assertIn(needle, caveats, needle)
        self.assertIn('href="/benchmarks/swe-v4-sonnet55-v323.html#run-notes"', self.page_html)

    def test_card_is_pinned(self):
        # Copied byte for byte from the harness (docs/results/swe-v4-sonnet55-2026-10/sonnet55-vs-frontier.png), 2400 by 2445.
        card = ROOT / "assets/cards/swe-v4-sonnet55-vs-frontier.png"
        self.assertEqual(hashlib.sha256(card.read_bytes()).hexdigest(), "48450d8f54edd1682515866d8efe6cf967d48699b0ef65de7eb3ed8ebd68a0c8")
        self.assertIn('src="/assets/cards/swe-v4-sonnet55-vs-frontier.png" width="2400" height="2445"', self.page_html)
        self.assertIn('href="/assets/cards/swe-v4-sonnet55-vs-frontier.png" download', self.page_html)

    def test_get_the_data_links(self):
        for bundle in ("swe-v4-sonnet55-v323", "swe-v4-opus55-v315", "swe-v4-gpt61-sol-v318"):
            self.assertIn(f'href="https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/{bundle}"', self.page_html)
        for folder in ("swe-v4-sonnet55-2026-10", "swe-v4-opus55-2026-09", "swe-v4-gpt61-sol-2026-09"):
            self.assertIn(f'href="https://github.com/morganlinton/VulcanBench/tree/main/docs/results/{folder}"', self.page_html)
        self.assertIn('href="https://github.com/morganlinton/vulcanbench-opus55-traces"', self.page_html)
        self.assertIn('href="https://github.com/morganlinton/vulcanbench-sonnet55-traces"', self.page_html)

    def test_site_references(self):
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "benchmarks/swe-v4-sonnet55-v323.html",
                     "models/claude-sonnet-5-5.html", "models/claude-opus-5-5.html", "models/gpt-6-1-sol.html"):
            self.assertIn("swe-v4-sonnet55-vs-frontier.html", (ROOT / name).read_text(), name)
        self.assertIn(f"<loc>{FRONTIER_URL}</loc>", (ROOT / "sitemap.xml").read_text())
        feed_item = next(item for item in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{FRONTIER_URL}</link>" in item)
        self.assertIn("VulcanBench Frontier v4", feed_item)
        self.assertNotIn("SWE v4", feed_item)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-sonnet55-vs-frontier.html"), index.index("swe-v4-sonnet55-v323.html"))

    def test_page_links_resolve(self):
        # Fails until the card and the Sonnet bundle are in place.
        for link in self.page.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            self.assertTrue((ROOT / unquote(parsed.path).lstrip("/")).is_file(), link)

    @unittest.skipUnless(BUNDLE_READY, "the v3.23 bundle is not exported yet")
    def test_sonnet_rows_match_the_bundle(self):
        groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        for e in EFFORTS:
            g = groups[e]
            self.assertEqual(self.page.rows["sonnet55", e][2:6], [f'{g["combined_33"]["mean"]:.2f}', f'\u00b1{g["combined_33"]["se"]:.2f}', str(g["n"]),
                                                                 f'{g["code_quality"]["mean"]:.2f}'], e)


@unittest.skipUnless(BUNDLE_READY, "the v3.23 bundle is not exported yet")
class SonnetBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())
        cls.provenance = json.loads((DATA / "provenance.json").read_text())
        with (ROOT / "assets/data/swe-v4-sonnet55-v323-scores.csv").open(newline="") as source:
            cls.scores = {r["effort"]: r for r in csv.DictReader(source)}
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)

    def scored_mean(self, r, key):
        return statistics.mean(r["panels"][p][key] for p in r["scored_panels"])

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 115)
        self.assertEqual((self.runs["published"], self.runs["unpublished"]), (115, 0))
        self.assertTrue(all(r["judged_under"] == "code-quality-maintenance-v3.23" for r in self.rows))
        self.assertTrue(all(r["finished"] and r["duration_s"] < 10800 for r in self.rows))  # no timeouts
        self.assertEqual(self.runs["weights"], {"functional": 0.5, "quality": 0.085, "security": 0.085, "code_quality": 0.33})
        self.assertEqual(self.runs["code_quality_split"], {"l1": 0.24, "l2": 0.09})
        for r in self.rows:
            self.assertFalse(r["solver_fallback"])
            self.assertEqual(list(r["replies_by_model"]), ["claude-sonnet-5-5"])
            self.assertEqual(list(r["token_usage"]["by_model"]), ["claude-sonnet-5-5"])
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            self.assertEqual(set(r["task_hash_bridge"]), {"recorded", "lock"})
            self.assertNotEqual(r["task_hash_bridge"]["recorded"], r["task_hash_bridge"]["lock"])
            self.assertGreater(r["estimated_usd"], 0)
            self.assertGreater(r["raw_tokens"], 0)
            reviewed = self.scored_mean(r, "reviewed_score")
            self.assertAlmostEqual(r["reviewed_score"], reviewed, places=9)
            if r["intent_recovery_redistributed"]:
                code_quality = reviewed
            else:
                intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in r["scored_panels"] if r["panels"][p]["intent_recovery"] is not None)
                self.assertAlmostEqual(r["intent_recovery"], intent, places=9)
                code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"] + .20 * code_quality / 100), places=9)
            for p in r["scored_panels"]:
                self.assertFalse(r["panels"][p]["reviewer_fallback"], r["run_id"])
                self.assertAlmostEqual(r["panels"][p]["reviewed_score"], (r["panels"][p]["readability"] + r["panels"][p]["maintainability"]) / 2, places=6)
            self.assertEqual(r["functional"] == 1, r["hidden_behaviours_fixed"] == r["hidden_behaviours"], r["run_id"])
        for effort, versions in CLI_VERSIONS.items():
            got = {}
            for r in self.rows:
                if r["effort"] == effort:
                    version = r["solver_cli_version"].split()[0]
                    got[version] = got.get(version, 0) + 1
            self.assertEqual(got, versions, effort)
        self.assertEqual(len({(r["effort"], r["task"]) for r in self.rows}), 115)

    def test_runs_csv_matches_runs_json(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), 115)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], places=6)
            self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])
            self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], places=3)
            self.assertAlmostEqual(float(c["code_quality"]), r["code_quality"], places=3)
            self.assertEqual(c["scored_panels"], "+".join(r["scored_panels"]))

    def test_groups_and_scores_csv_match_runs(self):
        self.assertEqual(set(self.groups), set(EFFORTS))
        for effort, g in self.groups.items():
            rs = [r for r in self.rows if r["effort"] == effort]
            self.assertEqual((len(rs), g["runs"]), (23, 23))
            for field, values in (("combined_33", [r["combined_33"] for r in rs]), ("code_quality", [r["code_quality"] for r in rs]),
                                  ("combined_20_profile", [r["combined_20_profile"] for r in rs]),
                                  ("readability", [self.scored_mean(r, "readability") for r in rs]),
                                  ("maintainability", [self.scored_mean(r, "maintainability") for r in rs]),
                                  ("minutes", [r["duration_s"] / 60 for r in rs]), ("usd", [r["estimated_usd"] for r in rs]),
                                  ("raw_tokens", [r["raw_tokens"] for r in rs])):
                mean, se = mean_se(values)
                self.assertAlmostEqual(g[field]["mean"], mean, places=6, msg=(effort, field))
                self.assertAlmostEqual(g[field]["se"], se, places=6, msg=(effort, field))
            row = self.scores[effort]
            for column, field in (("combined_33", "combined_33"), ("code_quality", "code_quality"), ("mean_minutes", "minutes"), ("mean_usd", "usd")):
                self.assertAlmostEqual(float(row[column]), g[field]["mean"], places=4, msg=(effort, column))
        g = self.groups
        self.assertEqual([g[e]["passed_all_runs"] for e in EFFORTS], PASSED)
        self.assertEqual([g[e]["hidden_behaviours_fixed"] for e in EFFORTS], HIDDEN)
        self.assertEqual([f'{g[e]["minutes"]["mean"]:.1f}' for e in EFFORTS], MINUTES)
        self.assertEqual([f'{g[e]["usd"]["mean"]:.2f}' for e in EFFORTS], USD)

    def test_page_tables_match_groups(self):
        g = self.groups
        for effort in EFFORTS:
            expected = [f'{g[effort]["combined_33"]["mean"]:.2f}', f'{g[effort]["combined_33"]["se"]:.2f}', f'{g[effort]["combined_20_profile"]["mean"]:.2f}',
                        f'{g[effort]["code_quality"]["mean"]:.2f}', f'{g[effort]["readability"]["mean"]:.1f}', f'{g[effort]["maintainability"]["mean"]:.1f}',
                        f'{g[effort]["intent_recovery"]["mean"]:.1f}', f'{g[effort]["n"]}/23']
            self.assertEqual(self.page.rows["sonnet55", effort][2:10], expected, effort)
        for name, key, d in (("Combined score", "combined_33", 2), ("Code quality", "code_quality", 2), ("Human readability", "readability", 1),
                             ("Maintainability", "maintainability", 1), ("Intent recovery", "intent_recovery", 1)):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e][key]['mean']:.{d}f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        for name, p in (("Rated by Muse Spark 1.3", "muse"), ("Rated by Grok 4.6", "grok")):
            self.assertIn(f'<th scope="row">{name}</th>' + "".join(f"<td>{g[e]['by_panel'][p]['mean']:.1f}</td>" for e in EFFORTS) + "</tr>", self.page_html, name)
        self.assertIn('<th scope="row">Standard error</th>' + "".join(f"<td>{g[e]['combined_33']['se']:.2f}</td>" for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Standard error of Code quality</th>' + "".join(f"<td>{g[e]['code_quality']['se']:.2f}</td>" for e in EFFORTS), self.page_html)
        start = self.page_html.index('<tr data-compare="combined-sonnet55">')
        self.assertIn("".join(f"<td>{g[e]['combined_33']['mean']:.2f}</td>" for e in EFFORTS) + "</tr>", self.page_html[start:start + 400])

    def test_economics(self):
        t = self.econ["totals"]["sonnet55"]
        self.assertEqual(t["runs"], 115)
        self.assertEqual((f'{t["usd"]:.2f}', f'{t["usd"] / 115:.2f}'), ("394.77", "3.43"))
        rates = self.econ["rates_per_million"]["claude-sonnet-5-5"]
        self.assertEqual((rates["cache_hit_pricing_table"], rates["cache_hit_caching_section"]), (0.20, 0.10))
        self.assertEqual(self.econ["pricing_verified"], "2026-10-07")

    def test_calibration_and_protocol_record(self):
        for judge, gate in (("muse", "g11_repeatability"), ("grok", "g04_formatting_is_presentation")):
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertTrue(record["allowance_used"])
            self.assertEqual(record["failing_gates"], [gate])
            self.assertEqual(record["call_count"], 80)
            self.assertEqual(len(record["gates"]), 20)
            self.assertEqual(record["allowance"], {"max_failing_gates": 1, "max_shortfall": 0.5})
        self.assertEqual(self.protocols["protocol_ids"], {"muse": "code-quality-maintenance-v3.23", "grok": "code-quality-maintenance-v3.23"})
        population = self.protocols["population"]
        self.assertEqual((population["excluded"], population["missing"]), ([], []))
        self.assertEqual(population["cells"], {f"sonnet55/{e}": 23 for e in EFFORTS})
        pins = self.protocols["judge_pins"]
        self.assertEqual(pins["source"], "docs/judging/judge-pins-v3.json")
        self.assertEqual(pins["original_protocol_sha256"], {"v3.3": "b82da5987bb555443c9006e51e5a4d555c41858dc710140f0571bd90ed8a5eec",
                                                            "v3.4": "1d80e0974526f8d825f14921c9102c8eda47ec312a0981783475149e31fd8524"})
        self.assertIn("2026.10.01-e373342", pins["cursor"])
        self.assertIn("2026.09.02-c22c1a3", pins["cursor"])
        self.assertTrue(pins["settings_match_v3_4_bundle"])
        v34 = json.loads((FABLE / "judge-protocols.json").read_text())["scored_panel"]
        self.assertEqual(self.protocols["scored_panel"], v34)
        self.assertEqual(pins["binary_sha256"]["muse"], v34["muse"]["binary_sha256"])
        self.assertEqual(self.protocols["task_hash_bridge"]["file"], "docs/judging/task-hash-bridge-sonnet55.json")
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("SWE v4", text, name)
            self.assertNotIn("ultra", text.lower(), name)

    def test_cards_are_pinned_and_placed(self):
        for name, sha in CARDS.items():
            self.assertEqual(hashlib.sha256((ROOT / "assets/cards" / name).read_bytes()).hexdigest(), sha, name)
            self.assertIn(f'href="/assets/cards/{name}" download', self.page_html, name)
            self.assertIn(f'src="/assets/cards/{name}"', self.page_html, name)
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-sonnet55-v323-report.pdf").stat().st_size, 100_000)
        self.assertIn("PDF, 10 pages", self.page_html)

    def test_scores_appear_everywhere(self):
        figures = [f'{self.groups[e]["combined_33"]["mean"]:.2f}' for e in EFFORTS]
        for name in ("benchmarks.html", "index.html", "feed.xml", "llms.txt", "models/claude-sonnet-5-5.html", "leaderboard.html",
                     "assets/data/swe-v4-sonnet55-v323/README.md"):
            text = (ROOT / name).read_text()
            for figure in figures:
                self.assertIn(figure, text, (name, figure))


if __name__ == "__main__":
    unittest.main()
