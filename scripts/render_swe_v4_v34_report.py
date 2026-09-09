"""Render the technical PDF for the v3.4 neutral-panel Code quality comparison.

Reads only the public evidence bundle and the committed card; no model calls.
Requires reportlab and the VulcanBench rankings-chart font folder.

    python3 scripts/render_swe_v4_v34_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>
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
DATA = ROOT / "assets/data/swe-v4-astra-fable51-v34"
CARD = ROOT / "assets/cards/swe-v4-astra-fable51-v34.png"
ECONOMICS_CARD = ROOT / "assets/cards/swe-v4-astra-fable51-v34-economics.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-astra-fable51-v34-report.pdf"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccc4")
PAGES = 10


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

    def name(model):
        return "Astra" if model == "astra" else "Fable 5.1"

    astra_max, fable_max = g["astra", "max"], g["fable", "max"]
    best = {m: max((g[m, e] for e in EFFORTS), key=lambda r: r["combined_33"]["mean"]) for m in ("astra", "fable")}

    # Page 1: abstract and headline table
    p("GPT-6 Astra vs. Fable 5.1 under a neutral Code quality panel", "h1")
    p("VulcanBench-SWE v4 | Code quality protocol v3.4 | September 2026", "small")
    heading("Abstract")
    p(f"The same 230 runs from the September 2026 effort comparison, 23 tasks at five effort levels for each model, are rescored "
      f"under a revised Code quality protocol. Code quality now carries 33% of the combined score, is judged for a named human "
      f"reader by two models from labs with no entry on the board, Muse Spark 1.3 (Meta) and Grok 4.6 (xAI), and includes a "
      f"ground-truth intent-recovery probe. Fable 5.1 in Claude Code has the higher combined score and the higher Code quality at "
      f"every matched effort; Astra in Codex is faster at every effort. At Max effort the combined scores are "
      f"{fable_max['combined_33']['mean']:.2f} and {astra_max['combined_33']['mean']:.2f}; Code quality is "
      f"{fable_max['code_quality']['mean']:.2f} against {astra_max['code_quality']['mean']:.2f}, with the widest gap on human "
      f"readability ({fable_max['readability']['mean']:.1f} against {astra_max['readability']['mean']:.1f}).")
    p("Under the earlier published protocol, in which Astra and an Anthropic model judged the same code, Astra led Code quality at "
      "all five efforts. The reversal comes from who judges and what the rubric asks, not from the weight change alone: under "
      "the old 20% weight and the new judges Fable still leads at every effort.")
    heading("Table 1. Combined score, Code quality and runtime by effort")
    records = [[name(m), e.replace("-", " ").title(), f'{g[m, e]["combined_33"]["mean"]:.2f}', f'{g[m, e]["combined_33"]["se"]:.2f}',
                f'{g[m, e]["combined_20_profile"]["mean"]:.2f}', f'{g[m, e]["code_quality"]["mean"]:.2f}', f'{g[m, e]["minutes"]["mean"]:.1f}',
                f'{g[m, e]["passed"]}/23'] for m in ("astra", "fable") for e in EFFORTS]
    table(["Model", "Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Passed"],
          records, [52, 62, 78, 40, 78, 70, 52, 48], size=8.9)
    p("Combined (33%) = 0.50 functional + 0.085 automated quality + 0.085 security + 0.33 Code quality. Combined (20%) applies the "
      "prior 50/15/15/20 profile to the same new Code quality scores for comparison. SE is one sample standard error across 23 "
      "tasks, not judge uncertainty or a significance test. Runtime is solver wall-clock per task; judging is excluded.", "small")

    # Page 2: what changed and why
    story.append(PageBreak())
    p("Why the protocol changed", "h1")
    p("Two failure modes motivated the revision. First, the automated quality metric rewards compression: the maintainability "
      "index carries a lines-of-code term and per-function complexity stays low when each dense line does something different, "
      "so five statements on a line with names like x and k can outscore the same logic written for a person. Second, a large "
      "model reading compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability "
      "judge, it rated a squashed six-line function the same as its formatted copy.")
    p("Weight moved from the automated metric to a reviewed score: Code quality rose from 20% to 33% of the combined score, "
      "locked on September 7, 2026 before any submission was rescored. Both automated quality and security fell to 8.5%. The "
      "prior profile is reported beside the new one on every table.")
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
      "punished twice. <b>Measured maintenance, designed for 12 points, not yet built.</b> Until it exists the pre-registered "
      "split above is in force and is stated on the card receipt.")

    # Page 3: judges and calibration
    story.append(PageBreak())
    p("Judges and calibration", "h1")
    p("The scored panel is Muse Spark 1.3 through the Muse CLI on its Standard tier, which does not train on prompts, and Grok 4.6 "
      "through the Cursor CLI at medium effort. Neither lab has a model on this board, so neither judge grades a relative. Every "
      "session is fresh, tools are disabled, the workspace is empty, model identity is checked per call from the CLI's own "
      "records, and solver labels are withheld. GLM 5.3 was tried first and failed calibration on validity after fabricating an "
      "excerpt in both attempts on one control. Astra and Claude Opus 5 also passed the exam under an earlier protocol version "
      "but were retired from the score by the benchmark owner because Astra would otherwise have judged its own code while "
      "Fable never did.")
    heading("The calibration exam")
    p("Before scoring a single submission each judge reviews ten held-out programs that implement the same ledger specification: "
      "clear, compressed, compressed then auto-formatted, verbose with duplicated policy, needlessly abstracted, misleadingly "
      "commented, narrated with a comment on every line, a documented legacy quirk, an embedded instruction to give full marks, "
      "and hidden module state. Each program is reviewed five times in a seeded order. Twenty gates fixed in advance check that "
      "the judge sees the construct; a judge may miss at most one gate by at most half a point.")
    heading("Table 2. Calibration verdicts")
    table(["Judge", "Protocol", "Calls", "Result", "Allowance used", "Failing gates"], [
        ["Muse Spark 1.3", protocols["protocol_ids"]["muse"], str(calibration["muse"]["call_count"]),
         "passed" if calibration["muse"]["passed"] else "failed", "yes" if calibration["muse"].get("allowance_used") else "no", ", ".join(calibration["muse"]["failing_gates"]) or "none"],
        ["Grok 4.6", protocols["protocol_ids"]["grok"], str(calibration["grok"]["call_count"]),
         "passed" if calibration["grok"]["passed"] else "failed", "yes" if calibration["grok"].get("allowance_used") else "no", ", ".join(calibration["grok"]["failing_gates"]) or "none"],
        ["GLM 5.3", "code-quality-maintenance-v3.3", str(calibration["glm"]["call_count"]), "failed", "n/a", ", ".join(calibration["glm"]["failing_gates"])],
    ], [80, 150, 40, 50, 74, 90], size=8.6, padding=3)
    heading("Table 3. Control means on five of the ten calibration programs")
    dims = ("naming", "presentation", "intent", "structure", "changeability", "verifiability")
    records = []
    for judge in ("muse", "grok"):
        cm = calibration[judge]["control_means"]
        for label, key in (("clear", "0"), ("compressed", "1"), ("formatted", "2"), ("misleading comments", "5"), ("hidden state", "9")):
            records.append([("Muse" if judge == "muse" else "Grok"), label, *[f'{cm[key][d]:.2f}' for d in dims]])
    table(["Judge", "Control", "Naming", "Present.", "Intent", "Struct.", "Change.", "Verif."], records,
          [44, 108, 48, 52, 46, 48, 50, 44], size=8.4, padding=3)
    p("Both judges separate the clear program from the compressed one by more than two points on naming and presentation, credit "
      "formatting on presentation but not on naming, penalise misleading comments on intent, and penalise hidden state on "
      "verifiability. Full gate values are in calibration.json.", "small")

    # Page 4: results in detail
    story.append(PageBreak())
    p("Results in detail", "h1")
    heading("Table 4. Code quality components at each model's best effort")
    a, f = best["astra"], best["fable"]
    rows = [("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
            ("Intent recovery", "intent_recovery", 1), ("Reviewed score", "reviewed_score", 1)]
    records = [[label, f'{a[key]["mean"]:.{d}f}', f'{f[key]["mean"]:.{d}f}', f'{f[key]["mean"] - a[key]["mean"]:+.{max(d, 1)}f}'] for label, key, d in rows]
    records += [["Rated by Muse Spark 1.3", f'{a["by_panel"]["muse"]["mean"]:.1f}', f'{f["by_panel"]["muse"]["mean"]:.1f}',
                 f'{f["by_panel"]["muse"]["mean"] - a["by_panel"]["muse"]["mean"]:+.1f}'],
                ["Rated by Grok 4.6", f'{a["by_panel"]["grok"]["mean"]:.1f}', f'{f["by_panel"]["grok"]["mean"]:.1f}',
                 f'{f["by_panel"]["grok"]["mean"] - a["by_panel"]["grok"]["mean"]:+.1f}'],
                ["Standard error of Code quality", f'{a["code_quality"]["se"]:.2f}', f'{f["code_quality"]["se"]:.2f}', ""]]
    table(["Component", f"Astra, {a['effort']}", f"Fable 5.1, {f['effort']}", "Fable minus Astra"], records, [190, 100, 100, 100], size=9, padding=4)
    p("Both judges agree on every ranking and differ by a few points on levels. The largest gap between the models is human "
      "readability; intent recovery, the ground-truth layer, is close, which says both models teach the next maintainer the real "
      "contract about equally well and differ in how readable the code is for a person.")
    heading("Table 5. Four factors by effort, mean score out of 100")
    table(["Model", "Effort", "Functional", "Auto quality", "Security", "Code quality"],
          [[name(m), e.replace("-", " ").title(), *[f'{g[m, e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for m in ("astra", "fable") for e in EFFORTS], [60, 73, 91, 91, 73, 92], size=8.8, padding=3)
    p("Functional scores retain partial credit and are the same values as the earlier report. Automated quality and security are "
      "unchanged measurements; only their weights moved. Code quality is the new protocol's score.", "small")

    # Page 5: cost and tokens
    story.append(PageBreak())
    p("Cost and tokens across effort levels", "h1")
    p("The same 230 runs priced from their solver receipts at list API rates, cache-aware, solver inference only, judging excluded. "
      "Both models ran on subscriptions, so these are API-equivalent estimates rather than bills. Astra is cheaper at every effort; its cost "
      "rises with effort while Fable's does not track the effort label.")
    heading("Table 6. API-equivalent cost, raw tokens and runtime by effort")
    et = econ["totals"]
    records = [[e.replace("-", " ").title(), f'${eg["astra", e]["usd"]["mean"]:.2f}', f'${eg["astra", e]["long_context_upper_usd"]["mean"]:.2f}',
                f'${eg["fable", e]["usd"]["mean"]:.2f}', f'{eg["fable", e]["usd"]["mean"] / eg["astra", e]["usd"]["mean"]:.1f}x',
                f'{eg["astra", e]["raw_tokens"]["mean"] / 1e6:.2f}M', f'{eg["fable", e]["raw_tokens"]["mean"] / 1e6:.2f}M',
                f'{eg["astra", e]["minutes"]["mean"]:.1f}', f'{eg["fable", e]["minutes"]["mean"]:.1f}'] for e in EFFORTS]
    records.append(["Full sweep", f'${et["astra"]["usd"]:,.2f}', f'${et["astra"]["long_context_upper_usd"]:,.2f}', f'${et["fable"]["usd"]:,.2f}',
                    f'{et["fable"]["usd"] / et["astra"]["usd"]:.1f}x', f'{et["astra"]["raw_tokens"] / 1e6:,.0f}M', f'{et["fable"]["raw_tokens"] / 1e6:,.0f}M',
                    f'{et["astra"]["solver_hours"]:.1f} h', f'{et["fable"]["solver_hours"]:.1f} h'])
    table(["Effort", "Astra $/task", "Astra bound", "Fable $/task", "Ratio", "Astra tokens", "Fable tokens", "Astra min", "Fable min"],
          records, [58, 60, 58, 60, 40, 62, 62, 48, 48], size=8.6, padding=3)
    p(f"Rates checked {econ['pricing_verified']}. Astra input includes cache reads and output includes reasoning; Claude pricing covers observed "
      "five-minute and one-hour cache writes, Fable, Opus 5, Opus 4.8 fallback and auxiliary Haiku usage. Astra's receipts do not record per-request "
      "sizes, so the central estimate uses standard rates and the bound prices every run that exceeded 272k cumulative input tokens at the long-context "
      "tier; Astra stays cheaper at every effort under that bound. Tokens are raw solver totals including cache reads, which makes Fable's token count a "
      "poor cost proxy. The sweep totals, per-run estimates and rate tables are in economics.json and runs.csv.", "small")
    heading("Limitations recorded with the ledger")
    for item in econ["limitations"]:
        p("\u2022 " + item, "small")

    # Page 6: history of the run
    story.append(PageBreak())
    p("How the run actually went", "h1")
    p("Every protocol version was frozen by hash before its first counted call, and each older panel ran from a git worktree pinned "
      "to its own freeze commit once the runner had moved on. The freeze history is part of the published record.")
    table(["Version", "Change", "Outcome"], [
        ["v3", "Three repeats, exact-excerpt rule, verifiability gate with a naming clause", "Reader passed; Astra failed repeatability and the naming clause; Opus 5 stopped on non-verbatim excerpts"],
        ["v3.1", "Line-level excerpt rule; naming clause dropped", "Astra failed a different single gate; Opus 5 stopped on a dots-only elision line"],
        ["v3.2", "Five repeats; one-gate allowance of 0.5; elision markers", "Astra and Opus 5 passed with no allowance; the Haiku reader failed its gate by one answer"],
        ["v3.3", "Neutral panel: GLM 5.3 and Grok 4.6", "Grok passed with no allowance; GLM failed on a fabricated excerpt"],
        ["v3.4", "Muse Spark 1.3 replaces GLM 5.3", "Muse passed with no allowance; both neutral judges completed all 230 submissions"],
    ], [48, 196, 236], size=8.4, padding=3, wrap=True)
    heading("Operator interventions")
    p("A wrapper outside the frozen code applied a small set of documented rules when a judge call stopped, and halted for a person "
      "on anything else. Every application is printed to the run log and recorded inside the receipt it touched, with the "
      "original response preserved. The rules: one fresh attempt after a CLI structured-output failure; re-wrapping an excerpt to "
      "the source's own line breaks when every fragment is verbatim, including quotes that start mid-line, drop Markdown code marks, "
      "omit a receiver or index, or decode an escape into a control character; normalising decorated quirk identifiers; one fresh "
      "attempt after an outside SIGTERM; and archive-and-resume with backoff after a transport rate limit. Fabricated text never "
      "recovers. Muse needed two excerpt recoveries and one SIGTERM retry across 690 calls; Grok needed five excerpt recoveries and "
      "six rate-limit resumes across 960 calls. Neither judge produced a reviewer fallback.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe "
      "task sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. "
      "Runs were not repeated, CLI versions were not held fixed across weeks, and effort labels are harness-specific. The 11 Fable "
      "runs that fell back to Opus 4.8 remain in the population and are flagged in the run records. Hash checks bind the export to "
      "frozen files; they do not prove that judges were unbiased or that no training overlap exists.")

    # Page 6: reproduction and evidence
    story.append(PageBreak())
    p("Evidence and reproduction", "h1")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, both judges' "
      f"six-dimension sub-scores and intent recovery; <font name='Mono'>groups.json</font>; <font name='Mono'>calibration.json</font> with "
      f"every gate value and control mean; <font name='Mono'>judge-protocols.json</font> with the exact rubric, system text, probe and "
      f"match instructions, schemas and weights; <font name='Mono'>economics.json</font> with cost and token aggregates, rate tables and pricing limitations; "
      f"and <font name='Mono'>provenance.json</font> with source hashes. "
      f"<link href='{escape(args.github_url)}' color='#10A37F'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of "
      "the two judges. The combined score is 100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. "
      "Group means weight the 23 tasks equally. The export script recomputes every row from the frozen summary and refuses to "
      "write if any value differs.")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k, v[:32] + "..."] for k, v in provenance["source_artifacts_sha256"].items()], [190, 300], size=8.2, padding=3)
    p("The protocol documents, controls, quirk-key format, runner and operator wrapper are in the VulcanBench repository under "
      "docs/judging and harness. The quirk answer keys themselves describe hidden-test behaviour and are not published.", "small")

    # Page 7: appendix of all runs? Keep compact: per-task Code quality at Max for both models
    story.append(PageBreak())
    p("Appendix. Code quality per task at Max effort", "h1")
    by = {(r["model"], r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})
    records = []
    for t in tasks:
        ra, rf = by["astra", "max", t], by["fable", "max", t]
        records.append([t.replace("legacy-", "").replace("-binary-parity", "").replace("-parity", ""), f'{ra["code_quality"]:.1f}', f'{rf["code_quality"]:.1f}',
                        f'{rf["code_quality"] - ra["code_quality"]:+.1f}', f'{ra["combined_33"]:.2f}', f'{rf["combined_33"]:.2f}'])
    table(["Task", "Astra CQ", "Fable CQ", "Difference", "Astra combined", "Fable combined"], records, [150, 62, 62, 66, 80, 80], size=8.4, padding=2.6)
    p("Per-task values from runs.json; Max effort for both models. Task names are shortened for width.", "small")

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | SWE v4 | Code quality protocol v3.4 | September 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | Astra vs. Fable 5.1 under a neutral Code quality panel")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench-SWE v4: Astra vs. Fable 5.1 under a neutral Code quality panel",
                          author="VulcanBench", subject="Code quality protocol v3.4: neutral judges, 33% weight, effort sweep")
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
