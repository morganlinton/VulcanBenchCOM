"""Render the technical PDF for the v3.5 GPT-5.5 versus GPT-5.6 Luna comparison.

Reads only the public evidence bundle and the committed cards; no model calls.
Requires reportlab and the VulcanBench rankings-chart font folder.

    python3 scripts/render_swe_v4_v35_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>
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
DATA = ROOT / "assets/data/swe-v4-gpt55-luna-v35"
CARD = ROOT / "assets/cards/swe-v4-gpt55-luna-v35.png"
ECONOMICS_CARD = ROOT / "assets/cards/swe-v4-gpt55-luna-v35-economics.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-gpt55-luna-v35-report.pdf"
LEVELS = {"gpt55": ("low", "medium", "high", "extra-high"), "luna": ("low", "medium", "high", "extra-high", "max")}
EFFORTS = LEVELS["luna"]
SHARED = LEVELS["gpt55"]
NAMES = {"gpt55": "GPT-5.5", "luna": "Luna"}
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

    gpt_best, luna_best = g["gpt55", "extra-high"], g["luna", "max"]
    low_gap = g["gpt55", "low"]["combined_33"]["mean"] - g["luna", "low"]["combined_33"]["mean"]
    med_gap = g["gpt55", "medium"]["combined_33"]["mean"] - g["luna", "medium"]["combined_33"]["mean"]
    high_gap = g["luna", "high"]["combined_33"]["mean"] - g["gpt55", "high"]["combined_33"]["mean"]
    xh_gap = g["luna", "extra-high"]["combined_33"]["mean"] - g["gpt55", "extra-high"]["combined_33"]["mean"]
    ratios = [eg["gpt55", e]["usd"]["mean"] / eg["luna", e]["usd"]["mean"] for e in SHARED]

    # Page 1: abstract and headline table
    p("GPT-5.5 vs. GPT-5.6 Luna across every effort level", "h1")
    p("VulcanBench-SWE v4 | Code quality protocol v3.5 | September 2026", "small")
    heading("Abstract")
    p(f"GPT-5.5 and GPT-5.6 Luna ran the 23-task VulcanBench-SWE v4 suite through the Codex CLI on a ChatGPT subscription, once per task "
      f"at every effort level each API accepts: four levels for GPT-5.5 and five for Luna, 207 runs in all. Code quality carries 33% of the "
      f"combined score and is judged for a named human reader by Muse Spark 1.3 (Meta) and Grok 4.6 (xAI) under the same frozen protocol as "
      f"the Astra and Fable 5.1 report, with a ground-truth intent-recovery probe. The effort knob decides the comparison: GPT-5.5 leads at "
      f"Low and Medium by {low_gap:.2f} and {med_gap:.2f} points, Luna leads at High and Extra-high by {high_gap:.2f} and {xh_gap:.2f} points, "
      f"inside one standard error, and Luna's Max level, which GPT-5.5 does not offer, is the top cell at {luna_best['combined_33']['mean']:.2f} "
      f"with {luna_best['passed']} of 23 tasks passed. Luna is rated higher on Code quality at every matched effort, by under three points "
      f"from Medium up. At list API rates Luna costs {min(ratios):.1f} to {max(ratios):.1f} times less per task at matched effort.")
    p("Under the prior 50/15/15/20 profile applied to the same Code quality scores the same ordering holds at every effort, so the picture "
      "does not depend on the weight change.")
    heading("Table 1. Combined score, Code quality, tasks passed and runtime by effort")
    records = [[NAMES[m], label(e), f'{g[m, e]["combined_33"]["mean"]:.2f}', f'{g[m, e]["combined_33"]["se"]:.2f}',
                f'{g[m, e]["combined_20_profile"]["mean"]:.2f}', f'{g[m, e]["code_quality"]["mean"]:.2f}', f'{g[m, e]["minutes"]["mean"]:.1f}',
                f'{g[m, e]["passed"]}/23'] for m in LEVELS for e in LEVELS[m]]
    table(["Model", "Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Passed"],
          records, [52, 62, 78, 40, 78, 70, 52, 48], size=8.9)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality. Combined (20%) applies the "
      "prior 50/15/15/20 profile to the same Code quality scores for comparison. SE is one sample standard error across 23 "
      "tasks, not judge uncertainty or a significance test. Passed counts tasks with a perfect functional score. Runtime is solver "
      "wall-clock per task; judging is excluded. GPT-5.5's API has no Max level.", "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p("Protocol v3.5 is the v3.4 protocol applied to this population. Nothing in the rubric, controls, quirk keys, gates, repeats, seed or "
      "judge settings changed; both judges retook the calibration exam under v3.5 before any counted call, and both neutral judges are "
      "scored in one directory with no sensitivity panels.")
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
      "punished twice; a submission that passed none has no intent-recovery score and its Code quality is the reviewed score alone, "
      f"which happened on {g['luna', 'low']['intent_recovery_redistributed_runs']} Luna Low runs and "
      f"{g['luna', 'medium']['intent_recovery_redistributed_runs']} Luna Medium run. "
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
    muse_short = calibration["muse"]["gates"]["g11_repeatability"]["shortfall"]
    table(["Judge", "Protocol", "Calls", "Result", "Allowance used", "Failing gates"], [
        ["Muse Spark 1.3", protocols["protocol_ids"]["muse"], str(calibration["muse"]["call_count"]),
         "passed" if calibration["muse"]["passed"] else "failed", f"yes, g11 by {muse_short:.2f}" if calibration["muse"]["allowance_used"] else "no",
         ", ".join(calibration["muse"]["failing_gates"]) or "none"],
        ["Grok 4.6", protocols["protocol_ids"]["grok"], str(calibration["grok"]["call_count"]),
         "passed" if calibration["grok"]["passed"] else "failed", "yes" if calibration["grok"]["allowance_used"] else "no",
         ", ".join(calibration["grok"]["failing_gates"]) or "none"],
    ], [80, 150, 40, 50, 84, 90], size=8.6, padding=3)
    p(f"Muse Spark 1.3 used the pre-registered allowance: its five repeats on one control spread {muse_short:.2f} of a point more than gate 11 "
      "permits, within the half-point allowance, and every other gate passed. Grok 4.6 passed every gate.")
    heading("Table 3. Control means on five of the ten calibration programs")
    dims = ("naming", "presentation", "intent", "structure", "changeability", "verifiability")
    records = []
    for judge in ("muse", "grok"):
        cm = calibration[judge]["control_means"]
        for name, key in (("clear", "0"), ("compressed", "1"), ("formatted", "2"), ("misleading comments", "5"), ("hidden state", "9")):
            records.append([("Muse" if judge == "muse" else "Grok"), name, *[f'{cm[key][d]:.2f}' for d in dims]])
    table(["Judge", "Control", "Naming", "Present.", "Intent", "Struct.", "Change.", "Verif."], records,
          [44, 108, 48, 52, 46, 48, 50, 44], size=8.4, padding=3)
    p("Both judges separate the clear program from the compressed one by more than two points on naming and about two points on "
      "presentation, credit formatting on presentation but not on naming, penalise misleading comments on intent, and penalise hidden state on "
      "verifiability. Full gate values are in calibration.json.", "small")
    # Page 4: results in detail
    story.append(PageBreak())
    p("Results in detail", "h1")
    heading("Table 4. Code quality components at each model's best effort")
    a, f = gpt_best, luna_best
    rows = [("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
            ("Intent recovery", "intent_recovery", 1), ("Reviewed score", "reviewed_score", 1)]
    records = [[name, f'{a[key]["mean"]:.{d}f}', f'{f[key]["mean"]:.{d}f}', f'{f[key]["mean"] - a[key]["mean"]:+.{max(d, 1)}f}'] for name, key, d in rows]
    records += [["Rated by Muse Spark 1.3", f'{a["by_panel"]["muse"]["mean"]:.1f}', f'{f["by_panel"]["muse"]["mean"]:.1f}',
                 f'{f["by_panel"]["muse"]["mean"] - a["by_panel"]["muse"]["mean"]:+.1f}'],
                ["Rated by Grok 4.6", f'{a["by_panel"]["grok"]["mean"]:.1f}', f'{f["by_panel"]["grok"]["mean"]:.1f}',
                 f'{f["by_panel"]["grok"]["mean"] - a["by_panel"]["grok"]["mean"]:+.1f}'],
                ["Standard error of Code quality", f'{a["code_quality"]["se"]:.2f}', f'{f["code_quality"]["se"]:.2f}', ""]]
    table(["Component", "GPT-5.5, Extra-high", "Luna, Max", "Luna minus GPT-5.5"], records, [190, 100, 100, 100], size=9, padding=4)
    p("At each model's best effort the reviewed scores are close and GPT-5.5 reads slightly better; Luna recovers more of the hidden "
      "contract. Across matched efforts Luna's Code quality and human readability are higher at every level, while maintainability and "
      "intent recovery trade places; both judges rank the reviewed score the same way in every cell. Both models sit well below the "
      "Astra and Fable 5.1 board under the same rubric, 62 to 72 here against 70 to 82 there.")
    heading("Table 5. Four factors by effort, mean score out of 100")
    table(["Model", "Effort", "Functional", "Lint, complexity", "Security", "Code quality"],
          [[NAMES[m], label(e), *[f'{g[m, e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for m in LEVELS for e in LEVELS[m]], [60, 73, 91, 91, 73, 92], size=8.8, padding=3)
    p("Functional scores retain partial credit. Lint and complexity and security are the sweep's automated measurements. Code quality is "
      "the protocol's score, the reviewed score alone where a submission passed no quirk family.", "small")

    # Page 5: cost and tokens
    story.append(PageBreak())
    p("Cost and tokens across effort levels", "h1")
    p("The same 207 runs priced from their Codex receipts at list API rates, cache-aware, solver inference only, judging excluded. "
      "Both models ran on a ChatGPT subscription, so these are API-equivalent estimates rather than bills. GPT-5.5 lists at 25 times "
      "Luna's input, cached-input and output rates. Luna uses more tokens than GPT-5.5 from High up, most of them cache reads.")
    heading("Table 6. API-equivalent cost, raw tokens and runtime by effort")
    et = econ["totals"]
    records = []
    for e in EFFORTS:
        b = eg["luna", e]
        if ("gpt55", e) in eg:
            a = eg["gpt55", e]
            records.append([label(e), f'${a["usd"]["mean"]:.2f}', f'${b["usd"]["mean"]:.2f}', f'{a["usd"]["mean"] / b["usd"]["mean"]:.1f}x',
                            f'{a["raw_tokens"]["mean"] / 1e6:.2f}M', f'{b["raw_tokens"]["mean"] / 1e6:.2f}M',
                            f'{a["minutes"]["mean"]:.1f}', f'{b["minutes"]["mean"]:.1f}'])
        else:
            records.append([label(e), "no level", f'${b["usd"]["mean"]:.2f}', "", "", f'{b["raw_tokens"]["mean"] / 1e6:.2f}M', "", f'{b["minutes"]["mean"]:.1f}'])
    records.append(["Full sweeps", f'${et["gpt55"]["usd"]:,.2f}', f'${et["luna"]["usd"]:,.2f}', f'{et["gpt55"]["usd"] / et["luna"]["usd"]:.1f}x',
                    f'{et["gpt55"]["raw_tokens"] / 1e6:,.0f}M', f'{et["luna"]["raw_tokens"] / 1e6:,.0f}M',
                    f'{et["gpt55"]["solver_hours"]:.1f} h', f'{et["luna"]["solver_hours"]:.1f} h'])
    table(["Effort", "GPT-5.5 $/task", "Luna $/task", "Ratio", "GPT-5.5 tokens", "Luna tokens", "GPT-5.5 min", "Luna min"],
          records, [66, 70, 64, 44, 72, 66, 58, 54], size=8.6, padding=3)
    rates = econ["rates_per_million"]
    p(f"Rates checked {econ['pricing_verified']}: GPT-5.5 at ${rates['gpt55']['input']:.2f} input, ${rates['gpt55']['cached_input']:.2f} cached input and "
      f"${rates['gpt55']['output']:.2f} output per million tokens; Luna at ${rates['luna']['input']:.2f}, ${rates['luna']['cached_input']:.2f} and "
      f"${rates['luna']['output']:.2f}. Codex receipts report input, cached input, output and reasoning tokens per run, so cached input is billed at "
      "the cache-read rate and the rest at the standard rate. The full sweeps are 92 GPT-5.5 runs and 115 Luna runs. Tokens are raw solver totals "
      "including cache reads. Per-run estimates and the rate table are in economics.json and runs.csv.", "small")
    heading("Limitations recorded with the estimates")
    for item in econ["limitations"]:
        p("• " + item, "small")

    # Page 6: reproduction and evidence
    story.append(PageBreak())
    p("Evidence and reproduction", "h1")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, both judges' "
      f"six-dimension sub-scores and intent recovery; <font name='Mono'>groups.json</font>; <font name='Mono'>calibration.json</font> with "
      f"every gate value and control mean; <font name='Mono'>judge-protocols.json</font> with the exact rubric, system text, probe and "
      f"match instructions, schemas and weights; <font name='Mono'>economics.json</font> with cost and token aggregates, the rate table and pricing limitations; "
      f"and <font name='Mono'>provenance.json</font> with source hashes. "
      f"<link href='{escape(args.github_url)}' color='#10A37F'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of "
      "the two judges, or the reviewed score alone where the submission passed no quirk family. The combined score is "
      "100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. Group means weight the 23 tasks equally. "
      "The export script recomputes every row from the frozen summary, re-prices every run from its receipt, and refuses to write if "
      "any value differs.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe "
      "task sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. "
      "Runs were not repeated and effort labels are Codex's own. One GPT-5.5 Extra-high task was re-run after its first attempt "
      "overran the cap under a harness fault; the re-run is the judged run. Hash checks bind the export to frozen files; they do not "
      "prove that judges were unbiased or that no training overlap exists.")
    heading("Operator record")
    p("Each judge made 718 calls: 80 in calibration, 207 primary reviews, 9 repeats, 8 pairwise checks, 207 intent probes and 207 "
      "answer-key matches. Muse needed a second attempt on five calls (two unsupported excerpts, two malformed JSON responses, one "
      "missing consequence in calibration) and Grok on six (four unsupported excerpts, one malformed response, and one transport fault "
      "when the Cursor CLI could not resolve its API host). The transport fault stopped the run for a person; the operator wrapper gained "
      "a rule that gives one fresh attempt after a judge CLI network fault, with the receipt retained, and the call was retried under it. "
      "Neither judge produced a reviewer fallback. Every second attempt is archived beside the first in the harness run directory.", "small")

    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k, v[:32] + "..."] for k, v in provenance["source_artifacts_sha256"].items()], [190, 300], size=8.2, padding=3)
    p("The protocol documents, controls, quirk-key format, runner and operator wrapper are in the VulcanBench repository under "
      "docs/judging and harness. The quirk answer keys themselves describe hidden-test behaviour and are not published.", "small")

    # Page 7: appendix, per task at each model's best effort
    story.append(PageBreak())
    p("Appendix. Per task at each model's best effort", "h1")
    by = {(r["model"], r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})
    records = []
    for t in tasks:
        ra, rf = by["gpt55", "extra-high", t], by["luna", "max", t]
        records.append([t.replace("legacy-", "").replace("-binary-parity", "").replace("-parity", ""), f'{ra["code_quality"]:.1f}', f'{rf["code_quality"]:.1f}',
                        f'{rf["code_quality"] - ra["code_quality"]:+.1f}', f'{ra["combined_33"]:.2f}', f'{rf["combined_33"]:.2f}'])
    table(["Task", "GPT-5.5 CQ", "Luna CQ", "Difference", "GPT-5.5 combined", "Luna combined"], records, [150, 66, 62, 66, 90, 86], size=8.4, padding=2.6)
    p("Per-task values from runs.json; GPT-5.5 at Extra-high and Luna at Max. Task names are shortened for width.", "small")

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | SWE v4 | Code quality protocol v3.5 | September 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | GPT-5.5 vs. GPT-5.6 Luna across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench-SWE v4: GPT-5.5 vs. GPT-5.6 Luna across every effort level",
                          author="VulcanBench", subject="Code quality protocol v3.5: neutral judges, 33% weight, Codex effort sweeps")
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
