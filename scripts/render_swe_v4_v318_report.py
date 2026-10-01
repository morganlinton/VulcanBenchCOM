"""Render the technical PDF for the v3.18 GPT-6.1 Sol effort sweep.

Reads only the public evidence bundles (this one, GPT-6 Sol's and GPT-5.6
Sol's for the comparison, and the Frontier v4 board) and the committed cards;
no model calls. Requires reportlab and the VulcanBench rankings-chart font
folder.

    python3 scripts/render_swe_v4_v318_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>
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
DATA = ROOT / "assets/data/swe-v4-gpt61-sol-v318"
SOL6 = ROOT / "assets/data/swe-v4-gpt6-sol-v317"
SOL56 = ROOT / "assets/data/swe-v4-sol-v37"
BOARD = ROOT / "assets/data/swe-v4-board.json"
CARD = ROOT / "assets/cards/swe-v4-gpt61-sol-v318.png"
ECONOMICS_CARD = ROOT / "assets/cards/swe-v4-gpt61-sol-v318-economics.png"
FAMILY_CARD = ROOT / "assets/cards/swe-v4-sol-family-combined.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-gpt61-sol-v318-report.pdf"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccc4")
PAGES = 11


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
    t, et = load(DATA, "gpt61sol")
    s6, e6 = load(SOL6, "gpt6sol")
    s56, e56 = load(SOL56, "sol")
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
    totals = econ["totals"]["gpt61sol"]
    one_panel = [r for r in runs if r["judged"] != "published"]
    assert [(r["effort"], short(r["task"])) for r in one_panel] == [("medium", "paddockcore")]
    [single] = one_panel
    [finding] = protocols["one_panel"]
    [recovery] = protocols["operator_recoveries"]
    assert (recovery["effort"], short(recovery["task"])) == ("high", "codeccore")
    rebuilds = protocols["evidence_rebuilds"]
    assert len(rebuilds) == 3
    best = max(EFFORTS, key=lambda e: t[e]["combined_33"]["mean"])
    ranks = {r["effort"]: r["rank"] for r in board if r["key"] == "gpt61sol"}

    # Page 1: abstract and headline table
    p("GPT-6.1 Sol across every effort level", "h1")
    p("VulcanBench Frontier v4 | Code quality protocol v3.18 | October 2026", "small")
    heading("Abstract")
    p(f"GPT-6.1 Sol ran the 23-task VulcanBench Frontier v4 suite through Codex CLI 0.159.0 on a ChatGPT Pro subscription on September 29 "
      f"to 30, 2026, once per task at each of five effort levels, Low to Max, 115 runs in all. Code quality carries 33% of the combined score "
      f"and is judged for a named human reader by Muse Spark 1.3 (Meta) and Grok 4.6 (xAI) under the same frozen protocol as the other "
      f"Frontier v4 reports, with a ground-truth intent-recovery probe. The combined score is {comb[0]:.2f} at Low, {comb[1]:.2f} at Medium, "
      f"{comb[2]:.2f} at High, {comb[3]:.2f} at Extra-high and {comb[4]:.2f} at Max, a flat curve. GPT-6.1 Sol passes "
      f"{t['low']['passed_all_runs']}, {t['medium']['passed_all_runs']}, {t['high']['passed_all_runs']}, {t['extra-high']['passed_all_runs']} "
      f"and {t['max']['passed_all_runs']} of 23 tasks from Low to Max and fixes {t['low']['hidden_behaviours_fixed']}, "
      f"{t['medium']['hidden_behaviours_fixed']} and then all 231 of the 231 hidden behaviours tested. Code quality runs from {min(cq):.2f} to "
      f"{max(cq):.2f}. Cost per task runs from ${et['low']['usd']['mean']:.2f} at Low to ${et['max']['usd']['mean']:.2f} at Max; the whole "
      f"sweep prices at ${totals['usd']:.2f}, ${totals['usd'] / totals['runs']:.2f} per task.")
    p("Every run finished inside the flat 3-hour task bound and every run carries a published Code quality score, so every cell is judged "
      "on 23 runs. One run, Medium paddockcore, is scored from Muse Spark 1.3 alone because Grok 4.6's review of it had no valid response. "
      "From High up GPT-6.1 Sol passes every hidden test, so Frontier v4 no longer separates its top levels on correctness. It leads GPT-6 Sol "
      "and GPT-5.6 Sol at every level on combined score, tasks passed and cost.")
    heading("Table 1. Combined score, Code quality, runtime and tasks passed by effort")
    records = [[label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{t[e]["combined_33"]["se"]:.2f}',
                f'{t[e]["combined_20_profile"]["mean"]:.2f}', f'{t[e]["code_quality"]["mean"]:.2f}', f'{t[e]["minutes"]["mean"]:.1f}',
                f'{t[e]["n"]}', f'{t[e]["passed_all_runs"]}/23'] for e in EFFORTS]
    table(["Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Judged", "Passed"],
          records, [62, 74, 40, 72, 66, 56, 50, 48], size=8.8)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality. Combined (20%) applies the prior "
      "50/15/15/20 profile to the same Code quality scores. SE is one sample standard error across the cell's tasks, not judge uncertainty "
      "or a significance test. Runtime is solver wall-clock per task; judging is excluded.", "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p("Protocol v3.18 is the same protocol applied to this population. Nothing in the rubric, controls, quirk keys, gates, repeats, seed, "
      "weights or judges changed from v3.7; both judges retook the calibration exam under v3.18 before any counted call. The population froze "
      "on September 30 with 115 rows, none missing and none excluded. The frozen summary publishes a submission from the panels with a valid "
      "review; that rule applied once, described under Results in detail.")
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
    p("<b>Reviewed panel, 24 points.</b> The six-dimension rubric above, averaged across the judges with a valid review. "
      "<b>Intent recovery, 9 points.</b> Every task in this suite is a rewrite of a retired binary whose real behaviour departs "
      "from its written specification in documented ways. The judge sees only the specification and the code, never the issue "
      "text, and lists where the code departs from the specification; a separate call matches that list against the frozen "
      "answer key. The denominator is the quirks the submission actually passed tests for, so a functional failure is not "
      "punished twice; a submission that passed none would have no intent-recovery score and its Code quality would be the reviewed "
      "score alone, which no GPT-6.1 Sol run needed. "
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
    p("Both judges passed every gate with no allowance used, as under v3.17.")
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

    # Page 4: results in detail, the one-panel row and the operator record
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
    p("Means cover 23 runs per cell; Grok 4.6's Medium mean covers the 22 runs it reviewed validly. Grok is the higher rater at every level.",
      "small")
    heading("Table 5. Four factors by effort, mean score out of 100")
    table(["Effort", "Functional", "Lint, complexity", "Security", "Code quality"],
          [[label(e), *[f'{t[e][k]["mean"]:.2f}' for k in ("functional", "automated_quality", "security", "code_quality")]]
           for e in EFFORTS], [80, 91, 91, 80, 92], size=8.8, padding=3)
    heading("The one-panel Medium row")
    p(f"On paddockcore at Medium, Grok 4.6's primary review had no valid response after the protocol's single retry: both attempts quoted "
      f"<font name='Mono'>{escape(finding['attempt_2_excerpt'])}</font> as evidence where the code reads "
      f"<font name='Mono'>{escape(finding['code_reads'])}</font>, a changed token that no recovery rule accepts. Following the owner's v3.14 "
      f"decision on the same case, the rule {finding['rule']} marked the call invalid, and the frozen summary scores the run from Muse Spark "
      f"1.3 alone: reviewed score {single['reviewed_score']:.2f}, intent recovery {single['intent_recovery']:.2f}, Code quality "
      f"{single['code_quality']:.2f}, combined {single['combined_33']:.2f}. The run passed its tests. Grok's probe answer for that run is not "
      "used and not published. The harness score card's intent-recovery row at Medium (78.4) averages both judges' probes on that run; the "
      f"published Medium figure is {t['medium']['intent_recovery']['mean']:.2f}.", "small")
    heading("Operator record")
    p(f"On high codeccore, Muse Spark 1.3's first probe attempt wrote an invalid JSON escape and its second quoted a code line with the string "
      f"escapes decoded into control characters. By owner decision the new rule {recovery['rule']} respelled that excerpt with the source's "
      f"escapes, after which it had to be verbatim; attempt {recovery['source_attempt']} passed every other check and was selected. Three runs "
      "(low payrollcore, medium lodgecore and low cellarcore) add test fixtures the saved text patch cannot re-apply, so their judging "
      "evidence was rebuilt from the saved workspace's index diff after checking it against the run's patch; only fixtures differ. Each judge "
      "made 440 counted calls (80 in calibration, 115 primary reviews, 5 repeats, 10 pairwise checks, 115 intent probes, 115 answer-key "
      "matches); Muse needed a second attempt on eight and Grok on nine. Neither judge produced a reviewer fallback.", "small")

    # Page 5: cost and tokens
    story.append(PageBreak())
    p("Cost and tokens across effort levels", "h1")
    p("All 115 runs priced from their Codex receipts at list API rates, cache-aware, solver inference only, judging excluded. GPT-6.1 Sol ran "
      "on a ChatGPT Pro subscription, so these are API-equivalent estimates rather than bills. Low is the cheapest and fastest level. Medium "
      "uses the most tokens per task and High the fewest, so High costs less than Medium; Max is the most expensive level.")
    heading("Table 6. API-equivalent cost, raw tokens and runtime by effort")
    records = [[label(e), str(et[e]["n"]), f'${et[e]["usd"]["mean"]:.2f}', f'${et[e]["usd_total"]:.2f}',
                f'{et[e]["raw_tokens"]["mean"] / 1e6:.2f}M', f'{et[e]["minutes"]["mean"]:.1f}'] for e in EFFORTS]
    records.append(["Full sweep", str(totals["runs"]), f'${totals["usd"] / totals["runs"]:.2f}', f'${totals["usd"]:,.2f}',
                    f'{totals["raw_tokens"] / 1e6:,.0f}M', f'{totals["solver_hours"]:.1f} h'])
    table(["Effort", "Runs", "$/task", "Level total", "Tokens/task", "Min/task"], records, [80, 50, 70, 84, 84, 70], size=8.6, padding=3)
    rates = econ["rates_per_million"]["gpt61sol"]
    p(f"Rates checked {econ['pricing_verified']}: GPT-6.1 Sol at ${rates['input']:.2f} input, ${rates['cached_input']:.2f} cached input and "
      f"${rates['output']:.2f} output per million tokens. Codex receipts report input, cached input, output and reasoning tokens per run, so "
      "cached input is billed at the cache-read rate and the rest at the standard rate. The sweep stamped each run at these rates at run time; "
      "the export recomputed every run from its receipt and matched every stamp. Tokens are raw solver totals including cache reads.", "small")
    heading("Limitations recorded with the estimates")
    for item in econ["limitations"]:
        p("&#8226; " + item, "small")

    # Page 6: three generations of Sol, the board, and the correctness ceiling
    story.append(PageBreak())
    p("Three generations of Sol", "h1")
    p("GPT-6 Sol and GPT-5.6 Sol ran the same 23 tasks through Codex in September and were judged by the same judges under v3.17 and v3.7 "
      "(GPT-6 Sol at Medium and GPT-5.6 Sol at Max judged on 22 of 23). GPT-6.1 Sol leads both at every effort level on combined score, tasks "
      "passed and cost per task, and its Code quality is higher at every level.")
    heading("Table 7. GPT-6.1 Sol, GPT-6 Sol and GPT-5.6 Sol by effort")
    records = []
    for e in EFFORTS:
        records.append([label(e), f'{t[e]["combined_33"]["mean"]:.2f} / {s6[e]["combined_33"]["mean"]:.2f} / {s56[e]["combined_33"]["mean"]:.2f}',
                        f'{t[e]["passed_all_runs"]} / {s6[e]["passed_all_runs"]} / {s56[e]["passed_all_runs"]}',
                        f'${et[e]["usd"]["mean"]:.2f} / ${e6[e]["usd"]["mean"]:.2f} / ${e56[e]["usd"]["mean"]:.2f}',
                        f'{et[e]["minutes"]["mean"]:.1f} / {e6[e]["minutes"]["mean"]:.1f} / {e56[e]["minutes"]["mean"]:.1f}'])
    table(["Effort", "Combined", "Passed of 23", "$/task", "Min/task"], records, [66, 130, 80, 120, 94], size=8.4, padding=3)
    p("Each cell reads GPT-6.1 Sol / GPT-6 Sol / GPT-5.6 Sol. Combined scores are over judged runs; pass counts, cost and minutes cover all 23 "
      "runs per cell. Each model is priced at its own list rates. The sweeps ran on different Codex CLI versions (0.159.0, 0.155.0 and "
      "0.153.4). GPT-6.1 Sol is slower than GPT-5.6 Sol at Extra-high and Max.", "small")
    heading("On the Frontier v4 board")
    leaders = [r for r in board if r["rank"] < ranks[best]]
    p(f"GPT-6.1 Sol's best level, {label(best)} at {t[best]['combined_33']['mean']:.2f}, ranks {ranks[best]} of the board's {len(board)} "
      f"columns, behind {len(leaders)} columns of Fable 5.1, Opus 5.5, GPT-6 Astra and GPT-5.6 Terra. Fable 5.1 and GPT-6 Astra at Max also pass all 23 tasks, and Opus "
      "5.5 at High all 22 of its judged runs, so the gap is in the judged and scanned factors, mainly Code quality (74.99 against 82.43 for Fable 5.1 at Max and 76.26 for GPT-6 Astra at Max), "
      "and against Opus 5.5 also its security score. Of the 16 columns scoring 88 or more, GPT-6.1 Sol's three are the cheapest per task.")
    heading("Perfect hidden tests from High up")
    p("From High to Max every task passes every hidden test, so Frontier v4 no longer separates GPT-6.1 Sol's top levels on correctness; Code "
      "quality, the lint and security scans, and cost still do. The integrity audit is clean on all 115 runs (no web access, no benchmark-data "
      "or answer-key paths), and OpenAI gives GPT-6.1 Sol a knowledge cutoff of April 30, 2026, before the tasks were built in August 2026. The "
      "suite charter's saturation-pruning rule calls for re-gating the suite when a new frontier generation lands; that is a planned follow-up.")

    # Page 7: how it was run, evidence and reproduction
    story.append(PageBreak())
    p("How it was run", "h1")
    p("<b>Codex CLI 0.159.0.</b> Codex 0.155.0, 0.157.0 and 0.158.0 refuse GPT-6.1 Sol on a ChatGPT account before any work; 0.159.0 is the "
      "first release that serves it and runs from its own install for this column only. <b>The sweep overlapped another model's judging.</b> "
      "The solver sweep ran September 29, 19:18 PDT, to September 30, 17:21 PDT; at the owner's request its first 11.5 hours, to September 30, "
      "06:51 PDT, ran alongside GPT-6 Sol's v3.17 judging on the same machine, covering every Low, Medium and High run and the first five "
      "Extra-high runs, which matters for the wall-clock figures. <b>Judging</b> ran September 30, 20:58 PDT, to October 1, 06:01 PDT, and "
      "06:04 to 12:52 PDT after the Grok finding on page 4, with no solver sweep running. <b>One attempt per task and level</b>; no run was "
      "retried, and effort labels are Codex's own.")
    heading("Evidence and reproduction")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, hidden behaviours "
      f"fixed, integrity verdicts and each scored judge's six-dimension sub-scores and intent recovery; <font name='Mono'>groups.json</font>; "
      f"<font name='Mono'>calibration.json</font> with every gate value and control mean; <font name='Mono'>judge-protocols.json</font> with "
      f"the exact rubric, system text, probe and match instructions, schemas, weights, the one-panel row, the escaping recovery and the three "
      f"evidence rebuilds; <font name='Mono'>economics.json</font> with cost and token aggregates, the rate table and pricing limitations; and "
      f"<font name='Mono'>provenance.json</font> with source hashes and limits. "
      f"<link href='{escape(args.github_url)}' color='#10A37F'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of the judges "
      "with a valid review (both, except Muse Spark 1.3 alone on Medium paddockcore). The combined score is "
      "100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. Group means weight the cell's tasks equally. "
      "The export script recomputes every row from the frozen summary, re-prices every run from its receipt, asserts that the one invalid "
      "judge call is the Grok review of Medium paddockcore, checks the figures against the harness card tables, and refuses to write if any "
      "value differs.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe "
      "task sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. "
      "Runs were not repeated. Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training "
      "overlap exists.")

    # Page 8: source hashes and per task appendix
    story.append(PageBreak())
    p("Appendix. Per task at Low, Medium and Max", "h1")
    by = {(r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})

    def cell(r, key, digits):
        return f"{r[key]:.{digits}f}" + ("*" if r["judged"] != "published" else "")

    records = [[short(task), cell(by["low", task], "code_quality", 1), cell(by["max", task], "code_quality", 1),
                cell(by["low", task], "combined_33", 2), cell(by["medium", task], "combined_33", 2), cell(by["max", task], "combined_33", 2)]
               for task in tasks]
    table(["Task", "Low CQ", "Max CQ", "Low combined", "Medium combined", "Max combined"], records, [100, 60, 64, 80, 94, 84], size=7.8, padding=1.6)
    p("Per-task values from runs.json. Task names are shortened for width. * scored from Muse Spark 1.3 alone, as described on page 4.", "small")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k.replace("v3.18/calls/", "calls/").replace("v3.18/reconstruction/", "reconstruction/"), v[:32] + "..."]
                                          for k, v in provenance["source_artifacts_sha256"].items()], [300, 190], size=6.8, padding=1.3)
    story.pop()  # no trailing spacer, so a full appendix page does not spill an empty page before the cards

    story.extend([NextPageTemplate("card"), PageBreak()])
    story.append(Image(str(CARD), width=620, height=620 * 1867 / 2400))
    story.append(PageBreak())
    story.append(Image(str(ECONOMICS_CARD), width=660, height=660 * 1725 / 2400))
    story.append(PageBreak())
    story.append(Image(str(FAMILY_CARD), width=500, height=500 * 2269 / 2400))

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | Frontier v4 | Code quality protocol v3.18 | October 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | GPT-6.1 Sol across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench Frontier v4: GPT-6.1 Sol across every effort level",
                          author="VulcanBench", subject="Code quality protocol v3.18: neutral judges, 33% weight, Codex effort sweep, three generations of Sol")
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
