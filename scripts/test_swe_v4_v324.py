"""Stdlib checks for the v3.24 Claude Haiku 5.5 bundle, its report page, its comparison page, its cards and the site links to them."""

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
DATA = ROOT / "assets/data/swe-v4-haiku55-v324"
PAGE = ROOT / "benchmarks/swe-v4-haiku55-v324.html"
COMPARE = ROOT / "benchmarks/swe-v4-haiku55-vs-frontier.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-haiku55-v324.html"
COMPARE_URL = "https://vulcanbench.com/benchmarks/swe-v4-haiku55-vs-frontier.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "grok")
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
PASSED = [13, 13, 17, 22, 22]
JUDGED = [23, 22, 23, 22, 21]
CLI_VERSIONS = {"low": {"2.1.293": 22, "2.1.294": 1}, "medium": {"2.1.294": 3, "2.1.295": 20}, "high": {"2.1.295": 23},
                "extra-high": {"2.1.295": 2, "2.1.296": 21}, "max": {"2.1.296": 23}}
UNSCORED = {("medium", "legacy-paddockcore-binary-parity"), ("extra-high", "legacy-paddockcore-binary-parity"),
            ("max", "legacy-paddockcore-binary-parity"), ("max", "legacy-codeccore-binary-parity")}
TIER = {"floor": (0.10, 0.125, 0.01, 0.50), "ceiling": (0.50, 0.625, 0.05, 2.50)}
# Copied byte for byte from the harness (docs/results/swe-v4-haiku55-2026-10).
CARDS = {
    "swe-v4-haiku55-v324.png": ("da91e92a062ef7a723b731fec7ada551241228e5af2fa7dde10d209f5be980bd", 2235),
    "swe-v4-haiku55-vs-sonnet55.png": ("ec5071355ff1f85263dc144cf59e8c3a7a594775ecb5052b841dc55acaf325db", 2340),
    "swe-v4-haiku55-vs-gpt61sol.png": ("e68316c3a67e77b10e721d48b380260c0c0884740d06313aaa9a2122c623c35a", 2340),
    "swe-v4-haiku55-vs-luna.png": ("9518aa1c96665f70ab21e62e0c0c5eaf022235074e71533ab553bc60fc03107b", 2340),
}
TOUCHED = ("benchmarks/swe-v4-haiku55-v324.html", "benchmarks/swe-v4-haiku55-vs-frontier.html", "models/claude-haiku-5-5.html",
           "models/claude-haiku-4-5.html", "models/claude-sonnet-5-5.html", "models/claude-opus-5-5.html", "models/gpt-6-1-sol.html",
           "models/gpt-6-luna.html", "benchmarks.html", "index.html", "feed.xml", "llms.txt", "leaderboard.html", "README.md",
           "assets/data/README.md", "assets/data/swe-v4-haiku55-v324/README.md", "assets/data/swe-v4-haiku55-v324/REPRODUCING.md",
           "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v324.py")


def plain(markup):
    """Visible text: tags dropped, entities decoded."""
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def label(effort):
    return effort.replace("-", " ").capitalize().replace("Extra high", "Extra-high")


def bundle(name, model):
    groups = {g["effort"]: g for g in json.loads((ROOT / "assets/data" / name / "groups.json").read_text()) if g["model"] == model}
    econ = {g["effort"]: g for g in json.loads((ROOT / "assets/data" / name / "economics.json").read_text())["groups"] if g["model"] == model}
    return groups, econ


def links_resolve(test, parser):
    for link in parser.links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            continue
        if parsed.path:
            test.assertTrue((ROOT / unquote(parsed.path).lstrip("/")).is_file(), link)
        elif parsed.fragment:
            test.assertIn(parsed.fragment, parser.ids)


class HaikuBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = json.loads((DATA / "runs.json").read_text())
        cls.rows = cls.runs["rows"]
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.calibration = json.loads((DATA / "calibration.json").read_text())
        cls.protocols = json.loads((DATA / "judge-protocols.json").read_text())
        cls.econ = json.loads((DATA / "economics.json").read_text())
        cls.provenance = json.loads((DATA / "provenance.json").read_text())

    def test_every_run_recomputes(self):
        self.assertEqual(len(self.rows), 115)
        self.assertEqual((self.runs["published"], self.runs["unpublished"], self.runs["excluded"]), (111, 1, 3))
        self.assertEqual({(r["effort"], r["task"]) for r in self.rows if r["judged"] != "published"}, UNSCORED)
        for r in self.rows:
            self.assertTrue(r["finished"] and r["duration_s"] < 10800)
            self.assertFalse(r["solver_fallback"])
            self.assertEqual(list(r["replies_by_model"]), ["claude-haiku-5-5"])
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            usage = r["token_usage"]["by_model"]["claude-haiku-5-5"]
            for tier, (inp, write, read, out) in TIER.items():
                priced = (usage["input_tokens"] * inp + usage["cache_creation_tokens"] * write + usage["cache_read_tokens"] * read
                          + usage["output_tokens"] * out) / 1e6
                self.assertAlmostEqual(r[f"usd_{tier}"], priced, places=9)
            self.assertGreater(r["estimated_usd"], r["usd_floor"])
            self.assertLessEqual(r["estimated_usd"], 1.005 * r["usd_ceiling"])
            if r["judged"] != "published":
                self.assertIsNone(r["combined_33"])
                self.assertIsNone(r["code_quality"])
                self.assertEqual(r["functional"], 1.0 if "codeccore" in r["task"] else 0.0)
                continue
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
            code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            self.assertAlmostEqual(r["combined_33"], 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"]
                                                            + .33 * code_quality / 100), places=9)
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"]
                                                                    + .20 * code_quality / 100), places=9)
        for effort, versions in CLI_VERSIONS.items():
            got = {}
            for r in self.rows:
                if r["effort"] == effort:
                    version = r["solver_cli_version"].split()[0]
                    got[version] = got.get(version, 0) + 1
            self.assertEqual(got, versions, effort)
        self.assertEqual(sorted((r["effort"], r["task"]) for r in self.rows if r["estimated_usd"] > r["usd_ceiling"]),
                         [("max", "legacy-depotcore-binary-parity"), ("medium", "legacy-lodgecore-binary-parity")])

    def test_runs_csv_and_scores_csv(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), 115)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], places=6)
            self.assertAlmostEqual(float(c["usd_floor"]), r["usd_floor"], places=6)
            self.assertEqual(c["judged"], {"published": "published"}.get(r["judged"], "unpublished" if r["judged"].startswith("unpublished") else "not judged"))
        with (ROOT / "assets/data/swe-v4-haiku55-v324-scores.csv").open(newline="") as source:
            scores = {r["effort"]: r for r in csv.DictReader(source)}
        for e, g in self.groups.items():
            self.assertAlmostEqual(float(scores[e]["combined_33"]), g["combined_33"]["mean"], places=4)
            self.assertEqual(int(scores[e]["passed_of_23"]), g["passed_all_runs"])

    def test_groups_match_runs(self):
        for i, e in enumerate(EFFORTS):
            g = self.groups[e]
            rs = [r for r in self.rows if r["effort"] == e]
            judged = [r for r in rs if r["judged"] == "published"]
            self.assertEqual((g["runs"], g["n"], len(judged)), (23, JUDGED[i], JUDGED[i]))
            self.assertEqual(g["passed_all_runs"], PASSED[i])
            for field, values in (("combined_33", [r["combined_33"] for r in judged]), ("code_quality", [r["code_quality"] for r in judged])):
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(values), places=9)
                self.assertAlmostEqual(g[field]["se"], statistics.stdev(values) / len(values) ** .5, places=9)
            for field, key in (("minutes", lambda r: r["duration_s"] / 60), ("usd", lambda r: r["estimated_usd"]),
                               ("usd_floor", lambda r: r["usd_floor"]), ("usd_ceiling", lambda r: r["usd_ceiling"])):
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(key(r) for r in rs), places=9)
        self.assertEqual([round(self.groups[e]["combined_33"]["mean"], 2) for e in EFFORTS], [84.42, 84.03, 88.01, 91.83, 92.16])
        t = self.econ["totals"]["haiku55"]
        self.assertEqual((f'{t["usd"]:.2f}', f'{t["usd_floor"]:.2f}', f'{t["usd_ceiling"]:.2f}'), ("138.31", "31.10", "155.50"))

    def test_judges_and_pins(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertTrue(record["passed"])
            self.assertFalse(record["allowance_used"])
            self.assertEqual(record["failing_gates"], [])
            self.assertEqual(record["call_count"], 80)
        pins = self.protocols["judge_pins"]
        self.assertEqual({v: x["sha256"] for v, x in pins["settings_sources"].items()},
                         {"v3.3": "b82da5987bb555443c9006e51e5a4d555c41858dc710140f0571bd90ed8a5eec",
                          "v3.4": "1d80e0974526f8d825f14921c9102c8eda47ec312a0981783475149e31fd8524"})
        self.assertEqual((pins["cursor_version"]["version"], pins["cursor_version"]["digest"]),
                         ("2026.10.01-e373342", "dedbb877a8405b20e38a3dc32f38bf614bcd96d6e557f73eb6e99ff8c87b8a73"))
        self.assertEqual(self.protocols["scored_panel"], json.loads((ROOT / "assets/data/swe-v4-astra-fable51-v34/judge-protocols.json").read_text())["scored_panel"])
        self.assertEqual(self.protocols["display_name"]["accepted_renames_recorded"], 426)
        self.assertEqual(self.protocols["second_attempts"], {"muse": 9, "grok": 5})
        [unpublished] = self.protocols["unpublished"]
        self.assertEqual((unpublished["effort"], unpublished["task"], unpublished["panel"], unpublished["stage"]),
                         ("max", "legacy-codeccore-binary-parity", "grok", "probe"))
        [recovery] = self.protocols["operator_recoveries"]
        self.assertEqual((recovery["effort"], recovery["task"], recovery["rule"]), ("extra-high", "legacy-vaultcore-binary-parity", "recover_excerpts"))
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/", "SWE v4", "no model on the board"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("ultra", text.lower(), name)


class HaikuPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)
        cls.groups, cls.econ = bundle("swe-v4-haiku55-v324", "haiku55")

    def section(self, start, end):
        return plain(self.page_html[self.page_html.index(f'id="{start}"'):self.page_html.index(f'id="{end}"')])

    def test_no_placeholders_left(self):
        left = {name: (ROOT / name).read_text().count(PLACEHOLDER) for name in TOUCHED}
        self.assertEqual({name: n for name, n in left.items() if n}, {})

    def test_structure_writing_and_links(self):
        self.assertEqual(self.page.structure_errors, [])
        self.assertEqual(self.page.structure, [])
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra", "no model on the board", "no model on this board"):
            self.assertNotIn(mark, self.text, mark)
        self.assertIn(f'<link rel="canonical" href="{URL}">', self.page_html)
        self.assertIn("intent/post?text=Claude%20Haiku%205.5%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertIn("labs other than Anthropic", self.text)
        links_resolve(self, self.page)

    def test_tables_match_the_bundle(self):
        g, c = self.groups, self.econ
        self.assertEqual(set(self.page.rows), {("haiku55", e) for e in EFFORTS})
        for e in EFFORTS:
            row = self.page.rows["haiku55", e]
            self.assertEqual(row[1:4], [label(e), f'{g[e]["combined_33"]["mean"]:.2f}', f'{g[e]["combined_33"]["se"]:.2f}'])
            self.assertEqual(row[-3:], [f'{g[e]["n"]}/23' + ("*" if g[e]["n"] < 23 else ""), f'{g[e]["passed_all_runs"]}/23', f'{g[e]["minutes"]["mean"]:.1f}'])
            cells = (f'<td>23</td><td>${c[e]["usd"]["mean"]:.2f}</td><td>${c[e]["usd"]["se"]:.2f}</td><td>${c[e]["usd_floor"]["mean"]:.2f}</td>'
                     f'<td>${c[e]["usd_ceiling"]["mean"]:.2f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}', self.page_html, e)
        self.assertIn('<th scope="row">Judged runs</th>' + "".join(f"<td>{n}</td>" for n in JUDGED), self.page_html)
        self.assertIn('<th scope="row">Tasks passed</th>' + "".join(f"<td>{p}/23</td>" for p in PASSED), self.page_html)

    def test_required_disclosures(self):
        notes = self.section("run-notes", "reproduce")
        for needle in ("Low ran 22 tasks on 2.1.293 and 1 on 2.1.294", "Medium 3 on 2.1.294 and 20 on 2.1.295", "High on 2.1.295",
                       "Extra-high 2 on 2.1.295 and 21 on 2.1.296", "Max on 2.1.296", "Refusal fallback on, never used",
                       "October 9, 15:43 UTC, to October 10, 09:20 UTC", "October 10, 19:48 UTC, to October 11, 15:50 UTC", "timing is intact",
                       "tagged run worktree", "No hash bridge"):
            self.assertIn(needle, notes, needle)
        unscored = self.section("not-judged", "cost")
        for needle in ("safety classifier", "empty patch", "count as failed tasks", "Max codeccore is unpublished", "not valid JSON",
                       "counts as a passed task", "v3.7 and v3.17"):
            self.assertIn(needle, unscored, needle)
        cost = self.section("cost", "board")
        for needle in ("five times as much", "floor", "ceiling", "cli_reported_cost_usd", "1-hour"):
            self.assertIn(needle, cost, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("recovered from the owner’s private backup", "b82da598", "1d80e097", "same binary as every earlier round",
                       "Cursor CLI 2026.10.01-e373342, pinned by version for the whole round", "same Cursor CLI that judged Claude Sonnet 5.5",
                       "“Grok 4.6 Medium”", "“Cursor Grok 4.6 Medium”", "426 times", "passed every gate with no allowance used",
                       "labs other than Anthropic"):
            self.assertIn(needle, judges, needle)
        self.assertIn("never compared with Routine v1 Code quality", self.text)
        board = self.section("board", "code-quality")
        self.assertIn("ranks 4th of the board’s 63", board)
        self.assertIn("behind only Grok 4.7’s three top levels, which are judged by a different panel", board)

    def test_cards_pinned(self):
        for name, (sha, height) in CARDS.items():
            self.assertEqual(hashlib.sha256((ROOT / "assets/cards" / name).read_bytes()).hexdigest(), sha, name)
        self.assertIn('src="/assets/cards/swe-v4-haiku55-v324.png" width="2400" height="2235"', self.page_html)
        self.assertGreater((ROOT / "assets/reports/vulcanbench-swe-v4-haiku55-v324-report.pdf").stat().st_size, 100_000)
        self.assertIn("PDF, 10 pages", self.page_html)


class HaikuComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_html = COMPARE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)

    def section(self, start, end):
        return plain(self.page_html[self.page_html.index(f'id="{start}"'):self.page_html.index(f'id="{end}"')])

    def test_structure_writing_and_links(self):
        self.assertEqual(self.page.structure_errors, [])
        self.assertEqual(self.page.structure, [])
        for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra", "no model on the board", "best model"):
            self.assertNotIn(mark, self.text, mark)
        self.assertIn(f'<link rel="canonical" href="{COMPARE_URL}">', self.page_html)
        self.assertIn("VulcanBench%20Frontier%20v4", self.page_html)
        links_resolve(self, self.page)
        for name, (_, height) in CARDS.items():
            if name != "swe-v4-haiku55-v324.png":
                self.assertIn(f'src="/assets/cards/{name}" width="2400" height="{height}"', self.page_html)

    def test_rows_equal_the_four_bundles(self):
        models = {"haiku55": "swe-v4-haiku55-v324", "sonnet55": "swe-v4-sonnet55-v323", "gpt61sol": "swe-v4-gpt61-sol-v318", "gpt6luna": "swe-v4-gpt6-luna-v316"}
        self.assertEqual(set(self.page.rows), {(m, e) for m in models for e in EFFORTS})
        for key, name in models.items():
            groups, econ = bundle(name, key)
            for e in EFFORTS:
                g, c = groups[e], econ[e]
                expected = [label(e), f'{g["combined_33"]["mean"]:.2f}', f'±{g["combined_33"]["se"]:.2f}', str(g["n"]), f'{g["code_quality"]["mean"]:.2f}',
                            f'{g["passed_all_runs"]}/23', f'${c["usd"]["mean"]:.2f}', f'{c["minutes"]["mean"]:.1f}']
                self.assertEqual(self.page.rows[key, e][1:], expected, (key, e))
        luna, _ = bundle("swe-v4-gpt6-luna-v316", "gpt6luna")
        for e in EFFORTS:
            self.assertIn(f'<tr data-luna="{e}"><th scope="row">{label(e)}</th><td>{luna[e]["n"]}</td><td>{luna[e]["timeouts"]}</td>', self.page_html)
        self.assertIn(f'{luna["max"]["combined_timeouts_zero"]["mean"]:.2f} &plusmn;', self.page_html)

    def test_findings_are_as_strong_as_the_data(self):
        h, hc = bundle("swe-v4-haiku55-v324", "haiku55")
        s, sc = bundle("swe-v4-sonnet55-v323", "sonnet55")
        findings = self.section("findings", "by-level")
        gap = h["max"]["combined_33"]["mean"] - s["max"]["combined_33"]["mean"]
        self.assertLess(abs(gap), h["max"]["combined_33"]["se"])
        self.assertIn(f"a {gap:.2f}-point gap, far inside the error", findings)
        self.assertIn(f'about {sc["max"]["usd"]["mean"] / hc["max"]["usd"]["mean"]:.1f} times less at Max', findings)
        self.assertIn("passes fewer tasks from Low to High (13, 13 and 17 against 15, 17 and 20)", findings)
        self.assertIn("Sol solves more tasks at every level", findings)
        self.assertIn("6 of its runs hit the 3-hour bound", findings)
        self.assertNotIn("better than Sonnet", findings)

    def test_caveats_and_data(self):
        caveats = self.section("caveats", "data")
        for needle in ("v3.24", "v3.23", "v3.18", "v3.16", "Cost bases differ", "Harnesses differ", "harness confounded",
                       "Claude Code 2.1.293 to 2.1.296", "Codex 0.159.0", "Codex 0.155.0", "safety classifier", "timeouts are unpriced",
                       "paused twice", "recovered original v3.3 and v3.4 protocols", "Routine v1 Code quality", "labs other than Anthropic and OpenAI"):
            self.assertIn(needle, caveats, needle)
        for bundle_dir in ("swe-v4-haiku55-v324", "swe-v4-sonnet55-v323", "swe-v4-gpt61-sol-v318", "swe-v4-gpt6-luna-v316"):
            self.assertIn(f'href="https://github.com/morganlinton/VulcanBenchCOM/tree/main/assets/data/{bundle_dir}"', self.page_html)
        for folder in ("swe-v4-haiku55-2026-10", "swe-v4-sonnet55-2026-10", "swe-v4-gpt61-sol-2026-09", "swe-v4-gpt6-luna-2026-09"):
            self.assertIn(f'href="https://github.com/morganlinton/VulcanBench/tree/main/docs/results/{folder}"', self.page_html)
        for traces in ("vulcanbench-haiku55-traces", "vulcanbench-sonnet55-traces"):
            self.assertIn(f'href="https://github.com/morganlinton/{traces}"', self.page_html)

    def test_site_references(self):
        for page in ("swe-v4-haiku55-v324.html", "swe-v4-haiku55-vs-frontier.html"):
            for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "models/claude-haiku-5-5.html"):
                self.assertIn(page, (ROOT / name).read_text(), (name, page))
        for name in ("models/claude-sonnet-5-5.html", "models/gpt-6-1-sol.html", "models/gpt-6-luna.html"):
            self.assertIn("swe-v4-haiku55-vs-frontier.html", (ROOT / name).read_text(), name)
        for name in ("models/claude-haiku-4-5.html", "models/claude-sonnet-5-5.html", "models/claude-opus-5-5.html"):
            self.assertIn('href="claude-haiku-5-5.html"', (ROOT / name).read_text(), name)
        self.assertIn('href="models/claude-haiku-5-5.html"', (ROOT / "benchmarks.html").read_text())
        for page_url in (URL, COMPARE_URL):
            self.assertIn(f"<loc>{page_url}</loc>", (ROOT / "sitemap.xml").read_text())
            item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{page_url}</link>" in i)
            self.assertIn("VulcanBench Frontier v4", item)
            self.assertNotIn(chr(0x2014), item)
        self.assertIn('<a href="benchmarks/swe-v4-haiku55-v324.html">Haiku 5.5</a>', (ROOT / "leaderboard.html").read_text())
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-haiku55-vs-frontier.html"), index.index("swe-v4-sonnet55-vs-frontier.html"))


if __name__ == "__main__":
    unittest.main()
