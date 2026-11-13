"""Charts for Report 01, drawn from assets/data/report-01/summary.json.

Fills the regions between <!-- chart:NAME --> and <!-- /chart:NAME --> in
reports/01-how-claude-fable-5-2-thinks.html with inline SVG or HTML tables.

    python3 scripts/build_report01_charts.py           # rewrite the page
    python3 scripts/build_report01_charts.py --check   # exit 1 if the page is stale
"""

from __future__ import annotations

import json
import math
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/report-01/summary.json"
PAGE = ROOT / "reports/01-how-claude-fable-5-2-thinks.html"
LEVELS = ["low", "medium", "high", "extra-high", "max"]
LEVEL_NAMES = {"low": "Low", "medium": "Medium", "high": "High", "extra-high": "Extra-high", "max": "Max"}
MODELS = {
    "fable52": ("Claude Fable 5.2", "#D97757"),
    "opus55": ("Claude Opus 5.5", "#8C3A1F"),
    "fable51": ("Claude Fable 5.1", "#5E5BA8"),
    "astra": ("GPT-6 Astra", "#10A37F"),
}
GROUPS = [
    ("reading", "Reading code and binary", "#3F6BA8"),
    ("probing", "Probing the binary", "#D9A21B"),
    ("editing", "Editing the module", "#6B4FA0"),
    ("testing", "Testing", "#16967F"),
    ("wrapup", "Wrap-up", "#B5654A"),
]
ACT_GROUP = {"orient": "reading", "inspect": "reading", "probe": "probing", "edit": "editing",
             "harness": "testing", "test": "testing", "review": "wrapup", "report": "wrapup"}
GROUP_COLOR = {k: c for k, _, c in GROUPS}
GROUP_NAME = {k: n for k, n, _ in GROUPS}


def f(v, nd=1):
    return f"{v:.{nd}f}"


def row(d, model, effort):
    return next(r for r in d["levels"] if r["model"] == model and r["effort"] == effort)


def legend(items, round_marks=False):
    cls = "dot" if round_marks else ""
    return '<div class="an-legend">' + "".join(
        f'<span><i class="rp-key {cls}" style="background:{c}"></i>{escape(n)}</span>' for n, c in items
    ) + "</div>"


# ------------------------------------------------------------------ timeline

def chart_timeline(d):
    rows = [("fable52", e) for e in LEVELS] + [("opus55", "low")]
    W, left, right, top, rh = 760, 196, 744, 40, 66
    H = top + rh * len(rows) + 24
    pw = right - left
    longest = max(d["timelines"][f"{m}/{e}"]["minutes"] for m, e in rows)
    peak = max(c[2] for m, e in rows for c in d["timelines"][f"{m}/{e}"]["calls"])
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="rp-t1" class="an-chart"><title id="rp-t1">'
           "One task, blendcore, solved at each effort level: each tick is a tool call, each bar the thinking "
           "before it</title>"]
    for i in range(0, 101, 25):
        x = left + pw * i / 100
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 8}" y2="{top + rh * len(rows) - 8}" class="grid"/>')
        out.append(f'<text x="{x:.1f}" y="{top + rh * len(rows) + 8}" text-anchor="middle" class="tick">{i}%</text>')
    out.append(f'<text x="{right}" y="{H - 4}" text-anchor="end" class="tick">share of the run, start to finish</text>')
    for j, (m, e) in enumerate(rows):
        tl = d["timelines"][f"{m}/{e}"]
        y0 = top + rh * j + 30
        name = LEVEL_NAMES[e] if m == "fable52" else "Opus 5.5, Low"
        out.append(f'<text x="0" y="{y0 - 10}" class="rl">{escape(name)}</text>')
        out.append(f'<text x="0" y="{y0 + 6}" class="rs">{f(tl["minutes"])} min, {len(tl["calls"])} calls</text>')
        bw = 168 * tl["minutes"] / longest
        out.append(f'<rect x="0" y="{y0 + 13}" width="{max(bw, 2):.1f}" height="4" rx="2" fill="{MODELS[m][1]}">'
                   f'<title>{f(tl["minutes"])} minutes on the wall clock</title></rect>')
        out.append(f'<line x1="{left}" x2="{right}" y1="{y0 + 0.5}" y2="{y0 + 0.5}" stroke="var(--hairline)"/>')
        for t, act, think in tl["calls"]:
            x = left + pw * min(1.0, t / tl["minutes"])
            g = ACT_GROUP[act]
            tip = f"{f(t)} min: {GROUP_NAME[g].lower()}"
            if think:
                h = 34 * math.sqrt(think / peak)
                out.append(f'<rect x="{x - 2:.1f}" y="{y0 - 2 - h:.1f}" width="4" height="{h:.1f}" rx="1.5" '
                           f'fill="{MODELS[m][1]}" opacity="0.7"><title>{escape(tip)}, about {think:,} thinking '
                           "tokens before it</title></rect>")
            out.append(f'<rect x="{x - 1.25:.1f}" y="{y0 + 3}" width="2.5" height="10" rx="1" fill="{GROUP_COLOR[g]}">'
                       f'<title>{escape(tip)}</title></rect>')
    out.append("</svg>")
    keys = legend([(n, c) for _, n, c in GROUPS if _ != "wrapup"] + [("Wrap-up", GROUP_COLOR["wrapup"])])
    return (keys + '<div class="an-scroll">' + "".join(out) + "</div>"
            '<p class="an-note">Ticks: tool calls, coloured by activity. Bars above the line: thinking tokens '
            "spent before that call (height is the square root, so small bursts stay visible). The short bar "
            "under each label is the run's wall-clock length, on one scale for all six runs.</p>")


