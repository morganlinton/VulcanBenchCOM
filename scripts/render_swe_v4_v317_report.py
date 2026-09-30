"""Render the technical PDF for the v3.17 GPT-6 Sol effort sweep.

Reads only the public evidence bundles (this one and GPT-5.6 Sol's, for the
comparison) and the committed cards; no model calls. Requires reportlab and
the VulcanBench rankings-chart font folder.

    python3 scripts/render_swe_v4_v317_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>
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
DATA = ROOT / "assets/data/swe-v4-gpt6-sol-v317"
SOL56 = ROOT / "assets/data/swe-v4-sol-v37"
CARD = ROOT / "assets/cards/swe-v4-gpt6-sol-v317.png"
ECONOMICS_CARD = ROOT / "assets/cards/swe-v4-gpt6-sol-v317-economics.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-gpt6-sol-v317-report.pdf"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccc4")
PAGES = 10


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
    s56 = {g["effort"]: g for g in json.loads((SOL56 / "groups.json").read_text())}
    e56 = {g["effort"]: g for g in json.loads((SOL56 / "economics.json").read_text())["groups"]}
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
    cq = [t[e]["code_quality"]["mean"] for e in EFFORTS]
    totals = econ["totals"]["gpt6sol"]
    unpublished = [r for r in runs if r["judged"] != "published"]
    assert [(r["effort"], short(r["task"])) for r in unpublished] == [("medium", "codeccore")]
    finding = protocols["unpublished"][0]
    recovery = protocols["operator_recoveries"][0]
    assert (recovery["effort"], short(recovery["task"])) == ("high", "payrollcore")

    # Page 1: abstract and headline table
    p("GPT-6 Sol across every effort level", "h1")
    p("VulcanBench Frontier v4 | Code quality protocol v3.17 | September 2026", "small")
    heading("Abstract")
    p(f"GPT-6 Sol ran the 23-task VulcanBench Frontier v4 suite through Codex CLI 0.155.0 on a ChatGPT Pro subscription on September 28 "
      f"to 29, 2026, once per task at each of five effort levels, Low to Max, 115 runs in all. Code quality carries 33% of the combined score "
      f"and is judged for a named human reader by Muse Spark 1.3 (Meta) and Grok 4.6 (xAI) under the same frozen protocol as the other "
      f"Frontier v4 reports, with a ground-truth intent-recovery probe. The combined score rises at every step, from {comb[0]:.2f} at Low to "
      f"{comb[1]:.2f} at Medium, {comb[2]:.2f} at High, {comb[3]:.2f} at Extra-high and {comb[4]:.2f} at Max. GPT-6 Sol passes "
      f"{t['low']['passed_all_runs']}, {t['medium']['passed_all_runs']}, {t['high']['passed_all_runs']}, {t['extra-high']['passed_all_runs']} "
      f"and {t['max']['passed_all_runs']} of 23 tasks from Low to Max. Code quality rises from {min(cq):.2f} to {max(cq):.2f}. Cost per task "
      f"runs from ${et['low']['usd']['mean']:.2f} at Low to ${et['max']['usd']['mean']:.2f} at Max; the whole sweep prices at "
      f"${totals['usd']:.2f}, ${totals['usd'] / totals['runs']:.2f} per task.")
    p("Every run finished inside the flat 3-hour task bound, so nothing is excluded. One Medium run, codeccore, has no published Code "
      "quality score: Grok 4.6's intent probe gave no valid answer after the protocol's single retry, so the Medium cell's Code quality "
      "and combined score cover 22 of its 23 runs. The run failed its tests and is counted in every pass count, runtime, token and cost "
      "figure. Beside GPT-5.6 Sol, GPT-6 Sol scores slightly lower at every level, is slower, and costs more per task from Medium up.")
    heading("Table 1. Combined score, Code quality, runtime and tasks passed by effort")
    records = [[label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{t[e]["combined_33"]["se"]:.2f}',
                f'{t[e]["combined_20_profile"]["mean"]:.2f}', f'{t[e]["code_quality"]["mean"]:.2f}', f'{t[e]["minutes"]["mean"]:.1f}',
                f'{t[e]["n"]}', f'{t[e]["passed_all_runs"]}/23'] for e in EFFORTS]
    table(["Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Judged", "Passed"],
          records, [62, 74, 40, 72, 66, 56, 50, 48], size=8.8)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality, over judged runs. Combined (20%) "
      "applies the prior 50/15/15/20 profile to the same Code quality scores. SE is one sample standard error across the cell's judged "
      "tasks, not judge uncertainty or a significance test. Passed counts all 23 runs. Runtime is solver wall-clock per task over every "
      "run in the cell; judging is excluded.", "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p("Protocol v3.17 is the same protocol applied to this population. Nothing in the rubric, controls, quirk keys, gates, repeats, seed, "
      "weights or judges changed from v3.7; both judges retook the calibration exam under v3.17 before any counted call. The population froze "
      "on September 29 with 115 rows, none missing and none excluded. A submission without a valid answer-key match from every passing "
      "panel is left unpublished by the frozen summary; that rule applied once, described under Results in detail.")
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
    assert all(t[e]["intent_recovery_redistributed_runs"] == 0 for e in EFFORTS)
    p("<b>Reviewed panel, 24 points.</b> The six-dimension rubric above, averaged across both judges. "
      "<b>Intent recovery, 9 points.</b> Every task in this suite is a rewrite of a retired binary whose real behaviour departs "
      "from its written specification in documented ways. The judge sees only the specification and the code, never the issue "
      "text, and lists where the code departs from the specification; a separate call matches that list against the frozen "
      "answer key. The denominator is the quirks the submission actually passed tests for, so a functional failure is not "
      "punished twice; a submission that passed none would have no intent-recovery score and its Code quality would be the reviewed "
      "score alone, which no GPT-6 Sol run needed. "
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
        return ", ".join(calibration[judge]["failing_gates"]) or "none"

    table(["Judge", "Protocol", "Calls", "Result", "Allowance", "Failing gates"], [
        ["Muse Spark 1.3", protocols["protocol_ids"]["muse"], str(calibration["muse"]["call_count"]),
         "passed" if calibration["muse"]["passed"] else "failed", "used" if calibration["muse"]["allowance_used"] else "not used", failing("muse")],
        ["Grok 4.6", protocols["protocol_ids"]["grok"], str(calibration["grok"]["call_count"]),
         "passed" if calibration["grok"]["passed"] else "failed", "used" if calibration["grok"]["allowance_used"] else "not used", failing("grok")],
    ], [72, 150, 36, 46, 60, 110], size=8.4, padding=3, wrap=True)
    p("Both judges passed every gate with no allowance used; under v3.16 each had needed the pre-registered one-gate allowance.")
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

    # Page 4: results in detail, the unpublished row and the operator record
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
    p(f"Code quality rises from {min(cq):.2f} at Low to about 70.8 at Extra-high and Max, with Grok 4.6 the higher rater at every level. "
      "Means cover judged runs.", "small")
    heading("Table 5. Four factors by effort, mean score out of 100 over judged runs")
    table(["Effort", "Functional", "Lint, complexity", "Security", "Code quality"],
          [[label(e), *[f'{t[e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for e in EFFORTS], [80, 91, 91, 80, 92], size=8.8, padding=3)
    heading("The unpublished Medium row")
    p(f"On codeccore at Medium, Grok 4.6's intent probe produced no valid answer after the protocol's single retry. Attempt 1 was not valid "
      f"JSON; attempt 2 quoted <font name='Mono'>{escape(finding['unsupported_excerpts']['2'][0])}</font>, which is not in the code. No "
      "recovery rule accepts an invented excerpt, so no answer-key match was made and the frozen summary publishes no Code quality or "
      "combined score for the run. It is the same codeccore line Grok 4.6 misquoted for GPT-5.6 Sol at Max under v3.7. Both judges' reviews "
      "and the Muse probe are retained in the harness archive. The run failed its tests, so it counts as a failed task, and its runtime, "
      "tokens and cost are in every economics figure. The operator's finding is recorded beside the two attempts and its hash is in "
      "provenance.json.", "small")
    heading("Operator record")
    p(f"On high payrollcore, both of Grok 4.6's primary-review attempts returned a complete JSON review followed by a stray closing brace. "
      f"The formatting-only rule {recovery['rule']} decoded the first JSON object, dropped the trailing brace and applied every normal check; "
      f"attempt {recovery['source_attempt']} passed and was selected, reviewed score {recovery['reviewed_score']:.2f}. No field was edited. "
      "Under v3.17 Muse Spark 1.3 made 440 counted calls (80 in calibration, 115 primary reviews, 5 repeats, 10 pairwise checks, 115 intent "
      "probes, 115 answer-key matches) and Grok 4.6 made 439, with 114 matches. Muse needed a second attempt on six calls, all unsupported "
      "excerpts; Grok on five, three primary reviews with a trailing brace and two probes. Neither judge produced a reviewer fallback.", "small")

    # Page 5: cost and tokens
    story.append(PageBreak())
    p("Cost and tokens across effort levels", "h1")
    p("All 115 runs priced from their Codex receipts at list API rates, cache-aware, solver inference only, judging excluded. GPT-6 Sol ran "
      "on a ChatGPT Pro subscription, so these are API-equivalent estimates rather than bills. Low is the cheapest and fastest level; High "
      "uses more tokens and costs more per task than Extra-high, and Max is the most expensive. Every run is priced, including the Medium "
      "run without a published Code quality score.")
    heading("Table 6. API-equivalent cost, raw tokens and runtime by effort")
    records = [[label(e), str(et[e]["n"]), f'${et[e]["usd"]["mean"]:.2f}', f'${et[e]["usd_total"]:.2f}',
                f'{et[e]["raw_tokens"]["mean"] / 1e6:.2f}M', f'{et[e]["minutes"]["mean"]:.1f}'] for e in EFFORTS]
    records.append(["Full sweep", str(totals["runs"]), f'${totals["usd"] / totals["runs"]:.2f}', f'${totals["usd"]:,.2f}',
                    f'{totals["raw_tokens"] / 1e6:,.0f}M', f'{totals["solver_hours"]:.1f} h'])
    table(["Effort", "Runs", "$/task", "Level total", "Tokens/task", "Min/task"], records, [80, 50, 70, 84, 84, 70], size=8.6, padding=3)
    rates = econ["rates_per_million"]["gpt6sol"]
    p(f"Rates checked {econ['pricing_verified']}: GPT-6 Sol at ${rates['input']:.2f} input, ${rates['cached_input']:.2f} cached input and "
      f"${rates['output']:.2f} output per million tokens. Codex receipts report input, cached input, output and reasoning tokens per run, so "
      "cached input is billed at the cache-read rate and the rest at the standard rate. The sweep stamped each run at these rates at run time; "
      "the export recomputed every run from its receipt and matched every stamp. Tokens are raw solver totals including cache reads.", "small")
    heading("Limitations recorded with the estimates")
    for item in econ["limitations"]:
        p("&#8226; " + item, "small")

    # Page 6: beside GPT-5.6 Sol, and how it was run
    story.append(PageBreak())
    p("Beside GPT-5.6 Sol", "h1")
    p("GPT-5.6 Sol ran the same 23 tasks through Codex in September and was judged by the same judges under v3.7 (Max judged on 22 of 23). "
      "GPT-6 Sol's combined score is slightly lower at every level; the gaps at Extra-high and Max are within one standard error of either "
      "model. At half the list price per token, GPT-6 Sol uses 1.8 to 3.9 times the raw tokens per task, so it costs less only at Low.")
    heading("Table 7. GPT-6 Sol and GPT-5.6 Sol by effort")
    records = []
    for e in EFFORTS:
        passed56 = s56[e]["passed_all_runs"]
        records.append([label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{s56[e]["combined_33"]["mean"]:.2f}',
                        f'{t[e]["passed_all_runs"]} / {passed56}', f'${et[e]["usd"]["mean"]:.2f} / ${e56[e]["usd"]["mean"]:.2f}',
                        f'{et[e]["minutes"]["mean"]:.1f} / {e56[e]["minutes"]["mean"]:.1f}'])
    table(["Effort", "GPT-6 Sol", "GPT-5.6 Sol", "Passed of 23", "$/task", "Min/task"], records, [74, 70, 76, 80, 100, 90], size=8.6, padding=3)
    p("Combined scores are over judged runs; pass counts, cost and minutes cover all 23 runs per cell, GPT-6 Sol first in each pair. Each "
      "model is priced at its own list rates (GPT-5.6 Sol $4.00 input and $20.00 output per million tokens). The sweeps ran on different "
      "Codex CLI versions (0.155.0 and 0.153.4).", "small")
    heading("How it was run")
    p("<b>Codex CLI 0.155.0.</b> The earlier Codex columns ran on 0.153.4, which refuses GPT-6 models on a ChatGPT account before any "
      "work; 0.155.0 is the lowest release that serves them and was installed beside the global CLI for the GPT-6 sweeps only. "
      "<b>The sweep overlapped another model's judging.</b> The solver sweep ran September 28, 00:31 PDT, to September 29, 14:53 PDT; at the "
      "owner's request it ran alongside GPT-6 Luna's judging, September 28, 00:32 to 14:32 PDT, which matters for the wall-clock figures. "
      "<b>One infrastructure retry.</b> The first Max depotcore attempt ended after eight minutes when the API reported the model at "
      "capacity; the harness re-queued it and the retry is the counted run. <b>Judging</b> ran September 29, 14:54 PDT, to September 30, "
      "06:51 PDT, resumed after the two Grok findings on page 4, while GPT-6.1 Sol's solver sweep ran at the owner's request; the judges "
      "share no quota with it. <b>One attempt per task and level</b>; effort labels are Codex's own.")

    # Page 7: evidence and reproduction
    story.append(PageBreak())
    p("Evidence and reproduction", "h1")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, both judges' "
      f"six-dimension sub-scores and intent recovery for each published run; <font name='Mono'>groups.json</font>; "
      f"<font name='Mono'>calibration.json</font> with every gate value and control mean; <font name='Mono'>judge-protocols.json</font> with "
      f"the exact rubric, system text, probe and match instructions, schemas, weights, the finding on the unpublished row and the one "
      f"operator recovery; <font name='Mono'>economics.json</font> with cost and token aggregates, the rate table and pricing limitations; and "
      f"<font name='Mono'>provenance.json</font> with source hashes and limits. "
      f"<link href='{escape(args.github_url)}' color='#10A37F'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of "
      "the two judges, or the reviewed score alone where the submission passed no quirk family. The combined score is "
      "100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. Group means weight the cell's judged tasks equally. "
      "The export script recomputes every row from the frozen summary, re-prices every run from its receipt, asserts that exactly one row is "
      "unpublished and that it is the row carrying the operator's invalid-probe marker, checks the figures against the harness card tables, "
      "and refuses to write if any value differs.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe "
      "task sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. "
      "Runs were not repeated. The Medium cell's Code quality and combined score are means over 22 of 23 runs. "
      "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k.replace("v3.17/calls/grok/", "calls/grok/"), v[:32] + "..."]
                                          for k, v in provenance["source_artifacts_sha256"].items()], [250, 240], size=7.8, padding=2.4)

    # Page 8: appendix, per task
    story.append(PageBreak())
    p("Appendix. Per task at Low, Medium and Max", "h1")
    by = {(r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})

    def cell(r, key, digits):
        return "unpublished" if r["judged"] != "published" else f"{r[key]:.{digits}f}"

    records = [[short(task), cell(by["low", task], "code_quality", 1), cell(by["max", task], "code_quality", 1),
                cell(by["low", task], "combined_33", 2), cell(by["medium", task], "combined_33", 2), cell(by["max", task], "combined_33", 2)]
               for task in tasks]
    table(["Task", "Low CQ", "Max CQ", "Low combined", "Medium combined", "Max combined"], records, [100, 60, 64, 80, 94, 84], size=8.2, padding=2.4)
    p("Per-task values from runs.json. Task names are shortened for width. The codeccore Medium run is unpublished for the reason given on "
      "page 4.", "small")

    story.extend([NextPageTemplate("card"), PageBreak()])
    story.append(Image(str(CARD), width=620, height=620 * 1867 / 2400))
    story.append(PageBreak())
    story.append(Image(str(ECONOMICS_CARD), width=660, height=660 * 1725 / 2400))

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | Frontier v4 | Code quality protocol v3.17 | September 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | GPT-6 Sol across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench Frontier v4: GPT-6 Sol across every effort level",
                          author="VulcanBench", subject="Code quality protocol v3.17: neutral judges, 33% weight, Codex effort sweep, GPT-5.6 Sol comparison")
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
