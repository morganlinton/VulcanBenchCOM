"""Independently check the public evidence without private files or model calls."""

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1] / "assets/data/swe-v4-astra-fable51"


def load(name):
    return json.loads((ROOT / name).read_text())


def main():
    data = load("runs.json")
    rows, groups = data["rows"], load("groups.json")
    votes, calls, costs = load("ratings.json"), load("reviewer-calls.json"), load("costs.json")
    assert len(rows) == 230 and len(votes) == 1380 and len(calls) == 1386
    assert data["weights"] == {"functional": .5, "quality": .15, "security": .15, "human_like": .2}
    assert len({(r["model"], r["effort"], r["task"]) for r in rows}) == 230
    assert len({r["task"] for r in rows}) == 23
    rated = defaultdict(list)
    for vote in votes:
        rated[vote["solver"], vote["effort"], vote["run_id"], vote["reviewer"]].append(vote)
    selected = {c["sha256"] for c in calls if c["included_in_score"]}
    assert len(selected) == 1380 and selected == {v["raw_stream_sha256"] for v in votes}
    assert sum(c["fallback"] and c["included_in_score"] for c in calls) == 10
    assert sum(c["format_recovered"] for c in calls) == 2
    assert Counter((c["solver"], c["reviewer"]) for c in calls if c["included_in_score"]) == {
        ("astra", "astra"): 345, ("astra", "claude"): 345,
        ("fable", "astra"): 345, ("fable", "claude"): 345}
    for row in rows:
        for reviewer in ("astra", "claude"):
            panel = rated[row["model"], row["effort"], row["run_id"], reviewer]
            assert {v["persona"] for v in panel} == {"correctness", "readability", "maintainability"}
            assert len(panel) == 3
            assert round(sum(v["score"] for v in panel) / 300, 4) == row[reviewer]
        score = .5 * row["functional"] + .15 * row["quality"] + .15 * row["security"]
        panel = (row["astra"] + row["claude"]) / 2
        assert math.isclose(panel, row["panel"], abs_tol=1e-12)
        assert math.isclose(score + .2 * panel, row["combined"], abs_tol=1e-12)
    assert len(groups) == 10
    tasks = {r["task"] for r in rows}
    for group in groups:
        subset = [r for r in rows if (r["model"], r["effort"]) == (group["model"], group["effort"])]
        assert len(subset) == 23 and {r["task"] for r in subset} == tasks
        for metric in ("combined", "panel", "functional", "quality", "security", "astra", "claude", "minutes"):
            values = [r["duration_s"] / 60 if metric == "minutes" else 100 * r[metric] for r in subset]
            assert math.isclose(statistics.mean(values), group[metric]["mean"], abs_tol=1e-10)
            assert math.isclose(statistics.stdev(values) / math.sqrt(23), group[metric]["se"], abs_tol=1e-10)
        assert sum(r["solver_receipt"]["raw_tokens"] for r in subset) == group["raw_tokens"]
    assert len(costs["rows"]) == 230
    assert {(r["model"], r["run_id"]) for r in costs["rows"]} == {(r["model"], r["run_id"]) for r in rows}
    for model in ("astra", "fable"):
        total = sum(c["estimated_usd"] for c in costs["rows"] if c["model"] == model)
        assert math.isclose(total, costs["totals_usd"][model], abs_tol=1e-8)
    for path in ROOT.iterdir():
        if path.suffix in {".json", ".md"}:
            text = path.read_text()
            assert not any(mark in text for mark in (chr(0x2014), chr(0x2013), "/Users/", "/home/")), path
    print("Verified 230 runs, 1380 ratings, 1386 calls, ten groups, fixed weights and cost totals.")


if __name__ == "__main__":
    main()
