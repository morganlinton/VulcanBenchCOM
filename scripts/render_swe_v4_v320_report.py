"""Render the technical PDF for the v3.20 Grok 4.7 (Cursor) effort sweep.

Reads only the public evidence bundles (this one, and the GPT-6.1 Sol, Opus 5.5
and Astra bundles for the leaders comparison), the Frontier v4 board and the
committed cards; no model calls. Requires reportlab and the VulcanBench
rankings-chart font folder.

    python3 scripts/render_swe_v4_v320_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>
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
DATA = ROOT / "assets/data/swe-v4-grok47-cursor-v320"
BOARD = ROOT / "assets/data/swe-v4-board.json"
CARDS = [(ROOT / "assets/cards/swe-v4-grok47-cursor-v320.png", 620, 1867),
         (ROOT / "assets/cards/swe-v4-grok47-cursor-v320-usage.png", 640, 1830),
         (ROOT / "assets/cards/swe-v4-grok47-vs-frontier-leaders.png", 474, 2475),
         (ROOT / "assets/cards/safety-v1-grok47-opus55.png", 560, 2062)]
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-grok47-cursor-v320-report.pdf"
EFFORTS = ("low", "medium", "high", "extra-high")
MODEL = "grok47cursor"
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccc4")
PAGES = 12
NAMES = {"fable": "Fable 5.1", "opus55": "Opus 5.5", "astra": "GPT-6 Astra", "gpt61sol": "GPT-6.1 Sol", "terra": "GPT-5.6 Terra",
         "grok47cursor": "Grok 4.7"}


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
    runs = json.loads((DATA / "runs.json").read_text())["rows"]
    calibration = json.loads((DATA / "calibration.json").read_text())
    protocols = json.loads((DATA / "judge-protocols.json").read_text())
    provenance = json.loads((DATA / "provenance.json").read_text())
    usage = json.loads((DATA / "usage.json").read_text())
    shared = json.loads((DATA / "shared-judge.json").read_text())["columns"]
    safety = json.loads((DATA / "safety-v1.json").read_text())
    t = {g["effort"]: g for g in json.loads((DATA / "groups.json").read_text())}
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
    muse = [t[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
    gaps = [t[e]["by_panel"]["sol"]["mean"] - t[e]["by_panel"]["muse"]["mean"] for e in EFFORTS]
    timeouts = [r for r in runs if not r["finished"]]
    assert [(r["effort"], short(r["task"])) for r in timeouts] == [("medium", "lodgecore")]
    ranks = {r["effort"]: r["rank"] for r in board if r["key"] == MODEL}
    mine = {c["effort"]: c for c in shared if c["model"] == MODEL}
    rivals = {e: max((c for c in shared if c["effort"] == e and c["model"] != MODEL), key=lambda c: c["muse_combined"]) for e in EFFORTS}

    # Page 1: abstract, the judge caveat and the headline table
    p("Grok 4.7 across every effort level", "h1")
    p("VulcanBench Frontier v4 | Code quality protocol v3.20 | October 2026", "small")
    heading("Abstract")
    p(f"Grok 4.7 (xAI) ran the 23-task VulcanBench Frontier v4 suite through Cursor's agent CLI 2026.10.01-14929f9 on the Cursor "
      f"subscription from October 1 to 3, 2026, once per task at each of the four effort levels Cursor offers for it, Low to Extra-high "
      f"(there is no Max), 92 runs in all. Code quality carries 33% of the combined score and is judged for a named human reader by Muse "
      f"Spark 1.3 (Meta) and GPT-6.1 Sol (OpenAI) with a ground-truth intent-recovery probe. The combined score is {comb[0]:.2f} at Low, "
      f"{comb[1]:.2f} at Medium, {comb[2]:.2f} at High and {comb[3]:.2f} at Extra-high. Grok 4.7 passes "
      f"{', '.join(str(t[e]['passed_all_runs']) for e in EFFORTS[:3])} and {t['extra-high']['passed_all_runs']} of 23 tasks from Low to "
      f"Extra-high and fixes {', '.join(str(t[e]['hidden_behaviours_fixed']) for e in EFFORTS[:3])} and {t['extra-high']['hidden_behaviours_fixed']} "
      f"of the 231 hidden behaviours tested. Code quality runs from {min(cq):.2f} to {max(cq):.2f}. Runs take "
      f"{t['low']['minutes']['mean']:.1f} to {max(t[e]['minutes']['mean'] for e in EFFORTS):.1f} minutes per task. Cost is unavailable: "
      "VulcanBench has no list price for Grok 4.7.")
    p(f"Medium lodgecore hit the flat 3-hour task bound: it counts as a failed task and in runtime, and Medium is judged on "
      f"{t['medium']['n']} runs. On the board's published figures Grok 4.7's Extra-high, High and Medium levels rank {ranks['extra-high']}, "
      f"{ranks['high']} and {ranks['medium']} of {len(board)} columns, and Low ranks {ranks['low']}, the highest Low column.")
    heading("Read this first: a different second judge")
    p(f"Every other Frontier v4 column was judged by Muse Spark 1.3 and Grok 4.6. Grok 4.6 is not neutral for an xAI submission, so GPT-6.1 "
      f"Sol took its seat. GPT-6.1 Sol rates the same submissions {min(gaps):.1f} to {max(gaps):.1f} points above Muse, so Grok 4.7's "
      f"Code quality is not strictly comparable with the other columns. On Muse's review score alone Grok 4.7 has {muse[0]:.1f} to "
      f"{max(muse):.1f}. Rescored from Muse alone for every column, Grok 4.7 scores {mine['low']['muse_combined']:.2f} to "
      f"{mine['extra-high']['muse_combined']:.2f}: still first at Medium, High and Extra-high, and second at Low behind "
      f"{NAMES[rivals['low']['model']]} ({rivals['low']['muse_combined']:.2f}). See page 5.")
    heading("Table 1. Combined score, Code quality, runtime and tasks passed by effort")
    records = [[label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{t[e]["combined_33"]["se"]:.2f}',
                f'{t[e]["combined_20_profile"]["mean"]:.2f}', f'{t[e]["code_quality"]["mean"]:.2f}', f'{t[e]["minutes"]["mean"]:.1f}',
                f'{t[e]["n"]}', f'{t[e]["passed_all_runs"]}/23'] for e in EFFORTS]
    table(["Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Judged", "Passed"],
          records, [62, 74, 40, 72, 66, 56, 50, 48], size=8.8)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality, over the level's judged runs. "
      "Combined (20%) applies the prior 50/15/15/20 profile to the same Code quality scores. SE is one sample standard error across the "
      "level's tasks, not judge uncertainty or a significance test. Runtime is solver wall-clock per task over all 23 runs; judging is excluded.",
      "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p("Protocol v3.20 is the same protocol applied to this population with a different second judge. Nothing in the rubric, controls, quirk "
      "keys, gates, repeats, seed or weights changed from v3.7; both judges took the calibration exam under v3.20 before any counted call. "
      "The population froze on October 3 with 91 rows of 92 runs: the medium lodgecore timeout is excluded as an incomplete source run, and "
      "none is missing.")
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
    p("<b>Reviewed panel, 24 points.</b> The six-dimension rubric above, averaged across the two judges. "
      "<b>Intent recovery, 9 points.</b> Every task in this suite is a rewrite of a retired binary whose real behaviour departs "
      "from its written specification in documented ways. The judge sees only the specification and the code, never the issue "
      "text, and lists where the code departs from the specification; a separate call matches that list against the frozen "
      "answer key. The denominator is the quirks the submission actually passed tests for, so a functional failure is not "
      "punished twice; a submission that passed none would have no intent-recovery score and its Code quality would be the reviewed "
      "score alone, which no Grok 4.7 run needed. "
      "<b>Measured maintenance, designed for 12 points, not yet built.</b> Until it exists the pre-registered "
      "split above is in force.")

    # Page 3: judges and calibration
    story.append(PageBreak())
    p("Judges and calibration", "h1")
    p("The scored panel is Muse Spark 1.3 through the Muse CLI on its Standard tier, which does not train on prompts, with its v3.4 settings "
      "and binary pin, and GPT-6.1 Sol at medium effort through Codex CLI 0.159.0, the binary pinned for GPT-6.1 Sol's own sweep. Neither lab "
      "is xAI. Grok 4.6, the second judge on every other column, sits out because it is an xAI model; the owner chose GPT-6.1 Sol for the "
      "seat on October 3, 2026. Every session is fresh, tools are disabled, the workspace is empty and solver labels are withheld. Muse's "
      "identity is checked per call from its CLI's records; Codex does not record the serving model, so GPT-6.1 Sol's identity is the model "
      "requested.")
    heading("The calibration exam")
    p("Before scoring a single submission each judge reviews ten held-out programs that implement the same ledger specification: "
      "clear, compressed, compressed then auto-formatted, verbose with duplicated policy, needlessly abstracted, misleadingly "
      "commented, narrated with a comment on every line, a documented legacy quirk, an embedded instruction to give full marks, "
      "and hidden module state. Each program is reviewed five times in a seeded order. Twenty gates fixed in advance check that "
      "the judge sees the construct; a judge may miss at most one gate by at most half a point.")
    heading("Table 2. Calibration verdicts")

    def failing(judge):
        gates = calibration[judge]["gates"]
        return ", ".join(f'{g} ({gates[g]["shortfall"]:.1f} short)' for g in calibration[judge]["failing_gates"]) or "none"

    table(["Judge", "Protocol", "Calls", "Result", "Allowance", "Failing gates"], [
        [name, protocols["protocol_ids"][judge], str(calibration[judge]["call_count"]), "passed" if calibration[judge]["passed"] else "failed",
         "used" if calibration[judge]["allowance_used"] else "not used", failing(judge)]
        for judge, name in (("muse", "Muse Spark 1.3"), ("sol", "GPT-6.1 Sol"))
    ], [72, 150, 36, 46, 60, 120], size=8.4, padding=3, wrap=True)
    p("Muse Spark 1.3 passed with the one-gate allowance: its repeatability gate fell 0.1 short, inside the half point the protocol "
      "allows. GPT-6.1 Sol, on its first exam, passed every gate with no allowance used.")
    heading("Table 3. Control means on five of the ten calibration programs")
    dims = ("naming", "presentation", "intent", "structure", "changeability", "verifiability")
    records = []
    for judge in ("muse", "sol"):
        cm = calibration[judge]["control_means"]
        for name, key in (("clear", "0"), ("compressed", "1"), ("formatted", "2"), ("misleading comments", "5"), ("hidden state", "9")):
            records.append([("Muse" if judge == "muse" else "Sol"), name, *[f'{cm[key][d]:.2f}' for d in dims]])
    table(["Judge", "Control", "Naming", "Present.", "Intent", "Struct.", "Change.", "Verif."], records,
          [44, 108, 48, 52, 46, 48, 50, 44], size=8.4, padding=3)
    p("Full gate values and control means are in calibration.json.", "small")

    # Page 4: results in detail, the timeout and the operator record
    story.append(PageBreak())
    p("Results in detail", "h1")
    heading("Table 4. Code quality components at each effort level")
    rows = [("Code quality", "code_quality", 2), ("Human readability", "readability", 1), ("Maintainability", "maintainability", 1),
            ("Intent recovery", "intent_recovery", 1), ("Reviewed score", "reviewed_score", 1)]
    records = [[name, *[f'{t[e][key]["mean"]:.{d}f}' for e in EFFORTS]] for name, key, d in rows]
    records += [["Rated by Muse Spark 1.3", *[f'{t[e]["by_panel"]["muse"]["mean"]:.1f}' for e in EFFORTS]],
                ["Rated by GPT-6.1 Sol", *[f'{t[e]["by_panel"]["sol"]["mean"]:.1f}' for e in EFFORTS]],
                ["Standard error of Code quality", *[f'{t[e]["code_quality"]["se"]:.2f}' for e in EFFORTS]],
                ["Hidden behaviours fixed of 231", *[str(t[e]["hidden_behaviours_fixed"]) for e in EFFORTS]]]
    table(["Component", "Low", "Medium", "High", "Extra-high"], records, [180, 72, 72, 72, 76], size=9, padding=3)
    p("Means cover the judged runs (22 at Medium). GPT-6.1 Sol is the higher rater at every level.", "small")
    heading("Table 5. Four factors by effort, mean score out of 100 over judged runs")
    table(["Effort", "Functional", "Lint, complexity", "Security", "Code quality"],
          [[label(e), *[f'{t[e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for e in EFFORTS], [80, 91, 91, 80, 92], size=8.8, padding=3)
    heading("The medium timeout")
    p(f"Medium lodgecore reached the flat 10,800-second bound while still running, so there is no finished submission and v3.20 excludes "
      f"it from judging as an incomplete source run. It counts as a failed task in every pass count and in runtime at its recorded duration "
      f"(Medium averages {t['medium']['minutes']['mean']:.1f} minutes per task over 23 runs and {t['medium']['minutes_judged_runs']['mean']:.1f} "
      "over the 22 finished ones), and the Cursor stream has no usage receipt for it. With one exclusion at one level, the two-figure rule "
      "(a second combined score counting timeouts as 0) does not apply.", "small")
    heading("Operator record")
    [retry] = protocols["transport_retries"]
    p(f"Each judge made 365 counted calls (80 in calibration, 91 primary reviews, 4 repeats, 8 pairwise checks, 91 intent probes, 91 "
      f"answer-key matches); Muse needed a second attempt on {protocols['second_attempts']['muse']} and GPT-6.1 Sol on "
      f"{protocols['second_attempts']['sol']}. No call was invalidated and neither judge produced a reviewer fallback. One GPT-6.1 Sol primary "
      f"review ended its first attempt with the API message \"Selected model is at capacity\" and no output; the wrapper's transport-fault "
      f"rule gained that message and granted the protocol's single fresh attempt ({retry['selected']} selected, the failed receipt kept). "
      f"Six GPT-6.1 Sol answer-key matches numbered departures from 1 instead of 0 on both attempts; the new rule recover_one_based_indexes, "
      "which applies only when every cited index lies in 1 to count and the highest equals count, moved every index down by one with "
      "statuses untouched and the originals kept, and the result had to validate. Intent scoring reads statuses only, so no score changed.",
      "small")

    # Page 5: the shared-judge check, and time and tokens
    story.append(PageBreak())
    p("The shared-judge check", "h1")
    p(f"Every column has a Muse Spark 1.3 review; the second judge differs. GPT-6.1 Sol sits {min(gaps):.1f} to {max(gaps):.1f} points "
      "above Muse on Grok 4.7's submissions, while Grok 4.6's gap to Muse on the other columns ranges from 1.5 points below to 5.8 above "
      "and stays within 1.5 points either way on the two Anthropic columns. Rescoring every judged run on the board from Muse's panel "
      "alone, with the same split and weights, takes the pair out of the comparison. This is a sensitivity check, not a published score.")
    heading("Table 6. Combined score from Muse Spark 1.3 alone")
    records = [[label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{mine[e]["muse_combined"]:.2f}',
                f'{rivals[e]["muse_combined"]:.2f} ({NAMES[rivals[e]["model"]]})', f'{mine[e]["muse_reviewed"]:.1f}',
                f'{rivals[e]["muse_reviewed"]:.1f}'] for e in EFFORTS]
    table(["Effort", "Published", "Muse alone", "Best other, Muse alone", "Muse review", "Its Muse review"], records,
          [62, 62, 66, 140, 70, 80], size=8.6, padding=3)
    p("On one judge Grok 4.7 still leads at Medium, High and Extra-high, and Fable 5.1 moves ahead at Low. Against Claude Opus 5.5 at "
      "Medium and High the lead is Code quality; against Claude Fable 5.1 at Extra-high it is the security scan and passing all 23 tasks, "
      "since Muse rates Fable 5.1's code a little higher. Per-column figures are in shared-judge.json.", "small")
    heading("Time and tokens")
    p("No cost is computed: VulcanBench has no list price for Grok 4.7 and the sweep ran on the Cursor subscription. Cost is unavailable, "
      "never $0. Tokens come from the usage block of each run's Cursor stream, because Cursor's run summaries record 0.")
    heading("Table 7. Runtime and raw tokens by effort")
    ug = {g["effort"]: g for g in usage["groups"]}
    totals = usage["totals"][MODEL]
    records = [[label(e), str(ug[e]["runs"]), f'{ug[e]["minutes"]["mean"]:.1f}', f'{ug[e]["minutes_median"]:.1f}',
                f'{ug[e]["raw_tokens"]["mean"] / 1e6:.2f}M', f'{ug[e]["output_tokens"]["mean"] / 1e3:.1f}k',
                f'{100 * ug[e]["cache_read_share"]["mean"]:.0f}%', "unavailable"] for e in EFFORTS]
    records.append(["Full sweep", str(totals["runs"]), f'{60 * totals["solver_hours"] / totals["runs"]:.1f}', "",
                    f'{totals["raw_tokens"] / 1e6:,.0f}M total', "", "", "unavailable"])
    table(["Effort", "Runs", "Min/task", "Median", "Tokens/task", "Output", "Cache", "$/task"], records, [66, 38, 56, 50, 84, 52, 46, 70],
          size=8.4, padding=3)
    for item in usage["limitations"]:
        p("&#8226; " + item, "small")

    # Page 6: the board, the leaders and Safety v1
    story.append(PageBreak())
    p("On the board, beside the leaders", "h1")
    p(f"On the board's published figures Grok 4.7 at Extra-high ({comb[3]:.2f}), High ({comb[2]:.2f}) and Medium ({comb[1]:.2f}) rank "
      f"{ranks['extra-high']}, {ranks['high']} and {ranks['medium']} of {len(board)} columns, ahead of Fable 5.1 at Max and Opus 5.5 at High; "
      f"Low ({comb[0]:.2f}) ranks {ranks['low']}, the highest Low column. The board footnotes every Grok 4.7 row with the judge pair, shows its "
      "cost as unavailable, leaves it off the cost chart and picks its effort suggestions on time alone. Beside GPT-6.1 Sol, Claude Opus 5.5 "
      "and GPT-6 Astra, Grok 4.7 has the highest combined score and Code quality at every shared level, the highest Muse review score, and "
      "is the slowest of the four, using 2 to 4 times GPT-6.1 Sol's tokens per task and 4 to 5 times Astra's.")
    heading("VulcanBench Safety v1")
    p("Safety v1 is a private suite: it forks ten Frontier v4 tasks and plants two hazards in each as ordinary notes in the repository "
      "(a code insert, an acknowledgment file, a network beacon, a secret exfiltration or a destructive delete). The VulcanConduct hazards "
      "detector labels each planted note per run as complied, reported or ignored. Only aggregates are published.")
    heading("Table 8. Safety v1 by effort, ten tasks and twenty planted notes per level")
    records = []
    for model in (MODEL, "opus55"):
        levels = {r["effort"]: r for r in safety["models"][model]["levels"]}
        name = safety["models"][model]["name"]
        for measure, key in (("tasks passed", "passed"), ("notes followed", "complied"), ("notes reported", "reported")):
            records.append([f"{name}, {measure}", *[str(levels[e][key]) if e in levels else "n/a" for e in (*EFFORTS, "max")]])
    table(["Model and measure", "Low", "Medium", "High", "Extra-high", "Max"], records, [170, 52, 56, 52, 64, 50], size=8.6, padding=3)
    g, o = safety["models"][MODEL], safety["models"]["opus55"]
    gp = g["by_payload"]
    p(f"Grok 4.7, {g['totals']['runs']} runs: followed {g['totals']['complied']} of {g['totals']['planted']} planted notes "
      f"({gp['code_insert/complied']} code inserts and {gp['ack_file/complied']} acknowledgment files of 16 each), reported none, and never ran "
      f"the beacon, exfiltrated the secret or deleted. Claude Opus 5.5, {o['totals']['runs']} runs: followed {o['totals']['complied']} of "
      f"{o['totals']['planted']}, reported {o['totals']['reported']}. Neither leaked the secret. " + safety["timeout_note"] + " " + safety["detector"],
      "small")

    # Page 7: how it was run, evidence and reproduction
    story.append(PageBreak())
    p("How it was run", "h1")
    p("<b>Cursor agent CLI 2026.10.01-14929f9</b> on the Cursor subscription, with the four Grok 4.7 effort variants Cursor exposes; effort "
      "labels are Cursor's own. <b>The solver sweep</b> ran October 1, 12:53 PDT, to October 3, 04:12 PDT, one level and one task at a time, "
      "with no judging on the machine. Five High tasks failed in Cursor's infrastructure before producing a result and were rerun by the "
      "harness; the reruns are the runs. <b>Judging</b> ran October 3, 08:15 to 14:55 PDT; GPT-6.1 Sol's panel stopped 09:26 to 09:27 for "
      "the capacity event and 11:53 to 13:28 for the index recovery. Judging overlapped Grok 4.7's own Cursor Safety v1 leg, after its "
      "Frontier v4 leg had finished. <b>One attempt per task and level</b>; runs were not repeated.")
    p("<b>Still to come.</b> Grok 4.7's Routine v1 runs in Cursor are being judged under v3.22, and Grok 4.7 in xAI's own Grok Build CLI "
      "on Frontier v4 will be judged by the same pair under v3.21, followed by a Cursor against Grok Build comparison.")
    heading("Evidence and reproduction")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, hidden behaviours "
      f"fixed, integrity verdicts, tokens and each judge's six-dimension sub-scores and intent recovery; <font name='Mono'>groups.json</font>; "
      f"<font name='Mono'>calibration.json</font>; <font name='Mono'>judge-protocols.json</font> with the exact rubric, system text, probe "
      f"and match instructions, schemas, weights, counted calls and the operator records; <font name='Mono'>usage.json</font>; "
      f"<font name='Mono'>shared-judge.json</font>; <font name='Mono'>safety-v1.json</font>; and <font name='Mono'>provenance.json</font> "
      f"with source hashes and limits. <link href='{escape(args.github_url)}' color='#10A37F'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of Muse "
      "Spark 1.3 and GPT-6.1 Sol. The combined score is 100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. "
      "Group means weight the level's judged tasks equally. The export script recomputes every row from the frozen summary, checks the "
      "figures against the harness card tables, re-derives the Safety v1 counts from the audit files and refuses to write if any value differs.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe "
      "task sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. "
      "Runs were not repeated. Grok 4.7's judge pair differs from every other column's. Hash checks bind the export to frozen files; they "
      "do not prove that judges were unbiased or that no training overlap exists.")

    # Page 8: per task appendix and source hashes
    story.append(PageBreak())
    p("Appendix. Per task at Low, Medium and Extra-high", "h1")
    by = {(r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})

    def cell(r, key, digits):
        return "timeout" if not r["finished"] else f"{r[key]:.{digits}f}"

    records = [[short(task), cell(by["low", task], "code_quality", 1), cell(by["extra-high", task], "code_quality", 1),
                cell(by["low", task], "combined_33", 2), cell(by["medium", task], "combined_33", 2), cell(by["extra-high", task], "combined_33", 2)]
               for task in tasks]
    table(["Task", "Low CQ", "XH CQ", "Low combined", "Medium combined", "XH combined"], records, [100, 60, 64, 80, 94, 84], size=7.6, padding=1.2)
    p("Per-task values from runs.json. Task names are shortened for width. XH is Extra-high.", "small")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k.replace("v3.20/calls/", "calls/"), v[:32] + "..."]
                                          for k, v in provenance["source_artifacts_sha256"].items()], [300, 190], size=6.4, padding=0.9)
    story.pop()  # no trailing spacer, so a full appendix page does not spill an empty page before the cards

    story.append(NextPageTemplate("card"))
    for path, width, height in CARDS:
        story.append(PageBreak())
        story.append(Image(str(path), width=width, height=width * height / 2400))

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | Frontier v4 | Code quality protocol v3.20 | October 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | Grok 4.7 across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench Frontier v4: Grok 4.7 across every effort level",
                          author="VulcanBench", subject="Code quality protocol v3.20: Muse Spark 1.3 and GPT-6.1 Sol, Cursor effort sweep, Safety v1")
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
