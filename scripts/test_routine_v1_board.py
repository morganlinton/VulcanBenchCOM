"""The Routine v1 leaderboard block and CSV are generated from the public aggregate file and current."""

import csv
import html
import json
import unittest
from pathlib import Path

import build_routine_v1_board as board

ROOT = Path(__file__).resolve().parents[1]


def cell(key, effort, combined, usd, seconds, passes=12, tasks=12):
    return {"model_key": key, "effort": effort, "tasks": tasks, "tasks_expected": 12, "complete": tasks == 12, "passes": passes,
            "mean_combined": combined, "se_combined": 0.5, "mean_code_quality": 70.0, "mean_duration_s": seconds, "mean_cost_usd": usd,
            "mean_completion_tokens": 1000.0, "mean_total_no_judges": 0.9, "contaminated": 0, "astra_long_context_runs": 0}


def sample(cells):
    return {"tasks": 12, "task_hash_drift": 0, "cells": cells,
            "code_quality": {"status": "judged", "ready_for_publication": True, "passing_panels": ["muse", "grok"]}}


class RuleTests(unittest.TestCase):
    """The publication gate and the suggestion rule, on synthetic aggregates."""

    def test_suggestion_is_cheapest_then_fastest_within_tolerance(self):
        data = sample([cell("astra", "low", 86.0, 0.30, 70), cell("astra", "medium", 88.5, 0.26, 75), cell("astra", "max", 90.0, 0.56, 180)])
        picks = board.suggestions(board.rows(data))
        self.assertEqual(picks["astra"]["effort"], "medium")  # low is 4 points under the best; medium is cheaper than max
        self.assertEqual(picks["astra"]["best_effort"], "max")

    def test_unpriced_model_is_picked_on_time(self):
        data = sample([cell("luna", "medium", 85.0, None, 200), cell("luna", "high", 86.0, None, 150), cell("luna", "max", 86.5, None, 400)])
        self.assertEqual(board.suggestions(board.rows(data))["luna"]["effort"], "high")
        self.assertIn("<td>unavailable</td>", board.table_html(board.rows(data), board.suggestions(board.rows(data))))

    def test_incomplete_unjudged_or_flagged_data_is_refused(self):
        self.assertEqual(board.problems(sample([cell("astra", "low", 86.0, 0.3, 70)])), [])
        self.assertTrue(board.problems(sample([cell("astra", "low", 86.0, 0.3, 70, tasks=11)])))
        unjudged = sample([cell("astra", "low", 86.0, 0.3, 70)])
        unjudged["code_quality"] = {"status": "not judged yet"}
        self.assertTrue(board.problems(unjudged))
        flagged = sample([cell("astra", "low", 86.0, 0.3, 70)])
        flagged["cells"][0]["contaminated"] = 1
        self.assertTrue(board.problems(flagged))

    def test_private_fields_are_refused(self):
        path = ROOT / "scripts" / "_routine_private_probe.json"
        path.write_text(json.dumps({"cells": [{"task_id": "x"}]}))
        try:
            with self.assertRaises(SystemExit):
                board.load(path)
        finally:
            path.unlink()

    def test_block_is_inserted_once_above_the_v3_board_and_then_replaced(self):
        data = sample([cell("astra", "low", 86.0, 0.3, 70)])
        block = board.render(data, board.rows(data))
        page = "<main>\n" + board.ANCHOR + ' aria-labelledby="x">\n</section></main>'
        once = board.place(page, block)
        self.assertEqual(once.count(board.START), 1)
        self.assertLess(once.index(board.START), once.index(board.ANCHOR))
        self.assertEqual(board.place(once, block), once)
        text = html.unescape(block)
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn(chr(0x2013), text)
        self.assertIn("Routine and Frontier Code quality are not comparable.", text)


@unittest.skipUnless(board.DATA.is_file(), "Routine v1 aggregates are not published yet")
class PublishedBoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = board.load()
        cls.rows = board.rows(cls.data)
        cls.page = (ROOT / "leaderboard.html").read_text()

    def test_published_data_passes_the_gate(self):
        self.assertEqual(board.problems(self.data), [])
        self.assertTrue(all(r["n"] == 12 for r in self.rows))

    def test_outputs_are_current(self):
        self.assertIn(board.render(self.data, self.rows), self.page)
        self.assertEqual(board.csv_text(self.rows, board.suggestions(self.rows)), board.CSV.read_text())
        with board.CSV.open(newline="") as source:
            table = list(csv.DictReader(source))
        self.assertEqual(len(table), len(self.rows))
        self.assertEqual(sum(1 for r in table if r["suggested_for_routine"] == "True"), len({r["key"] for r in self.rows}))

    def test_grok47_cells(self):
        grok = {r["effort"]: r for r in self.rows if r["key"] == "grok47-cursor"}
        self.assertEqual(list(grok), ["low", "medium", "high", "extra-high"])  # Cursor offers no max level for Grok 4.7
        self.assertTrue(all(r["passed"] == r["n"] == 12 for r in grok.values()))
        self.assertEqual([r["combined"] for r in grok.values()], [97.29, 97.21, 97.37, 97.14])
        self.assertEqual([r["code_quality"] for r in grok.values()], [94.62, 94.27, 94.62, 93.92])
        self.assertEqual([round(r["seconds"] / 60, 1) for r in grok.values()], [1.1, 1.8, 3.2, 4.0])
        self.assertTrue(all(r["protocol"] == "code-quality-maintenance-v3.22" and r["usd"] is None and r["completion_tokens"] is None
                            for r in grok.values()))
        pick = board.suggestions(self.rows)["grok47-cursor"]
        self.assertEqual((pick["effort"], pick["basis"]), ("low", "time (no public price)"))
        self.assertEqual(max(r["combined"] for r in self.rows), 97.37)  # Grok 4.7 high is the top Routine column
        [record] = [r for r in self.data["code_quality"]["additional_records"] if r["protocol"] == "code-quality-maintenance-v3.22"]
        self.assertEqual((record["passing_panels"], record["failed_panels"], record["published_submissions"]), (["muse"], ["sol"], 48))
        self.assertIn("Grok 4.7 is judged under v3.22 by Muse Spark 1.3 alone", self.page)
        self.assertIn("failed that protocol&rsquo;s calibration exam on two gates", self.page)
        self.assertIn("lowest tested levels at 93.1 to 95.6, against Grok 4.7&rsquo;s 97.3 at Low", self.page)
        with board.CSV.open(newline="") as source:
            for row in csv.DictReader(source):
                if row["model"] == "Grok 4.7":
                    self.assertEqual((row["mean_usd"], row["mean_completion_tokens"]), ("", ""))
        block = self.page.split(board.START, 1)[1].split(board.END, 1)[0]
        self.assertEqual(block.count('data-model="grok47-cursor"'), 4)
        self.assertEqual(block.count("<td>unavailable</td>"), 4)
        self.assertNotIn("SWE-2", block)
        self.assertNotIn("Devin", block)

    def test_page_order_and_no_task_content(self):
        self.assertLess(self.page.index('id="swe-v4-board"'), self.page.index('id="routine-v1-board"'))
        self.assertLess(self.page.index('id="routine-v1-board"'), self.page.index('id="swe-v3-board"'))
        self.assertNotIn("routine-", self.page.split(board.START, 1)[1].split(board.END, 1)[0].replace("routine-v1-board", ""))


if __name__ == "__main__":
    unittest.main()
