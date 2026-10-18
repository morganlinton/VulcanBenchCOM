"""Stdlib checks for the Muse Wonder Full bundle (v3.26 to v3.26.3), its report page, its card, its model page and the site links to them."""

import csv
import hashlib
import html
import json
import re
import statistics
import unittest
from pathlib import Path

from check_benchmark_index import IndexParser
from test_swe_v4_v324 import label, links_resolve, plain

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/swe-v4-musewonder-full-v326"
PAGE = ROOT / "benchmarks/swe-v4-musewonder-full-v326.html"
MODEL_PAGE = ROOT / "models/muse-wonder-full.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-musewonder-full-v326.html"
MODEL_URL = "https://vulcanbench.com/models/muse-wonder-full.html"
TRACES = "https://github.com/morganlinton/vulcanbench-musewonder-full-traces"
EFFORTS = ("low", "medium", "high", "extra-high")
PANELS = ("claude", "sol")
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
RUNS = 92
PASSED = [18, 21, 19, 19]
JUDGED = [23, 23, 22, 22]
TIMEOUTS = {("high", "legacy-paddockcore-binary-parity"), ("extra-high", "legacy-depotcore-binary-parity")}
VERSIONS = {"low": {"1.4.6": 23}, "medium": {"1.4.6": 21, "1.4.9": 2}, "high": {"1.4.9": 23}, "extra-high": {"1.4.9": 23}}
ROUNDS = {"low": {"v3.26": 23}, "medium": {"v3.26": 21, "v3.26.1": 2}, "high": {"v3.26.2": 22}, "extra-high": {"v3.26.3": 22}}
WONDER = (4.00, 0.20, 20.00)  # Muse Wonder 1.0 list price per million: uncached input, cached input, output
SPARK = (1.25, 0.15, 4.25)  # Muse Spark 1.3 list price, for Muse Code 1.4.9's reminder observers
# The harness card (docs/results/swe-v4-musewonder-full-2026-10/musewonder-full-vs-frontier.json), per level.
CARD = {
    "low": {"combined": 86.95102934239672, "combined_se": 1.1638903461497077, "zero": None, "functional": 95.82478260869566,
            "usd": 3.9315751304347826, "minutes": 27.28644927536232, "claude": 58.8768115942029, "sol": 75.9963768115942},
    "medium": {"combined": 88.26905476045692, "combined_se": 0.9473842794010099, "zero": None, "functional": 98.5508695652174,
               "usd": 4.085145954347826, "minutes": 27.33825, "claude": 58.242753623188406, "sol": 75.27173913043478},
    "high": {"combined": 88.18992946144763, "combined_se": 1.0433045559797345, "zero": 84.35558470225426, "functional": 93.19521739130435,
             "usd": 4.719412567391305, "minutes": 36.17281014492754, "claude": 59.56439393939394, "sol": 77.08333333333333},
    "extra-high": {"combined": 87.58899923939697, "combined_se": 0.964079486318422, "zero": 83.78078188116231, "functional": 93.16782608695652,
                   "usd": 5.081019567391304, "minutes": 33.337392028985505, "claude": 57.765151515151516, "sol": 74.90530303030303},
}
# Copied byte for byte from the harness (docs/results/swe-v4-musewonder-full-2026-10/musewonder-full-vs-frontier.png).
CARD_PNG = ("swe-v4-musewonder-full-v326.png", "fbd9ed9221e51acae49af56ae420f0e6518ee6ddd6a7655e2d1adb13f684930e", 3450, 2370)
TOUCHED = ("benchmarks/swe-v4-musewonder-full-v326.html", "models/muse-wonder-full.html", "models/muse-spark-1-2.html", "benchmarks.html",
           "index.html", "feed.xml", "llms.txt", "leaderboard.html", "README.md", "assets/data/README.md",
           "assets/data/swe-v4-musewonder-full-v326/README.md", "assets/data/swe-v4-musewonder-full-v326/REPRODUCING.md",
           "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v326.py")