# ------------------------------------------------------- where thinking goes

def chart_split(d):
    rows = [("fable52", e) for e in LEVELS] + [("opus55", e) for e in LEVELS]
    W, left, right, top, rh = 760, 196, 744, 18, 30
    gap_between = 22
    H = top + rh * len(rows) + gap_between + 26
    pw = right - left
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="rp-t2" class="an-chart"><title id="rp-t2">'
           "Share of thinking tokens by the activity they preceded, by effort level</title>"]
    for j, (m, e) in enumerate(rows):
        r = row(d, m, e)
        y = top + rh * j + (gap_between if m == "opus55" else 0)
        if e == "low":
            out.append(f'<text x="0" y="{y - 4}" class="rs" style="fill:var(--ink)">{escape(MODELS[m][0])}</text>')
        label = LEVEL_NAMES[e]
        out.append(f'<text x="14" y="{y + 16}" class="tl-label">{label}</text>')
        out.append(f'<text x="{left - 8}" y="{y + 16}" text-anchor="end" class="tick">n={r["n_traces"]}</text>')
        x = left
        for g, name, color in GROUPS:
            share = r["think_" + g]
            w = pw * share
            if w <= 0:
                continue
            out.append(f'<rect x="{x:.1f}" y="{y + 3}" width="{max(w - 2, 0.5):.1f}" height="19" rx="3" fill="{color}">'
                       f"<title>{escape(MODELS[m][0])}, {label}: {round(100 * share)}% of thinking before "
                       f"{escape(name.lower())}</title></rect>")
            if share >= 0.07:
                out.append(f'<text x="{x + (w - 2) / 2:.1f}" y="{y + 16.5}" text-anchor="middle" class="seg" '
                           f'fill="{"#1c1a17" if g == "probing" else "#fff"}">{round(100 * share)}%</text>')
            x += w
    out.append("</svg>")
    return legend([(n, c) for _, n, c in GROUPS]) + '<div class="an-scroll">' + "".join(out) + "</div>"


# --------------------------------------------------------------- deciles

def chart_deciles(d):
    W, left, top, rh, cw = 760, 120, 22, 30, 62
    H = top + rh * 5 + 26
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="rp-t3" class="an-chart"><title id="rp-t3">'
           "Claude Fable 5.2: share of a level's thinking in each tenth of the run</title>"]
    for i in range(10):
        out.append(f'<text x="{left + cw * i + cw / 2:.0f}" y="{top - 8}" text-anchor="middle" class="tick">'
                   f"{i * 10}-{i * 10 + 10}%</text>")
    for j, e in enumerate(LEVELS):
        r = row(d, "fable52", e)
        y = top + rh * j
        out.append(f'<text x="0" y="{y + 18}" class="tl-label">{LEVEL_NAMES[e]}</text>')
        for i, v in enumerate(r["deciles"]):
            a = min(1.0, v / 0.27)
            ink = "#fff" if a > 0.55 else "var(--ink)"
            out.append(f'<rect x="{left + cw * i:.0f}" y="{y}" width="{cw - 2}" height="{rh - 2}" rx="3" '
                       f'fill="#D97757" fill-opacity="{0.08 + 0.92 * a:.2f}"><title>{LEVEL_NAMES[e]}: '
                       f"{round(100 * v)}% of thinking in the {i * 10} to {i * 10 + 10}% slice of the run</title></rect>")
            out.append(f'<text x="{left + cw * i + (cw - 2) / 2:.0f}" y="{y + 18}" text-anchor="middle" class="seg" '
                       f'fill="{ink}">{round(100 * v)}%</text>')
    out.append(f'<text x="{left + cw * 10 - 2}" y="{H - 4}" text-anchor="end" class="tick">tenth of the run, '
               "by wall-clock time</text></svg>")
    return ('<div class="an-legend"><span>Claude Fable 5.2: share of each level\'s thinking in each tenth of '
            'the run</span></div><div class="an-scroll">' + "".join(out) + "</div>")


