"""Render the technical PDF for the v3.16 GPT-6 Luna effort sweep.

Reads only the public evidence bundle and the committed cards; no model calls.
Requires reportlab and the VulcanBench rankings-chart font folder.

    python3 scripts/render_swe_v4_v316_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>
"""

import argparse
import json
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, Image, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/swe-v4-gpt6-luna-v316"
CARD = ROOT / "assets/cards/swe-v4-gpt6-luna-v316.png"
ECONOMICS_CARD = ROOT / "assets/cards/swe-v4-gpt6-luna-v316-economics.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-gpt6-luna-v316-report.pdf"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccc4")
PAGES = 9


def label(effort):
    return effort.replace("-", " ").title().replace("Extra High", "Extra-high")


def short(task):
    return task.replace("legacy-", "").replace("-binary-parity", "").replace("-order-book-parity", "").replace("-store-parity", "")


def main():  # noqa: PLR0915, one linear document
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fonts", type=Path, required=True)
    parser.add_argument("--github-url", required=True)
    args = parser.parse_args()
    assert args.github_url.startswith("https://github.com/morganlinton/VulcanBenchCOM/tree/")
    for name, file in (("Body", "geist-400.ttf"), ("Bold", "geist-600.ttf"), ("Display", "chakra-600.ttf"), ("Mono", "ibm-plex-mono-400.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(args.fonts / file)))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Bold", italic="Body", boldItalic="Bold")
    groups = json.loads((DATA / "groups.json").read_text())
    runs = json.loads((DATA / "runs.json").read_text())["rows"]
    calibration = json.loads((DATA / "calibration.json").read_text())
    protocols = json.loads((DATA / "judge-protocols.json").read_text())
    provenance = json.loads((DATA / "provenance.json").read_text())
    econ = json.loads((DATA / "economics.json").read_text())
    et = {r["effort"]: r for r in econ["groups"]}
    t = {g["effort"]: g for g in groups}
    styles = {
        "body": ParagraphStyle("body", fontName="Body", fontSize=10.2, leading=14.4, textColor=INK, spaceAfter=9),
        "small": ParagraphStyle("small", fontName="Body", fontSize=8.7, leading=12, textColor=GREY, spaceAfter=8),
        "h1": ParagraphStyle("h1", fontName="Display", fontSize=25, leading=29, textColor=INK, spaceAfter=12),
        "h2": ParagraphStyle("h2", fontName="Display", fontSize=15.3, leading=19, textColor=INK, spaceBefore=10, spaceAfter=9),
        "th": ParagraphStyle("th", fontName="Bold", fontSize=8.6, leading=11, textColor=INK, alignment=TA_LEFT),
    }
    story = []

    def p(text, style="body"):
        assert not any(d in text for d in (chr(0x2014), chr(0x2013)))
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
    zero = [t[e]["combined_timeouts_zero"]["mean"] for e in EFFORTS]
    cq = [t[e]["code_quality"]["mean"] for e in EFFORTS]
    totals = econ["totals"]["gpt6luna"]
    timeouts = [r for r in runs if not r["finished"]]
    assert [(r["effort"], short(r["task"])) for r in timeouts] == [
        ("extra-high", "depotcore"), ("extra-high", "paddockcore"), ("max", "cellarcore"), ("max", "depotcore"), ("max", "lodgecore"), ("max", "paddockcore")]

    # Page 1: abstract and headline table
    p("GPT-6 Luna across every effort level", "h1")
    p("VulcanBench Frontier v4 | Code quality protocol v3.16 | September 2026", "small")
    heading("Abstract")
    p(f"GPT-6 Luna ran the 23-task VulcanBench Frontier v4 suite through Codex CLI 0.155.0 on a ChatGPT Pro subscription on September 25 "
      f"to 28, 2026, once per task at each of the five effort levels Codex offers for it, 115 runs in all. Code quality carries 33% of the "
      f"combined score and is judged for a named human reader by Muse Spark 1.3 (Meta) and Grok 4.6 (xAI) under the same frozen protocol as "
      f"the other Frontier v4 reports, with a ground-truth intent-recovery probe. Over judged runs the combined score rises at every step, "
      f"from {comb[0]:.2f} at Low to {comb[1]:.2f} at Medium, {comb[2]:.2f} at High, {comb[3]:.2f} at Extra-high and {comb[4]:.2f} at Max. "
      f"GPT-6 Luna passes {t['low']['passed_all_runs']} of 23 tasks at Low and Medium, {t['high']['passed_all_runs']} at High, "
      f"{t['extra-high']['passed_all_runs']} at Extra-high and {t['max']['passed_all_runs']} at Max. Code quality stays between "
      f"{min(cq):.2f} and {max(cq):.2f}. Cost per priced task runs from ${et['medium']['usd']['mean']:.3f} at Medium to "
      f"${et['extra-high']['usd']['mean']:.3f} at Extra-high; the whole sweep prices at ${totals['usd']:.2f}.")
    p(f"Six runs hit the flat 3-hour task bound while still working: {t['extra-high']['timeouts']} at Extra-high and {t['max']['timeouts']} at Max. "
      f"They have no finished code to judge, so the standard combined score and Code quality at those levels cover {t['extra-high']['n']} and "
      f"{t['max']['n']} of 23 runs. Every combined score in this report is therefore given two ways: over judged runs, as for every other board "
      f"column, and with each timeout counted as 0 over all 23 runs, which gives {zero[3]:.2f} at Extra-high and {zero[4]:.2f} at Max. Tasks "
      "passed always counts timeouts as failures.")
    heading("Table 1. Combined score two ways, Code quality, runtime and tasks passed by effort")
    records = [[label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{t[e]["combined_33"]["se"]:.2f}', f'{t[e]["combined_timeouts_zero"]["mean"]:.2f}',
                f'{t[e]["combined_20_profile"]["mean"]:.2f}', f'{t[e]["code_quality"]["mean"]:.2f}', f'{t[e]["minutes"]["mean"]:.1f}',
                f'{t[e]["n"]}', f'{t[e]["passed_all_runs"]}/23'] for e in EFFORTS]
    table(["Effort", "Combined (33%)", "SE", "Timeouts as 0", "Combined (20%)", "Code quality", "Min/task", "Judged", "Passed"],
          records, [58, 62, 36, 58, 60, 56, 54, 50, 46], size=8.7)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality, over judged runs. Timeouts as 0 "
      "counts each run stopped at the 3-hour bound as a combined score of 0 over all 23 runs. Combined (20%) applies the prior 50/15/15/20 "
      "profile to the same Code quality scores over judged runs. SE is one sample standard error across the cell's judged tasks, not judge "
      "uncertainty or a significance test. Passed counts all 23 runs. Runtime is solver wall-clock per task over every run in the cell, "
      "timeouts at their recorded 180 minutes; judging is excluded.", "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p("Protocol v3.16 is the same protocol applied to this population. Nothing in the rubric, controls, quirk keys, gates, repeats, seed, "
      "weights or judges changed from v3.7; both judges retook the calibration exam under v3.16 before any counted call. The population froze "
      "on September 28 with 109 rows, none missing, and six runs excluded as incomplete source runs: the six that hit the 3-hour bound.")
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
    redistributed = [t[e]["intent_recovery_redistributed_runs"] for e in EFFORTS]
    p("<b>Reviewed panel, 24 points.</b> The six-dimension rubric above, averaged across both judges. "
      "<b>Intent recovery, 9 points.</b> Every task in this suite is a rewrite of a retired binary whose real behaviour departs "
      "from its written specification in documented ways. The judge sees only the specification and the code, never the issue "
      "text, and lists where the code departs from the specification; a separate call matches that list against the frozen "
      "answer key. The denominator is the quirks the submission actually passed tests for, so a functional failure is not "
      "punished twice; a submission that passed none has no intent-recovery score and its Code quality is the reviewed score alone. "
      f"{sum(redistributed)} GPT-6 Luna runs needed that rule ({redistributed[0]} at Low, {redistributed[1]} at Medium, {redistributed[2]} at High). "
      "<b>Measured maintenance, designed for 12 points, not yet built.</b> Until it exists the pre-registered "
      "split above is in force.")

    # Page 3: judges and calibration
    story.append(PageBreak())
    p("Judges and calibration", "h1")
    p("The scored panel is Muse Spark 1.3 through the Muse CLI on its Standard tier, which does not train on prompts, and Grok 4.6 "
      "through the Cursor CLI at medium effort, the v3.7 pair under the same pinned binaries. Neither lab has a model on this board, so "
      "neither judge grades a relative. Every session is fresh, tools are disabled, the workspace is empty, model identity is checked per "
      "call from the CLI's own records, and solver labels are withheld.")
    heading("The calibration exam")
    p("Before scoring a single submission each judge reviews ten held-out programs that implement the same ledger specification: "
      "clear, compressed, compressed then auto-formatted, verbose with duplicated policy, needlessly abstracted, misleadingly "
      "commented, narrated with a comment on every line, a documented legacy quirk, an embedded instruction to give full marks, "
      "and hidden module state. Each program is reviewed five times in a seeded order. Twenty gates fixed in advance check that "
      "the judge sees the construct; a judge may miss at most one gate by at most half a point.")
    heading("Table 2. Calibration verdicts")

    def failing(judge):
        return ", ".join(f'{g} (short by {calibration[judge]["gates"][g]["shortfall"]:.2f})' for g in calibration[judge]["failing_gates"]) or "none"

    table(["Judge", "Protocol", "Calls", "Result", "Allowance", "Failing gate"], [
        ["Muse Spark 1.3", protocols["protocol_ids"]["muse"], str(calibration["muse"]["call_count"]),
         "passed" if calibration["muse"]["passed"] else "failed", "used" if calibration["muse"]["allowance_used"] else "not used", failing("muse")],
        ["Grok 4.6", protocols["protocol_ids"]["grok"], str(calibration["grok"]["call_count"]),
         "passed" if calibration["grok"]["passed"] else "failed", "used" if calibration["grok"]["allowance_used"] else "not used", failing("grok")],
    ], [66, 136, 32, 42, 56, 162], size=8.2, padding=3, wrap=True)
    p("Both judges passed, each using the pre-registered one-gate allowance: Muse Spark 1.3 fell 0.06 short on the repeatability gate and "
      "Grok 4.6 fell 0.10 short on the gate that checks formatting is credited as presentation, both well inside the half-point bound. Every "
      "other gate passed for both.")
    heading("Table 3. Control means on five of the ten calibration programs")
    dims = ("naming", "presentation", "intent", "structure", "changeability", "verifiability")
    records = []
    for judge in ("muse", "grok"):
        cm = calibration[judge]["control_means"]
        for name, key in (("clear", "0"), ("compressed", "1"), ("formatted", "2"), ("misleading comments", "5"), ("hidden state", "9")):
            records.append([("Muse" if judge == "muse" else "Grok"), name, *[f'{cm[key][d]:.2f}' for d in dims]])
    table(["Judge", "Control", "Naming", "Present.", "Intent", "Struct.", "Change.", "Verif."], records,
          [44, 108, 48, 52, 46, 48, 50, 44], size=8.4, padding=3)
    p("Full gate values and control means are in calibration.json.", "small")

    # Page 4: results in detail and the timeouts
    story.append(PageBreak())
    p("Results in detail", "h1")
    heading("Table 4. Code quality components at each effort level")
    rows = [("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
            ("Intent recovery", "intent_recovery", 1), ("Reviewed score", "reviewed_score", 1)]
    records = [[name, *[f'{t[e][key]["mean"]:.{d}f}' for e in EFFORTS]] for name, key, d in rows]
    records += [["Rated by Muse Spark 1.3", *[f'{t[e]["by_panel"]["muse"]["mean"]:.1f}' for e in EFFORTS]],
                ["Rated by Grok 4.6", *[f'{t[e]["by_panel"]["grok"]["mean"]:.1f}' for e in EFFORTS]],
                ["Standard error of Code quality", *[f'{t[e]["code_quality"]["se"]:.2f}' for e in EFFORTS]],
                ["Judged runs", *[str(t[e]["n"]) for e in EFFORTS]]]
    table(["Component", "Low", "Medium", "High", "Extra-high", "Max"], records, [170, 62, 62, 62, 70, 62], size=9, padding=3)
    p(f"Code quality sits between {min(cq):.2f} and {max(cq):.2f}, with Grok 4.6 the higher rater at every level. Intent recovery at Low "
      f"covers only the {t['low']['n'] - redistributed[0]} Low runs that passed any documented departure, so it is not comparable with the "
      "other levels. Means cover judged runs.", "small")
    heading("Table 5. Four factors by effort, mean score out of 100 over judged runs")
    table(["Effort", "Functional", "Lint, complexity", "Security", "Code quality"],
          [[label(e), *[f'{t[e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for e in EFFORTS], [80, 91, 91, 80, 92], size=8.8, padding=3)
    heading("Table 6. Runs stopped at the 3-hour bound")
    table(["Effort", "Task", "Minutes", "Judged", "Priced"],
          [[label(r["effort"]), short(r["task"]), f'{r["duration_s"] / 60:.1f}', "no", "no"] for r in timeouts],
          [80, 110, 70, 60, 60], size=8.6, padding=3)
    p("Each trace shows continuous work to the bound, with no idle gap over four minutes. A timed-out run has no finished submission, so "
      "v3.16 excludes it from judging, as v3.15 excluded an incomplete Claude Opus 5.5 run. With four of 23 Max runs out of the judged set, "
      "all failures, the judged mean alone flatters the top levels; the owner's decision (harness decision log, September 28) is to publish "
      "both figures everywhere a score appears, with the judged figure as the headline cell value because it is computed the same way as "
      "every other board column.", "small")

    # Page 5: cost and tokens
    story.append(PageBreak())
    p("Cost and tokens across effort levels", "h1")
    p(f"The {totals['priced_runs']} finished runs priced from their Codex receipts at list API rates, cache-aware, solver inference only, "
      "judging excluded. GPT-6 Luna ran on a ChatGPT Pro subscription, so these are API-equivalent estimates rather than bills. The six "
      "timeouts ended before Codex reported usage: they are unpriced, not $0, so Extra-high and Max spend is understated. Medium is the "
      "cheapest and fastest level, and Extra-high the most expensive per priced task.")
    heading("Table 7. API-equivalent cost, raw tokens and runtime by effort")
    records = [[label(e), str(et[e]["n"]), f'${et[e]["usd"]["mean"]:.3f}', f'${et[e]["usd_total"]:.2f}',
                f'{et[e]["raw_tokens"]["mean"] / 1e6:.2f}M', f'{et[e]["minutes"]["mean"]:.1f}'] for e in EFFORTS]
    records.append(["Full sweep", str(totals["priced_runs"]), f'${totals["usd"] / totals["priced_runs"]:.3f}', f'${totals["usd"]:,.2f}',
                    f'{totals["raw_tokens"] / 1e6:,.0f}M', f'{totals["solver_hours"]:.1f} h'])
    table(["Effort", "Priced runs", "$/task", "Level total", "Tokens/task", "Min/task"], records, [80, 64, 70, 84, 84, 70], size=8.6, padding=3)
    rates = econ["rates_per_million"]["gpt6luna"]
    p(f"Rates checked {econ['pricing_verified']}: GPT-6 Luna at ${rates['input']:.2f} input, ${rates['cached_input']:.2f} cached input and "
      f"${rates['output']:.2f} output per million tokens. Codex receipts report input, cached input, output and reasoning tokens per run, so "
      "cached input is billed at the cache-read rate and the rest at the standard rate. The sweep stamped each run at these rates at run time; "
      "the export recomputed every priced run from its receipt and matched every stamp. Tokens are raw solver totals including cache reads, "
      "over priced runs. Runtime covers all 115 runs.", "small")
    heading("Limitations recorded with the estimates")
    for item in econ["limitations"]:
        p("&#8226; " + item, "small")

    # Page 6: run notes, reproduction and evidence
    story.append(PageBreak())
    p("How it was run, and the evidence", "h1")
    p("<b>Codex CLI 0.155.0.</b> Every other Codex column on the board ran on 0.153.4, which refuses GPT-6 Luna on a ChatGPT account "
      "before any work; 0.155.0 is the lowest release that serves it and was installed beside the global CLI for this sweep only. "
      "<b>Operator stop.</b> The first Extra-high pacecore run went silent after a Codex reconnect message; after about 88 idle minutes the "
      "operator stopped it, the harness re-queued it, and the retry is the counted run. <b>Judging alongside another sweep.</b> Judging ran "
      "on September 28, 00:32 to 14:32 PDT, alongside the GPT-6 Sol solver sweep at the owner's request; the GPT-6 Luna runs had finished. "
      "<b>One attempt per task and level</b>; effort labels are Codex's own.")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, both judges' "
      f"six-dimension sub-scores and intent recovery for each judged run, and the six timeouts; <font name='Mono'>groups.json</font> with "
      f"both combined figures; <font name='Mono'>calibration.json</font> with every gate value and control mean; "
      f"<font name='Mono'>judge-protocols.json</font> with the exact rubric, system text, probe and match instructions, schemas and weights; "
      f"<font name='Mono'>economics.json</font> with cost and token aggregates, the rate table and pricing limitations; and "
      f"<font name='Mono'>provenance.json</font> with source hashes and limits. "
      f"<link href='{escape(args.github_url)}' color='#10A37F'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of "
      "the two judges, or the reviewed score alone where the submission passed no quirk family. The combined score is "
      "100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale; the timeouts-as-0 figure uses 0 for each timed-out "
      "run. The export script recomputes every row from the frozen summary, re-prices every priced run from its receipt, checks both combined "
      "figures against the harness card tables, and refuses to write if any value differs.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe "
      "task sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. "
      "Runs were not repeated. The Extra-high and Max standard combined scores and Code quality are means over 21 and 19 of 23 runs. "
      "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k, v[:32] + "..."] for k, v in provenance["source_artifacts_sha256"].items()
                                          if not k.startswith("runs-effort-")], [230, 260], size=8.0, padding=2.4)
    p("provenance.json also carries the hashes of the six timed-out runs' summaries.", "small")

    # Page 7: appendix, per task
    story.append(PageBreak())
    p("Appendix. Per task at Low, Extra-high and Max", "h1")
    by = {(r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})

    def cell(r, key, digits):
        return "timeout" if not r["finished"] else f"{r[key]:.{digits}f}"

    records = [[short(task), cell(by["low", task], "code_quality", 1), cell(by["max", task], "code_quality", 1),
                cell(by["low", task], "combined_33", 2), cell(by["extra-high", task], "combined_33", 2), cell(by["max", task], "combined_33", 2)]
               for task in tasks]
    table(["Task", "Low CQ", "Max CQ", "Low combined", "Extra-high combined", "Max combined"], records, [100, 60, 64, 80, 100, 84], size=8.2, padding=2.4)
    p("Per-task values from runs.json. Task names are shortened for width. A timeout has no Code quality or standard combined score; in the "
      "timeouts-as-0 figure it counts as 0.", "small")

    story.extend([NextPageTemplate("card"), PageBreak()])
    story.append(Image(str(CARD), width=552, height=552 * 2130 / 2400))
    story.append(PageBreak())
    story.append(Image(str(ECONOMICS_CARD), width=660, height=660 * 1785 / 2400))

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | Frontier v4 | Code quality protocol v3.16 | September 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | GPT-6 Luna across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench Frontier v4: GPT-6 Luna across every effort level",
                          author="VulcanBench", subject="Code quality protocol v3.16: neutral judges, 33% weight, Codex effort sweep, six timeouts, two combined figures")
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
