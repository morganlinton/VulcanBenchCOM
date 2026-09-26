"""Build the VulcanBench Routine v1 section of the leaderboard from the public aggregates.

Routine v1 is the private companion to Frontier v4: twelve routine tickets
(small Python packages, one clear ticket each). Task content is never
published, so this reads one aggregate file, per model and effort level,
written by the private repository's scripts/build_routine_aggregates.py, and
writes assets/data/routine-v1-board.csv and the block between the markers in
leaderboard.html.

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
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "leaderboard.html"
DATA = ROOT / "assets/data/routine-v1-aggregates.json"
CSV = ROOT / "assets/data/routine-v1-board.csv"
START, END = "<!-- routine-v1-board:start -->", "<!-- routine-v1-board:end -->"
ANCHOR = '  <section class="lb-section" id="swe-v3-board"'  # the Routine section goes in just above the retired v3 board
EFFORTS = ("low", "medium", "high", "extra-high", "max")
# Board order and display: key -> (model, harness, model page slug, lab, colour). Colours match the Frontier v4 board.
MODELS = {
    "fable": ("Fable 5.1", "Claude Code", "fable-5-1", "Anthropic", "#FF7A3D"),
    "opus55": ("Opus 5.5", "Claude Code", "claude-opus-5-5", "Anthropic", "#FFB347"),
    "astra": ("GPT-6 Astra", "Codex", "gpt-6-astra", "OpenAI", "#00FF9D"),
    "terra": ("GPT-5.6 Terra", "Codex", "gpt-5-6-terra", "OpenAI", "#00C9B1"),
    "sol": ("GPT-5.6 Sol", "Codex", "gpt-5-6-sol", "OpenAI", "#D4FF3F"),
    "luna": ("GPT-5.6 Luna", "Codex", "gpt-5-6-luna", "OpenAI", "#A8FFD8"),
    "gpt55": ("GPT-5.5", "Codex", "gpt-5-5", "OpenAI", "#22B573"),
    "swe2": ("SWE-2", "Devin CLI", "swe-2", "Cognition", "#B48CFF"),
}
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
            "completion_tokens": c["mean_completion_tokens"],
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


def money(value):
    return "n/a" if value is None else (f"${value:.3f}" if value < 0.1 else f"${value:.2f}")


def table_html(board, picks):
    lines = ['<div class="lb-scroll">', '<table class="lb" id="routineboard">',
             '<caption class="sr-only">VulcanBench Routine v1: every model and effort level on twelve routine tickets</caption>',
             '<thead><tr><th class="l" scope="col">Model / harness</th><th scope="col">Effort</th><th scope="col">Passed</th>'
             '<th scope="col">Combined</th><th scope="col">SE</th><th scope="col">Code quality</th><th scope="col">Sec/task</th>'
             '<th scope="col">$/task</th></tr></thead>', "<tbody>"]
    for r in board:
        picked = picks[r["key"]]["effort"] == r["effort"]
        tag = '<span class="fb-best">suggested</span>' if picked else ""
        page = ROOT / f'models/{r["slug"]}.html'
        name = f'<a class="lb-model" href="models/{r["slug"]}.html">{escape(r["model"])}</a>' if page.is_file() else f'<span class="lb-model">{escape(r["model"])}</span>'
        se = "" if r["combined_se"] is None else f'{r["combined_se"]:.2f}'
        lines.append(
            f'<tr data-model="{r["key"]}" data-effort="{r["effort"]}" data-suggested="{int(picked)}">'
            f'<td class="l"><span class="v4dot" style="background:{MODELS[r["key"]][4]}"></span>{name} <span class="lb-harness">{escape(r["harness"])}</span>{tag}</td>'
            f'<td class="fb-eff">{r["effort"]}</td><td>{r["passed"]}/{r["n"]}</td><td class="lb-win">{r["combined"]:.2f}</td><td>{se}</td>'
            f'<td>{r["code_quality"]:.2f}</td><td>{r["seconds"]:.0f}</td><td>{money(r["usd"])}</td></tr>')
    lines += ["</tbody>", "</table>", "</div>"]
    return "\n".join(lines)


def picks_html(picks):
    items = []
    for key in MODELS:
        if key not in picks:
            continue
        p = picks[key]
        note = "its lowest level" if p["effort"] == p["lowest_effort"] else f'{p["gap"]:.1f} points under its best at {p["best_effort"]}'
        items.append(f'<li><strong>{escape(p["model"])}</strong>: {p["effort"]} ({p["passed"]}/{p["n"]} passed, combined {p["combined"]:.1f}, {note})</li>')
    return '<ul class="lb-context">' + "".join(items) + "</ul>"


def render(data, board):
    picks = suggestions(board)
    models = len({r["key"] for r in board})
    runs = sum(r["n"] for r in board)
    panels = " and ".join({"muse": "Muse Spark 1.3", "grok": "Grok 4.6"}.get(p, p) for p in data["code_quality"]["passing_panels"])
    return (f"{START}\n"
            '  <section class="lb-section" id="routine-v1-board" aria-labelledby="rv1-board-heading" style="margin-top:40px;">\n'
            '    <div class="lb-shead">\n      <h2 id="rv1-board-heading">VulcanBench Routine v1</h2>\n    </div>\n'
            f'<p class="lb-context">Frontier v4 asks which model and effort level can do hard work. Routine v1 asks the everyday question: what is the cheapest effort level '
            f"that is enough for an ordinary ticket. It is {data['tasks']} private routine tickets on small Python packages (a targeted bug fix, a small feature behind a flag, input validation, "
            "an edge case in dates, money or text), each admitted because a frontier model at its lowest effort finds it easy. "
            f"{models} models, {len(board)} model&times;effort columns, {runs:,} runs, one attempt per task and level, each model through its own CLI on a subscription. "
            "The tasks stay private so they cannot leak into training data, so only per-model, per-effort aggregates are published.</p>\n"
            '<p class="lb-context"><strong>Suggested effort for routine work</strong>, by the same rule as the Frontier board: the cheapest level, then the fastest, '
            f"within {TOLERANCE:g} combined-score points of the model&rsquo;s best.</p>\n"
            f"{picks_html(picks)}\n"
            f"{table_html(board, picks)}\n"
            '<p class="lb-context">Combined score uses the Frontier weights: 50% functional correctness from hidden tests, 8.5% lint and complexity, 8.5% security and 33% Code quality, '
            f"judged by {panels} under Code quality protocol v3.8 (Opus 5.5 under v3.14, the same protocol on its own population, judged in a separate session) with the same rubric, controls, gates and calibration exam as Frontier v4. "
            "<strong>Routine and Frontier Code quality are not comparable.</strong> On Frontier v4 part of Code quality measures whether a reviewer can recover each task&rsquo;s deliberate legacy quirks; "
            "routine tickets have no such quirks by design, so the protocol&rsquo;s own pre-registered rule scores Routine Code quality from the reviewed panel alone. Compare levels and models within this table, never across the two boards. "
            "SE is one task standard error of the combined score. Sec/task is mean wall clock. $/task is API-equivalent at list rates from the solver receipts, not a subscription bill; "
            "SWE-2 has no public per-token price, so its cost is not shown and its suggestion is made on time alone. "
            '<a href="assets/data/routine-v1-board.csv" download>Download this table as CSV</a>.</p>\n'
            "  </section>\n"
            f"{END}")


def csv_text(board, picks):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["model", "lab", "harness", "effort", "suggested_for_routine", "n", "passed", "combined_33", "combined_33_se", "code_quality_l1",
                     "mean_seconds", "mean_usd", "mean_completion_tokens", "protocol"])
    for r in board:
        writer.writerow([r["model"], r["lab"], r["harness"], r["effort"], picks[r["key"]]["effort"] == r["effort"], r["n"], r["passed"],
                         f'{r["combined"]:.4f}', "" if r["combined_se"] is None else f'{r["combined_se"]:.4f}', f'{r["code_quality"]:.4f}',
                         f'{r["seconds"]:.1f}', "" if r["usd"] is None else f'{r["usd"]:.6f}', f'{r["completion_tokens"]:.1f}',
                         r["protocol"]])
    return buffer.getvalue()


def place(page, block):
    """Replace the marked block, or insert it above the retired v3 section the first time."""
    if page.count(START) == 1 and page.count(END) == 1:
        head, rest = page.split(START, 1)
        _, tail = rest.split(END, 1)
        return head + block + tail
    assert START not in page and END not in page, "leaderboard.html has a broken routine-v1-board block"
    assert page.count(ANCHOR) == 1, "leaderboard.html lost the v3 section the Routine block sits above"
    head, tail = page.split(ANCHOR, 1)
    return head + block + "\n\n" + ANCHOR + tail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--from", dest="source", type=Path, help="import this aggregate file into assets/data first")
    parser.add_argument("--preview", action="store_true", help="build from unfinished data into a scratch copy of the page; never for publication")
    args = parser.parse_args()
    data = load(args.source or DATA)
    blockers = problems(data)
    if blockers and not args.preview:
        print("refusing to publish Routine v1:")
        for b in blockers:
            print(f"  {b}")
        sys.exit(1)
    if args.preview:
        for c in data["cells"]:  # unjudged preview only: stand in the no-judges total so the layout can be checked
            c.setdefault("mean_combined", round(100 * c["mean_total_no_judges"], 2))
            c.setdefault("mean_code_quality", 0.0)
        data.setdefault("code_quality", {}).setdefault("passing_panels", ["muse", "grok"])
        data["cells"] = [c for c in data["cells"] if c["model_key"] in MODELS]
    board = rows(data)
    block = render(data, board)
    table = csv_text(board, suggestions(board))
    for text in (block, table):
        assert chr(0x2014) not in text and chr(0x2013) not in text
    new_page = place(PAGE.read_text(), block)
    if args.preview:
        out = ROOT / "leaderboard.preview.html"
        out.write_text(new_page)
        print(f"PREVIEW ONLY ({len(blockers)} blocker(s)); wrote {out.name}, which is not tracked or published")
        return
    outputs = {PAGE: new_page, CSV: table, DATA: json.dumps(data, indent=1) + "\n"}
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
