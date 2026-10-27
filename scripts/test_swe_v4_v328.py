"""Stdlib checks for the Reflection Beam bundle (v3.28), its report page, its card, its model page and the site links to them."""

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
DATA = ROOT / "assets/data/swe-v4-beam-v328"
PAGE = ROOT / "benchmarks/swe-v4-beam-v328.html"
MODEL_PAGE = ROOT / "models/reflection-beam.html"
URL = "https://vulcanbench.com/benchmarks/swe-v4-beam-v328.html"
MODEL_URL = "https://vulcanbench.com/models/reflection-beam.html"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PANELS = ("muse", "sol")
PLACEHOLDER = "{{" + "TBD:"  # spelled in two parts so this line does not count itself
ENTITIES = ("&" + "mdash;", "&" + "ndash;")  # spelled in parts so this file carries no dash entity
RUNS = 115
JUDGED = [11, 20, 23, 23, 22]
PASSED = [0, 0, 0, 4, 6]
# The harness card's per-level table (docs/results/swe-v4-beam-2026-10/beam-vs-frontier-card-efforts.csv), to four places.
CARD = {"low": (39.5089, 2.3493, 72.9167, 0.3778), "medium": (44.7872, 1.9047, 70.4640, 1.9332),
        "high": (55.0072, 2.7933, 68.5216, 9.2017), "extra-high": (64.7163, 3.7590, 66.9498, 18.7529),
        "max": (63.9155, 4.1249, 65.8132, 22.4451)}
# Copied byte for byte from the harness (docs/results/swe-v4-beam-2026-10/beam-vs-frontier-card.png, 2400x1350), shown at 1600x900.
CARD_PNG = ("swe-v4-beam-v328.png", "7a7e6398f3171577a1ab7af582a75a2b853921b3943780d4b047d91cac4d2a38", 2400, 1350)
# Published comparator rows: Claude Opus 5.5 (v3.15), GPT-6.1 Sol (v3.18) and GPT-6 Astra (v3.4) bundles.
COMPARATORS = {"opus55": "swe-v4-opus55-v315", "gpt61sol": "swe-v4-gpt61-sol-v318", "astra": "swe-v4-astra-fable51-v34"}
TOUCHED = ("benchmarks/swe-v4-beam-v328.html", "models/reflection-beam.html", "benchmarks.html", "index.html", "feed.xml", "llms.txt",
           "leaderboard.html", "README.md", "assets/data/README.md", "assets/data/swe-v4-beam-v328/README.md",
           "assets/data/swe-v4-beam-v328/REPRODUCING.md", "scripts/test_swe_v4_board.py", "scripts/test_swe_v4_v328.py")


def code_quality(reviewed, intent):
    return reviewed if intent is None else (0.24 * reviewed + 0.09 * intent) / 0.33


def combined(r, cq, weight=0.33):
    other = (0.5 - weight) / 2
    return 100 * (.5 * r["functional"] + other * r["automated_quality"] + other * r["security"] + weight * cq / 100)


