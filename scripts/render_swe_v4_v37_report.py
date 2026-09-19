"""Render the technical PDF for the v3.7 GPT-5.6 Sol effort sweep.

Reads only the public evidence bundle and the committed cards; no model calls.
Requires reportlab and the VulcanBench rankings-chart font folder.

    python3 scripts/render_swe_v4_v37_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>
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
DATA = ROOT / "assets/data/swe-v4-sol-v37"
CARD = ROOT / "assets/cards/swe-v4-sol-v37.png"
ECONOMICS_CARD = ROOT / "assets/cards/swe-v4-sol-v37-economics.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-sol-v37-report.pdf"
LEVELS = {"sol": ("low", "medium", "high", "extra-high", "max")}
EFFORTS = LEVELS["sol"]
NAMES = {"sol": "Sol"}
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccc4")
PAGES = 9


def label(effort):
    return effort.replace("-", " ").title().replace("Extra High", "Extra-high")


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
    eg = {(r["model"], r["effort"]): r for r in econ["groups"]}
    g = {(r["model"], r["effort"]): r for r in groups}
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
        t = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 1), (-1, -1), "Body"), ("FONTSIZE", (0, 1), (-1, -1), size), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), padding), ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
            ("LINEABOVE", (0, 0), (-1, 0), 1, INK), ("LINEBELOW", (0, 0), (-1, 0), .7, INK), ("LINEBELOW", (0, -1), (-1, -1), 1, INK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f2")])]))
        story.extend([t, Spacer(1, 9)])

    def cells(model, effort):
        return g[model, effort]

    t = {e: g["sol", e] for e in EFFORTS}
    et = {e: eg["sol", e] for e in EFFORTS}
    comb = [t[e]["combined_33"]["mean"] for e in EFFORTS]
    cq = [t[e]["code_quality"]["mean"] for e in EFFORTS]
    totals = econ["totals"]["sol"]

    unpublished = [r for r in runs if r["judged"] != "published"]
    assert [(r["effort"], r["task"]) for r in unpublished] == [("max", "legacy-codeccore-binary-parity")]
    finding = protocols["unpublished"][0]

    # Page 1: abstract and headline table
    p("GPT-5.6 Sol across every effort level", "h1")
    p("VulcanBench Frontier v4 | Code quality protocol v3.7 | September 2026", "small")
    heading("Abstract")
    p(f"GPT-5.6 Sol ran the 23-task VulcanBench Frontier v4 suite through the Codex CLI on a ChatGPT Pro subscription on September 17 to 18, "
      f"2026, once per task at each of the five effort levels its API offers, 115 runs in all. Code quality carries 33% of the combined score "
      f"and is judged for a named human reader by Muse Spark 1.3 (Meta) and Grok 4.6 (xAI) under the same frozen protocol as the other "
      f"Frontier v4 reports, with a ground-truth intent-recovery probe. The combined score rises from {comb[0]:.2f} at Low to {comb[4]:.2f} "
      f"at Max, and most of that range is the first step: {comb[1] - comb[0]:.1f} points from Low to Medium, then {comb[2] - comb[1]:.1f} to High, "
      f"{comb[3] - comb[2]:.1f} to Extra-high and {comb[4] - comb[3]:.1f} to Max. Sol passes {t['low']['passed']} of 23 tasks at Low, "
      f"{t['high']['passed']} of 23 at High and {t['max']['passed']} of the {t['max']['n']} judged at Max. Code quality stays between "
      f"{min(cq):.2f} and {max(cq):.2f} at every effort: the knob buys correctness, not readability. Cost per task does not follow the ladder: "
      f"${et['low']['usd']['mean']:.2f} at Low, ${et['high']['usd']['mean']:.2f} at High, the most expensive level, and "
      f"${et['max']['usd']['mean']:.2f} at Max.")
    p("One Max run, codeccore, has no published Code quality score: Grok 4.6's intent probe quoted an excerpt absent from the code on both "
      "attempts and the frozen protocol accepts no invented characters, so the Max cell's Code quality and combined score cover 22 of its 23 "
      "runs. The run passed its tests and is counted in every runtime, token and cost figure. Under the prior 50/15/15/20 profile applied to "
      "the same Code quality scores the ladder has the same shape, so the picture does not depend on the weight change.")
    heading("Table 1. Combined score, Code quality, tasks passed and runtime by effort")
    records = [["Sol", label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{t[e]["combined_33"]["se"]:.2f}',
                f'{t[e]["combined_20_profile"]["mean"]:.2f}', f'{t[e]["code_quality"]["mean"]:.2f}', f'{t[e]["minutes"]["mean"]:.1f}',
                f'{t[e]["passed"]}/{t[e]["n"]}'] for e in EFFORTS]
    table(["Model", "Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Passed"],
          records, [52, 62, 78, 40, 78, 70, 52, 48], size=8.9)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality. Combined (20%) applies the "
      "prior 50/15/15/20 profile to the same Code quality scores for comparison. SE is one sample standard error across the cell's "
      "tasks, not judge uncertainty or a significance test. Passed counts judged tasks with a perfect functional score; at Max that is 21 of "
      "the 22 judged runs (22 of 23 in the sweep). Runtime is solver wall-clock per task over every run in the cell; judging is excluded.", "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p("Protocol v3.7 is the same protocol applied to this population. Nothing in the rubric, controls, quirk keys, gates, repeats, seed or "
      "judge settings changed; both judges retook the calibration exam under v3.7 before any counted call. The population froze on "
      "September 18 with all five cells complete, none missing and none excluded. A submission without a valid answer-key match from every "
      "passing panel is left unpublished by the frozen summary; that rule applied once, described under Results in detail.")
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
    p("<b>Reviewed panel, 24 points.</b> The six-dimension rubric above, averaged across both judges. "
      "<b>Intent recovery, 9 points.</b> Every task in this suite is a rewrite of a retired binary whose real behaviour departs "
      "from its written specification in documented ways. The judge sees only the specification and the code, never the issue "
      "text, and lists where the code departs from the specification; a separate call matches that list against the frozen "
      "answer key. The denominator is the quirks the submission actually passed tests for, so a functional failure is not "
      "punished twice; a submission that passed none would have no intent-recovery score and its Code quality would be the reviewed "
      "score alone, which no Sol run needed. "
      "<b>Measured maintenance, designed for 12 points, not yet built.</b> Until it exists the pre-registered "
      "split above is in force and is stated on the card.")

    # Page 3: judges and calibration
    story.append(PageBreak())
    p("Judges and calibration", "h1")
    p("The scored panel is Muse Spark 1.3 through the Muse CLI on its Standard tier, which does not train on prompts, and Grok 4.6 "
      "through the Cursor CLI at medium effort. Neither lab has a model on this board, so neither judge grades a relative. Every "
      "session is fresh, tools are disabled, the workspace is empty, model identity is checked per call from the CLI's own "
      "records, and solver labels are withheld.")
    heading("The calibration exam")
    p("Before scoring a single submission each judge reviews ten held-out programs that implement the same ledger specification: "
      "clear, compressed, compressed then auto-formatted, verbose with duplicated policy, needlessly abstracted, misleadingly "
      "commented, narrated with a comment on every line, a documented legacy quirk, an embedded instruction to give full marks, "
      "and hidden module state. Each program is reviewed five times in a seeded order. Twenty gates fixed in advance check that "
      "the judge sees the construct; a judge may miss at most one gate by at most half a point.")
    heading("Table 2. Calibration verdicts")
    table(["Judge", "Protocol", "Calls", "Result", "Allowance used", "Failing gates"], [
        ["Muse Spark 1.3", protocols["protocol_ids"]["muse"], str(calibration["muse"]["call_count"]),
         "passed" if calibration["muse"]["passed"] else "failed", "yes" if calibration["muse"]["allowance_used"] else "no",
         ", ".join(calibration["muse"]["failing_gates"]) or "none"],
        ["Grok 4.6", protocols["protocol_ids"]["grok"], str(calibration["grok"]["call_count"]),
         "passed" if calibration["grok"]["passed"] else "failed", "yes" if calibration["grok"]["allowance_used"] else "no",
         ", ".join(calibration["grok"]["failing_gates"]) or "none"],
    ], [80, 150, 40, 50, 84, 90], size=8.6, padding=3)
    p("Both judges passed every gate with no allowance used. Under v3.5 and v3.6 Muse Spark 1.3 had needed the pre-registered allowance "
      "on the repeatability gate; under v3.7 it did not.")
    heading("Table 3. Control means on five of the ten calibration programs")
    dims = ("naming", "presentation", "intent", "structure", "changeability", "verifiability")
    records = []
    for judge in ("muse", "grok"):
        cm = calibration[judge]["control_means"]
        for name, key in (("clear", "0"), ("compressed", "1"), ("formatted", "2"), ("misleading comments", "5"), ("hidden state", "9")):
            records.append([("Muse" if judge == "muse" else "Grok"), name, *[f'{cm[key][d]:.2f}' for d in dims]])
    table(["Judge", "Control", "Naming", "Present.", "Intent", "Struct.", "Change.", "Verif."], records,
          [44, 108, 48, 52, 46, 48, 50, 44], size=8.4, padding=3)
    p("Both judges separate the clear program from the compressed one by more than two points on naming and by 2.0 to 2.1 points on "
      "presentation, credit formatting mainly on presentation, penalise misleading comments on intent, and penalise hidden state on "
      "verifiability. Full gate values are in calibration.json.", "small")

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
                ["Judged runs", *[str(t[e]["n"]) for e in EFFORTS]]]
    table(["Component", "Low", "Medium", "High", "Extra-high", "Max"], records, [170, 62, 62, 62, 70, 62], size=9, padding=3)
    p(f"Code quality sits between {min(cq):.2f} and {max(cq):.2f} at every effort, with the two judges within four points of each other "
      "in every cell and Grok 4.6 the higher rater at each level. Intent recovery, the ground-truth layer, rises from Low to High as more "
      "of the hidden contract is implemented and holds there; human readability and maintainability do not move with the knob.")
    heading("Table 5. Four factors by effort, mean score out of 100")
    table(["Model", "Effort", "Functional", "Lint, complexity", "Security", "Code quality"],
          [["Sol", label(e), *[f'{t[e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for e in EFFORTS], [60, 73, 91, 91, 73, 92], size=8.8, padding=3)
    p("Functional scores retain partial credit. Lint and complexity and security are the sweep's automated measurements. Code quality is "
      "the protocol's score. Means at Max cover the 22 judged runs.", "small")
    heading("The unpublished Max row")
    p(f"On codeccore at Max, Grok 4.6's intent probe quoted <font name='Mono'>{escape(finding['unsupported_excerpts']['1'][0])}</font> on both "
      "attempts where the source line is <font name='Mono'>memo = record[31:46].rstrip(\".,\")</font>. A character is inserted inside the "
      "string literal; it is neither a re-wrap, an omission nor an escape spelling, so no recovery rule accepts it and none was added. No "
      "answer-key match was made and the frozen summary, which requires a valid match from every passing panel, publishes no Code quality "
      "or combined score for the run. Both judges' reviews and the Muse probe are retained in the harness archive. The run passed its tests, "
      "so the sweep itself passed 22 of 23 at Max; its runtime, tokens and cost are in every economics figure. The operator's finding is "
      "recorded beside the two attempts and its hash is in provenance.json.", "small")
    heading("Operator record")
    p("Under v3.7 Muse Spark 1.3 made 440 calls (80 in calibration, 115 primary reviews, 5 repeats, 10 pairwise checks, 115 intent probes, "
      "115 answer-key matches) and Grok 4.6 made 439, with 114 matches. Muse needed a second attempt on nine calls: four unsupported excerpts "
      "and five malformed JSON responses. Grok needed a second attempt on nine: five unsupported excerpts (including the codeccore probe above), "
      "one malformed JSON probe, two transport faults retried under the network-fault rule, and one calibration probe the provider blocked "
      "before any model output, retried once under a new wrapper rule recorded in the operations log. Neither judge produced a reviewer "
      "fallback. Every attempt is archived beside its replacement in the harness run directory.", "small")
    # Page 5: cost and tokens
    story.append(PageBreak())
    p("Cost and tokens across effort levels", "h1")
    p("The same 115 runs priced from their Codex receipts at list API rates, cache-aware, solver inference only, judging excluded. "
      "Sol ran on a ChatGPT Pro subscription, so these are API-equivalent estimates rather than bills. Cost and tokens do not follow the "
      "ladder: High is the most expensive and slowest level, and Extra-high and Max cost less than it while passing more tasks. Every run "
      "is priced, including the Max run without a published Code quality score.")
    heading("Table 6. API-equivalent cost, raw tokens and runtime by effort")
    records = [[label(e), str(et[e]["n"]), f'${et[e]["usd"]["mean"]:.2f}', f'${et[e]["usd_total"]:.2f}',
                f'{et[e]["raw_tokens"]["mean"] / 1e6:.2f}M', f'{et[e]["minutes"]["mean"]:.1f}'] for e in EFFORTS]
    records.append(["Full sweep", str(totals["runs"]), f'${totals["usd"] / totals["runs"]:.2f}', f'${totals["usd"]:,.2f}',
                    f'{totals["raw_tokens"] / 1e6:,.0f}M', f'{totals["solver_hours"]:.1f} h'])
    table(["Effort", "Runs", "$/task", "Level total", "Tokens/task", "Min/task"], records, [80, 50, 70, 84, 84, 70], size=8.6, padding=3)
    rates = econ["rates_per_million"]["sol"]
    p(f"Rates checked {econ['pricing_verified']}: Sol at ${rates['input']:.2f} input, ${rates['cached_input']:.2f} cached input and "
      f"${rates['output']:.2f} output per million tokens. Codex receipts report input, cached input, output and reasoning tokens per run, so "
      "cached input is billed at the cache-read rate and the rest at the standard rate. The sweep stamped each run at these rates at run time; "
      "the export recomputed every run from its receipt and matched every stamp. Tokens are raw solver totals including cache reads. "
      "Per-run estimates and the rate table are in economics.json and runs.csv.", "small")
    heading("Limitations recorded with the estimates")
    for item in econ["limitations"]:
        p("• " + item, "small")

    # Page 6: reproduction and evidence
    story.append(PageBreak())
    p("Evidence and reproduction", "h1")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, both judges' "
      f"six-dimension sub-scores and intent recovery for each published run; <font name='Mono'>groups.json</font>; <font name='Mono'>calibration.json</font> with "
      f"every gate value and control mean; <font name='Mono'>judge-protocols.json</font> with the exact rubric, system text, probe and "
      f"match instructions, schemas, weights and the finding on the unpublished row; <font name='Mono'>economics.json</font> with cost and token aggregates, the rate table and pricing limitations; "
      f"and <font name='Mono'>provenance.json</font> with source hashes and limits. "
      f"<link href='{escape(args.github_url)}' color='#10A37F'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of "
      "the two judges, or the reviewed score alone where the submission passed no quirk family. The combined score is "
      "100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. Group means weight the cell's judged tasks equally. "
      "The export script recomputes every row from the frozen summary, re-prices every run from its receipt, asserts that exactly one row is "
      "unpublished and that it is the row carrying the operator's invalid-probe marker, and refuses to write if any value differs.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe "
      "task sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. "
      "Runs were not repeated and effort labels are Codex's own. The Max cell's Code quality and combined score are means over 22 of 23 runs. "
      "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training "
      "overlap exists.")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k, v[:32] + "..."] for k, v in provenance["source_artifacts_sha256"].items()], [230, 260], size=8.2, padding=3)
    p("The protocol documents, controls, quirk-key format, runner and operator wrapper are in the VulcanBench repository under "
      "docs/judging and harness. The quirk answer keys themselves describe hidden-test behaviour and are not published.", "small")

    # Page 7: appendix, per task at Low and Max
    story.append(PageBreak())
    p("Appendix. Per task at Low and Max effort", "h1")
    by = {(r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})
    records = []
    for task in tasks:
        lo, hi = by[("low", task)], by[("max", task)]
        judged = hi["judged"] == "published"
        records.append([task.replace("legacy-", "").replace("-binary-parity", "").replace("-parity", ""), f'{lo["code_quality"]:.1f}',
                        f'{hi["code_quality"]:.1f}' if judged else "unpublished", f'{lo["combined_33"]:.2f}', f'{hi["combined_33"]:.2f}' if judged else "unpublished"])
    table(["Task", "Low CQ", "Max CQ", "Low combined", "Max combined"], records, [150, 70, 80, 90, 100], size=8.4, padding=2.6)
    p("Per-task values from runs.json. Task names are shortened for width. The codeccore Max run is unpublished for the reason given on page 4.", "small")

    story.extend([NextPageTemplate("card"), PageBreak()])
    story.append(Image(str(CARD), width=680, height=488.75))
    story.append(PageBreak())
    story.append(Image(str(ECONOMICS_CARD), width=680, height=488.75))

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | Frontier v4 | Code quality protocol v3.7 | September 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | GPT-5.6 Sol across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench Frontier v4: GPT-5.6 Sol across every effort level",
                          author="VulcanBench", subject="Code quality protocol v3.7: neutral judges, 33% weight, Codex effort sweep, one unpublished Max row")
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
