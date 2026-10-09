"""Render the technical PDF for the v3.23 Claude Sonnet 5.5 effort sweep.

Reads only the public evidence bundles (this one, Claude Opus 5.5's and Claude
Fable 5.1's for the comparison, and the Frontier v4 board) and the committed
cards; no model calls. Every number is computed from the bundles at render
time. Requires reportlab and the VulcanBench rankings-chart font folder.

    python3 scripts/render_swe_v4_v323_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>

PAGES is the expected page count (eight text pages and two card pages); if the
final text runs longer, adjust it here and in verify_swe_v4_v323_pdf.py.
"""

import argparse
import json
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, Image, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/swe-v4-sonnet55-v323"
OPUS = ROOT / "assets/data/swe-v4-opus55-v315"
FABLE = ROOT / "assets/data/swe-v4-astra-fable51-v34"
BOARD = ROOT / "assets/data/swe-v4-board.json"
CARD = ROOT / "assets/cards/swe-v4-sonnet55-v323.png"
CLAUDE_CARD = ROOT / "assets/cards/swe-v4-sonnet55-vs-claude.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-sonnet55-v323-report.pdf"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccc4")
PAGES = 10


def label(effort):
    return effort.replace("-", " ").title().replace("Extra High", "Extra-high")


def short(task):
    return task.replace("legacy-", "").replace("-binary-parity", "").replace("-order-book-parity", "").replace("-store-parity", "")


def load(bundle, model):
    groups = {g["effort"]: g for g in json.loads((bundle / "groups.json").read_text()) if g["model"] == model}
    econ = {g["effort"]: g for g in json.loads((bundle / "economics.json").read_text())["groups"] if g["model"] == model}
    return groups, econ


