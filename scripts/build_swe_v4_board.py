"""Build the VulcanBench Frontier v4 leaderboard from the published evidence bundles.

Every model-and-harness column at every effort level it ran, ranked by
combined score, with Code quality, tasks passed, runtime and API-equivalent
cost beside it (unavailable for a column with no list price, never $0). Reads only the public bundles under assets/data/ and writes
assets/data/swe-v4-board.json, assets/data/swe-v4-board.csv and the table
block between the markers in leaderboard.html.

    python3 scripts/build_swe_v4_board.py            # rewrite the outputs
    python3 scripts/build_swe_v4_board.py --check    # exit 1 if any output is stale
"""

import argparse
import csv
import io
import json
import statistics
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "leaderboard.html"
START, END = "<!-- swe-v4-board:start -->", "<!-- swe-v4-board:end -->"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
LABEL = {"low": "low", "medium": "medium", "high": "high", "extra-high": "extra-high", "max": "max"}
SOURCES = [
    {"bundle": "swe-v4-astra-fable51-v34", "report": "benchmarks/swe-v4-astra-fable51-v34.html", "protocol": "v3.4",
     "models": {"astra": ("GPT-6 Astra", "Codex", "gpt-6-astra", "OpenAI"), "fable": ("Fable 5.1", "Claude Code", "fable-5-1", "Anthropic")}},
    {"bundle": "swe-v4-gpt55-luna-v35", "report": "benchmarks/swe-v4-gpt55-luna-v35.html", "protocol": "v3.5",
     "models": {"gpt55": ("GPT-5.5", "Codex", "gpt-5-5", "OpenAI"), "luna": ("GPT-5.6 Luna", "Codex", "gpt-5-6-luna", "OpenAI")}},
    {"bundle": "swe-v4-terra-v36", "report": "benchmarks/swe-v4-terra-v36.html", "protocol": "v3.6",
     "models": {"terra": ("GPT-5.6 Terra", "Codex", "gpt-5-6-terra", "OpenAI")}},
    {"bundle": "swe-v4-sol-v37", "report": "benchmarks/swe-v4-sol-v37.html", "protocol": "v3.7",
     "models": {"sol": ("GPT-5.6 Sol", "Codex", "gpt-5-6-sol", "OpenAI")}},
    {"bundle": "swe-v4-opus55-v315", "report": "benchmarks/swe-v4-opus55-v315.html", "protocol": "v3.15",
     "models": {"opus55": ("Opus 5.5", "Claude Code", "claude-opus-5-5", "Anthropic")}},
    # Six GPT-6 Luna runs hit the 3-hour bound: passes count over all 23 runs, and the cells carry the timeouts-as-0 figure.
    {"bundle": "swe-v4-gpt6-luna-v316", "report": "benchmarks/swe-v4-gpt6-luna-v316.html", "protocol": "v3.16", "pass_over_all_runs": True,
     "models": {"gpt6luna": ("GPT-6 Luna", "Codex", "gpt-6-luna", "OpenAI")}},
    # One GPT-6 Sol medium run has no published Code quality score; it failed its tests, so passes count over all 23 runs.
    {"bundle": "swe-v4-gpt6-sol-v317", "report": "benchmarks/swe-v4-gpt6-sol-v317.html", "protocol": "v3.17", "pass_over_all_runs": True,
     "models": {"gpt6sol": ("GPT-6 Sol", "Codex", "gpt-6-sol", "OpenAI")}},
    # Every GPT-6.1 Sol row is published (one, medium paddockcore, from Muse alone), so judged and passed counts are over 23.
    {"bundle": "swe-v4-gpt61-sol-v318", "report": "benchmarks/swe-v4-gpt61-sol-v318.html", "protocol": "v3.18",
     "models": {"gpt61sol": ("GPT-6.1 Sol", "Codex", "gpt-6-1-sol", "OpenAI")}},
    # Grok 4.7 is judged by Muse Spark 1.3 and GPT-6.1 Sol (Grok 4.6 is not neutral for xAI). One medium timeout, so passes count over
    # all 23 runs. No list price: the bundle has usage.json (time and tokens) in place of economics.json, and $/task is unavailable.
    {"bundle": "swe-v4-grok47-cursor-v320", "report": "benchmarks/swe-v4-grok47-cursor-v320.html", "protocol": "v3.20", "pass_over_all_runs": True,
     "economics": "usage.json", "judges": "Muse Spark 1.3 and GPT-6.1 Sol",
     "models": {"grok47cursor": ("Grok 4.7", "Cursor", "grok-4-7", "xAI")}},
]
FOOTNOTES = {
    "fable": "Fable 5.1 runs include 11 disclosed Opus 4.8 fallbacks across the sweep; they stay in the population.",
    "terra": "GPT-5.6 Terra at max includes paddockcore, run on September 17 on a second ChatGPT account after the first hit its quota window and judged under the v3.6.1 top-up with the same judges and calibration.",
    "opus55": "Opus 5.5 ran with Claude Code's refusal fallback on (Default Fallback) and counts every run: Opus 4.8 wrote some replies in 0, 3, 7, 8 and 12 runs from low to max (0.0, 6.4, 20.9, 32.4 and 47.8% of replies). High is judged on 22 of 23 tasks: on depotcore a safeguard classifier stop left an empty patch, so there is no code to review; the run scored 0 and is priced.",
    "gpt6luna": ("GPT-6 Luna at extra-high and max is judged on {xh_n} and {max_n} of 23 tasks: the other {xh_t} and {max_t} runs hit the flat "
                 "3-hour task bound while still working, have no finished code to judge, count as failed tasks and are unpriced ($/task "
                 "covers the finished runs; Min/task covers all 23). Counting each timeout as a combined score of 0 over all 23 runs gives "
                 "{xh_zero:.2f} at extra-high and {max_zero:.2f} at max; its best tag and effort suggestions use these figures. Ran on Codex CLI 0.155.0, the first release that serves GPT-6 Luna "
                 "on a ChatGPT plan; the extra-high pacecore run was retried after an 88-minute Codex client stall, and the retry counts."),
    "gpt6sol": ("GPT-6 Sol at medium is judged on 22 of 23 tasks: on codeccore, Grok 4.6's intent probe gave no valid answer (one "
                "malformed attempt, one quoting code absent from the run), so the v3.17 protocol publishes no Code quality score for that "
                "run; the run failed its tests, counts as a failed task in Passed (over all 23) and is priced. Ran on Codex CLI 0.155.0, the "
                "first release that serves GPT-6 Sol on a ChatGPT plan; no run reached the 3-hour bound."),
    "gpt61sol": ("GPT-6.1 Sol at medium includes paddockcore with Code quality from Muse Spark 1.3 alone: Grok 4.6's review of that run "
                 "had no valid response (both attempts quoted a changed line), so the v3.18 protocol scores it from the one valid review, as it "
                 "does for any such run. Every GPT-6.1 Sol cell is judged on 23 runs. Ran on Codex CLI 0.159.0, the first release that serves "
                 "GPT-6.1 Sol on a ChatGPT plan; no run reached the 3-hour bound."),
    "grok47cursor": ("Grok 4.7 (xAI) ran in Cursor's agent CLI 2026.10.01, which offers Low to Extra High and no Max. It is judged by Muse "
                     "Spark 1.3 and GPT-6.1 Sol under v3.20, because Grok 4.6, the second judge for every other column, is not neutral for an "
                     "xAI model. GPT-6.1 Sol rates Grok 4.7's code about {gap:.0f} points above Muse does, so its Code quality and combined "
                     "score are not strictly comparable with the other columns. Rescored from Muse Spark 1.3 alone for every column, Grok 4.7 "
                     "scores {muse_lo:.2f} to {muse_hi:.2f}: still first at Medium, High and Extra-high, and second at Low behind Fable 5.1 "
                     "({fable_low:.2f}). Medium is judged on {med_n} of 23 tasks: lodgecore hit the 3-hour bound, counts as a failed task in "
                     "Passed (over all 23) and in Min/task, and has no score. $/task is unavailable, not $0: VulcanBench has no list price for "
                     "Grok 4.7 and the sweep ran on the Cursor subscription, so it is not on the cost chart and its effort suggestions are "
                     "picked on time alone."),
    "sol": "GPT-5.6 Sol at max is judged on 22 of 23 tasks: on codeccore, Grok 4.6's intent probe quoted an excerpt absent from the code on both attempts, so the v3.7 protocol publishes no Code quality score for that run; the run passed its tests and is priced.",
}