class WonderBundleTests(unittest.TestCase):
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
        self.assertEqual((self.runs["published"], self.runs["timeouts"]), (90, 2))
        self.assertEqual({(r["effort"], r["task"]) for r in self.rows if r["judged"] != "published"}, TIMEOUTS)
        for r in self.rows:
            self.assertEqual(r["integrity_audit"]["contaminated"], False)
            self.assertEqual((r["integrity_audit"]["benchmark_data_paths"], r["integrity_audit"]["answer_key_paths"]), (0, 0))
            u = r["token_usage"]
            self.assertEqual(u["uncached_input_tokens"], u["input_tokens"] - u["cached_input_tokens"])
            self.assertEqual(r["raw_tokens"], u["input_tokens"] + u["output_tokens"])
            main = (u["uncached_input_tokens"] * WONDER[0] + u["cached_input_tokens"] * WONDER[1] + u["output_tokens"] * WONDER[2]) / 1e6
            self.assertAlmostEqual(r["main_model_usd"], main, places=9)
            rem = r["reminder_observer_usage"]
            if rem is None:
                self.assertEqual(r["reminder_usd"], 0.0)
            else:
                self.assertIn("1.4.9", r["solver_cli_version"])
                self.assertEqual(rem["model"], "muse-spark-1.3")
                spark = ((rem["input_tokens"] - rem["cached_input_tokens"]) * SPARK[0] + rem["cached_input_tokens"] * SPARK[1]
                         + rem["output_tokens"] * SPARK[2]) / 1e6
                self.assertAlmostEqual(r["reminder_usd"], spark, places=9)
            self.assertAlmostEqual(r["estimated_usd"], r["main_model_usd"] + r["reminder_usd"], places=9)
            if r["judged"] != "published":
                self.assertFalse(r["finished"])
                self.assertGreaterEqual(r["duration_s"], 10795)
                self.assertEqual((r["functional"], r["combined_timeouts_zero"], r["hidden_behaviours_fixed"]), (0.0, 0.0, 0))
                self.assertIsNone(r["combined_33"])
                self.assertIsNone(r["code_quality"])
                continue
            self.assertTrue(r["finished"] and r["duration_s"] < 10800)
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in PANELS)
            intent = statistics.mean(r["panels"][p]["intent_recovery"] for p in PANELS)
            code_quality = (0.24 * reviewed + 0.09 * intent) / 0.33
            self.assertAlmostEqual(r["code_quality"], code_quality, places=9)
            combined = 100 * (.5 * r["functional"] + .085 * r["automated_quality"] + .085 * r["security"] + .33 * code_quality / 100)
            self.assertAlmostEqual(r["combined_33"], combined, places=9)
            self.assertEqual(r["combined_timeouts_zero"], r["combined_33"])
            self.assertAlmostEqual(r["combined_20_profile"], 100 * (.5 * r["functional"] + .15 * r["automated_quality"] + .15 * r["security"]
                                                                    + .20 * code_quality / 100), places=9)
            for p in PANELS:
                alone = (0.24 * r["panels"][p]["reviewed_score"] + 0.09 * r["panels"][p]["intent_recovery"]) / 0.33
                self.assertAlmostEqual(r["combined_single_judge"][p], 100 * (.5 * r["functional"] + .085 * r["automated_quality"]
                                                                             + .085 * r["security"] + .33 * alone / 100), places=9)
        for effort in EFFORTS:
            rs = [r for r in self.rows if r["effort"] == effort]
            versions = {}
            for r in rs:
                v = r["solver_cli_version"].split()[2]
                versions[v] = versions.get(v, 0) + 1
            self.assertEqual(versions, VERSIONS[effort], effort)
            rounds = {}
            for r in rs:
                if r["judged_under"]:
                    k = r["judged_under"].removeprefix("code-quality-maintenance-")
                    rounds[k] = rounds.get(k, 0) + 1
            self.assertEqual(rounds, ROUNDS[effort], effort)
        self.assertEqual({r["task"] for r in self.rows if r["effort"] == "medium" and "1.4.9" in r["solver_cli_version"]},
                         {"legacy-cellarcore-binary-parity", "legacy-paddockcore-binary-parity"})
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e and r["overlap_minutes_logged"]) for e in EFFORTS[1:]], [9, 14, 5])
        self.assertTrue(all(r["overlap_minutes_logged"] is None for r in self.rows if r["effort"] == "low"))

    def test_runs_csv_and_scores_csv(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), RUNS)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            self.assertAlmostEqual(float(c["estimated_usd"]), r["estimated_usd"], delta=5.1e-7)
            self.assertEqual(c["judged"], "published" if r["judged"] == "published" else "timeout")
            self.assertAlmostEqual(float(c["combined_timeouts_zero"]), r["combined_timeouts_zero"], delta=5.1e-5)
        with (ROOT / "assets/data/swe-v4-musewonder-full-v326-scores.csv").open(newline="") as source:
            scores = {r["effort"]: r for r in csv.DictReader(source)}
        self.assertEqual(set(scores), set(EFFORTS))  # no max in Contributor mode
        for e, g in self.groups.items():
            self.assertAlmostEqual(float(scores[e]["combined_33"]), g["combined_33"]["mean"], places=4)
            self.assertAlmostEqual(float(scores[e]["combined_timeouts_zero"]), g["combined_timeouts_zero"]["mean"], places=4)
            self.assertEqual(int(scores[e]["passed_of_23"]), g["passed_all_runs"])

    def test_groups_match_runs_and_card(self):
        self.assertEqual(list(self.groups), list(EFFORTS))
        for i, e in enumerate(EFFORTS):
            g = self.groups[e]
            rs = [r for r in self.rows if r["effort"] == e]
            judged = [r for r in rs if r["judged"] == "published"]
            self.assertEqual((g["runs"], g["n"], len(judged)), (23, JUDGED[i], JUDGED[i]))
            self.assertEqual(g["passed_all_runs"], PASSED[i])
            for field, values in (("combined_33", [r["combined_33"] for r in judged]), ("code_quality", [r["code_quality"] for r in judged]),
                                  ("combined_timeouts_zero", [r["combined_timeouts_zero"] for r in rs])):
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(values), places=9)
                self.assertAlmostEqual(g[field]["se"], statistics.stdev(values) / len(values) ** .5, places=9)
            for field, key in (("minutes", lambda r: r["duration_s"] / 60), ("usd", lambda r: r["estimated_usd"]),
                               ("functional_all_runs", lambda r: 100 * r["functional"])):
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(key(r) for r in rs), places=9)
            c = CARD[e]
            self.assertAlmostEqual(g["combined_33"]["mean"], c["combined"], places=9)
            self.assertAlmostEqual(g["combined_33"]["se"], c["combined_se"], places=9)
            self.assertAlmostEqual(g["functional_all_runs"]["mean"], c["functional"], places=9)
            self.assertAlmostEqual(g["usd"]["mean"], c["usd"], places=9)
            self.assertAlmostEqual(g["minutes"]["mean"], c["minutes"], places=9)
            for p in PANELS:
                self.assertAlmostEqual(g["by_panel"][p]["mean"], c[p], places=9)
            if c["zero"] is None:
                self.assertEqual(g["timeouts"], 0)
                self.assertAlmostEqual(g["combined_timeouts_zero"]["mean"], g["combined_33"]["mean"], places=9)
            else:
                self.assertEqual(g["timeouts"], 1)
                self.assertAlmostEqual(g["combined_timeouts_zero"]["mean"], c["zero"], places=9)
        self.assertEqual([round(self.groups[e]["combined_33"]["mean"], 2) for e in EFFORTS], [86.95, 88.27, 88.19, 87.59])
        self.assertEqual([round(self.groups[e]["combined_timeouts_zero"]["mean"], 2) for e in EFFORTS], [86.95, 88.27, 84.36, 83.78])
        gap = statistics.mean(self.groups[e]["by_panel"]["sol"]["mean"] - self.groups[e]["by_panel"]["claude"]["mean"] for e in EFFORTS)
        self.assertEqual(round(gap), 17)
        t = self.econ["totals"]["musewonderfull"]
        self.assertEqual((t["runs"], f'{t["usd"]:.2f}', f'{t["reminder_usd"]:.2f}'), (RUNS, "409.79", "5.97"))

    def test_judges_and_rounds(self):
        for judge, protocol in (("claude", "code-quality-maintenance-v3.26"), ("sol", "code-quality-maintenance-v3.25")):
            record = self.calibration[judge]
            self.assertEqual(record["taken_under"], protocol)
            self.assertTrue(record["passed"])
            self.assertFalse(record["allowance_used"])
            self.assertEqual(record["failing_gates"], [])
            self.assertEqual(record["call_count"], 80)
        p = self.protocols
        self.assertEqual(set(p["scored_panel"]), set(PANELS))
        self.assertEqual(p["scored_panel"]["claude"]["model"], "claude-opus-5-5")
        self.assertEqual(p["scored_panel"]["sol"]["model"], "gpt-6.1-sol")
        self.assertEqual(set(p["excluded_judges"]), {"muse"})
        self.assertEqual(set(p["replaced_seats"]), {"grok"})
        self.assertEqual(p["grok_calls_before_stop"], {"calibration": 7})
        reused = p["exam_verdicts_reused"]
        self.assertEqual(set(reused), {"v3.26.1", "v3.26.2", "v3.26.3"})
        self.assertEqual(len({json.dumps(v, sort_keys=True) for v in reused.values()}), 1)  # one Opus verdict, one Sol verdict, every round
        self.assertEqual(reused["v3.26.2"]["sol"], p["scored_sibling"]["calibration_sha256"])
        primaries = {panel: sum(r.get("primary", 0) for r in rounds.values()) for panel, rounds in p["counted_calls"].items()}
        self.assertEqual(primaries, {"claude": 90, "sol": 90})
        self.assertEqual(len(p["operator_recoveries"]), 9)
        self.assertTrue(all(r["panel"] == "sol" and r["stage"] == "match" for r in p["operator_recoveries"]))
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/", "SWE v4", "no model on the board"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("ultra", text.lower(), name)


class WonderPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_html = PAGE.read_text()
        cls.page = IndexParser()
        cls.page.feed(cls.page_html)
        cls.text = plain(cls.page_html)
        cls.groups = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
        cls.econ = {g["effort"]: g for g in json.loads((DATA / "economics.json").read_text())["groups"]}

    def section(self, start, end):
        return plain(self.page_html[self.page_html.index(f'id="{start}"'):self.page_html.index(f'id="{end}"')])

    def test_no_placeholders_left(self):
        left = {name: (ROOT / name).read_text().count(PLACEHOLDER) for name in TOUCHED}
        self.assertEqual({name: n for name, n in left.items() if n}, {})

    def test_structure_writing_and_links(self):
        for markup, parser, text in ((self.page_html, self.page, self.text), (MODEL_PAGE.read_text(), None, None)):
            if parser is None:
                parser = IndexParser()
                parser.feed(markup)
                text = plain(markup)
            self.assertEqual(parser.structure_errors, [])
            self.assertEqual(parser.structure, [])
            self.assertEqual(len(parser.ids), len(set(parser.ids)))
            for mark in (chr(0x2014), chr(0x2013), "/Users/", "SWE v4", "ultra", "no model on the board", "no model on this board"):
                self.assertNotIn(mark, text, mark)
        links_resolve(self, self.page)
        model = IndexParser()
        model.feed(MODEL_PAGE.read_text())
        for link in model.links:  # relative links on the model page resolve from models/
            if "://" in link or link.startswith(("#", "mailto:")):
                continue
            self.assertTrue((ROOT / "models" / link.split("#")[0].split("?")[0]).resolve().is_file(), link)
        self.assertIn(f'<link rel="canonical" href="{URL}">', self.page_html)
        self.assertIn("intent/post?text=Muse%20Wonder%20Full%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertIn("Morgan Linton", self.text)
        self.assertNotIn(".pdf", self.page_html)
        for target in (TRACES, "https://github.com/morganlinton/VulcanBench", "/analysis/01-muse-wonder-full-vs-gpt-6-1-sol.html",
                       "/analysis/02-muse-wonder-full-combined-time-cost.html"):
            self.assertIn(f'href="{target}"', self.page_html)

    def test_tables_match_the_bundle(self):
        g, c = self.groups, self.econ
        self.assertEqual(set(self.page.rows), {("musewonderfull", e) for e in EFFORTS})
        for i, e in enumerate(EFFORTS):
            row = self.page.rows["musewonderfull", e]
            self.assertEqual(row[1:6], [label(e), f'{g[e]["combined_33"]["mean"]:.2f}', f'{g[e]["combined_33"]["se"]:.2f}',
                                        f'{g[e]["combined_timeouts_zero"]["mean"]:.2f}', f'{g[e]["combined_20_profile"]["mean"]:.2f}'])
            self.assertEqual(row[6], f'{g[e]["code_quality"]["mean"]:.2f}')
            self.assertEqual(row[-3:], [f'{g[e]["n"]}/23' + ("*" if g[e]["n"] < 23 else ""), f'{g[e]["passed_all_runs"]}/23', f'{g[e]["minutes"]["mean"]:.1f}'])
            cells = (f'<td>23</td><td>${c[e]["usd"]["mean"]:.2f}</td><td>${c[e]["usd"]["se"]:.2f}</td><td>${c[e]["reminder_usd_total"]:.2f}</td>'
                     f'<td>${c[e]["usd_total"]:.2f}</td><td>{c[e]["raw_tokens"]["mean"] / 1e6:.2f}M</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}', self.page_html, e)
        self.assertIn('<th scope="row">Judged runs</th>' + "".join(f"<td>{n}</td>" for n in JUDGED), self.page_html)
        self.assertIn('<th scope="row">Tasks passed</th>' + "".join(f"<td>{p}/23</td>" for p in PASSED), self.page_html)
        self.assertIn('<th scope="row">Timeouts counted as 0</th>' + "".join(f'<td>{g[e]["combined_timeouts_zero"]["mean"]:.2f}</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">Rated by Claude Opus 5.5</th>' + "".join(f'<td>{g[e]["by_panel"]["claude"]["mean"]:.1f}</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">Rated by GPT-6.1 Sol</th>' + "".join(f'<td>{g[e]["by_panel"]["sol"]["mean"]:.1f}</td>' for e in EFFORTS),
                      self.page_html)
        judges = self.section("judges", "run-notes")
        for e in EFFORTS:
            for p in PANELS:
                self.assertIn(f'{g[e]["combined_single_judge"][p]["mean"]:.2f}', judges, (e, p))

    def test_required_disclosures(self):
        unscored = self.section("not-judged", "cost")
        for needle in ("3-hour task bound", "count as failed tasks", "84.36", "83.78", "September 28, 2026"):
            self.assertIn(needle, unscored, needle)
        cost = self.section("cost", "board")
        for needle in ("no API price", "estimate", "Muse Wonder 1.0 list price", "$4.00", "$0.20", "$20.00", "Muse Spark 1.3", "$1.25",
                       "$0.15", "$4.25", "$5.97", "$409.79"):
            self.assertIn(needle, cost, needle)
        board = self.section("board", "code-quality")
        for needle in ("ranks 23rd of the board’s 67", "High ranks 25th, Extra-high 29th and Low 32nd", "not calibrated against each other"):
            self.assertIn(needle, board, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("Claude Opus 5.5", "GPT-6.1 Sol", "not neutral for a Meta submission", "Grok 4.7", "ran out of usage",
                       "scored sibling", "byte-identical", "no new exam", "about 17 points", "passed every gate with no allowance used",
                       "Nine of Sol’s answer-key matches"):
            self.assertIn(needle, judges, needle)
        notes = self.section("run-notes", "reproduce")
        for needle in ("Contributor mode", "Meta may train", "skill-reminder plugin was off", "offers no Max level", "1.4.6", "1.4.9",
                       "21 runs on 1.4.6 and 2 on 1.4.9", "weekly limit", "reset the quota", "transport error", "9 of the 23 Medium tasks",
                       "14 of the 23 High tasks", "5 Extra-high tasks", "145 of its 180 minutes", "clean rerun", "No hash bridge"):
            self.assertIn(needle, notes, needle)
        self.assertIn("never compared with Routine v1 Code quality", self.text)

    def test_card_pinned(self):
        name, sha, width, height = CARD_PNG
        data = (ROOT / "assets/cards" / name).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), sha)
        self.assertEqual((int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")), (width, height))
        self.assertIn(f'src="/assets/cards/{name}" width="{width}" height="{height}"', self.page_html)
        self.assertIn(f'<meta property="og:image:height" content="{height}">', self.page_html)


class WonderSiteTests(unittest.TestCase):
    def test_model_page_links_report_and_traces(self):
        markup = MODEL_PAGE.read_text()
        self.assertIn('href="../benchmarks/swe-v4-musewonder-full-v326.html"', markup)
        self.assertIn(f'href="{TRACES}"', markup)
        self.assertIn("Redacted agent traces", html.unescape(markup))
        self.assertIn(f'<link rel="canonical" href="{MODEL_URL}">', markup)
        for e, (combined, passed) in zip(EFFORTS, (("86.95", 18), ("88.27", 21), ("88.19", 19), ("87.59", 19))):
            self.assertIn(combined, markup, e)
        self.assertIn(f'href="{TRACES}"', PAGE.read_text())
        self.assertIn(f"{TRACES}", (DATA / "README.md").read_text())

    def test_site_references(self):
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "models/muse-wonder-full.html"):
            self.assertIn("swe-v4-musewonder-full-v326.html", (ROOT / name).read_text(), name)
        self.assertIn('href="models/muse-wonder-full.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn('href="muse-wonder-full.html"', (ROOT / "models/muse-spark-1-2.html").read_text())
        sitemap = (ROOT / "sitemap.xml").read_text()
        for page_url in (URL, MODEL_URL):
            self.assertIn(f"<loc>{page_url}</loc>", sitemap)
        item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in i)
        self.assertIn("VulcanBench Frontier v4", item)
        self.assertIn("17 Oct 2026", item)
        self.assertNotIn(chr(0x2014), item)
        leaderboard = (ROOT / "leaderboard.html").read_text()
        self.assertIn('<a href="benchmarks/swe-v4-musewonder-full-v326.html">Muse Wonder Full</a>', leaderboard)
        self.assertEqual(len(re.findall(r'data-model="musewonderfull" data-effort="[a-z-]+" data-best', leaderboard)), 4)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-musewonder-full-v326.html"), index.index("swe-v4-haiku55-vs-frontier.html"))


if __name__ == "__main__":
    unittest.main()
