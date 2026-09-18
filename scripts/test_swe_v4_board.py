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
        self.assertEqual(len(self.rows), 24)
        self.assertEqual({r["model"] for r in self.rows}, {"GPT-6 Astra", "Fable 5.1", "GPT-5.5", "GPT-5.6 Luna", "GPT-5.6 Terra"})
        self.assertEqual(sum(1 for r in self.rows if r["best"]), 5)
        self.assertEqual([r["rank"] for r in self.rows], list(range(1, 25)))
        self.assertEqual([r["combined"] for r in self.rows], sorted((r["combined"] for r in self.rows), reverse=True))
        self.assertEqual(sum(r["n"] for r in self.rows), 552)
        for r in self.rows:
            self.assertTrue((ROOT / f"models/{r['slug']}.html").is_file(), r["slug"])
            self.assertTrue((ROOT / r["report"]).is_file(), r["report"])
            self.assertGreater(r["usd"], 0)
            self.assertGreater(r["output_tokens_median"], 0)
            self.assertGreater(r["output_tokens_mean"], 0)
        terra_max = next(r for r in self.rows if r["key"] == "terra" and r["effort"] == "max")
        self.assertEqual(terra_max["n"], 23)
        self.assertEqual(len(self.csv), 24)
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
                self.assertEqual(r["passed"], g["passed"])
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
            best = max(levels, key=lambda r: r["combined"])
            self.assertEqual(entry["best_effort"], best["effort"])
            self.assertEqual(entry["shape"], "flat" if entry["spread"] <= 3 else "steep")
            for name, tol in self.json["tolerances"].items():
                pick = next(r for r in levels if r["effort"] == entry[name]["effort"])
                self.assertLessEqual(best["combined"] - pick["combined"], tol)
                for r in levels:  # nothing cheaper qualifies
                    if best["combined"] - r["combined"] <= tol:
                        self.assertGreaterEqual((r["usd"], r["minutes"]), (pick["usd"], pick["minutes"]))
        self.assertEqual({k: v["routine"]["effort"] for k, v in sug.items()},
                         {"fable": "low", "astra": "medium", "terra": "max", "luna": "max", "gpt55": "extra-high"})
        self.assertEqual({k: v["shape"] for k, v in sug.items()}, {"fable": "flat", "astra": "flat", "terra": "steep", "luna": "steep", "gpt55": "steep"})

    def test_page_writing_and_structure(self):
        text = html.unescape(self.page)
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn(chr(0x2013), text)
        self.assertEqual(self.page.count(board.START), 1)
        self.assertEqual(self.page.count(board.END), 1)
        self.assertIn("VulcanBench-SWE v3 (retired in August 2026)", self.page)
        self.assertLess(self.page.index('id="swe-v4-board"'), self.page.index('id="swe-v3-board"'))
        self.assertNotIn('id="fullboard"', self.page)  # the retired v3 board is JSON only; the page keeps one chart


if __name__ == "__main__":
    unittest.main()