def read(name):
    return json.loads((ROOT / "assets/data" / name).read_text())


def priced(r):
    return r["usd"] is not None


def usd_key(r):
    """Cost for sorting: an unpriced column sorts after every priced one."""
    return r["usd"] if priced(r) else float("inf")


def output_tokens(bundle):
    """Median and mean completion tokens per task for every model and effort cell of a bundle."""
    cells = {}
    for r in read(f"{bundle}/runs.json")["rows"]:
        if r["token_usage"] is None:  # a timed-out run with no usage receipt
            continue
        cells.setdefault((r["model"], r["effort"]), []).append(r["token_usage"]["output_tokens"])
    return {key: {"median": statistics.median(v), "mean": statistics.mean(v)} for key, v in cells.items()}


def rows():
    out = []
    for source in SOURCES:
        groups = read(f"{source['bundle']}/groups.json")
        econ = {(g["model"], g["effort"]): g for g in read(f"{source['bundle']}/{source.get('economics', 'economics.json')}")["groups"]}
        tokens = output_tokens(source["bundle"])
        for g in groups:
            name, harness, slug, lab = source["models"][g["model"]]
            e = econ[g["model"], g["effort"]]
            t = tokens[g["model"], g["effort"]]
            over_all = source.get("pass_over_all_runs", False)
            out.append({
                "model": name, "lab": lab, "harness": harness, "slug": slug, "key": g["model"], "effort": g["effort"], "n": g["n"],
                "combined": g["combined_33"]["mean"], "combined_se": g["combined_33"]["se"], "code_quality": g["code_quality"]["mean"],
                "passed": g["passed_all_runs"] if over_all else g["passed"], "passed_of": g["runs"] if over_all else g["n"],
                "combined_timeouts_zero": g["combined_timeouts_zero"]["mean"] if "combined_timeouts_zero" in g else None,
                "minutes": g["minutes"]["mean"], "usd": e["usd"]["mean"] if e["usd"] is not None else None, "raw_tokens": e["raw_tokens"]["mean"],
                "output_tokens_median": t["median"], "output_tokens_mean": t["mean"],
                "report": source["report"], "protocol": f"code-quality-maintenance-{source['protocol']}",
            })
    out.sort(key=lambda r: (-r["combined"], usd_key(r), r["model"], EFFORTS.index(r["effort"])))
    best = {}
    for key in {r["key"] for r in out}:
        # Best level by the decision score: timeouts counted as 0 where a column has timeouts.
        best[key] = min((r for r in out if r["key"] == key),
                        key=lambda r: (-decision_score(r), usd_key(r), EFFORTS.index(r["effort"])))["effort"]
    for i, r in enumerate(out, 1):
        r["rank"] = i
        r["best"] = best[r["key"]] == r["effort"]
    return out


