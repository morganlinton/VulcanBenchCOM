"""Build the VulcanBench Frontier v4 leaderboard from the published evidence bundles.

Every model-and-harness column at every effort level it ran, ranked by
combined score, with Code quality, tasks passed, runtime and API-equivalent
cost beside it. Reads only the public bundles under assets/data/ and writes
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
]
FOOTNOTES = {
    "fable": "Fable 5.1 runs include 11 disclosed Opus 4.8 fallbacks across the sweep; they stay in the population.",
    "terra": "GPT-5.6 Terra at max includes paddockcore, run on September 17 on a second ChatGPT account after the first hit its quota window and judged under the v3.6.1 top-up with the same judges and calibration.",
}


def read(name):
    return json.loads((ROOT / "assets/data" / name).read_text())


def output_tokens(bundle):
    """Median and mean completion tokens per task for every model and effort cell of a bundle."""
    cells = {}
    for r in read(f"{bundle}/runs.json")["rows"]:
        cells.setdefault((r["model"], r["effort"]), []).append(r["token_usage"]["output_tokens"])
    return {key: {"median": statistics.median(v), "mean": statistics.mean(v)} for key, v in cells.items()}


def rows():
    out = []
    for source in SOURCES:
        groups = read(f"{source['bundle']}/groups.json")
        econ = {(g["model"], g["effort"]): g for g in read(f"{source['bundle']}/economics.json")["groups"]}
        tokens = output_tokens(source["bundle"])
        for g in groups:
            name, harness, slug, lab = source["models"][g["model"]]
            e = econ[g["model"], g["effort"]]
            t = tokens[g["model"], g["effort"]]
            out.append({
                "model": name, "lab": lab, "harness": harness, "slug": slug, "key": g["model"], "effort": g["effort"], "n": g["n"],
                "combined": g["combined_33"]["mean"], "combined_se": g["combined_33"]["se"], "code_quality": g["code_quality"]["mean"],
                "passed": g["passed"], "minutes": g["minutes"]["mean"], "usd": e["usd"]["mean"], "raw_tokens": e["raw_tokens"]["mean"],
                "output_tokens_median": t["median"], "output_tokens_mean": t["mean"],
                "report": source["report"], "protocol": f"code-quality-maintenance-{source['protocol']}",
            })
    out.sort(key=lambda r: (-r["combined"], r["usd"], r["model"], EFFORTS.index(r["effort"])))
    best = {}
    for r in out:
        best.setdefault(r["key"], r["effort"])  # first row per model in ranked order is its best effort
    for i, r in enumerate(out, 1):
        r["rank"] = i
        r["best"] = best[r["key"]] == r["effort"]
    return out


COLORS = {"fable": "#FF7A3D", "astra": "#00FF9D", "terra": "#00C9B1", "luna": "#A8FFD8", "gpt55": "#22B573"}  # Anthropic orange; OpenAI greens, brightest for the newest


TOLERANCES = {"critical": 1.0, "routine": 3.0, "rough": 5.0}


def suggestions(board):
    """Per model and tolerance: the cheapest level (then fastest) within that many points of the model's best score."""
    out = {}
    by_model = {}
    for r in board:
        by_model.setdefault(r["key"], []).append(r)
    for key, levels in by_model.items():
        best = max(levels, key=lambda r: r["combined"])
        low = next(r for r in levels if r["effort"] == "low")
        entry = {"model": best["model"], "best_effort": best["effort"], "best_combined": best["combined"],
                 "spread": best["combined"] - low["combined"], "shape": "flat" if best["combined"] - low["combined"] <= 3 else "steep"}
        for name, tol in TOLERANCES.items():
            ok = [r for r in levels if best["combined"] - r["combined"] <= tol]
            pick = min(ok, key=lambda r: (r["usd"], r["minutes"]))
            entry[name] = {"effort": pick["effort"], "combined": pick["combined"], "gap": best["combined"] - pick["combined"],
                           "usd_vs_best": pick["usd"] / best["usd"], "minutes_vs_best": pick["minutes"] / best["minutes"], "passed": pick["passed"], "n": pick["n"]}
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
        mark = "&dagger;" if r["key"] == "fable" else ("&Dagger;" if r["key"] == "terra" and r["effort"] == "max" else "")
        lines.append(
            f'<tr class="v4row{cls}" data-model="{r["key"]}" data-effort="{r["effort"]}" data-best="{int(r["best"])}"><td class="l lb-rank">{r["rank"]}</td>'
            f'<td class="l"><span class="v4dot" style="background:{COLORS[r["key"]]}"></span><a class="lb-model" href="models/{r["slug"]}.html">{escape(r["model"])}</a> <span class="lb-harness">{escape(r["harness"])}</span>{tag}</td>'
            f'<td class="fb-eff">{LABEL[r["effort"]]}{mark}</td><td class="lb-win">{r["combined"]:.2f}</td><td>{r["combined_se"]:.2f}</td>'
            f'<td>{r["code_quality"]:.2f}</td><td>{r["passed"]}/{r["n"]}</td><td>{r["minutes"]:.1f}</td><td>${r["usd"]:.2f}</td></tr>')
    lines += ["</tbody>", "</table>", "</div>"]
    return "\n".join(lines)


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
            "under one frozen protocol (v3.4 to v3.6 apply the same rubric, controls, gates and judges to each population). The chart plots combined score against cost per task, most expensive on the left, one line per model from Max to Low; the table below carries every column. "
            "Completion tokens are the model's own output per task, reasoning included. $/task is API-equivalent at list rates from the solver receipts; every model here ran on a subscription.</p>\n"
            '<div id="v4app" class="v4app" aria-live="polite"></div>\n'
            '<noscript><p class="lb-context">The chart needs JavaScript; the table below carries every column.</p></noscript>\n'
            f"{table_html(board)}\n"
            '<p class="lb-context">&dagger; ' + escape(FOOTNOTES["fable"]) + " &Dagger; " + escape(FOOTNOTES["terra"]) +
            ' SE is one task standard error of the combined score. Astra&rsquo;s $/task is the central estimate; its report carries a long-context upper bound. '
            'The <span class="lb-tag" style="margin-left:0;">best</span> tag marks each model&rsquo;s highest-scoring effort level. '
            'Per-run records, judge sub-scores and pricing are in each report&rsquo;s evidence bundle: '
            '<a href="benchmarks/swe-v4-astra-fable51-v34.html">Astra vs. Fable 5.1</a>, '
            '<a href="benchmarks/swe-v4-gpt55-luna-v35.html">GPT-5.5 vs. Luna</a>, <a href="benchmarks/swe-v4-terra-v36.html">Terra</a>. '
            '<a href="assets/data/swe-v4-board.csv" download>Download the board as CSV</a>.</p>\n'
            f"{END}")


def csv_text(board):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["rank", "model", "lab", "harness", "effort", "best_effort", "n", "combined_33", "combined_33_se", "code_quality", "passed",
                     "mean_minutes", "mean_usd", "mean_raw_tokens", "median_output_tokens", "mean_output_tokens", "report", "protocol"])
    for r in board:
        writer.writerow([r["rank"], r["model"], r["lab"], r["harness"], r["effort"], r["best"], r["n"], f'{r["combined"]:.4f}', f'{r["combined_se"]:.4f}',
                         f'{r["code_quality"]:.4f}', r["passed"], f'{r["minutes"]:.4f}', f'{r["usd"]:.6f}', f'{r["raw_tokens"]:.1f}',
                         f'{r["output_tokens_median"]:.1f}', f'{r["output_tokens_mean"]:.1f}', r["report"], r["protocol"]])
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
