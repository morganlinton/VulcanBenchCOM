"""Build the published VulcanBench Routine v1 board data from the public aggregates.

Routine v1 is the private companion to Frontier v4: twelve routine tickets
(small Python packages, one clear ticket each). Task content is never
published, so this reads one aggregate file, per model and effort level,
written by the private repository's scripts/build_routine_aggregates.py, and
writes assets/data/routine-v1-board.csv. The leaderboard page shows Frontier v4
only, so nothing here writes to it.

Nothing partial is published: the build refuses unless every cell has all
twelve tasks, no run is flagged, and the Code quality v3.8 record says it is
ready for publication.

    python3 scripts/build_routine_v1_board.py                      # rewrite the outputs
    python3 scripts/build_routine_v1_board.py --check              # exit 1 if any output is stale
    python3 scripts/build_routine_v1_board.py --from ../VulcanRoutine/results/routine-v1-aggregates.json
"""

import argparse
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/routine-v1-aggregates.json"
CSV = ROOT / "assets/data/routine-v1-board.csv"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
# Board order and display: key -> (model, harness, model page slug, lab, colour).
MODELS = {
    "fable": ("Fable 5.1", "Claude Code", "fable-5-1", "Anthropic", "#FF7A3D"),
    "opus55": ("Opus 5.5", "Claude Code", "claude-opus-5-5", "Anthropic", "#FFB347"),
    "astra": ("GPT-6 Astra", "Codex", "gpt-6-astra", "OpenAI", "#00FF9D"),
    "terra": ("GPT-5.6 Terra", "Codex", "gpt-5-6-terra", "OpenAI", "#00C9B1"),
    "sol": ("GPT-5.6 Sol", "Codex", "gpt-5-6-sol", "OpenAI", "#D4FF3F"),
    "luna": ("GPT-5.6 Luna", "Codex", "gpt-5-6-luna", "OpenAI", "#A8FFD8"),
    "gpt55": ("GPT-5.5", "Codex", "gpt-5-5", "OpenAI", "#22B573"),
    "grok47-cursor": ("Grok 4.7", "Cursor", "grok-4-7", "xAI", "#A9B8FF"),
}
# Cursor's run summaries record 0 tokens (the adapter does not read the stream's usage block), so these models' token
# means in the aggregate file are not measurements; the board publishes them as blank, never 0.
TOKENS_UNRECORDED = {"grok47-cursor"}
TOLERANCE = 3.0  # the Frontier board's "routine" tolerance, in combined-score points
PRIVATE_KEYS = ("task_id", "run_id", "task", "source_directory", "issue")


def load(path=DATA):
    data = json.loads(Path(path).read_text())
    text = json.dumps(data)
    for key in PRIVATE_KEYS:
        if f'"{key}"' in text:
            raise SystemExit(f"{path} carries the private field {key!r}; publish the aggregate file only")
    return data


def problems(data):
    """Reasons this aggregate file must not be published yet."""
    out = []
    cq = data.get("code_quality", {})
    if cq.get("status") != "judged" or not cq.get("ready_for_publication"):
        out.append("Code quality v3.8 is not judged and ready for publication")
    if data.get("task_hash_drift"):
        out.append("task definitions drifted during the sweeps")
    for c in data["cells"]:
        where = f'{c["model_key"]}/{c["effort"]}'
        if c["model_key"] not in MODELS:
            out.append(f"{where}: unknown model")
        if not c["complete"]:
            out.append(f'{where}: {c["tasks"]} of {c["tasks_expected"]} tasks')
        if c.get("contaminated") or c.get("astra_long_context_runs"):
            out.append(f"{where}: flagged runs")
        if c.get("mean_combined") is None:
            out.append(f"{where}: no combined score")
    return out


def rows(data):
    out = []
    for c in data["cells"]:
        model, harness, slug, lab, _ = MODELS[c["model_key"]]
        out.append({
            "key": c["model_key"], "model": model, "harness": harness, "slug": slug, "lab": lab, "effort": c["effort"],
            "n": c["tasks"], "passed": c["passes"], "combined": c["mean_combined"], "combined_se": c.get("se_combined"),
            "code_quality": c["mean_code_quality"],
            "protocol": c.get("judging_protocol") or "code-quality-maintenance-v3.8", "seconds": c["mean_duration_s"], "usd": c["mean_cost_usd"],
            "completion_tokens": None if c["model_key"] in TOKENS_UNRECORDED else c["mean_completion_tokens"],
        })
    order = list(MODELS)
    out.sort(key=lambda r: (order.index(r["key"]), EFFORTS.index(r["effort"])))
    return out


def suggestions(board):
    """Per model: the cheapest level (then fastest) within TOLERANCE points of the model's best combined score.

    The same rule as the Frontier v4 board's routine tolerance. A model with no public price is picked on time alone.
    """
    by_model = {}
    for r in board:
        by_model.setdefault(r["key"], []).append(r)
    out = {}
    for key, levels in by_model.items():
        best = max(levels, key=lambda r: r["combined"])
        ok = [r for r in levels if best["combined"] - r["combined"] <= TOLERANCE]
        priced = all(r["usd"] is not None for r in levels)
        pick = min(ok, key=lambda r: (r["usd"], r["seconds"]) if priced else (r["seconds"],))
        lowest = levels[0]
        out[key] = {"model": pick["model"], "effort": pick["effort"], "combined": pick["combined"], "best_effort": best["effort"],
                    "best_combined": best["combined"], "gap": best["combined"] - pick["combined"],
                    "spread": best["combined"] - lowest["combined"], "lowest_effort": lowest["effort"],
                    "passed": pick["passed"], "n": pick["n"], "basis": "cost then time" if priced else "time (no public price)"}
    return out


def csv_text(board, picks):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["model", "lab", "harness", "effort", "suggested_for_routine", "n", "passed", "combined_33", "combined_33_se", "code_quality_l1",
                     "mean_seconds", "mean_usd", "mean_completion_tokens", "protocol"])
    for r in board:
        writer.writerow([r["model"], r["lab"], r["harness"], r["effort"], picks[r["key"]]["effort"] == r["effort"], r["n"], r["passed"],
                         f'{r["combined"]:.4f}', "" if r["combined_se"] is None else f'{r["combined_se"]:.4f}', f'{r["code_quality"]:.4f}',
                         f'{r["seconds"]:.1f}', "" if r["usd"] is None else f'{r["usd"]:.6f}', "" if r["completion_tokens"] is None else f'{r["completion_tokens"]:.1f}',
                         r["protocol"]])
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--from", dest="source", type=Path, help="import this aggregate file into assets/data first")
    args = parser.parse_args()
    data = load(args.source or DATA)
    blockers = problems(data)
    if blockers:
        print("refusing to publish Routine v1:")
        for b in blockers:
            print(f"  {b}")
        sys.exit(1)
    board = rows(data)
    table = csv_text(board, suggestions(board))
    assert chr(0x2014) not in table and chr(0x2013) not in table
    outputs = {CSV: table, DATA: json.dumps(data, indent=1) + "\n"}
    stale = [p for p, text in outputs.items() if not p.exists() or p.read_text() != text]
    if args.check:
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)}")
        print("Routine v1 board is current" if not stale else f"{len(stale)} stale output(s)")
        sys.exit(1 if stale else 0)
    for p, text in outputs.items():
        p.write_text(text)
    print(f"{len(board)} columns, {len({r['key'] for r in board})} models; wrote {', '.join(p.name for p in outputs)}")


if __name__ == "__main__":
    main()