COLORS = {"fable": "#E8590C", "opus55": "#A61E4D", "astra": "#0CA678", "terra": "#1098AD", "luna": "#E64980", "gpt55": "#6B7280", "sol": "#C77C02", "gpt6luna": "#9C36B5", "gpt6sol": "#8F9A00", "gpt61sol": "#2B8A3E", "grok47cursor": "#3B5BDB"}  # one distinct hue per model, dark enough to read on the white chart and page; Anthropic in warm reds


TOLERANCES = {"critical": 1.0, "routine": 3.0, "rough": 5.0}


def decision_score(r):
    """Combined score for choosing a level: timeouts counted as 0 where a column has them, else the judged score."""
    return r["combined"] if r.get("combined_timeouts_zero") is None else r["combined_timeouts_zero"]


def suggestions(board):
    """Per model and tolerance: the cheapest level (then fastest) within that many points of the model's best score.

    Scores are decision scores: a level whose runs hit the task bound is judged with each timeout as 0, so a
    level that times out often is not suggested on the strength of its finished runs alone. A model with no
    list price is picked on time alone, as on the Routine v1 board.
    """
    out = {}
    by_model = {}
    for r in board:
        by_model.setdefault(r["key"], []).append(r)
    for key, levels in by_model.items():
        best = max(levels, key=decision_score)
        low = next(r for r in levels if r["effort"] == "low")
        top, floor = decision_score(best), decision_score(low)
        has_price = all(priced(r) for r in levels)
        entry = {"model": best["model"], "best_effort": best["effort"], "best_combined": top,
                 "spread": top - floor, "shape": "flat" if top - floor <= 3 else "steep", "basis": "cost then time" if has_price else "time (no list price)"}
        for name, tol in TOLERANCES.items():
            ok = [r for r in levels if top - decision_score(r) <= tol]
            pick = min(ok, key=lambda r: (r["usd"], r["minutes"]) if has_price else (r["minutes"],))
            entry[name] = {"effort": pick["effort"], "combined": decision_score(pick), "gap": top - decision_score(pick),
                           "usd_vs_best": pick["usd"] / best["usd"] if has_price else None, "minutes_vs_best": pick["minutes"] / best["minutes"],
                           "passed": pick["passed"], "n": pick["n"]}
        out[key] = entry
    return out