def main():  # noqa: PLR0915, one linear document
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fonts", type=Path, required=True)
    parser.add_argument("--github-url", required=True)
    args = parser.parse_args()
    assert args.github_url.startswith("https://github.com/morganlinton/VulcanBenchCOM/tree/")
    for name, file in (("Body", "geist-400.ttf"), ("Bold", "geist-600.ttf"), ("Display", "chakra-600.ttf"), ("Mono", "ibm-plex-mono-400.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(args.fonts / file)))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Bold", italic="Body", boldItalic="Bold")
    runs = json.loads((DATA / "runs.json").read_text())["rows"]
    calibration = json.loads((DATA / "calibration.json").read_text())
    protocols = json.loads((DATA / "judge-protocols.json").read_text())
    provenance = json.loads((DATA / "provenance.json").read_text())
    econ = json.loads((DATA / "economics.json").read_text())
    t, et = load(DATA, "sonnet55")
    o, eo = load(OPUS, "opus55")
    f, ef = load(FABLE, "fable")
    board = json.loads(BOARD.read_text())["columns"]
    styles = {
        "body": ParagraphStyle("body", fontName="Body", fontSize=10.2, leading=14.4, textColor=INK, spaceAfter=9),
        "small": ParagraphStyle("small", fontName="Body", fontSize=8.7, leading=12, textColor=GREY, spaceAfter=8),
        "h1": ParagraphStyle("h1", fontName="Display", fontSize=25, leading=29, textColor=INK, spaceAfter=12),
        "h2": ParagraphStyle("h2", fontName="Display", fontSize=15.3, leading=19, textColor=INK, spaceBefore=10, spaceAfter=9),
        "th": ParagraphStyle("th", fontName="Bold", fontSize=8.6, leading=11, textColor=INK, alignment=TA_LEFT),
    }
    story = []

    def p(text, style="body"):
        assert not any(d in text for d in (chr(0x2014), chr(0x2013))) and "{{" + "TBD:" not in text
        story.append(Paragraph(text, styles[style]))

    def heading(text):
        p(text, "h2")

    def table(headers, records, widths=None, size=9.0, padding=5, wrap=False):
        cell = ParagraphStyle("cell", fontName="Body", fontSize=size, leading=size * 1.25, textColor=INK)
        body = [[Paragraph(escape(v), cell) for v in row] for row in records] if wrap else records
        values = [[Paragraph(escape(h), styles["th"]) for h in headers]] + body
        tbl = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 1), (-1, -1), "Body"), ("FONTSIZE", (0, 1), (-1, -1), size), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), padding), ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
            ("LINEABOVE", (0, 0), (-1, 0), 1, INK), ("LINEBELOW", (0, 0), (-1, 0), .7, INK), ("LINEBELOW", (0, -1), (-1, -1), 1, INK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f2")])]))
        story.extend([tbl, Spacer(1, 9)])

    comb = [t[e]["combined_33"]["mean"] for e in EFFORTS]
    cq = [t[e]["code_quality"]["mean"] for e in EFFORTS]
    totals = econ["totals"]["sonnet55"]
    one_panel = [r for r in runs if r["judged"] != "published"]
    assert not any(r["solver_fallback"] for r in runs)
    assert all(set(r["replies_by_model"]) == {"claude-sonnet-5-5"} for r in runs)
    best = max(EFFORTS, key=lambda e: t[e]["combined_33"]["mean"])
    ranks = {r["effort"]: r["rank"] for r in board if r["key"] == "sonnet55"}
    passed = [t[e]["passed_all_runs"] for e in EFFORTS]
    judged = [t[e]["n"] for e in EFFORTS]
    pins = protocols["judge_pins"]

    def judged_note():
        if all(n == 23 for n in judged) and not one_panel:
            return "every cell is judged on 23 runs, each the equal mean of both judges"
        return (f"cells are judged on {', '.join(str(n) for n in judged)} runs from Low to Max; {len(one_panel)} run(s) are scored from one "
                "judge, as listed in the appendix")

    # Page 1: abstract and headline table
    p("Claude Sonnet 5.5 across every effort level", "h1")
    p("VulcanBench Frontier v4 | Code quality protocol v3.23 | October 2026", "small")
    heading("Abstract")
    p(f"Claude Sonnet 5.5 ran the 23-task VulcanBench Frontier v4 suite through Claude Code 2.1.291 to 2.1.293 on a Claude Max "
      f"subscription from October 6 to 8, 2026, once per task at each of five effort levels, Low to Max, 115 runs in all, one task at a "
      f"time on the owner's Mac. Code quality carries 33% of the combined score and is judged for a named human reader by Muse Spark 1.3 "
      f"(Meta) and Grok 4.6 (xAI) under the same rubric, controls and gates as the other Frontier v4 reports, with a ground-truth "
      f"intent-recovery probe. The combined score is {comb[0]:.2f} at Low, {comb[1]:.2f} at Medium, {comb[2]:.2f} at High, "
      f"{comb[3]:.2f} at Extra-high and {comb[4]:.2f} at Max. Sonnet 5.5 passes {passed[0]}, {passed[1]}, {passed[2]}, {passed[3]} and "
      f"{passed[4]} of 23 tasks from Low to Max and fixes {', '.join(str(t[e]['hidden_behaviours_fixed']) for e in EFFORTS[:4])} and "
      f"{t['max']['hidden_behaviours_fixed']} of the 231 hidden behaviours tested. Code quality runs from {min(cq):.2f} to {max(cq):.2f}. "
      f"Cost per task, as Claude Code reports it, runs from ${min(et[e]['usd']['mean'] for e in EFFORTS):.2f} to "
      f"${max(et[e]['usd']['mean'] for e in EFFORTS):.2f}; the whole sweep comes to ${totals['usd']:.2f}, "
      f"${totals['usd'] / totals['runs']:.2f} per task.")
    p(f"Every run finished inside the flat 3-hour task bound and none was excluded; {judged_note()}. Claude Code's refusal fallback "
      "was on and no run used it. Two facts about how this column was produced are disclosed throughout: the sweep predates the "
      "harness's tagged-worktree rule and was admitted to judging through a committed task hash bridge, and Grok 4.6 judged through a "
      "newer Cursor CLI than in earlier rounds.")
    heading("Table 1. Combined score, Code quality, runtime and tasks passed by effort")
    records = [[label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{t[e]["combined_33"]["se"]:.2f}',
                f'{t[e]["combined_20_profile"]["mean"]:.2f}', f'{t[e]["code_quality"]["mean"]:.2f}', f'{t[e]["minutes"]["mean"]:.1f}',
                f'{t[e]["n"]}', f'{t[e]["passed_all_runs"]}/23'] for e in EFFORTS]
    table(["Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Judged", "Passed"],
          records, [62, 74, 40, 72, 66, 56, 50, 48], size=8.8)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality. Combined (20%) applies the prior "
      "50/15/15/20 profile to the same Code quality scores. SE is one sample standard error across the cell's tasks, not judge uncertainty "
      "or a significance test. Runtime is solver wall-clock per task; judging is excluded. Frontier Code quality is the reviewed layer "
      "plus intent recovery and is never compared with Routine v1 Code quality.", "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p("Protocol v3.23 is the v3.15 protocol applied to this population. Nothing in the rubric, controls, quirk keys, gates, repeats, seed, "
      "weights or judge settings changed; both judges retook the calibration exam under v3.23 before any counted call. What changed is "
      "which Cursor CLI carried Grok 4.6, described on the next page, and how runs were admitted, described under How it was run. The "
      "population froze on October 8 with 115 rows, none missing and none excluded.")
    heading("The rubric")
    p("Every judge receives the same instructions, frozen by hash before any review. The prompt names the reader it scores for: "
      "an engineer who has never seen the code, reads it top to bottom without running it, and must make a correct change in one "
      "sitting. It tells the judge that its own ease at parsing dense code is not evidence of readability. Six dimensions are "
      "scored 0 to 4 in half steps against written anchors, each with an exact excerpt and a concrete consequence for that reader.")
    table(["Sub-score", "Dimension", "What is assessed"], [
        ["Human readability", "Naming", "Identifiers say what things are in the task's domain"],
        ["Human readability", "Presentation", "Statements per line, nesting, function length, how much the reader must hold at once"],
        ["Human readability", "Intent", "Constants, thresholds and quirks explained by names or accurate comments that say why"],
        ["Maintainability", "Structure", "Coherent responsibilities, no duplicated policy, no abstraction beyond the task's scale"],
        ["Maintainability", "Changeability", "A named plausible change, every edit site traced, scored on locality and safety"],
        ["Maintainability", "Verifiability", "Explicit state, failures that name what went wrong, seams to test one rule alone"],
    ], [92, 78, 310], size=8.6, padding=3, wrap=True)
    heading("The layers under the 33 points")
    redistributed = sum(t[e]["intent_recovery_redistributed_runs"] for e in EFFORTS)
    p("<b>Reviewed panel, 24 points.</b> The six-dimension rubric above, averaged across the judges with a valid review. "
      "<b>Intent recovery, 9 points.</b> Every task in this suite is a rewrite of a retired binary whose real behaviour departs "
      "from its written specification in documented ways. The judge sees only the specification and the code, never the issue "
      "text, and lists where the code departs from the specification; a separate call matches that list against the frozen "
      "answer key. The denominator is the quirks the submission actually passed tests for, so a functional failure is not "
      "punished twice; a submission that passed none has no intent-recovery score and its Code quality is the reviewed score alone"
      + (", which no Sonnet 5.5 run needed. " if redistributed == 0 else f", which {redistributed} Sonnet 5.5 run(s) needed. ") +
      "<b>Measured maintenance, designed for 12 points, not yet built.</b> Until it exists the pre-registered "
      "split above is in force.")

    # Page 3: judges, settings and versions, and calibration
    story.append(PageBreak())
    p("Judges and calibration", "h1")
    p("The scored panel is Muse Spark 1.3 through the Muse CLI on its Standard tier, which does not train on prompts, and Grok 4.6 "
      "through the Cursor CLI at medium effort. Neither lab has a model on this board, so neither judge grades a relative, and both are "
      "neutral for an Anthropic submission. Every session is fresh, tools are disabled, the workspace is empty, model identity is checked "
      "per call from the CLI's own records, and solver labels are withheld.")
    heading("Judge settings and versions")
    originals = pins["original_protocol_sha256"]
    p(f"The original v3.3 and v3.4 judge protocol files were recovered from the owner's private backup, and their sha256 equal the "
      f"published values (v3.3 {originals['v3.3'][:8]}..., v3.4 {originals['v3.4'][:8]}...). The judge settings used in v3.23, read from "
      f"<font name='Mono'>{escape(pins['source'])}</font>, are identical to them. Muse Spark 1.3 ran the same binary as every earlier "
      f"round (sha256 {pins['binary_sha256']['muse'][:12]}..., a match). Grok 4.6 ran on a newer Cursor CLI: the Cursor pin hashes only "
      "Cursor's launcher script, which is the same in every Cursor release, so it never fixed the version. Cursor updated itself on "
      "October 7 at 14:43 PDT, and every v3.23 Grok call ran on Cursor CLI 2026.10.01-e373342, while the v3.3 round recorded "
      "2026.09.02-c22c1a3. The Grok model id is the same; Cursor reports its display name as Grok 4.6 Medium where the frozen settings "
      "say Cursor Grok 4.6 Medium, a rename the judging wrapper accepts and records. Grok 4.6 passed calibration under v3.23.")
    heading("The calibration exam")
    p("Before scoring a single submission each judge reviews ten held-out programs implementing one ledger specification, from clear "
      "to compressed, misleadingly commented, narrated, needlessly abstracted and carrying an embedded instruction to give full marks, "
      "five times each in a seeded order. Twenty gates fixed in advance check that the judge sees each construct; a judge may miss at "
      "most one gate by at most half a point.")
    heading("Table 2. Calibration verdicts")

    def failing(judge):
        gates = calibration[judge]["failing_gates"]
        return ", ".join(f"{g} (short by {calibration[judge]['gates'][g]['shortfall']:.2f})" for g in gates) or "none"

    table(["Judge", "Protocol", "Calls", "Result", "Allowance", "Failing gates"], [
        ["Muse Spark 1.3", protocols["protocol_ids"]["muse"], str(calibration["muse"]["call_count"]),
         "passed" if calibration["muse"]["passed"] else "failed", "used" if calibration["muse"]["allowance_used"] else "not used", failing("muse")],
        ["Grok 4.6", protocols["protocol_ids"]["grok"], str(calibration["grok"]["call_count"]),
         "passed" if calibration["grok"]["passed"] else "failed", "used" if calibration["grok"]["allowance_used"] else "not used", failing("grok")],
    ], [64, 138, 30, 40, 46, 189], size=8.2, padding=3, wrap=True)
    p("Both judges passed, each using the one-gate allowance, both well inside the half-point limit. Under v3.15, for Opus 5.5, both "
      "passed every gate with no allowance used.")
    heading("Table 3. Control means on three of the ten calibration programs")
    dims = ("naming", "presentation", "intent", "structure", "changeability", "verifiability")
    records = []
    for judge in ("muse", "grok"):
        cm = calibration[judge]["control_means"]
        for name, key in (("clear", "0"), ("compressed", "1"), ("misleading comments", "5")):
            records.append([("Muse" if judge == "muse" else "Grok"), name, *[f'{cm[key][d]:.2f}' for d in dims]])
    table(["Judge", "Control", "Naming", "Present.", "Intent", "Struct.", "Change.", "Verif."], records,
          [44, 108, 48, 52, 46, 48, 50, 44], size=8.4, padding=3)
    p("All ten controls, every gate value and both judges' control means are in calibration.json.", "small")

    # Page 4: results in detail
    story.append(PageBreak())
    p("Results in detail", "h1")
    heading("Table 4. Code quality components at each effort level")
    rows = [("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
            ("Intent recovery", "intent_recovery", 1), ("Reviewed score", "reviewed_score", 1)]
    records = [[name, *[f'{t[e][key]["mean"]:.{d}f}' for e in EFFORTS]] for name, key, d in rows]
    records += [["Rated by Muse Spark 1.3", *[f'{t[e]["by_panel"]["muse"]["mean"]:.1f}' for e in EFFORTS]],
                ["Rated by Grok 4.6", *[f'{t[e]["by_panel"]["grok"]["mean"]:.1f}' for e in EFFORTS]],
                ["Standard error of Code quality", *[f'{t[e]["code_quality"]["se"]:.2f}' for e in EFFORTS]],
                ["Hidden behaviours fixed of 231", *[str(t[e]["hidden_behaviours_fixed"]) for e in EFFORTS]]]
    table(["Component", "Low", "Medium", "High", "Extra-high", "Max"], records, [170, 62, 62, 62, 70, 62], size=9, padding=3)
    p("Means cover the judged runs per cell (n in Table 1). Per-judge means cover the runs each judge reviewed validly.", "small")
    heading("Table 5. Four factors by effort, mean score out of 100")
    table(["Effort", "Functional", "Lint, complexity", "Security", "Code quality"],
          [[label(e), *[f'{t[e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for e in EFFORTS], [80, 91, 91, 80, 92], size=8.8, padding=3)
    heading("Refusal fallback")
    p("Claude Code's refusal fallback stayed at its default (on), as for Opus 5.5, following Artificial Analysis's Default Fallback "
      "convention. No run used it: every assistant reply in every run came from claude-sonnet-5-5, and no other model appears in any "
      "run's final usage record.", "small")

    # Page 5: cost and tokens
    story.append(PageBreak())
    p("Cost and tokens across effort levels", "h1")
    p("Cost is Claude Code's own list-price total for each run, checked against the session's final total, as for the Opus 5.5 column. "
      "Anthropic's pricing page lists Sonnet 5.5 at $2 input and $10 output per million tokens, with cache writes at $2.50 (5 minutes) and "
      "$4 (1 hour), but gives two cache-read prices: $0.20 per million in its table and 0.05x input ($0.10) in its prompt caching section. "
      "Rather than pick one, the report uses the cost Claude Code reports. Sonnet 5.5 ran on a Claude Max subscription, so these are "
      "API-equivalent estimates rather than bills; judging is excluded.")
    heading("Table 6. Cost, raw tokens and runtime by effort")
    records = [[label(e), str(et[e]["n"]), f'${et[e]["usd"]["mean"]:.2f}', f'${et[e]["usd"]["se"]:.2f}', f'${et[e]["usd_total"]:.2f}',
                f'{et[e]["raw_tokens"]["mean"] / 1e6:.2f}M', f'{et[e]["minutes"]["mean"]:.1f}'] for e in EFFORTS]
    records.append(["Full sweep", str(totals["runs"]), f'${totals["usd"] / totals["runs"]:.2f}', "", f'${totals["usd"]:,.2f}',
                    f'{totals["raw_tokens"] / 1e6:,.0f}M', f'{totals["solver_hours"]:.1f} h'])
    table(["Effort", "Runs", "$/task", "SE", "Level total", "Tokens/task", "Min/task"], records, [76, 40, 60, 50, 76, 76, 60], size=8.6, padding=3)
    p("Tokens are Claude Code's session usage from its final record: input, cache reads, cache writes and output.", "small")
    heading("Limitations recorded with the estimates")
    for item in econ["limitations"]:
        p("&#8226; " + item, "small")

    # Page 6: beside Opus 5.5 and Fable 5.1, and the board
    story.append(PageBreak())
    p("Beside Claude Opus 5.5 and Claude Fable 5.1", "h1")
    p("Opus 5.5 and Fable 5.1 ran the same 23 tasks through Claude Code in September and were judged by the same judges under v3.15 and "
      "v3.4 (Opus 5.5 at High judged on 22 of 23). Their numbers are the published rows; nothing was re-judged. The three columns ran on "
      "different Claude Code versions (2.1.291 to 2.1.293, 2.1.280, and 2.1.259 to 2.1.261), so small gaps between them are harness "
      "confounded, and under v3.23 Grok 4.6 ran on a newer Cursor CLI.")
    heading("Table 7. Sonnet 5.5, Opus 5.5 and Fable 5.1 by effort")
    records = []
    for e in EFFORTS:
        records.append([label(e), f'{t[e]["combined_33"]["mean"]:.2f} / {o[e]["combined_33"]["mean"]:.2f} / {f[e]["combined_33"]["mean"]:.2f}',
                        f'{t[e]["passed_all_runs"]} / {o[e]["passed_all_runs"]} / {f[e]["passed"]}',
                        f'{t[e]["code_quality"]["mean"]:.1f} / {o[e]["code_quality"]["mean"]:.1f} / {f[e]["code_quality"]["mean"]:.1f}',
                        f'${et[e]["usd"]["mean"]:.2f} / ${eo[e]["usd"]["mean"]:.2f} / ${ef[e]["usd"]["mean"]:.2f}',
                        f'{et[e]["minutes"]["mean"]:.1f} / {eo[e]["minutes"]["mean"]:.1f} / {ef[e]["minutes"]["mean"]:.1f}'])
    table(["Effort", "Combined", "Passed of 23", "Code quality", "$/task", "Min/task"], records, [56, 116, 62, 92, 110, 74], size=8.0, padding=3)
    p("Each cell reads Sonnet 5.5 / Opus 5.5 / Fable 5.1. Combined scores and Code quality are over judged runs; pass counts, cost and "
      "minutes cover all 23 runs per cell. Cost is Claude Code's own total for Sonnet 5.5 and Opus 5.5 and the published v3.4 figure for "
      "Fable 5.1.", "small")
    heading("On the Frontier v4 board")
    above = sorted({r["model"] for r in board if r["rank"] < ranks[best]})
    assert above == ["Grok 4.7"], above  # the only columns above are judged by a different panel
    same_panel = [r for r in board if r["key"] not in ("sonnet55", "grok47cursor")]
    rival = max(same_panel, key=lambda r: r["combined"])
    opus = max((r for r in board if r["key"] == "opus55"), key=lambda r: r["combined"])
    p(f"Sonnet 5.5's best level, {label(best)} at {t[best]['combined_33']['mean']:.2f} (SE {t[best]['combined_33']['se']:.2f}), ranks "
      f"{ranks[best]} of the board's {len(board)} columns, behind only Grok 4.7's top three levels, which are judged by a different panel "
      f"(Muse Spark 1.3 and GPT-6.1 Sol). Among columns judged by Muse Spark 1.3 and Grok 4.6 it is the highest point estimate: "
      f"{t[best]['combined_33']['mean'] - rival['combined']:.2f} above {rival['model']} at {label(rival['effort'])} ({rival['combined']:.2f}, SE "
      f"{rival['combined_se']:.2f}), within one standard error, and {t[best]['combined_33']['mean'] - opus['combined']:.2f} above Opus 5.5 at "
      f"{label(opus['effort'])} ({opus['combined']:.2f}, SE {opus['combined_se']:.2f}), an edge rather than a clear win. Its levels rank "
      f"{', '.join(str(ranks[e]) for e in EFFORTS)} from Low to Max.")
    heading("Perfect hidden tests at Max")
    p("At Max every task passes every hidden test, 23 of 23 and all 231 tested behaviours, so Frontier v4 no longer separates Sonnet 5.5 "
      "at Max on correctness; Code quality, the lint and security scans, and cost still do. The integrity audit is clean on all 115 runs "
      "(no web access, no benchmark-data or answer-key paths).")

    # Page 7: how it was run, evidence and reproduction
    story.append(PageBreak())
    p("How it was run", "h1")
    p("<b>Before the tagged-worktree rule.</b> The sweep was launched on October 6 from a checkout that predates the harness's October 5 "
      "rule that every sweep runs from a tagged worktree. Run summaries therefore carry no source block, and their recorded task hashes "
      f"use an older format that counted __pycache__ files. Task content was verified identical to the frozen suite lock, and judging "
      f"admitted the runs through the committed hash bridge <font name='Mono'>{escape(protocols['task_hash_bridge']['file'])}</font> "
      f"({protocols['task_hash_bridge']['tasks']} tasks), which pairs each recorded hash with its lock hash. All 107 cached .pyc files an "
      "agent could see were byte-identical to compiling the starting source. <b>Claude Code versions.</b> Low ran 21 tasks on 2.1.291 and "
      "2 on 2.1.292; Medium and High on 2.1.292; Extra-high 22 on 2.1.292 and paddockcore on 2.1.293; Max on 2.1.293. Earlier Claude "
      "columns used older releases. <b>Where and how.</b> --billing subscription on a Claude Max plan, the local sandbox on the owner's Mac, "
      "a flat 3-hour task timeout, one task at a time, from October 6, 06:49 PDT, to October 8, 03:38 PDT. Anthropic's default effort for "
      "Sonnet 5.5 on the Claude API is High; the vendor does not state a Claude Code default. <b>One attempt per task and level</b>; no "
      "run was retried, and effort labels are Claude Code's own.")
    for item in provenance["limits"][-1:]:
        p(item, "small")
    heading("Evidence and reproduction")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, hidden behaviours "
      f"fixed, integrity verdicts, task hash bridge pair, Claude Code version, replies by serving model and each scored judge's "
      f"six-dimension sub-scores and intent recovery; <font name='Mono'>groups.json</font>; <font name='Mono'>calibration.json</font> with "
      f"every gate value and control mean; <font name='Mono'>judge-protocols.json</font> with the exact rubric, system text, probe and "
      f"match instructions, schemas, weights and the judge settings and version record; <font name='Mono'>economics.json</font> with cost and token "
      f"aggregates, the list rates as published and pricing limitations; and <font name='Mono'>provenance.json</font> with source hashes "
      f"and limits. <link href='{escape(args.github_url)}' color='#D97757'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of the judges "
      "with a valid review. The combined score is 100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. Group "
      "means weight the cell's tasks equally. The export script recomputes every row from the frozen summary, checks every run's cost "
      "against Claude Code's stream, every task hash against the bridge and the suite lock, and the reviewer settings against the v3.4 "
      "bundle, and refuses to write if any value differs.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe "
      "task sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. "
      "Runs were not repeated. Hash checks bind the export to frozen files; they do not prove that judges were unbiased, that the "
      "newer Cursor CLI serves Grok 4.6 exactly as the earlier one did, or that no training overlap exists.")

    # Page 8: per task appendix and source hashes
    story.append(PageBreak())
    p("Appendix. Per task at Low, Medium and Max", "h1")
    by = {(r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})

    def cell(r, key, digits):
        if r[key] is None:
            return "n/a"
        return f"{r[key]:.{digits}f}" + ("*" if r["judged"] != "published" else "")

    records = [[short(task), cell(by["low", task], "code_quality", 1), cell(by["max", task], "code_quality", 1),
                cell(by["low", task], "combined_33", 2), cell(by["medium", task], "combined_33", 2), cell(by["max", task], "combined_33", 2)]
               for task in tasks]
    table(["Task", "Low CQ", "Max CQ", "Low combined", "Medium combined", "Max combined"], records, [100, 60, 64, 80, 94, 84], size=7.8, padding=1.6)
    p("Per-task values from runs.json. Task names are shortened for width. * scored from one judge.", "small")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k.replace("v3.23/calls/", "calls/").replace("v3.23/reconstruction/", "reconstruction/"), v[:32] + "..."]
                                          for k, v in provenance["source_artifacts_sha256"].items()], [300, 190], size=6.8, padding=1.3)
    story.pop()  # no trailing spacer, so a full appendix page does not spill an empty page before the cards

    story.extend([NextPageTemplate("card"), PageBreak()])
    for card in (CARD, CLAUDE_CARD):  # landscape page, scaled to the frame height
        width, height = ImageReader(str(card)).getSize()
        frame_h = landscape(A4)[1] - 106
        story.append(Image(str(card), width=frame_h * width / height, height=frame_h))
        if card is CARD:
            story.append(PageBreak())

    def furniture(canvas, doc):
        width, height = canvas._pagesize
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.saveState()
        clip = canvas.beginPath()
        clip.roundRect(44, height - 41, 22, 22, 4.8)
        canvas.clipPath(clip, stroke=0, fill=0)
        canvas.drawImage(str(ROOT / "assets/logo.png"), 44, height - 41, 22, 22)
        canvas.restoreState()
        canvas.setFont("Display", 13)
        canvas.drawString(74, height - 35, "VulcanBench")
        canvas.setFont("Body", 8.5)
        canvas.drawRightString(width - 44, height - 33, "Technical report | Frontier v4 | Code quality protocol v3.23 | October 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | Claude Sonnet 5.5 across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench Frontier v4: Claude Sonnet 5.5 across every effort level",
                          author="VulcanBench", subject="Code quality protocol v3.23: neutral judges, 33% weight, Claude Code effort sweep")
    doc.addPageTemplates([
        PageTemplate(id="report", frames=Frame(44, 40, A4[0] - 88, A4[1] - 102, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
                     onPage=furniture, pagesize=A4),
        PageTemplate(id="card", frames=Frame(44, 40, landscape(A4)[0] - 88, landscape(A4)[1] - 102, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
                     onPage=furniture, pagesize=landscape(A4)),
    ])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
