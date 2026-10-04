"""The Frontier v4 leaderboard block, JSON and CSV are generated from the bundles and current."""

import csv
import html
import json
import unittest
from pathlib import Path

import build_swe_v4_board as board

ROOT = Path(__file__).resolve().parents[1]


class BoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = board.rows()
        cls.page = (ROOT / "leaderboard.html").read_text()
        cls.json = json.loads((ROOT / "assets/data/swe-v4-board.json").read_text())
        with (ROOT / "assets/data/swe-v4-board.csv").open(newline="") as source:
            cls.csv = list(csv.DictReader(source))

    def test_outputs_are_current(self):
        block = board.render(self.rows)
        self.assertIn(block, self.page)
        self.assertEqual(self.json["columns"], self.rows)
        self.assertEqual(board.csv_text(self.rows), (ROOT / "assets/data/swe-v4-board.csv").read_text())

    def test_every_column_is_on_the_board(self):
        self.assertEqual(len(self.rows), 53)
        self.assertEqual({r["model"] for r in self.rows}, {"GPT-6 Astra", "Fable 5.1", "GPT-5.5", "GPT-5.6 Luna", "GPT-5.6 Terra", "GPT-5.6 Sol", "Opus 5.5", "GPT-6 Luna", "GPT-6 Sol", "GPT-6.1 Sol", "Grok 4.7"})
        self.assertEqual(sum(1 for r in self.rows if r["best"]), 11)
        self.assertEqual([r["rank"] for r in self.rows], list(range(1, 54)))
        self.assertEqual([r["combined"] for r in self.rows], sorted((r["combined"] for r in self.rows), reverse=True))
        self.assertEqual(sum(r["n"] for r in self.rows), 1209)
        for r in self.rows:
            self.assertTrue((ROOT / f"models/{r['slug']}.html").is_file(), r["slug"])
            self.assertTrue((ROOT / r["report"]).is_file(), r["report"])
            if r["key"] == "grok47cursor":  # no list price: unavailable, never $0
                self.assertIsNone(r["usd"])
            else:
                self.assertGreater(r["usd"], 0)
            self.assertGreater(r["output_tokens_median"], 0)
            self.assertGreater(r["output_tokens_mean"], 0)
        terra_max = next(r for r in self.rows if r["key"] == "terra" and r["effort"] == "max")
        self.assertEqual(terra_max["n"], 23)
        sol_max = next(r for r in self.rows if r["key"] == "sol" and r["effort"] == "max")
        self.assertEqual(sol_max["n"], 22)
        self.assertEqual(sol_max["passed"], 21)
        self.assertTrue(all(r["n"] == 23 for r in self.rows if r["key"] == "sol" and r["effort"] != "max"))
        opus_high = next(r for r in self.rows if r["key"] == "opus55" and r["effort"] == "high")
        self.assertEqual((opus_high["n"], opus_high["passed"]), (22, 22))
        self.assertTrue(all(r["n"] == 23 for r in self.rows if r["key"] == "opus55" and r["effort"] != "high"))
        luna6 = {r["effort"]: r for r in self.rows if r["key"] == "gpt6luna"}
        self.assertEqual([luna6[e]["n"] for e in board.EFFORTS], [23, 23, 23, 21, 19])
        self.assertEqual([luna6[e]["passed"] for e in board.EFFORTS], [0, 0, 2, 11, 12])
        self.assertTrue(all(luna6[e]["passed_of"] == 23 for e in board.EFFORTS))  # timeouts count as failed tasks
        self.assertEqual([round(luna6[e]["combined"], 2) for e in board.EFFORTS], [40.83, 45.72, 57.35, 78.79, 81.42])
        self.assertEqual([round(luna6[e]["combined_timeouts_zero"], 2) for e in board.EFFORTS], [40.83, 45.72, 57.35, 71.94, 67.26])
        sol6 = {r["effort"]: r for r in self.rows if r["key"] == "gpt6sol"}
        self.assertEqual([sol6[e]["n"] for e in board.EFFORTS], [23, 22, 23, 23, 23])
        self.assertEqual([sol6[e]["passed"] for e in board.EFFORTS], [4, 13, 15, 18, 19])
        self.assertTrue(all(sol6[e]["passed_of"] == 23 and sol6[e]["combined_timeouts_zero"] is None for e in board.EFFORTS))
        self.assertEqual([round(sol6[e]["combined"], 2) for e in board.EFFORTS], [67.62, 80.60, 82.83, 85.94, 86.82])
        sol61 = {r["effort"]: r for r in self.rows if r["key"] == "gpt61sol"}
        self.assertEqual([sol61[e]["n"] for e in board.EFFORTS], [23, 23, 23, 23, 23])  # medium paddockcore is judged, from Muse alone
        self.assertEqual([sol61[e]["passed"] for e in board.EFFORTS], [20, 22, 23, 23, 23])
        self.assertEqual([round(sol61[e]["combined"], 2) for e in board.EFFORTS], [86.22, 86.44, 88.23, 88.78, 88.35])
        self.assertEqual([round(sol61[e]["code_quality"], 2) for e in board.EFFORTS], [70.79, 70.25, 73.67, 74.99, 73.80])
        self.assertEqual([r["rank"] for r in self.rows if r["key"] == "gpt61sol"], [17, 18, 19, 26, 28])
        grok = {r["effort"]: r for r in self.rows if r["key"] == "grok47cursor"}
        self.assertEqual(set(grok), {"low", "medium", "high", "extra-high"})  # Cursor offers no max level for Grok 4.7
        self.assertEqual([grok[e]["n"] for e in board.EFFORTS[:4]], [23, 22, 23, 23])  # medium lodgecore hit the 3-hour bound
        self.assertEqual([grok[e]["passed"] for e in board.EFFORTS[:4]], [18, 21, 22, 23])
        self.assertTrue(all(grok[e]["passed_of"] == 23 and grok[e]["combined_timeouts_zero"] is None for e in grok))
        self.assertEqual([round(grok[e]["combined"], 2) for e in board.EFFORTS[:4]], [89.42, 92.30, 92.71, 93.15])
        self.assertEqual([round(grok[e]["code_quality"], 2) for e in board.EFFORTS[:4]], [81.41, 83.90, 83.43, 84.35])
        self.assertEqual([grok[e]["rank"] for e in ("extra-high", "high", "medium", "low")], [1, 2, 3, 12])
        self.assertTrue(all(r["passed_of"] == r["n"] and r["combined_timeouts_zero"] is None for r in self.rows if r["key"] not in ("gpt6luna", "gpt6sol", "grok47cursor")))
        self.assertEqual(len(self.csv), 53)
        for row in self.csv:
            self.assertEqual(row["mean_usd"] == "", row["model"] == "Grok 4.7")
        self.assertEqual(self.csv[0]["rank"], "1")

    def test_board_matches_the_bundles(self):
        for source in board.SOURCES:
            groups = {(g["model"], g["effort"]): g for g in json.loads((ROOT / "assets/data" / source["bundle"] / "groups.json").read_text())}
            for r in self.rows:
                if r["report"] != source["report"]:
                    continue
                g = groups[r["key"], r["effort"]]
                self.assertAlmostEqual(r["combined"], g["combined_33"]["mean"], places=9)
                self.assertAlmostEqual(r["code_quality"], g["code_quality"]["mean"], places=9)
                self.assertEqual(r["passed"], g["passed_all_runs"] if source.get("pass_over_all_runs") else g["passed"])
                self.assertEqual(r["n"], g["n"])
            tokens = board.output_tokens(source["bundle"])
            for r in self.rows:
                if r["report"] == source["report"]:
                    self.assertAlmostEqual(r["output_tokens_median"], tokens[r["key"], r["effort"]]["median"], places=6)

    def test_suggestions_follow_the_rule(self):
        sug = self.json["suggestions"]
        self.assertEqual(sug, board.suggestions(self.rows))
        self.assertEqual(self.json["tolerances"], {"critical": 1.0, "routine": 3.0, "rough": 5.0})
        by_model = {}
        for r in self.rows:
            by_model.setdefault(r["key"], []).append(r)
        for key, entry in sug.items():
            levels = by_model[key]
            score = board.decision_score  # timeouts as 0 where a column has timeouts
            best = max(levels, key=score)
            self.assertEqual(entry["best_effort"], best["effort"])
            self.assertEqual(entry["shape"], "flat" if entry["spread"] <= 3 else "steep")
            for name, tol in self.json["tolerances"].items():
                pick = next(r for r in levels if r["effort"] == entry[name]["effort"])
                self.assertLessEqual(score(best) - score(pick), tol)
                for r in levels:  # nothing cheaper qualifies
                    if score(best) - score(r) <= tol:
                        if entry["basis"] == "cost then time":
                            self.assertGreaterEqual((r["usd"], r["minutes"]), (pick["usd"], pick["minutes"]))
                        else:  # no list price: picked on time alone
                            self.assertGreaterEqual(r["minutes"], pick["minutes"])
        self.assertEqual({k: v["routine"]["effort"] for k, v in sug.items()},
                         {"fable": "low", "astra": "medium", "terra": "max", "luna": "max", "gpt55": "extra-high", "sol": "extra-high", "opus55": "medium", "gpt6luna": "extra-high", "gpt6sol": "extra-high", "gpt61sol": "low", "grok47cursor": "high"})
        self.assertEqual({k: v["shape"] for k, v in sug.items()}, {"fable": "flat", "astra": "flat", "terra": "steep", "luna": "steep", "gpt55": "steep", "sol": "steep", "opus55": "steep", "gpt6luna": "steep", "gpt6sol": "steep", "gpt61sol": "flat", "grok47cursor": "steep"})
        self.assertEqual(sug["gpt6sol"]["best_effort"], "max")  # no timeouts, so the decision score is the judged score
        self.assertEqual((sug["gpt61sol"]["best_effort"], sug["gpt61sol"]["critical"]["effort"]), ("extra-high", "high"))
        self.assertEqual((sug["grok47cursor"]["best_effort"], sug["grok47cursor"]["basis"]), ("extra-high", "time (no list price)"))
        self.assertTrue(all(sug["grok47cursor"][t]["usd_vs_best"] is None for t in self.json["tolerances"]))
        self.assertTrue(all(v["basis"] == "cost then time" for k, v in sug.items() if k != "grok47cursor"))

    def test_page_writing_and_structure(self):
        text = html.unescape(self.page)
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn(chr(0x2013), text)
        self.assertEqual(self.page.count(board.START), 1)
        self.assertEqual(self.page.count(board.END), 1)
        self.assertIn("VulcanBench-SWE v3 (retired in August 2026)", self.page)
        self.assertIn("&sect; GPT-5.6 Sol at max is judged on 22 of 23 tasks", self.page)
        self.assertIn('data-model="sol" data-effort="max"', self.page)
        self.assertIn("<td class=\"fb-eff\">max&sect;</td>", self.page)
        self.assertIn('<a href="benchmarks/swe-v4-sol-v37.html">Sol</a>', self.page)
        self.assertIn("&para; GPT-6 Luna at extra-high and max is judged on 21 and 19 of 23 tasks", self.page)
        self.assertIn("its best tag and effort suggestions use these figures", self.page)
        self.assertIn('data-model="gpt6luna" data-effort="extra-high" data-best="1"', self.page)
        self.assertIn("gives 71.94 at extra-high and 67.26 at max", self.page)
        for effort in ("extra-high", "max"):
            self.assertIn(f'data-model="gpt6luna" data-effort="{effort}"', self.page)
            self.assertIn(f'<td class="fb-eff">{effort}&para;</td><td class="lb-win">', self.page)
        self.assertEqual(self.page.count("&para;</td>"), 2)
        self.assertIn('<a href="benchmarks/swe-v4-gpt6-luna-v316.html">GPT-6 Luna</a>', self.page)
        self.assertIn("&Vert; GPT-6 Sol at medium is judged on 22 of 23 tasks", self.page)
        self.assertIn('data-model="gpt6sol" data-effort="medium"', self.page)
        self.assertIn('<td class="fb-eff">medium&Vert;</td><td class="lb-win">', self.page)
        self.assertEqual(self.page.count("&Vert;</td>"), 1)
        self.assertIn('data-model="gpt6sol" data-effort="max" data-best="1"', self.page)
        self.assertIn('<a href="benchmarks/swe-v4-gpt6-sol-v317.html">GPT-6 Sol</a>', self.page)
        self.assertIn("* GPT-6.1 Sol at medium includes paddockcore with Code quality from Muse Spark 1.3 alone", self.page)
        self.assertIn('<td class="fb-eff">medium*</td><td class="lb-win">', self.page)
        self.assertEqual(self.page.count("*</td>"), 1)
        self.assertIn('data-model="gpt61sol" data-effort="extra-high" data-best="1"', self.page)
        self.assertIn('<a href="benchmarks/swe-v4-gpt61-sol-v318.html">GPT-6.1 Sol</a>', self.page)
        self.assertIn('<a href="benchmarks/swe-v4-opus55-v315.html">Opus 5.5</a>', self.page)
        self.assertIn("v3.4 to v3.7, v3.15 to v3.18 and v3.20", self.page)
        self.assertIn("&loz; Grok 4.7 (xAI) ran in Cursor&#x27;s agent CLI 2026.10.01", self.page)
        self.assertIn("judged by Muse Spark 1.3 and GPT-6.1 Sol under v3.20", self.page)
        self.assertIn("second at Low behind Fable 5.1 (89.46)", self.page)
        self.assertIn("$/task is unavailable, not $0", self.page)
        self.assertEqual(self.page.count("&loz;</td>"), 4)
        frontier = self.page.split(board.START, 1)[1].split(board.END, 1)[0]
        self.assertEqual(frontier.count("<td>unavailable</td>"), 4)
        self.assertNotIn('data-model="grok47cursor" data-effort="max"', self.page)
        self.assertIn('<a href="benchmarks/swe-v4-grok47-cursor-v320.html">Grok 4.7</a>', self.page)
        self.assertIn('data-model="grok47cursor" data-effort="extra-high" data-best="1"', self.page)
        js = (ROOT / "leaderboard-v4.js").read_text()
        self.assertIn("function plotted()", js)  # unpriced columns sit out the cost view
        self.assertIn("has no list price, so it is not on the cost view", js)
        models, columns, runs = len({r["model"] for r in self.rows}), len(self.rows), sum(r["n"] for r in self.rows)
        self.assertIn(f"&middot; {models} models &middot; {columns} model&times;effort columns &middot; {runs} runs &middot;", self.page)
        self.assertEqual(len(set(board.COLORS.values())), len(board.COLORS))
        self.assertEqual(set(board.COLORS), {r["key"] for r in self.rows})
        self.assertLess(self.page.index('id="swe-v4-board"'), self.page.index('id="swe-v3-board"'))
        self.assertNotIn('id="fullboard"', self.page)  # the retired v3 board is JSON only; the page keeps one chart


if __name__ == "__main__":
    unittest.main()