def table_html(board):
    lines = ['<div class="lb-scroll">', '<table class="lb" id="v4board">',
             '<caption class="sr-only">VulcanBench Frontier v4 board: every model and effort level, ranked by combined score</caption>',
             '<thead><tr><th class="l" scope="col">#</th><th class="l" scope="col">Model / harness</th><th scope="col">Effort</th>'
             '<th scope="col">Combined</th><th scope="col">SE</th><th scope="col">Code quality</th><th scope="col">Passed</th>'
             '<th scope="col">Min/task</th><th scope="col">$/task</th></tr></thead>', "<tbody>"]
    for r in board:
        cls = " leader" if r["rank"] == 1 else ""
        tag = '<span class="fb-best">best</span>' if r["best"] else ""
        mark = "&dagger;" if r["key"] == "fable" else ("&Dagger;" if r["key"] == "terra" and r["effort"] == "max" else ("&sect;" if r["key"] == "sol" and r["effort"] == "max" else ""))
        if r["key"] == "gpt6luna" and r["effort"] in ("extra-high", "max"):
            mark = "&para;"
        if r["key"] == "gpt6sol" and r["effort"] == "medium":
            mark = "&Vert;"
        if r["key"] == "gpt61sol" and r["effort"] == "medium":
            mark = "*"
        if r["key"] == "grok47cursor":
            mark = "&loz;"
        cost = f'${r["usd"]:.2f}' if priced(r) else "unavailable"
        lines.append(
            f'<tr class="v4row{cls}" data-model="{r["key"]}" data-effort="{r["effort"]}" data-best="{int(r["best"])}"><td class="l lb-rank">{r["rank"]}</td>'
            f'<td class="l"><span class="v4dot" style="background:{COLORS[r["key"]]}"></span><a class="lb-model" href="models/{r["slug"]}.html">{escape(r["model"])}</a> <span class="lb-harness">{escape(r["harness"])}</span>{tag}</td>'
            f'<td class="fb-eff">{LABEL[r["effort"]]}{mark}</td><td class="lb-win">{r["combined"]:.2f}</td><td>{r["combined_se"]:.2f}</td>'
            f'<td>{r["code_quality"]:.2f}</td><td>{r["passed"]}/{r["passed_of"]}</td><td>{r["minutes"]:.1f}</td><td>{cost}</td></tr>')
    lines += ["</tbody>", "</table>", "</div>"]
    return "\n".join(lines)