# ---------------------------------------------------------- effort curves

def panel(d, x0, w, key, title, models, unit_fmt, ticks):
    top, h = 36, 210
    lo, hi = math.log10(ticks[0]), math.log10(ticks[-1])
    X = lambda i: x0 + 52 + (w - 146) * i / 4  # noqa: E731
    Y = lambda v: top + h - h * (math.log10(v) - lo) / (hi - lo)  # noqa: E731
    out = [f'<text x="{x0}" y="14" class="rl">{escape(title)}</text>',
           f'<text x="{x0}" y="28" class="rs">mean per task, log scale, whiskers ±1 standard error</text>']
    for t in ticks:
        out.append(f'<line x1="{x0 + 44}" x2="{x0 + w - 86}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>')
        out.append(f'<text x="{x0 + 38}" y="{Y(t) + 4:.1f}" text-anchor="end" class="tick">{unit_fmt(t)}</text>')
    for i, e in enumerate(LEVELS):
        out.append(f'<text x="{X(i):.1f}" y="{top + h + 18}" text-anchor="middle" class="tick">'
                   f'{LEVEL_NAMES[e].replace("Extra-high", "XHigh")}</text>')
    ends = []
    for m in models:
        rs = [row(d, m, e) for e in LEVELS]
        pts = [(X(i), Y(r[key])) for i, r in enumerate(rs)]
        color = MODELS[m][1]
        out.append('<polyline fill="none" stroke="{}" stroke-width="2" points="{}"/>'.format(
            color, " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)))
        for (x, y), r, e in zip(pts, rs, LEVELS):
            se = r.get(key + "_se") or 0
            y1, y2 = Y(max(r[key] - se, ticks[0])), Y(r[key] + se)
            n = r.get("n_traces", r["n"]) if key != "minutes" else r["n"]
            out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{y1:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="1.5"/>')
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" stroke="var(--paper)" stroke-width="2">'
                       f"<title>{escape(MODELS[m][0])}, {LEVEL_NAMES[e]}: {unit_fmt(r[key], True)} "
                       f"(±{unit_fmt(se, True)}, n={n})</title></circle>")
        ends.append([pts[-1][1], MODELS[m][0].replace("Claude ", ""), color])
    ends.sort()
    for k in range(1, len(ends)):
        ends[k][0] = max(ends[k][0], ends[k - 1][0] + 13)
    for y, name, color in ends:
        out.append(f'<text x="{X(4) + 12:.1f}" y="{y + 4:.1f}" class="rs" style="fill:var(--ink)">{escape(name)}</text>')
    return "".join(out)


def chart_effort(d):
    def tok(v, full=False):
        return f"{v / 1000:.1f}k" if full else (f"{v / 1000:.0f}k" if v >= 1000 else f"{v:.0f}")

    def mins(v, full=False):
        return f"{v:.1f} min" if full else f"{v:g}"

    W, H = 860, 270
    svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="rp-t4" class="an-chart rp-wide">'
           '<title id="rp-t4">Thinking tokens and minutes per task by effort level</title>'
           + panel(d, 0, 430, "thinking", "Thinking tokens", ["fable52", "opus55", "astra"], tok,
                   [500, 1000, 3000, 10000, 30000, 100000])
           + panel(d, 440, 420, "minutes", "Minutes", ["fable52", "opus55", "fable51", "astra"], mins,
                   [3, 5, 10, 20, 40, 60])
           + "</svg>")
    return legend([(MODELS[m][0], MODELS[m][1]) for m in MODELS], True) + f'<div class="an-scroll">{svg}</div>'


# ------------------------------------------------------- committed tests

def chart_tests(d):
    W, left, right, top, h = 760, 40, 640, 16, 150
    X = lambda i: left + (right - left) * i / 4  # noqa: E731
    Y = lambda v: top + h - h * v / 23  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {top + h + 30}" role="img" aria-labelledby="rp-t5" class="an-chart">'
           '<title id="rp-t5">Runs whose patch adds a test file, of 23, by effort level</title>']
    for v in (0, 5, 10, 15, 23):
        out.append(f'<line x1="{left}" x2="{right}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>')
        out.append(f'<text x="{left - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" class="tick">{v}</text>')
    for i, e in enumerate(LEVELS):
        out.append(f'<text x="{X(i):.1f}" y="{top + h + 20}" text-anchor="middle" class="tick">{LEVEL_NAMES[e]}</text>')
    ends = []
    for m in ("astra", "fable51", "opus55", "fable52"):
        rs = [row(d, m, e) for e in LEVELS]
        pts = [(X(i), Y(r["runs_test_files"])) for i, r in enumerate(rs)]
        c = MODELS[m][1]
        out.append('<polyline fill="none" stroke="{}" stroke-width="2" points="{}"/>'.format(
            c, " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)))
        for (x, y), r, e in zip(pts, rs, LEVELS):
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{c}" stroke="var(--paper)" stroke-width="2">'
                       f"<title>{escape(MODELS[m][0])}, {LEVEL_NAMES[e]}: {r['runs_test_files']} of {r['n']} "
                       "patches add a test file</title></circle>")
        ends.append([pts[-1][1], MODELS[m][0], c])
    ends.sort()
    for k in range(1, len(ends)):
        ends[k][0] = max(ends[k][0], ends[k - 1][0] + 13)
    for y, name, c in ends:
        out.append(f'<text x="{right + 14}" y="{y + 4:.1f}" class="rs" style="fill:var(--ink)">{escape(name)}</text>')
    out.append("</svg>")
    return (legend([(MODELS[m][0], MODELS[m][1]) for m in MODELS], True)
            + '<div class="an-legend"><span>Runs whose patch adds a test file, of 23 at each level</span></div>'
            + '<div class="an-scroll">' + "".join(out) + "</div>")


# ------------------------------------------------------------ tables

def table_verify(d):
    kinds = [("mutation", "Mutation testing"),
             ("cross_build", "Linux build in a container"),
             ("performance", "Throughput check"),
             ("interpreters", "Second Python version")]
    head = "".join(f"<th>{LEVEL_NAMES[e]}</th>" for e in LEVELS)
    body = []
    for key, name in kinds:
        for m in ("fable52", "opus55"):
            cells = []
            for e in LEVELS:
                r = row(d, m, e)
                v, n = r["verify_" + key], r["n_traces"]
                cells.append(f'<td><span class="rp-bar"><span style="width:{100 * v / n:.0f}%;background:'
                             f'{MODELS[m][1]}"></span></span>{v}/{n}</td>')
            first = f'<td class="l rp-check" rowspan="2">{escape(name)}</td>' if m == "fable52" else ""
            body.append(f'<tr>{first}<td class="l rp-who"><i class="rp-key dot" style="background:{MODELS[m][1]}">'
                        f"</i>{MODELS[m][0].replace('Claude ', '')}</td>{''.join(cells)}</tr>")
    return (f'<div class="an-table"><table><thead><tr><th class="l">Check</th><th class="l">Model</th>{head}</tr>'
            f'</thead><tbody>{"".join(body)}</tbody></table></div>')


def table_levels(d):
    head = ("<tr><th class='l'>Per task, mean</th>" + "".join(f"<th>{LEVEL_NAMES[e]}</th>" for e in LEVELS) + "</tr>")
    spec = [
        ("Minutes", lambda r: f(r["minutes"])),
        ("Output tokens", lambda r: f"{r['output'] / 1000:.1f}k"),
        ("of which thinking", lambda r: f"{r['thinking'] / 1000:.1f}k ({round(100 * r['thinking_share'])}%)"),
        ("Tool calls", lambda r: f(r["tool_calls"])),
        ("Binary inspection calls", lambda r: f(r["inspect_calls"])),
        ("Calls that run the reference by hand", lambda r: f(r["probe_runs"])),
        ("Test runs", lambda r: f(r["test_runs"])),
        ("Edit-then-test cycles", lambda r: f(r["cycles"])),
        ("Thinking summary blocks", lambda r: f(r["thinking_blocks"], 0)),
        ("Largest single burst, share of thinking", lambda r: f"{round(100 * r['biggest_burst_share'])}%"),
        ("First binary inspection, median tool call", lambda r: f"{r['median_calls_before_inspect'] + 1:g}"),
        ("First edit, median minute", lambda r: f(r["median_min_to_edit"])),
    ]
    body = "".join(
        f"<tr><td class='l'>{escape(name)}</td>" + "".join(f"<td>{fn(row(d, 'fable52', e))}</td>" for e in LEVELS) + "</tr>"
        for name, fn in spec)
    return f'<div class="an-table"><table><thead>{head}</thead><tbody>{body}</tbody></table></div>'


def table_patch(d):
    head = ("<tr><th class='l'>Model</th><th class='l'>Effort</th><th>Solved</th><th>Module<br>only</th>"
            "<th>Adds a<br>test file</th><th>Module<br>lines</th><th>Test<br>lines</th>"
            "<th>Comment<br>share</th></tr>")
    body = []
    for m in ("fable52", "astra", "fable51", "opus55"):
        for e in LEVELS:
            r = row(d, m, e)
            first = (f'<td class="l rp-who" rowspan="5"><i class="rp-key dot" style="background:{MODELS[m][1]}"></i>'
                     f"{MODELS[m][0].replace('Claude ', '')}</td>") if e == "low" else ""
            sep = ' class="rp-sep"' if e == "low" else ""
            body.append(f"<tr{sep}>{first}<td class='l'>{LEVEL_NAMES[e]}</td><td>{r['solved']}/{r['n']}</td>"
                        f"<td>{r['runs_module_only']}</td><td>{r['runs_test_files']}</td><td>{r['median_module_added']:g}</td>"
                        f"<td>{r['median_test_added']:g}</td><td>{round(100 * r['comment_share'])}%</td></tr>")
    return f'<div class="an-table"><table><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></div>'


def table_compare(d):
    head = "<tr><th class='l'>Per task, mean</th><th class='l'>Model</th>" + "".join(
        f"<th>{LEVEL_NAMES[e]}</th>" for e in LEVELS) + "</tr>"
    spec = [
        ("Output tokens", "output", lambda v: f"{v / 1000:.1f}k", ("fable52", "opus55", "fable51", "astra")),
        ("Thinking or reasoning tokens", "thinking", lambda v: f"{v / 1000:.1f}k", ("fable52", "opus55", "astra")),
        ("Thinking share of output", "thinking_share", lambda v: f"{round(100 * v)}%", ("fable52", "opus55", "astra")),
        ("Minutes", "minutes", lambda v: f"{v:.1f}", ("fable52", "opus55", "fable51", "astra")),
    ]
    body = []
    for name, key, fn, models in spec:
        for k, m in enumerate(models):
            first = f"<td class='l' rowspan='{len(models)}'>{escape(name)}</td>" if k == 0 else ""
            sep = ' class="rp-sep"' if k == 0 else ""
            cells = "".join(f"<td>{fn(row(d, m, e)[key])}</td>" for e in LEVELS)
            body.append(f"<tr{sep}>{first}<td class='l rp-who'><i class='rp-key dot' style='background:{MODELS[m][1]}'>"
                        f"</i>{MODELS[m][0].replace('Claude ', '')}</td>{cells}</tr>")
    ns = ", ".join(f"{LEVEL_NAMES[e]} {row(d, 'opus55', e)['n_traces']}" for e in LEVELS)
    note = (f'<p class="an-note">Opus 5.5 tokens come from its runs without refusal fallback (n: {ns}); its minutes, '
            "like every other model's, cover all published runs (22 at High). Fable 5.1 left no thinking count.</p>")
    return f'<div class="an-table"><table><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></div>' + note


CHARTS = {
    "timeline": chart_timeline,
    "split": chart_split,
    "deciles": chart_deciles,
    "effort": chart_effort,
    "tests": chart_tests,
    "verify": table_verify,
    "levels": table_levels,
    "patch": table_patch,
    "compare": table_compare,
}


def render(page: str, d: dict) -> str:
    for name, fn in CHARTS.items():
        pat = re.compile(rf"(<!-- chart:{name} -->)(.*?)(<!-- /chart:{name} -->)", re.S)
        if not pat.search(page):
            raise SystemExit(f"marker chart:{name} missing from {PAGE.name}")
        page = pat.sub(lambda mo: mo.group(1) + "\n" + fn(d) + "\n" + mo.group(3), page)
    return page


def main():
    d = json.loads(DATA.read_text())
    page = PAGE.read_text()
    new = render(page, d)
    if "--check" in sys.argv:
        if new != page:
            print(f"{PAGE.relative_to(ROOT)} is stale; run python3 scripts/build_report01_charts.py")
            sys.exit(1)
        print(f"{PAGE.relative_to(ROOT)} charts are current")
        return
    PAGE.write_text(new)
    print(f"wrote charts into {PAGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