class BeamBundleTests(unittest.TestCase):
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
        self.assertEqual(dict(sorted((s, sum(r["status"] == s for r in self.rows)) for s in {r["status"] for r in self.rows})),
                         {"empty_patch": 3, "no_source_change": 12, "published": 99, "unreviewable": 1})
        for r in self.rows:
            self.assertTrue(r["finished"] and r["duration_s"] < 10800)
            self.assertEqual(r["integrity_audit"], {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False})
            self.assertEqual((r["solver_cli_version"], r["requested_model"], r["model_identity"]),
                             ("Mirror CLI 0.1.1", "Beam-1.0-501B-A23B", "harness-recorded"))
            self.assertEqual(r["requested_effort"], "xhigh" if r["effort"] == "extra-high" else r["effort"])
            self.assertEqual(r["source_tag"], "bench/2026-10-23-beam-mirror-frontier-v4")
            self.assertIsNone(r["cost_usd"])  # Reflection publishes no Beam price
            u = r["token_usage"]
            self.assertEqual(u["uncached_input_tokens"], u["input_tokens"] - u["cached_input_tokens"])
            self.assertEqual(r["raw_tokens"], u["input_tokens"] + u["output_tokens"])
            if r["status"] != "published":
                self.assertIsNone(r["combined_33"])
                self.assertNotEqual(r["judged"], "published")
                self.assertEqual(r["combined_no_code_zero"], None if r["status"] == "unreviewable" else 0.0)
                self.assertEqual(r["functional"] == 1, r["status"] == "unreviewable")  # hedgecore Max passed; no-code runs failed
                continue
            self.assertEqual((r["judged"], r["judged_under"]), ("published", "code-quality-maintenance-v3.28"))
            scored = r["scored_panels"]
            self.assertEqual(scored, ["muse"] if (r["effort"], r["task"]) == ("max", "legacy-payrollcore-binary-parity") else list(PANELS))
            reviewed = statistics.mean(r["panels"][p]["reviewed_score"] for p in scored)
            intents = [r["panels"][p]["intent_recovery"] for p in scored if r["panels"][p]["intent_recovery"] is not None]
            intent = statistics.mean(intents) if intents else None
            self.assertEqual(r["intent_recovery_redistributed"], intent is None)
            cq = code_quality(reviewed, intent)
            self.assertAlmostEqual(r["code_quality"], cq, places=9)
            self.assertAlmostEqual(r["combined_33"], combined(r, cq), places=9)
            self.assertEqual(r["combined_no_code_zero"], r["combined_33"])
            self.assertAlmostEqual(r["combined_20_profile"], combined(r, cq, 0.20), places=9)
            for p in PANELS:
                if p in scored:
                    alone = code_quality(r["panels"][p]["reviewed_score"], r["panels"][p]["intent_recovery"])
                    self.assertAlmostEqual(r["combined_single_judge"][p], combined(r, alone), places=9)
                else:
                    self.assertIsNone(r["combined_single_judge"][p])
        self.assertEqual([sum(1 for r in self.rows if r["effort"] == e) for e in EFFORTS], [23] * 5)
        self.assertEqual(sum(r["failed_model_requests"] for r in self.rows), 6)
        self.assertEqual(sum(1 for r in self.rows if r["intent_recovery_redistributed"]), 16)

    def test_runs_csv_and_scores_csv(self):
        with (DATA / "runs.csv").open(newline="") as source:
            csv_rows = {r["run_id"]: r for r in csv.DictReader(source)}
        self.assertEqual(len(csv_rows), RUNS)
        for r in self.rows:
            c = csv_rows[r["run_id"]]
            self.assertEqual(c["status"], r["status"])
            if r["combined_33"] is None:
                self.assertEqual(c["combined_33"], "")
            else:
                self.assertAlmostEqual(float(c["combined_33"]), r["combined_33"], delta=5.1e-5)
            self.assertEqual(int(c["raw_tokens"]), r["raw_tokens"])
        with (ROOT / "assets/data/swe-v4-beam-v328-scores.csv").open(newline="") as source:
            scores = {r["effort"]: r for r in csv.DictReader(source)}
        self.assertEqual(list(scores), list(EFFORTS))
        for e, g in self.groups.items():
            self.assertAlmostEqual(float(scores[e]["combined_33"]), g["combined_33"]["mean"], places=4)
            self.assertEqual(int(scores[e]["passed_of_23"]), g["passed_all_runs"])
            self.assertEqual(scores[e]["mean_usd"], "")

    def test_groups_match_runs_and_card(self):
        self.assertEqual(list(self.groups), list(EFFORTS))
        for i, e in enumerate(EFFORTS):
            g = self.groups[e]
            rs = [r for r in self.rows if r["effort"] == e]
            judged = [r for r in rs if r["status"] == "published"]
            self.assertEqual((g["runs"], g["n"], g["timeouts"]), (23, JUDGED[i], 0))
            self.assertEqual(g["passed_all_runs"], PASSED[i])
            self.assertEqual(g["passed_all_runs"], sum(r["functional"] == 1 for r in rs))
            for field, values in (("combined_33", [r["combined_33"] for r in judged]), ("code_quality", [r["code_quality"] for r in judged])):
                self.assertAlmostEqual(g[field]["mean"], statistics.mean(values), places=9)
                self.assertAlmostEqual(g[field]["se"], statistics.stdev(values) / len(values) ** .5, places=9)
            zero = [r["combined_no_code_zero"] for r in rs if r["combined_no_code_zero"] is not None]
            if any(r["status"] in ("empty_patch", "no_source_change") for r in rs):
                self.assertEqual(len(zero), 23)
                self.assertAlmostEqual(g["combined_no_code_zero"]["mean"], statistics.mean(zero), places=9)
            else:
                self.assertIsNone(g["combined_no_code_zero"])
            self.assertAlmostEqual(g["minutes"]["mean"], statistics.mean(r["duration_s"] / 60 for r in rs), places=9)
            self.assertIsNone(g["usd"])
            for value, expected in zip((g["combined_33"]["mean"], g["combined_33"]["se"], g["code_quality"]["mean"], g["minutes"]["mean"]), CARD[e]):
                self.assertAlmostEqual(value, expected, delta=5e-5, msg=e)
        self.assertEqual([round(self.groups[e]["combined_33"]["mean"], 2) for e in EFFORTS], [39.51, 44.79, 55.01, 64.72, 63.92])
        self.assertEqual([round(self.groups[e]["combined_no_code_zero"]["mean"], 2) for e in ("low", "medium")], [18.90, 38.95])
        self.assertEqual([round(self.groups[e]["functional_all_runs"]["mean"], 1) for e in EFFORTS], [0.9, 10.8, 35.6, 56.5, 58.3])
        self.assertEqual([f'{self.groups[e]["raw_tokens"]["mean"] / 1e6:.2f}' for e in EFFORTS], ["0.09", "0.44", "3.39", "12.42", "17.29"])
        gaps = [self.groups[e]["by_panel"]["sol"]["mean"] - self.groups[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
        self.assertEqual([round(x, 1) for x in gaps], [15.2, 17.6, 14.0, 10.7, 10.1])
        self.assertEqual(round(statistics.mean(gaps)), 14)
        t = self.econ["totals"]["beam"]
        self.assertEqual((t["runs"], t["usd"], t["failed_model_requests"], t["model_calls"]), (RUNS, None, 6, 11596))
        self.assertTrue(all(g["usd"] is None for g in self.econ["groups"]))

    def test_judges_and_protocol(self):
        for judge in PANELS:
            record = self.calibration[judge]
            self.assertEqual(record["taken_under"], "code-quality-maintenance-v3.28")
            self.assertTrue(record["passed"])
            self.assertFalse(record["allowance_used"])
            self.assertEqual(record["failing_gates"], [])
            self.assertEqual(record["call_count"], 80)
        p = self.protocols
        self.assertEqual(set(p["scored_panel"]), set(PANELS))
        self.assertEqual(p["scored_panel"]["muse"]["model"], "muse-spark-1.3")
        self.assertEqual((p["scored_panel"]["sol"]["model"], p["scored_panel"]["sol"]["effort"], p["scored_panel"]["sol"]["codex_version"]),
                         ("gpt-6.1-sol", "medium", "0.159.0"))
        v327 = json.loads((ROOT / "assets/data/swe-v4-deepseek-flash-v327/judge-protocols.json").read_text())
        for key in ("rubric", "system", "probe_instruction", "match_instruction", "schemas", "weights", "seed", "repeats", "gate_allowance"):
            self.assertEqual(p[key], v327[key], key)
        for q in PANELS:
            self.assertEqual(p["scored_panel"][q]["binary_sha256"], v327["scored_panel"][q]["binary_sha256"])
        self.assertIn("out of usage", p["seat"])
        self.assertEqual(p["counted_calls"], {"muse": {"calibration": 80, "match": 112, "pairwise": 10, "primary": 112, "probe": 112, "repeat": 5},
                                              "sol": {"calibration": 80, "match": 111, "pairwise": 10, "primary": 112, "probe": 112, "repeat": 5}})
        self.assertEqual(p["second_attempts"], {"muse": 2, "sol": 39})
        self.assertEqual(len(p["operator_recoveries"]), 24)
        self.assertEqual(len(p["transport_reviews"]), 3)
        rules = [m["rule"] for m in p["operator_markers"]]
        self.assertEqual((rules.count("no_source_change"), rules.count("input_over_judge_limit"), rules.count("invalidate_unrecoverable_primary")),
                         (24, 3, 1))
        for name in ("runs.json", "groups.json", "calibration.json", "judge-protocols.json", "economics.json", "provenance.json", "README.md", "REPRODUCING.md"):
            text = (DATA / name).read_text()
            for mark in (chr(0x2014), chr(0x2013), *ENTITIES, "/Users/", "/home/", "/private/", "/var/folders/", "SWE v4",
                         "no model on the board"):
                self.assertNotIn(mark, text, name)
            self.assertNotIn("ultra", text.lower(), name)


class BeamPageTests(unittest.TestCase):
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
        self.assertIn("intent/post?text=Reflection%20Beam%20across%20every%20effort%20level%20on%20VulcanBench%20Frontier%20v4", self.page_html)
        self.assertIn("Morgan Linton", self.text)
        self.assertNotIn(".pdf", self.page_html)
        for target in ("https://github.com/morganlinton/VulcanBench", "https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md",
                       "https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/mirror_cli.py"):
            self.assertIn(f'href="{target}"', self.page_html)

    def test_tables_match_the_bundle(self):
        g = self.groups
        self.assertEqual(set(self.page.rows), {("beam", e) for e in EFFORTS})
        for i, e in enumerate(EFFORTS):
            row = self.page.rows["beam", e]
            zero = g[e]["combined_no_code_zero"]
            self.assertEqual(row[1:6], [label(e), f'{g[e]["combined_33"]["mean"]:.2f}', f'{g[e]["combined_33"]["se"]:.2f}',
                                        f'{zero["mean"]:.2f}' if zero else "same", f'{g[e]["combined_20_profile"]["mean"]:.2f}'])
            self.assertEqual(row[6:10], [f'{g[e]["code_quality"]["mean"]:.2f}', f'{g[e]["readability"]["mean"]:.1f}',
                                         f'{g[e]["maintainability"]["mean"]:.1f}', f'{g[e]["intent_recovery"]["mean"]:.1f}'])
            self.assertEqual(row[-3:], [f"{JUDGED[i]}/23", f"{PASSED[i]}/23", f'{g[e]["minutes"]["mean"]:.1f}'])
            cells = (f'<td>23</td><td>{g[e]["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>{g[e]["output_tokens"]["mean"] / 1e3:.1f}K</td>'
                     f'<td>{100 * g[e]["cached_input_share"]["mean"]:.1f}%</td><td>{g[e]["model_calls"]["mean"]:.1f}</td>'
                     f'<td>{g[e]["failed_model_requests"]}</td><td>{g[e]["minutes"]["mean"]:.1f}</td><td>{g[e]["minutes_median"]:.1f}</td>')
            self.assertIn(f'<tr data-econ-effort="{e}"><th scope="row">{label(e)}</th>{cells}', self.page_html, e)
        self.assertIn('<th scope="row">Combined score</th>' + "".join(f'<td>{g[e]["combined_33"]["mean"]:.2f}</td>' for e in EFFORTS), self.page_html)
        self.assertIn('<th scope="row">Judged runs</th>' + "".join(f"<td>{n}</td>" for n in JUDGED), self.page_html)
        self.assertIn('<th scope="row">No-code runs counted as 0</th><td>18.90</td><td>38.95</td><td>same</td><td>same</td><td>same</td>', self.page_html)
        self.assertIn('<th scope="row">Tasks passed</th>' + "".join(f"<td>{p}/23</td>" for p in PASSED), self.page_html)
        self.assertIn('<th scope="row">Hidden behaviours fixed</th>' + "".join(f'<td>{g[e]["hidden_behaviours_fixed"]}/231</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">$ per task</th>' + "<td>unavailable</td>" * 5, self.page_html)
        self.assertIn('<th scope="row">Rated by Muse Spark 1.3</th>' + "".join(f'<td>{g[e]["by_panel"]["muse"]["mean"]:.1f}</td>' for e in EFFORTS),
                      self.page_html)
        self.assertIn('<th scope="row">Rated by GPT-6.1 Sol</th>' + "".join(f'<td>{g[e]["by_panel"]["sol"]["mean"]:.1f}</td>' for e in EFFORTS),
                      self.page_html)
        judges = self.section("judges", "run-notes")
        for e in EFFORTS:
            for p in PANELS:
                self.assertIn(f'{g[e]["combined_single_judge"][p]["mean"]:.2f}', judges, (e, p))

    def test_comparison_matches_the_published_bundles(self):
        for key, bundle in COMPARATORS.items():
            groups = {x["effort"]: x for x in json.loads((ROOT / "assets/data" / bundle / "groups.json").read_text()) if x["model"] == key}
            econ = {x["effort"]: x for x in json.loads((ROOT / "assets/data" / bundle / "economics.json").read_text())["groups"] if x["model"] == key}
            for e in EFFORTS:
                g, x = groups[e], econ[e]
                judged = f'{g["n"]}' + ("*" if g["n"] < 23 else "")
                cells = (f'<td>{label(e)}</td><td>{g["combined_33"]["mean"]:.2f}</td><td>{g["combined_33"]["se"]:.2f}</td><td>{judged}</td>'
                         f'<td>{g.get("passed_all_runs", g["passed"])}/23</td><td>{x["minutes"]["mean"]:.1f}</td>'
                         f'<td>{x["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>${x["usd"]["mean"]:.2f}</td>')
                row = self.page_html[self.page_html.index(f'data-compare="{key}-{e}"'):]
                self.assertIn(cells, row[:row.index("</tr>")], (key, e))
        for i, e in enumerate(EFFORTS):
            row = self.page_html[self.page_html.index(f'data-compare="beam-{e}"'):]
            g = self.groups[e]
            judged = f"{JUDGED[i]}" + ("*" if JUDGED[i] < 23 else "")
            self.assertIn(f'<td>{g["combined_33"]["mean"]:.2f}</td><td>{g["combined_33"]["se"]:.2f}</td><td>{judged}</td><td>{PASSED[i]}/23</td>'
                          f'<td>{g["minutes"]["mean"]:.1f}</td><td>{g["raw_tokens"]["mean"] / 1e6:.2f}M</td><td>unavailable</td>', row[:row.index("</tr>")])
        comparison = self.section("comparison", "tokens")
        for needle in ("far below the three frontier models", "64.72 at Extra-high", "90.68", "88.78", "89.16", "4 and 6 tasks",
                       "stops early", "17.29M", "not calibrated against each other", "judges a column it is shown beside", "Beam has no price"):
            self.assertIn(needle, comparison, needle)

    def test_required_disclosures(self):
        tokens = self.section("tokens", "board")
        for needle in ("no price", "unavailable, not zero", "Tokens and Minutes views", "Six model requests in five runs failed"):
            self.assertIn(needle, tokens, needle)
        board = self.section("board", "code-quality")
        for needle in ("ranks 63rd of the board’s 75", "Low 75th, Medium 72nd, High 68th, Extra-high 63rd, Max 64th", "Low is last",
                       "all pick Extra-high", "not calibrated against each other", "no-code runs as 0"):
            self.assertIn(needle, board, needle)
        results = plain(self.page_html[self.page_html.index('id="results"'):self.page_html.index('id="comparison"')])
        for needle in ("99 of the 115 runs", "empty patch", "changed no source file", "October 26, 2026", "6.5M characters",
                       "input limit", "cited no code", "payrollcore is published from Muse Spark 1.3 alone", "16 published runs"):
            self.assertIn(needle, results, needle)
        judges = self.section("judges", "run-notes")
        for needle in ("Muse Spark 1.3", "GPT-6.1 Sol", "Grok 4.6", "Cursor", "out of usage", "as protocol v3.27 did for DeepSeek V4.1 Flash",
                       "byte-identical backup", "judges a column it is shown beside", "about 14 points above", "15.2 at Low",
                       "passed every gate with no allowance used", "24 of Sol’s answer-key matches", "429", "operator marker"):
            self.assertIn(needle, judges, needle)
        notes = self.section("run-notes", "reproduce")
        for needle in ("Beam-1.0-501B-A23B", "Beam-501B-A23B", "harness-recorded", "reflection-mirror", "Apache-2.0", "0.1.1", "early beta",
                       "outer sandbox", "private Mirror home", "analytics were off", "web tools absent", "xhigh", "sandbox denied access",
                       "beyond the session’s scope", "not tool calls", "daily token limit", "1,200 attempts", "13 Max tasks",
                       "No timeouts, no overlapping jobs", "57.1 minutes"):
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


class BeamSiteTests(unittest.TestCase):
    def test_model_page_links_report(self):
        markup = MODEL_PAGE.read_text()
        self.assertIn('href="../benchmarks/swe-v4-beam-v328.html"', markup)
        self.assertIn(f'<link rel="canonical" href="{MODEL_URL}">', markup)
        for value in ("39.51", "44.79", "55.01", "64.72", "63.92", "18.90", "38.95", "0, 0, 0, 4 and 6 of 23", "63rd of 75"):
            self.assertIn(value, markup, value)

    def test_site_references(self):
        for name in ("benchmarks.html", "index.html", "sitemap.xml", "feed.xml", "llms.txt", "README.md", "models/reflection-beam.html"):
            self.assertIn("swe-v4-beam-v328.html", (ROOT / name).read_text(), name)
        self.assertIn('href="models/reflection-beam.html"', (ROOT / "benchmarks.html").read_text())
        self.assertIn("swe-v4-beam-v328/", (ROOT / "assets/data/README.md").read_text())
        sitemap = (ROOT / "sitemap.xml").read_text()
        for page_url in (URL, MODEL_URL):
            self.assertIn(f"<loc>{page_url}</loc>", sitemap)
        item = next(i for i in (ROOT / "feed.xml").read_text().split("<item>") if f"<link>{URL}</link>" in i)
        self.assertIn("VulcanBench Frontier v4", item)
        self.assertIn("27 Oct 2026", item)
        self.assertNotIn(chr(0x2014), item)
        leaderboard = (ROOT / "leaderboard.html").read_text()
        self.assertIn('<a href="benchmarks/swe-v4-beam-v328.html">Reflection Beam</a>', leaderboard)
        self.assertEqual(len(re.findall(r'data-model="beam" data-effort="[a-z-]+" data-best', leaderboard)), 5)
        index = (ROOT / "benchmarks.html").read_text()
        self.assertLess(index.index("swe-v4-beam-v328.html"), index.index("swe-v4-deepseek-flash-v327.html"))


if __name__ == "__main__":
    unittest.main()