def gpt6luna_footnote(board):
    cells = {r["effort"]: r for r in board if r["key"] == "gpt6luna"}
    xh, mx = cells["extra-high"], cells["max"]
    return FOOTNOTES["gpt6luna"].format(xh_n=xh["n"], max_n=mx["n"], xh_t=xh["passed_of"] - xh["n"], max_t=mx["passed_of"] - mx["n"],
                                        xh_zero=xh["combined_timeouts_zero"], max_zero=mx["combined_timeouts_zero"])


def grok47_footnote(board):
    cells = {r["effort"]: r for r in board if r["key"] == "grok47cursor"}
    shared = read("swe-v4-grok47-cursor-v320/shared-judge.json")["columns"]
    mine = [c for c in shared if c["model"] == "grok47cursor"]
    groups = read("swe-v4-grok47-cursor-v320/groups.json")
    gap = statistics.mean(g["by_panel"]["sol"]["mean"] - g["by_panel"]["muse"]["mean"] for g in groups)
    fable_low = next(c for c in shared if c["model"] == "fable" and c["effort"] == "low")["muse_combined"]
    return FOOTNOTES["grok47cursor"].format(gap=gap, muse_lo=min(c["muse_combined"] for c in mine), muse_hi=max(c["muse_combined"] for c in mine),
                                            fable_low=fable_low, med_n=cells["medium"]["n"])


def render(board):
    models = sorted({r["model"] for r in board})
    runs = sum(r["n"] for r in board)
    data = {"columns": [{k: r[k] for k in ("model", "lab", "harness", "slug", "key", "effort", "n", "combined", "combined_se", "code_quality",
                                            "passed", "minutes", "usd", "raw_tokens", "output_tokens_median", "output_tokens_mean", "rank", "best")} for r in board],
            "colors": COLORS, "efforts": list(EFFORTS), "tolerances": TOLERANCES, "suggestions": suggestions(board)}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    assert "</script" not in payload
    return (f"{START}\n"
            f"<script>window.VB_V4 = {payload};</script>\n"
            f'<p class="lb-context">{len(models)} models, {len(board)} model&times;effort columns, {runs:,} runs. Combined score is 50% functional '
            "correctness, 8.5% lint and complexity, 8.5% security and 33% Code quality, judged for a human reader by Muse Spark 1.3 and Grok 4.6 "
            "under one frozen protocol (v3.4 to v3.7, v3.15 to v3.18 and v3.20 apply the same rubric, controls and gates to each population; v3.20 "
            "seats GPT-6.1 Sol in place of Grok 4.6 to judge Grok 4.7, see &loz;). The chart plots combined score against cost per task, $0 on the left, one line per model from Low to Max; the cost axis shows up to $5 per task and scrolls sideways for anything costlier. The table below carries every column. "
            "Completion tokens are the model's own output per task, reasoning included. $/task is API-equivalent at list rates from the solver receipts; every model here ran on a subscription. "
            "Grok 4.7 has no list price, so its $/task is unavailable and it appears on the Tokens and Minutes views only.</p>\n"
            '<div id="v4app" class="v4app" aria-live="polite"></div>\n'
            '<noscript><p class="lb-context">The chart needs JavaScript; the table below carries every column.</p></noscript>\n'
            f"{table_html(board)}\n"
            '<p class="lb-context">&dagger; ' + escape(FOOTNOTES["fable"]) + " &Dagger; " + escape(FOOTNOTES["terra"]) + " &sect; " + escape(FOOTNOTES["sol"]) + " &para; " + escape(gpt6luna_footnote(board)) + " &Vert; " + escape(FOOTNOTES["gpt6sol"]) + " * " + escape(FOOTNOTES["gpt61sol"]) + " &loz; " + escape(grok47_footnote(board)) +
            ' SE is one task standard error of the combined score. Astra&rsquo;s $/task is the central estimate; its report carries a long-context upper bound. '
            'The <span class="lb-tag" style="margin-left:0;">best</span> tag marks each model&rsquo;s highest-scoring effort level. '
            'Per-run records, judge sub-scores and pricing are in each report&rsquo;s evidence bundle: '
            '<a href="benchmarks/swe-v4-astra-fable51-v34.html">Astra vs. Fable 5.1</a>, '
            '<a href="benchmarks/swe-v4-gpt55-luna-v35.html">GPT-5.5 vs. Luna</a>, <a href="benchmarks/swe-v4-terra-v36.html">Terra</a>, '
            '<a href="benchmarks/swe-v4-sol-v37.html">Sol</a>, <a href="benchmarks/swe-v4-opus55-v315.html">Opus 5.5</a>, '
            '<a href="benchmarks/swe-v4-gpt6-luna-v316.html">GPT-6 Luna</a>, <a href="benchmarks/swe-v4-gpt6-sol-v317.html">GPT-6 Sol</a>, <a href="benchmarks/swe-v4-gpt61-sol-v318.html">GPT-6.1 Sol</a>, <a href="benchmarks/swe-v4-grok47-cursor-v320.html">Grok 4.7</a>. '
            '<a href="assets/data/swe-v4-board.csv" download>Download the board as CSV</a>.</p>\n'
            f"{END}")


