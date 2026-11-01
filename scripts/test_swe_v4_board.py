"""The Frontier v4 leaderboard block, JSON and CSV are generated from the bundles and current."""

import csv
import html
import json
import re
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
        cls.chart = json.loads(re.search(r"window\.VB_V4 = (\{.*?\});</script>", cls.page).group(1))["columns"]

    def col(self, key, effort):
        return next((c for c in self.chart if c["key"] == key and c["effort"] == effort), None)

    def marks(self, mark):
        return sum(1 for c in self.chart if c["mark"] == mark)

    def test_outputs_are_current(self):
        block = board.render(self.rows)
        self.assertIn(block, self.page)
        self.assertEqual(self.json["columns"], self.rows)
        self.assertEqual(board.csv_text(self.rows), (ROOT / "assets/data/swe-v4-board.csv").read_text())

    def test_every_column_is_on_the_board(self):
        self.assertEqual(len(self.rows), 80)  # 53 + Sonnet 5.5 and Haiku 5.5 at five levels each + Muse Wonder Full at four + DeepSeek V4.1 Flash at three + Reflection Beam and GPT-6.1 Terra at five
        self.assertEqual({r["model"] for r in self.rows}, {"GPT-6 Astra", "Fable 5.1", "GPT-5.5", "GPT-5.6 Luna", "GPT-5.6 Terra", "GPT-5.6 Sol", "Opus 5.5", "GPT-6 Luna", "GPT-6 Sol", "GPT-6.1 Sol", "Grok 4.7", "Sonnet 5.5", "Haiku 5.5", "Muse Wonder Full", "DeepSeek V4.1 Flash", "Reflection Beam", "GPT-6.1 Terra"})
        self.assertEqual(sum(1 for r in self.rows if r["best"]), 17)
        self.assertEqual([r["rank"] for r in self.rows], list(range(1, 81)))
        self.assertEqual([r["combined"] for r in self.rows], sorted((r["combined"] for r in self.rows), reverse=True))
        # 1209 before Sonnet 5.5, plus its 115 judged runs, Haiku 5.5's 111, Muse Wonder Full's 90, DeepSeek V4.1 Flash's 69, Reflection Beam's 99 and GPT-6.1 Terra's 115.
        self.assertEqual(sum(r["n"] for r in self.rows), 1808)
        for r in self.rows:
            self.assertTrue((ROOT / f"models/{r['slug']}.html").is_file(), r["slug"])
            self.assertTrue((ROOT / r["report"]).is_file(), r["report"])
            if r["key"] in ("grok47cursor", "beam"):  # no list price: unavailable, never $0
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
        self.assertEqual([r["rank"] for r in self.rows if r["key"] == "gpt61sol"], [22, 26, 28, 40, 42])  # in rank order
        grok = {r["effort"]: r for r in self.rows if r["key"] == "grok47cursor"}
        self.assertEqual(set(grok), {"low", "medium", "high", "extra-high"})  # Cursor offers no max level for Grok 4.7
        self.assertEqual([grok[e]["n"] for e in board.EFFORTS[:4]], [23, 22, 23, 23])  # medium lodgecore hit the 3-hour bound
        self.assertEqual([grok[e]["passed"] for e in board.EFFORTS[:4]], [18, 21, 22, 23])
        self.assertTrue(all(grok[e]["passed_of"] == 23 and grok[e]["combined_timeouts_zero"] is None for e in grok))
        self.assertEqual([round(grok[e]["combined"], 2) for e in board.EFFORTS[:4]], [89.42, 92.30, 92.71, 93.15])
        self.assertEqual([round(grok[e]["code_quality"], 2) for e in board.EFFORTS[:4]], [81.41, 83.90, 83.43, 84.35])
        self.assertEqual([grok[e]["rank"] for e in ("extra-high", "high", "medium", "low")], [1, 2, 3, 17])
        sonnet = {r["effort"]: r for r in self.rows if r["key"] == "sonnet55"}
        self.assertEqual(set(sonnet), set(board.EFFORTS))
        self.assertEqual([sonnet[e]["n"] for e in board.EFFORTS], [23, 23, 23, 23, 23])
        self.assertEqual([sonnet[e]["passed"] for e in board.EFFORTS], [15, 17, 20, 22, 23])  # pass@1 0.652, 0.739, 0.870, 0.957, 1.000
        self.assertTrue(all(sonnet[e]["passed_of"] == 23 and sonnet[e]["combined_timeouts_zero"] is None for e in sonnet))
        self.assertEqual([round(sonnet[e]["combined"], 2) for e in board.EFFORTS], [81.63, 84.10, 86.79, 90.20, 92.02])
        self.assertEqual([round(sonnet[e]["code_quality"], 2) for e in board.EFFORTS], [61.67, 65.35, 70.84, 75.78, 81.72])
        self.assertEqual([round(sonnet[e]["minutes"], 1) for e in board.EFFORTS], [20.0, 20.8, 14.8, 21.6, 38.0])
        self.assertEqual([f'{sonnet[e]["usd"]:.2f}' for e in board.EFFORTS], ["2.88", "3.00", "2.39", "3.38", "5.52"])  # Claude Code's own cost
        self.assertEqual([sonnet[e]["rank"] for e in board.EFFORTS], [53, 47, 38, 13, 5])
        haiku = {r["effort"]: r for r in self.rows if r["key"] == "haiku55"}
        self.assertEqual(set(haiku), set(board.EFFORTS))
        self.assertEqual([haiku[e]["n"] for e in board.EFFORTS], [23, 22, 23, 22, 21])  # paddockcore stops at medium, extra-high, max; max codeccore unpublished
        self.assertEqual([haiku[e]["passed"] for e in board.EFFORTS], [13, 13, 17, 22, 22])  # over all 23: pass@1 0.565, 0.565, 0.739, 0.957, 0.957
        self.assertTrue(all(haiku[e]["passed_of"] == 23 and haiku[e]["combined_timeouts_zero"] is None for e in haiku))
        self.assertEqual([round(haiku[e]["combined"], 2) for e in board.EFFORTS], [84.42, 84.03, 88.01, 91.83, 92.16])
        self.assertEqual([round(haiku[e]["code_quality"], 2) for e in board.EFFORTS], [74.83, 76.07, 77.60, 80.13, 81.30])
        self.assertEqual([f'{haiku[e]["usd"]:.2f}' for e in board.EFFORTS], ["1.04", "1.36", "1.25", "0.84", "1.54"])  # Claude Code's own cost, every run
        self.assertEqual([haiku[e]["rank"] for e in board.EFFORTS], [45, 48, 31, 7, 4])
        wonder = {r["effort"]: r for r in self.rows if r["key"] == "musewonderfull"}
        self.assertEqual(set(wonder), {"low", "medium", "high", "extra-high"})  # Contributor mode offers no max level
        self.assertEqual([wonder[e]["n"] for e in board.EFFORTS[:4]], [23, 23, 22, 22])  # high paddockcore and extra-high depotcore timed out
        self.assertEqual([wonder[e]["passed"] for e in board.EFFORTS[:4]], [18, 21, 19, 19])
        self.assertTrue(all(wonder[e]["passed_of"] == 23 for e in wonder))
        self.assertEqual([round(wonder[e]["combined"], 2) for e in board.EFFORTS[:4]], [86.95, 88.27, 88.19, 87.59])
        self.assertEqual([round(wonder[e]["combined_timeouts_zero"], 2) for e in board.EFFORTS[:4]], [86.95, 88.27, 84.36, 83.78])
        self.assertEqual([f'{wonder[e]["usd"]:.2f}' for e in board.EFFORTS[:4]], ["3.93", "4.09", "4.72", "5.08"])  # estimate, every run
        self.assertEqual([wonder[e]["rank"] for e in board.EFFORTS[:4]], [36, 27, 29, 33])
        flash = {r["effort"]: r for r in self.rows if r["key"] == "dsflash"}
        self.assertEqual(set(flash), {"low", "high", "max"})  # DeepSeek's API offers no medium and nothing maps to extra-high
        self.assertTrue(all(flash[e]["n"] == flash[e]["passed_of"] == 23 and flash[e]["combined_timeouts_zero"] is None for e in flash))
        self.assertEqual([flash[e]["passed"] for e in ("low", "high", "max")], [21, 20, 20])
        self.assertEqual([round(flash[e]["combined"], 2) for e in ("low", "high", "max")], [88.65, 88.61, 88.36])
        self.assertEqual([f'{flash[e]["usd"]:.4f}' for e in ("low", "high", "max")], ["0.0577", "0.0667", "0.0741"])  # off-peak list price
        self.assertEqual([flash[e]["rank"] for e in ("low", "high", "max")], [23, 24, 25])
        self.assertEqual((flash["low"]["lab"], flash["low"]["harness"], flash["low"]["slug"]), ("DeepSeek", "DeepSeek Harness 0.2.1-rc.2", "deepseek-v4-1-flash"))
        beam = {r["effort"]: r for r in self.rows if r["key"] == "beam"}
        self.assertEqual(set(beam), set(board.EFFORTS))
        self.assertEqual([beam[e]["n"] for e in board.EFFORTS], [11, 20, 23, 23, 22])  # no-code runs not judged; max hedgecore unreviewable
        self.assertTrue(all(beam[e]["passed_of"] == 23 and beam[e]["usd"] is None for e in board.EFFORTS))  # no list price
        self.assertEqual([beam[e]["passed"] for e in board.EFFORTS], [0, 0, 0, 4, 6])
        self.assertEqual([round(beam[e]["combined"], 2) for e in board.EFFORTS], [39.51, 44.79, 55.01, 64.72, 63.92])
        self.assertEqual([None if beam[e]["combined_timeouts_zero"] is None else round(beam[e]["combined_timeouts_zero"], 2) for e in board.EFFORTS],
                         [18.90, 38.95, None, None, None])  # no-code runs as 0
        self.assertEqual([beam[e]["rank"] for e in board.EFFORTS], [80, 77, 73, 68, 69])
        self.assertEqual((beam["low"]["lab"], beam["low"]["harness"], beam["low"]["slug"]), ("Reflection", "Mirror CLI 0.1.1", "reflection-beam"))
        terra61 = {r["effort"]: r for r in self.rows if r["key"] == "gpt61terra"}
        self.assertEqual(set(terra61), set(board.EFFORTS))
        self.assertTrue(all(terra61[e]["n"] == terra61[e]["passed_of"] == 23 for e in board.EFFORTS))  # max settlecore recovered, every run judged
        self.assertEqual([terra61[e]["passed"] for e in board.EFFORTS], [13, 12, 15, 16, 23])
        self.assertEqual([round(terra61[e]["combined"], 2) for e in board.EFFORTS], [74.95, 80.10, 79.19, 83.68, 90.00])
        self.assertEqual([f'{terra61[e]["usd"]:.2f}' for e in board.EFFORTS], ["0.11", "0.14", "0.13", "0.24", "0.36"])
        self.assertEqual([terra61[e]["rank"] for e in board.EFFORTS], [62, 56, 57, 49, 16])
        self.assertEqual((terra61["max"]["lab"], terra61["max"]["harness"], terra61["max"]["slug"]), ("OpenAI", "Codex", "gpt-6-1-terra"))
        self.assertEqual({r["key"] for r in self.rows if r["rank"] < 4}, {"grok47cursor"})  # only Grok 4.7, judged by another panel, is above
        self.assertTrue(all(r["passed_of"] == r["n"] and r["combined_timeouts_zero"] is None for r in self.rows if r["key"] not in ("gpt6luna", "gpt6sol", "grok47cursor", "haiku55", "musewonderfull", "beam")))
        self.assertEqual(len(self.csv), 80)
        for row in self.csv:
            self.assertEqual(row["mean_usd"] == "", row["model"] in ("Grok 4.7", "Reflection Beam"))
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
                         {"fable": "low", "astra": "medium", "terra": "max", "luna": "max", "gpt55": "extra-high", "sol": "extra-high", "opus55": "medium", "gpt6luna": "extra-high", "gpt6sol": "extra-high", "gpt61sol": "low", "grok47cursor": "high",
                          "sonnet55": "extra-high", "haiku55": "extra-high", "musewonderfull": "low", "dsflash": "low", "beam": "extra-high", "gpt61terra": "max"})
        self.assertEqual({k: v["shape"] for k, v in sug.items()}, {"fable": "flat", "astra": "flat", "terra": "steep", "luna": "steep", "gpt55": "steep", "sol": "steep", "opus55": "steep", "gpt6luna": "steep", "gpt6sol": "steep", "gpt61sol": "flat", "grok47cursor": "steep",
                          "sonnet55": "steep", "haiku55": "steep", "musewonderfull": "flat", "dsflash": "flat", "beam": "steep", "gpt61terra": "steep"})
        self.assertEqual(sug["gpt6sol"]["best_effort"], "max")  # no timeouts, so the decision score is the judged score
        self.assertEqual((sug["gpt61sol"]["best_effort"], sug["gpt61sol"]["critical"]["effort"]), ("extra-high", "high"))
        self.assertEqual((sug["grok47cursor"]["best_effort"], sug["grok47cursor"]["basis"]), ("extra-high", "time (no list price)"))
        self.assertTrue(all(sug["grok47cursor"][t]["usd_vs_best"] is None for t in self.json["tolerances"]))
        self.assertTrue(all(v["basis"] == "cost then time" for k, v in sug.items() if k not in ("grok47cursor", "beam")))
        self.assertEqual(sug["beam"]["basis"], "time (no list price)")

    def test_page_writing_and_structure(self):
        text = html.unescape(self.page)
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn(chr(0x2013), text)
        self.assertEqual(self.page.count(board.START), 1)
        self.assertEqual(self.page.count(board.END), 1)
        self.assertIn("&sect; GPT-5.6 Sol at max is judged on 22 of 23 tasks", self.page)
        self.assertIsNotNone(self.col("sol", "max"))
        self.assertEqual(self.col("sol", "max")["mark"], "\u00a7")
        self.assertIn('<a href="benchmarks/swe-v4-sol-v37.html">Sol</a>', self.page)
        self.assertIn("&para; GPT-6 Luna at extra-high and max is judged on 21 and 19 of 23 tasks", self.page)
        self.assertIn("its best tag and effort suggestions use these figures", self.page)
        self.assertTrue(self.col("gpt6luna", "extra-high")["best"])
        self.assertIn("gives 71.94 at extra-high and 67.26 at max", self.page)
        for effort in ("extra-high", "max"):
            self.assertIsNotNone(self.col("gpt6luna", effort))
            self.assertEqual(self.col("gpt6luna", effort)["mark"], "\u00b6")
        self.assertEqual(self.marks("\u00b6"), 2)  # GPT-6 Luna's single mark, not DeepSeek's doubled one
        self.assertIn('<a href="benchmarks/swe-v4-gpt6-luna-v316.html">GPT-6 Luna</a>', self.page)
        self.assertIn("&Vert; GPT-6 Sol at medium is judged on 22 of 23 tasks", self.page)
        self.assertIsNotNone(self.col("gpt6sol", "medium"))
        self.assertEqual(self.col("gpt6sol", "medium")["mark"], "\u2016")
        self.assertEqual(self.marks("\u2016"), 1)
        self.assertTrue(self.col("gpt6sol", "max")["best"])
        self.assertIn('<a href="benchmarks/swe-v4-gpt6-sol-v317.html">GPT-6 Sol</a>', self.page)
        self.assertIn("* GPT-6.1 Sol at medium includes paddockcore with Code quality from Muse Spark 1.3 alone", self.page)
        self.assertEqual(self.col("gpt61sol", "medium")["mark"], "*")
        self.assertEqual(self.marks("*"), 1)  # GPT-6.1 Sol's single mark, not GPT-6.1 Terra's doubled one
        self.assertTrue(self.col("gpt61sol", "extra-high")["best"])
        self.assertIn('<a href="benchmarks/swe-v4-gpt61-sol-v318.html">GPT-6.1 Sol</a>', self.page)
        self.assertIn('<a href="benchmarks/swe-v4-opus55-v315.html">Opus 5.5</a>', self.page)
        self.assertIn("v3.4 to v3.7, v3.15 to v3.18, v3.20, v3.23, v3.24, v3.26, v3.27, v3.28 and v3.29", self.page)
        self.assertIn("&sect;&sect; Muse Wonder Full (Meta) ran in Muse Code in Contributor mode", self.page)
        self.assertIn("judged by Claude Opus 5.5 and GPT-6.1 Sol under v3.26 to v3.26.3, not by Muse Spark 1.3 and Grok 4.6", self.page)
        self.assertIn("gives 84.36 at high and 83.78 at extra-high", self.page)
        self.assertIn("priced at the Muse Wonder 1.0 list price", self.page)
        self.assertEqual(self.marks("\u00a7\u00a7"), 4)
        self.assertTrue(self.col("musewonderfull", "medium")["best"])
        self.assertIn('<a href="benchmarks/swe-v4-musewonder-full-v326.html">Muse Wonder Full</a>', self.page)
        self.assertIn("&para;&para; DeepSeek V4.1 Flash (deepseek-flash, which DeepSeek&#x27;s pricing page mapped to DeepSeek-V4.1-Flash-1017)", self.page)
        self.assertIn("judged by Muse Spark 1.3 and GPT-6.1 Sol under v3.27, not by Muse Spark 1.3 and Grok 4.6", self.page)
        self.assertIn("whose account was out of usage", self.page)
        self.assertIn("about 8 points above Muse (7.3 to 9.6 by level)", self.page)
        self.assertIn("GPT-6.1 Sol judges a column it is shown beside", self.page)
        self.assertIn("offers low, high and max only", self.page)
        self.assertIn("off-peak list price ($0.15 input, $0.003 cached, $0.60 output per million)", self.page)
        self.assertIn("the billed amount was $0.068 to $0.101 per task", self.page)
        self.assertIn("every model here ran on a subscription except DeepSeek V4.1 Flash", self.page)
        self.assertEqual(self.marks("\u00b6\u00b6"), 3)
        self.assertTrue(self.col("dsflash", "low")["best"])
        self.assertIn('<a href="benchmarks/swe-v4-deepseek-flash-v327.html">DeepSeek V4.1 Flash</a>', self.page)
        self.assertIn("&loz;&loz; Reflection Beam (Beam-1.0-501B-A23B, 501B total and 23B active parameters) ran in Mirror CLI 0.1.1", self.page)
        self.assertIn("judged by Muse Spark 1.3 and GPT-6.1 Sol under v3.28, the v3.27 panel, not by Muse Spark 1.3 and Grok 4.6", self.page)
        self.assertIn("about 14 points above Muse (10.1 to 17.6 by level)", self.page)
        self.assertIn("12 at low and 3 at medium", self.page)
        self.assertIn("gives 18.90 at low and 38.95 at medium", self.page)
        self.assertIn("Max is judged on 22 of 23", self.page)
        self.assertIn("Grok 4.7 and Reflection Beam have no list price", self.page)
        self.assertEqual(self.marks("\u25ca\u25ca"), 5)
        self.assertTrue(self.col("beam", "extra-high")["best"])
        self.assertIn('<a href="benchmarks/swe-v4-beam-v328.html">Reflection Beam</a>', self.page)
        self.assertIn("** GPT-6.1 Terra ran in Codex CLI 0.159.0 on a ChatGPT subscription", self.page)
        self.assertIn("Muse Spark 1.3&#x27;s intent probe of settlecore is published through the owner-approved escape rule", self.page)
        self.assertIn("At extra-high, three runs printed Codex&#x27;s notice", self.page)
        self.assertEqual(self.marks("**"), 2)
        self.assertTrue(self.col("gpt61terra", "max")["best"])
        self.assertIn('<a href="benchmarks/swe-v4-gpt61-terra-v329.html">GPT-6.1 Terra</a>', self.page)
        self.assertIn("&Dagger;&Dagger; Haiku 5.5 ran in Claude Code 2.1.293 to 2.1.296", self.page)
        self.assertIn("judged on 22, 22 and 21 of 23 tasks", self.page)
        self.assertEqual(self.marks("\u2021\u2021"), 5)
        self.assertIn('<a href="benchmarks/swe-v4-haiku55-v324.html">Haiku 5.5</a>', self.page)
        self.assertIn("&dagger;&dagger; Sonnet 5.5 ran in Claude Code 2.1.291 to 2.1.293", self.page)
        self.assertIn("committed hash bridge", self.page)
        self.assertIn("Grok 4.6 ran through Cursor CLI 2026.10.01, which updates itself", self.page)
        self.assertEqual(self.marks("\u2020\u2020"), 5)
        self.assertIn('<a href="benchmarks/swe-v4-sonnet55-v323.html">Sonnet 5.5</a>', self.page)
        self.assertIn("&loz; Grok 4.7 (xAI) ran in Cursor&#x27;s agent CLI 2026.10.01", self.page)
        self.assertIn("judged by Muse Spark 1.3 and GPT-6.1 Sol under v3.20", self.page)
        self.assertIn("second at Low behind Fable 5.1 (89.46)", self.page)
        self.assertIn("$/task is unavailable, not $0", self.page)
        self.assertEqual(self.marks("\u25ca"), 4)  # Grok 4.7's single mark, not Beam's doubled one
        self.assertEqual(sum(1 for c in self.chart if c["usd"] is None), 9)  # Grok 4.7's four columns and Reflection Beam's five
        self.assertIsNone(self.col("grok47cursor", "max"))
        self.assertIn('<a href="benchmarks/swe-v4-grok47-cursor-v320.html">Grok 4.7</a>', self.page)
        self.assertTrue(self.col("grok47cursor", "extra-high")["best"])
        js = (ROOT / "leaderboard-v4.js").read_text()
        self.assertIn("function plotted()", js)  # unpriced columns sit out the cost view
        self.assertIn("on the Tokens and Minutes views only", js)  # unpriced models are named in the caption
        self.assertIn("Most attractive quadrant", js)  # the shaded top-left corner: a score of 80 or more, left of the median x
        self.assertNotIn('id="v4board"', self.page)  # the chart and the CSV carry the board; no table
        models, columns, runs = len({r["model"] for r in self.rows}), len(self.rows), sum(r["n"] for r in self.rows)
        self.assertIn(f"&middot; {models} models &middot; {columns} model&times;effort columns &middot; {runs} runs &middot;", self.page)
        self.assertEqual(len(set(board.COLORS.values())), len(board.COLORS))
        self.assertEqual(set(board.COLORS), {r["key"] for r in self.rows})
        self.assertNotIn('id="swe-v3-board"', self.page)  # the leaderboard page shows Frontier v4 only
        self.assertNotIn('id="fullboard"', self.page)  # the retired v3 board stays JSON only; the page keeps one chart


if __name__ == "__main__":
    unittest.main()
