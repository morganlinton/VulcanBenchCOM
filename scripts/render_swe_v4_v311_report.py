"""Render the technical PDF for the v3.11 Devin SWE-2 effort sweep.

Reads only the public evidence bundle and the committed cards; no model calls.
Requires reportlab and the VulcanBench rankings-chart font folder.

    python3 scripts/render_swe_v4_v311_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>
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
DATA = ROOT / "assets/data/swe-v4-devin-swe2-v311"
CARD = ROOT / "assets/cards/swe-v4-devin-swe2-v311.png"
ECONOMICS_CARD = ROOT / "assets/cards/swe-v4-devin-swe2-v311-economics.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-devin-swe2-v311-report.pdf"
LEVELS = {"swe2": ("medium", "high", "max")}
EFFORTS = LEVELS["swe2"]
NAMES = {"swe2": "SWE-2"}
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccc4")
PAGES = 9


def label(effort):
    return effort.capitalize()


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
    record = json.loads((DATA / "runs.json").read_text())
    runs = record["rows"]
    did_not_finish = record["did_not_finish"]
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

    t = {e: g["swe2", e] for e in EFFORTS}
    et = {e: eg["swe2", e] for e in EFFORTS}
    comb = [t[e]["combined_33"]["mean"] for e in EFFORTS]
    cq = [t[e]["code_quality"]["mean"] for e in EFFORTS]
    totals = econ["totals"]["swe2"]
    excluded = [r for r in runs if r["judged"] != "published"] + did_not_finish
    assert len(excluded) == 4 and len(did_not_finish) == 1
    assert all(r["judged"] == "published" or r["functional"] == 0.0 for r in excluded)

    # Page 1: abstract and headline table
    p("Devin SWE-2 across every effort level", "h1")
    p("VulcanBench Frontier v4 | Code quality protocol v3.11 | September 2026", "small")
    heading("Abstract")
    p(f"Devin SWE-2 ran the 23-task VulcanBench Frontier v4 suite through the Devin CLI on a Devin subscription on September 18 to 21, "
      f"2026, once per task at each of the three effort levels the model offers (medium, high and max, its whole catalog), 69 runs in all. "
      f"Code quality carries 33% of the combined score. It is judged here for a named human reader by <b>Muse Spark 1.3 (Meta) alone</b>, "
      f"not by the two-judge neutral panel behind every other Frontier v4 entry: Grok 4.6 failed the calibration exam under protocol v3.9 "
      f"and GPT-5.6 Sol, admitted under v3.10 to fill the second seat, failed under v3.10, both on gate 16, so the protocol's pre-registered "
      f"single-panel rule applies. Read every Code quality number in this report as one judge's rating. "
      f"Medium and high are indistinguishable: {comb[0]:.2f} and {comb[1]:.2f}, with standard errors of "
      f"{t['medium']['combined_33']['se']:.2f} and {t['high']['combined_33']['se']:.2f}, and both pass "
      f"{t['medium']['passed']} of 23 tasks. Only max moves, to {comb[2]:.2f} and {t['max']['passed']} of 23. Code quality runs "
      f"{min(cq):.2f} to {max(cq):.2f} across the three levels. Cost per task is unavailable: Cognition publishes no per-token rate for "
      f"SWE-2, so nothing here is priced. What the sweep spends is time and tokens, "
      f"{et['high']['minutes']['mean']:.1f} to {et['max']['minutes']['mean']:.1f} minutes and "
      f"{et['high']['raw_tokens']['mean'] / 1e6:.2f}M to {et['medium']['raw_tokens']['mean'] / 1e6:.2f}M raw tokens per task.")
    p("65 of the 69 runs are judged. One high run (cellarcore) reached the 3-hour task budget before verification and did not finish; three "
      "more (snapcore and vaultcore at high, freightcore at max) changed no recognized source file, so there was no submission to review and "
      "the sweep's automated quality and security metrics are undefined for them. The protocol excludes those four rather than judging them. "
      "All four failed their tests, so the sweep's pass counts are unchanged by the exclusions. Under the prior 50/15/15/20 profile applied "
      "to the same Code quality scores the shape is the same, so the picture does not depend on the weight change.")
    heading("Table 1. Combined score, Code quality, tasks passed and runtime by effort")
    records = [[NAMES["swe2"], label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{t[e]["combined_33"]["se"]:.2f}',
                f'{t[e]["combined_20_profile"]["mean"]:.2f}', f'{t[e]["code_quality"]["mean"]:.2f}', f'{t[e]["minutes"]["mean"]:.1f}',
                f'{t[e]["passed"]}/{t[e]["n"]}'] for e in EFFORTS]
    table(["Model", "Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Passed"],
          records, [52, 62, 78, 40, 78, 70, 52, 48], size=8.9)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality. Combined (20%) applies the "
      "prior 50/15/15/20 profile to the same Code quality scores for comparison. SE is one sample standard error across the cell's "
      "tasks, not judge uncertainty or a significance test. Passed counts judged tasks with a perfect functional score, out of the judged "
      "runs in the cell; because every excluded run failed, the sweep's own counts are 15, 15 and 21 of 23. Runtime is solver wall-clock "
      "per task over every finished run in the cell; judging is excluded.", "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p(f"Protocol {protocols['protocol_ids']['muse']} is the same protocol applied to this population. Nothing in the rubric, controls, "
      "quirk keys, gates, repeats, seed or "
      "judge settings changed. What did change is the population and the panel. The population is the sweep minus the four runs that carry "
      "no judgeable submission, frozen on September 21 with 65 rows, none missing. The panel is one judge, for the reason set out on the "
      "next page. Every card and report that shows Devin's Code quality is required by the amendment to say so.")
    heading("The rubric")
    p("The judge receives instructions frozen by hash before any review. The prompt names the reader it scores for: "
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
    p("<b>Reviewed panel, 24 points.</b> The six-dimension rubric above, from the single scored judge. "
      "<b>Intent recovery, 9 points.</b> Every task in this suite is a rewrite of a retired binary whose real behaviour departs "
      "from its written specification in documented ways. The judge sees only the specification and the code, never the issue "
      "text, and lists where the code departs from the specification; a separate call matches that list against the frozen "
      "answer key. The denominator is the quirks the submission actually passed tests for, so a functional failure is not "
      "punished twice; one high run passed none, so its Code quality is the reviewed score alone under the pre-registered "
      "redistribution. "
      "<b>Measured maintenance, designed for 12 points, not yet built.</b> Until it exists the pre-registered "
      "split above is in force and is stated on the card.")

    # Page 3: judges and calibration
    story.append(PageBreak())
    p("One judge, and why", "h1")
    p("The scored panel is Muse Spark 1.3 through the Muse CLI on its Standard tier, which does not train on prompts, and nothing else. "
      "Meta has no model on this board, so the judge does not grade a relative. Every session is fresh, tools are disabled, the workspace "
      "is empty, model identity is checked per call, and solver labels are withheld. This is the only Frontier v4 entry scored by a single "
      "judge; the rest carry the mean of Muse Spark 1.3 and Grok 4.6.")
    heading("The calibration exam")
    p("Before scoring a single submission a judge reviews ten held-out programs that implement the same ledger specification: clear, "
      "compressed, auto-formatted, verbose, over-abstracted, misleadingly commented, over-narrated, quirky, prompt-injecting and stateful. "
      "Each is reviewed five times in a seeded order, and twenty gates fixed in advance check that the judge sees the construct; a judge "
      "may miss at most one gate by at most half a point.")
    p("Gate 16 is the probe on the clear control, and it is boolean: a program with no documented departure from its specification must "
      "draw an empty probe on at least four of five repeats. Grok 4.6 reported invented departures on two repeats under v3.9 and GPT-5.6 "
      "Sol on four under v3.10. Each passed every other gate, repeatability included, and because the gate is boolean the one-gate "
      "allowance cannot cover it. Under the pre-registered single-panel rule nothing further runs for a judge that fails, and no judge "
      "retakes a gate it failed. Both verdicts stay published. Muse's own verdict comes from the v3.9 freeze rather than a fresh exam: the "
      "exam is per judge and control set and neither changed between v3.9 and v3.11, so on the v3.6.1 precedent the runner reuses it.")
    heading("Table 2. Calibration verdicts")
    table(["Judge", "Protocol", "Calls", "Result", "Allowance used", "Failing gates"],
          [[c["judge"] + (", scored" if c["scored"] else ", not scored"), p_id, str(c["call_count"]),
            "passed" if c["passed"] else "failed", "yes" if c["allowance_used"] else "no", ", ".join(c["failing_gates"]) or "none"]
           for p_id, c in (("code-quality-maintenance-v3.9", calibration["panels"]["muse"]),
                           ("code-quality-maintenance-v3.9", calibration["panels"]["grok"]),
                           ("code-quality-maintenance-v3.10", calibration["panels"]["sol"]))],
          [110, 150, 40, 50, 84, 160], size=8.6, padding=3)
    p("Muse passed 19 of the 20 gates outright and used the pre-registered one-gate allowance on the repeatability gate, within the "
      "allowance as written. Both failures are on gate 16, the one call that rewards saying nothing.", "small")
    heading("Table 3. Control means on three of the ten calibration programs")
    dims = ("naming", "presentation", "intent", "structure", "changeability", "verifiability")
    records = []
    for judge, short in (("muse", "Muse"), ("grok", "Grok"), ("sol", "Sol")):
        cm = calibration["panels"][judge]["control_means"]
        for name, key in (("clear", "0"), ("compressed", "1"), ("misleading comments", "5")):
            records.append([short, name, *[f'{cm[key][d]:.2f}' for d in dims]])
    table(["Judge", "Control", "Naming", "Present.", "Intent", "Struct.", "Change.", "Verif."], records,
          [44, 108, 48, 52, 46, 48, 50, 44], size=8.0, padding=2)
    p("All three judges separate the clear program from the compressed one on naming and presentation and penalise misleading comments on "
      "intent; the two that are not scored here failed only on the clear control's probe. Full gate values and all ten control means for "
      "all three judges are in calibration.json.", "small")

    # Page 4: results in detail
    story.append(PageBreak())
    p("Results in detail", "h1")
    heading("Table 4. Code quality components at each effort level")
    rows = [("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
            ("Intent recovery", "intent_recovery", 1), ("Reviewed score", "reviewed_score", 1)]
    records = [[name, *[f'{t[e][key]["mean"]:.{d}f}' for e in EFFORTS]] for name, key, d in rows]
    records += [["Standard error of Code quality", *[f'{t[e]["code_quality"]["se"]:.2f}' for e in EFFORTS]],
                ["Judged runs", *[str(t[e]["n"]) for e in EFFORTS]],
                ["Runs attempted", *[str(t[e]["runs_attempted"]) for e in EFFORTS]]]
    table(["Component", "Medium", "High", "Max"], records, [200, 80, 80, 80], size=9, padding=3)
    p(f"Code quality runs {min(cq):.2f} to {max(cq):.2f}. The rise is carried by the reviewed layer, whose human readability sub-score "
      f"climbs {t['max']['readability']['mean'] - t['medium']['readability']['mean']:.1f} points from medium to max, while intent recovery, "
      f"the ground-truth layer, stays flat at {min(t[e]['intent_recovery']['mean'] for e in EFFORTS):.1f} to "
      f"{max(t[e]['intent_recovery']['mean'] for e in EFFORTS):.1f}. With standard errors of "
      f"{min(t[e]['code_quality']['se'] for e in EFFORTS):.2f} to {max(t[e]['code_quality']['se'] for e in EFFORTS):.2f} the medium to high "
      "step sits inside the noise. One judge produced every one of these numbers.")
    heading("Table 5. Four factors by effort, mean score out of 100")
    table(["Model", "Effort", "Functional", "Lint, complexity", "Security", "Code quality"],
          [[NAMES["swe2"], label(e), *[f'{t[e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for e in EFFORTS], [60, 73, 91, 91, 73, 92], size=8.8, padding=3)
    p("Functional scores retain partial credit, so they sit above the whole-task pass counts. Lint and complexity and security are the "
      "sweep's automated measurements. Code quality is the protocol's score. Every mean covers the judged runs in the cell.", "small")
    heading("The four unjudged runs")
    table(["Effort", "Task", "Finished", "Reason recorded in the population record"],
          [[label(r["effort"]), r["task"].replace("legacy-", "").replace("-binary-parity", ""), "yes" if r["finished"] else "no",
            "Changed no recognized source file, so there is no submission to judge and the sweep's automated quality and security metrics "
            "are undefined" if r["finished"] else "Reached the 3-hour task budget before verification, so the run has no receipt"]
           for r in sorted(excluded, key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))],
          [50, 80, 52, 308], size=8.2, padding=2.6, wrap=True)
    p("Every one of the four scored 0 functionally and counts as a fail, so the sweep's pass counts (15, 15 and 21 of 23) are unchanged by "
      "the exclusions. The three that finished keep their runtime and tokens in every economics figure; the one that did not has no receipt "
      "and its 3.0 hours sit outside the totals. Under v3.11 Muse Spark 1.3 made 204 counted calls: 65 primary reviews, 3 repeats, 6 "
      "pairwise checks, 65 intent probes and 65 answer-key matches. No call needed a second attempt, no operator rule was invoked and no "
      "reviewer fallback occurred. The earlier v3.9 and v3.10 passes, including the two failed calibration exams, stay archived in the "
      "harness run directories.", "small")

    # Page 5: cost and tokens
    story.append(PageBreak())
    p("Cost and tokens across effort levels", "h1")
    p("<b>Cost per task is unavailable, and that is the published value.</b> Cognition publishes no per-token rate for SWE-2. The cost tier "
      "\"Free\" in Devin's catalog is a promotion dated through 2026-10-10, not a rate, so a figure taken from it would read as a measured "
      "price and would stop being true when the promotion ends. No cost is estimated on this page or in the evidence bundle, the population "
      "record carries a null cost for every run, and SWE-2 is not compared on cost with the priced models on this board. If Cognition "
      "publishes a rate, these runs can be repriced from their receipts.")
    p("Devin's own credit and ACU counters in the CLI receipts read zero on every run and are recorded per run, but a zero counter on a "
      "subscription is a counter and not a price. What the sweep does spend is time and tokens, and it spends a great deal of both. Neither "
      "follows the effort ladder: medium is the heaviest level in tokens, high the lightest and the fastest, and max the slowest. Against "
      "the Codex models measured on the same suite, which run about 10 to 12 minutes and 1.8M to 2.8M tokens per task, Devin is several "
      "times slower and several times heavier.")
    heading("Table 6. Tokens, runtime and cost by effort")
    records = [[label(e), str(et[e]["n"]), f'{et[e]["output_tokens"]["mean"] / 1e3:.0f}K',
                f'{et[e]["raw_tokens"]["mean"] / 1e6:.2f}M', f'{et[e]["raw_tokens_total"] / 1e6:.0f}M',
                f'{et[e]["minutes"]["mean"]:.1f}', "unavailable"] for e in EFFORTS]
    records.append(["Full sweep", str(totals["runs"]), f'{totals["output_tokens"] / totals["runs"] / 1e3:.0f}K',
                    f'{totals["raw_tokens"] / totals["runs"] / 1e6:.2f}M', f'{totals["raw_tokens"] / 1e6:,.0f}M',
                    f'{totals["solver_hours"]:.1f} h', "unavailable"])
    table(["Effort", "Runs", "Output/task", "Tokens/task", "Level tokens", "Min/task", "$/task"],
          records, [62, 40, 66, 66, 66, 56, 70], size=8.6, padding=3)
    p("Runs here are the finished runs of each cell, 68 in all; the run that did not finish has no receipt. Tokens are the Devin CLI's own "
      "per-request usage receipts, deduplicated by request id and summed as uncached input, cache reads and output. Per-run records, "
      "including Devin's credit and ACU counters, are in economics.json and runs.csv.", "small")
    heading("Limitations recorded with the measurements")
    for item in econ["limitations"]:
        p("• " + item, "small")

    # Page 6: reproduction and evidence
    story.append(PageBreak())
    p("Evidence and reproduction", "h1")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every finished run's factors, the "
      f"judge's six-dimension sub-scores and intent recovery for each published run, and the four exclusions with their reasons; "
      f"<font name='Mono'>groups.json</font>; <font name='Mono'>calibration.json</font> with all three verdicts, every gate value and "
      f"control mean; <font name='Mono'>judge-protocols.json</font> with the exact rubric, system text, probe and match instructions, "
      f"schemas, weights, the single-panel rule and the population record; <font name='Mono'>economics.json</font> with token and runtime "
      f"aggregates and the record of why cost is unavailable; and <font name='Mono'>provenance.json</font> with source hashes and limits. "
      f"<link href='{escape(args.github_url)}' color='#10A37F'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, both terms from the single scored judge, or "
      "the reviewed score alone where the submission passed no quirk family. The combined score is "
      "100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. Group means weight the cell's judged tasks equally. "
      "The export script recomputes every row from the frozen summary, asserts that the four excluded runs are exactly the four the "
      "population record lists and that each is a functional fail, asserts that no run carries a cost figure, and refuses to write if any "
      "value differs.")
    heading("What this report does not claim")
    p("Code quality here is one model's judgment for a human reader, without the second opinion every other Frontier v4 entry carries and "
      "without any human validation. Standard errors describe task sampling only. The measured-maintenance layer is unbuilt, so the 33 "
      "points are 24 reviewed plus 9 intent recovery. Runs were not repeated and effort labels are Devin's own. The high cell's Code quality "
      "and combined score are means over 20 of 23 runs and the max cell's over 22 of 23. Hash checks bind the export to frozen files; they "
      "do not prove that the judge was unbiased or that no training overlap exists.")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k, v[:32] + "..."] for k, v in provenance["source_artifacts_sha256"].items()], [230, 260], size=8.2, padding=3)
    p("The protocol documents, controls, quirk-key format, runner and operator wrapper are in the VulcanBench repository under "
      "docs/judging and harness. The quirk answer keys themselves describe hidden-test behaviour and are not published.", "small")

    # Page 7: appendix, per task at medium and max
    story.append(PageBreak())
    p("Appendix. Per task at medium and max effort", "h1")
    by = {(r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})
    records = []
    for task in tasks:
        lo, hi = by.get(("medium", task)), by.get(("max", task))
        records.append([task.replace("legacy-", "").replace("-binary-parity", "").replace("-parity", ""),
                        f'{lo["code_quality"]:.1f}' if lo and lo["code_quality"] is not None else "excluded",
                        f'{hi["code_quality"]:.1f}' if hi and hi["code_quality"] is not None else "excluded",
                        f'{lo["combined_33"]:.2f}' if lo and lo["combined_33"] is not None else "excluded",
                        f'{hi["combined_33"]:.2f}' if hi and hi["combined_33"] is not None else "excluded"])
    table(["Task", "Medium CQ", "Max CQ", "Medium combined", "Max combined"], records, [150, 70, 80, 90, 100], size=8.4, padding=2.6)
    p("Per-task values from runs.json. Task names are shortened for width. The freightcore run at max is excluded for the reason given on "
      "page 4; the two other finished exclusions and the unfinished one are at high effort.", "small")

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | Frontier v4 | Code quality protocol v3.11 | September 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | Devin SWE-2 across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench Frontier v4: Devin SWE-2 across every effort level",
                          author="VulcanBench",
                          subject="Code quality protocol v3.11: a single neutral judge, 33% weight, Devin CLI effort sweep, four runs excluded")
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