def csv_text(board):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["rank", "model", "lab", "harness", "effort", "best_effort", "n", "combined_33", "combined_33_se", "code_quality", "passed",
                     "mean_minutes", "mean_usd", "mean_raw_tokens", "median_output_tokens", "mean_output_tokens", "report", "protocol",
                     "passed_of", "combined_timeouts_zero"])
    for r in board:
        writer.writerow([r["rank"], r["model"], r["lab"], r["harness"], r["effort"], r["best"], r["n"], f'{r["combined"]:.4f}', f'{r["combined_se"]:.4f}',
                         f'{r["code_quality"]:.4f}', r["passed"], f'{r["minutes"]:.4f}', f'{r["usd"]:.6f}' if priced(r) else "", f'{r["raw_tokens"]:.1f}',
                         f'{r["output_tokens_median"]:.1f}', f'{r["output_tokens_mean"]:.1f}', r["report"], r["protocol"],
                         r["passed_of"], "" if r["combined_timeouts_zero"] is None else f'{r["combined_timeouts_zero"]:.4f}'])
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    board = rows()
    block = render(board)
    for text in (block, csv_text(board)):
        assert chr(0x2014) not in text and chr(0x2013) not in text
    page = PAGE.read_text()
    assert page.count(START) == 1 and page.count(END) == 1, "leaderboard.html needs exactly one swe-v4-board block"
    head, rest = page.split(START, 1)
    _, tail = rest.split(END, 1)
    new_page = head + block + tail
    outputs = {
        PAGE: new_page,
        ROOT / "assets/data/swe-v4-board.json": json.dumps({"columns": board, "sources": SOURCES, "tolerances": TOLERANCES,
                                                             "suggestions": suggestions(board)}, indent=2, ensure_ascii=False) + "\n",
        ROOT / "assets/data/swe-v4-board.csv": csv_text(board),
    }
    stale = [p for p, text in outputs.items() if not p.exists() or p.read_text() != text]
    if args.check:
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)}")
        print("Frontier v4 board is current" if not stale else f"{len(stale)} stale output(s)")
        sys.exit(1 if stale else 0)
    for p, text in outputs.items():
        p.write_text(text)
    print(f"{len(board)} columns, {len({r['model'] for r in board})} models; wrote {', '.join(p.name for p in outputs)}")


if __name__ == "__main__":
    main()
