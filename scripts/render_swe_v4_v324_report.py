"""Render the technical PDF for the v3.24 Claude Haiku 5.5 effort sweep.

Reads only the public evidence bundles (this one, Claude Sonnet 5.5's and
GPT-6.1 Sol's for the comparison, and the Frontier v4 board) and the committed
cards; no model calls. Every number is computed from the bundles at render
time. Requires reportlab and the VulcanBench rankings-chart font folder.

    python3 scripts/render_swe_v4_v324_report.py --fonts ../VulcanBench/scripts/rankings-chart --github-url <tree url>

PAGES is the expected page count (eight text pages and two card pages); if the
final text runs longer, adjust it here and in verify_swe_v4_v324_pdf.py.
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
DATA = ROOT / "assets/data/swe-v4-haiku55-v324"
SONNET = ROOT / "assets/data/swe-v4-sonnet55-v323"
SOL = ROOT / "assets/data/swe-v4-gpt61-sol-v318"
BOARD = ROOT / "assets/data/swe-v4-board.json"
CARD = ROOT / "assets/cards/swe-v4-haiku55-v324.png"
COMPARE_CARD = ROOT / "assets/cards/swe-v4-haiku55-vs-sonnet55.png"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-haiku55-v324-report.pdf"
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
    t, et = load(DATA, "haiku55")
    s, es = load(SONNET, "sonnet55")
    o, eo = load(SOL, "gpt61sol")
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
    totals = econ["totals"]["haiku55"]
    assert not any(r["solver_fallback"] for r in runs)
    assert all(set(r["replies_by_model"]) == {"claude-haiku-5-5"} for r in runs)
    unscored = [r for r in runs if r["judged"] != "published"]
    assert sorted((r["effort"], short(r["task"])) for r in unscored) == [("extra-high", "paddockcore"), ("max", "codeccore"), ("max", "paddockcore"),
                                                                          ("medium", "paddockcore")]
    best = max(EFFORTS, key=lambda e: t[e]["combined_33"]["mean"])
    ranks = {r["effort"]: r["rank"] for r in board if r["key"] == "haiku55"}
    passed = [t[e]["passed_all_runs"] for e in EFFORTS]
    judged = [t[e]["n"] for e in EFFORTS]
    pins = protocols["judge_pins"]
    usd = [et[e]["usd"]["mean"] for e in EFFORTS]

    # Page 1: abstract and headline table
    p("Claude Haiku 5.5 across every effort level", "h1")
    p("VulcanBench Frontier v4 | Code quality protocol v3.24 | October 2026", "small")
    heading("Abstract")
    p(f"Claude Haiku 5.5 ran the 23-task VulcanBench Frontier v4 suite through Claude Code 2.1.293 to 2.1.296 on a Claude Max "
      f"subscription from October 8 to 11, 2026, once per task at each of five effort levels, Low to Max, 115 runs in all, one task at a "
      f"time on the owner's Mac. Code quality carries 33% of the combined score and is judged for a named human reader by Muse Spark 1.3 "
      f"(Meta) and Grok 4.6 (xAI), both from labs other than Anthropic, under the same rubric, controls and gates as the other Frontier v4 "
      f"reports, with a ground-truth intent-recovery probe. The combined score is {comb[0]:.2f} at Low, {comb[1]:.2f} at Medium, "
      f"{comb[2]:.2f} at High, {comb[3]:.2f} at Extra-high and {comb[4]:.2f} at Max, over {', '.join(map(str, judged[:4]))} and {judged[4]} "
      f"judged runs. Haiku 5.5 passes {', '.join(map(str, passed[:4]))} and {passed[4]} of 23 tasks from Low to Max. Code quality runs from "
      f"{min(cq):.2f} to {max(cq):.2f}. Cost per task, as Claude Code reports it, runs from ${min(usd):.2f} to ${max(usd):.2f}; the whole "
      f"sweep comes to ${totals['usd']:.2f}, between a floor of ${totals['usd_floor']:.2f} and a ceiling of ${totals['usd_ceiling']:.2f} for "
      f"Haiku's two price tiers.")
    p("Every run finished inside the flat 3-hour task bound. Four runs carry no Code quality score and all four count in tasks passed, time "
      "and cost: three that a safety classifier stopped with an empty patch, and one whose judge probe had no valid answer. Claude Code's "
      "refusal fallback was on and no run used it. The sweep paused twice between tasks, which leaves run timings intact.")
    heading("Table 1. Combined score, Code quality, runtime and tasks passed by effort")
    records = [[label(e), f'{t[e]["combined_33"]["mean"]:.2f}', f'{t[e]["combined_33"]["se"]:.2f}',
                f'{t[e]["combined_20_profile"]["mean"]:.2f}', f'{t[e]["code_quality"]["mean"]:.2f}', f'{t[e]["minutes"]["mean"]:.1f}',
                f'{t[e]["n"]}', f'{t[e]["passed_all_runs"]}/23'] for e in EFFORTS]
    table(["Effort", "Combined (33%)", "SE", "Combined (20%)", "Code quality", "Min/task", "Judged", "Passed"],
          records, [62, 74, 40, 72, 66, 56, 50, 48], size=8.8)
    p("Combined (33%) = 0.50 functional + 0.085 lint and complexity + 0.085 security + 0.33 Code quality, over the judged runs. Combined "
      "(20%) applies the prior 50/15/15/20 profile to the same Code quality scores. SE is one sample standard error across the cell's judged "
      "tasks, not judge uncertainty or a significance test. Runtime is solver wall-clock per task over every run; judging is excluded. "
      "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.", "small")

    # Page 2: the protocol
    story.append(PageBreak())
    p("The Code quality protocol", "h1")
    p("Two failure modes motivated the reviewed score. The lint and complexity metric rewards compression: the maintainability index "
      "carries a lines-of-code term and per-function complexity stays low when each dense line does something different, so five "
      "statements on a line with names like x and k can outscore the same logic written for a person. And a large model reading "
      "compressed code pays almost nothing to parse it; when a frontier model was calibrated as a readability judge, it rated a squashed "
      "six-line function the same as its formatted copy. Since September 7, 2026 Code quality carries 33% of the combined score and lint "
      "and complexity and security carry 8.5% each. The prior profile is reported beside the new one on every table.")
    p("Protocol v3.24 is the v3.23 protocol applied to this population. Nothing in the rubric, controls, quirk keys, gates, repeats, seed, "
      "weights or judge settings changed; both judges retook the calibration exam under v3.24 before any counted call. What changed is how "
      "the Cursor CLI that carries Grok 4.6 is pinned, described on the next page. The population froze on October 11 with 112 judgeable "
      "rows, three runs excluded and none missing.")
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
      "punished twice; no judged Haiku 5.5 run needed the rule for a submission that passed none. "
      "<b>Measured maintenance, designed for 12 points, not yet built.</b> Until it exists the pre-registered split above is in force.")

    # Page 3: judges, settings and versions, and calibration
    story.append(PageBreak())
    p("Judges and calibration", "h1")
    p("The scored panel is Muse Spark 1.3 through the Muse CLI on its Standard tier, which does not train on prompts, and Grok 4.6 "
      "through the Cursor CLI at medium effort. Both are from labs other than Anthropic, so neither grades a relative of Haiku 5.5. Every "
      "session is fresh, tools are disabled, the workspace is empty, model identity is checked per call from the CLI's own records, and "
      "solver labels are withheld.")
    heading("Judge settings and versions")
    originals = {v: x["sha256"] for v, x in pins["settings_sources"].items()}
    cursor = pins["cursor_version"]
    p(f"The judge settings are read from the original v3.3 and v3.4 protocol files, recovered from the owner's private backup, whose "
      f"sha256 equal the published values (v3.3 {originals['v3.3'][:8]}..., v3.4 {originals['v3.4'][:8]}...). Muse Spark 1.3 ran the same "
      f"binary as every earlier round (sha256 {pins['muse_binary_sha256'][:12]}..., a match). Grok 4.6 ran through Cursor CLI "
      f"{cursor['version']}, pinned by version for the whole round: the round judged through that version's own launcher and re-checked a "
      f"digest of its version directory ({cursor['digest'][:12]}...) before every stage, so the CLI could not change mid-round. It is the "
      f"same Cursor CLI that judged Claude Sonnet 5.5 under v3.23. The Grok model id is the same as in every round; Cursor reports its "
      f"display name as Grok 4.6 Medium where the frozen settings say Cursor Grok 4.6 Medium, a rename the judging wrapper accepts and "
      f"recorded {protocols['display_name']['accepted_renames_recorded']} times in this round.")
    heading("The calibration exam")
    p("Before scoring a single submission each judge reviews ten held-out programs implementing one ledger specification, from clear "
      "to compressed, misleadingly commented, narrated, needlessly abstracted and carrying an embedded instruction to give full marks, "
      "five times each in a seeded order. Twenty gates fixed in advance check that the judge sees each construct; a judge may miss at "
      "most one gate by at most half a point.")
    heading("Table 2. Calibration verdicts")
    table(["Judge", "Protocol", "Calls", "Result", "Allowance", "Failing gates"], [
        [name, protocols["protocol_ids"][j], str(calibration[j]["call_count"]), "passed" if calibration[j]["passed"] else "failed",
         "used" if calibration[j]["allowance_used"] else "not used", ", ".join(calibration[j]["failing_gates"]) or "none"]
        for j, name in (("muse", "Muse Spark 1.3"), ("grok", "Grok 4.6"))], [64, 138, 30, 40, 56, 179], size=8.2, padding=3, wrap=True)
    p("Both judges passed every gate with no allowance used. Under v3.23, for Sonnet 5.5, each needed the one-gate allowance.")
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

    # Page 4: results in detail and the runs without a score
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
    p("Means cover the judged runs per cell (n in Table 1); hidden behaviours cover all 23 runs.", "small")
    heading("Four runs without a Code quality score")
    p("<b>Three safety-classifier stops.</b> On paddockcore at Medium, Extra-high and Max a safety classifier stopped the session while "
      "Haiku 5.5 probed the legacy binary, and the run ended with an empty patch, so there is no code to review. As for Claude Opus 5.5's "
      "High depotcore, these runs are excluded from judging, count as failed tasks, and are priced and timed. The combined score at those "
      "levels is over the judged runs and does not include these failures; tasks passed does. <b>Max codeccore is unpublished.</b> "
      "Grok 4.6's intent probe gave no valid answer after the single retry: attempt 1 quoted a code line absent from the run, which no "
      "recovery rule accepts, and attempt 2 was not valid JSON. The frozen protocol therefore publishes no Code quality score for the run, "
      "as for the same task under v3.7 and v3.17. The run passed its tests and counts as passed.", "small")
    heading("Operator record and calls")
    calls = protocols["counted_calls"]
    p(f"Each judge made {calls['muse']['calibration']} calibration calls, {calls['muse']['primary']} primary reviews, {calls['muse']['repeat']} "
      f"repeats, {calls['muse']['pairwise']} pairwise checks and {calls['muse']['probe']} intent probes; Muse made {calls['muse']['match']} "
      f"answer-key matches and Grok {calls['grok']['match']}. Muse needed a second attempt on {protocols['second_attempts']['muse']} calls and "
      f"Grok on {protocols['second_attempts']['grok']}. One Grok review was recovered by the standing recover_excerpts rule: on Extra-high "
      "vaultcore both attempts failed only because a quoted line is hard-wrapped in the source, so attempt 1 was selected with the quote "
      "re-wrapped to the source's line breaks, scores untouched. Neither judge produced a reviewer fallback. Claude Code's refusal fallback "
      "was on and no run used it: every reply came from claude-haiku-5-5.", "small")

    # Page 5: cost and the price tiers
    story.append(PageBreak())
    p("Cost, tokens and the price tiers", "h1")
    up = econ["rates_per_million"]["claude-haiku-5-5"]["up_to_100k"]
    p(f"Haiku 5.5 has two list prices per token. Anthropic's pricing page, checked {econ['pricing_verified']}, charges ${up['input']:.2f} "
      f"input, ${up['cache_write_5m']:.3f} for 5-minute cache writes, ${up['cache_hit']:.2f} for cache reads and ${up['output']:.2f} output per "
      f"million tokens for prompts up to 100,000 tokens, and five times as much on every line for longer prompts. Claude Code's receipts "
      "hold cumulative session usage, not the size of each request, so each run carries Claude Code's own list-price total (the published "
      "cost) beside a floor, every request at the standard tier, and a ceiling, every request at the higher one. Haiku 5.5 ran on a Claude "
      "Max subscription, so all three are API-equivalent estimates rather than bills; judging is excluded.")
    heading("Table 5. Cost with floor and ceiling, raw tokens and runtime by effort")
    records = [[label(e), str(et[e]["n"]), f'${et[e]["usd"]["mean"]:.2f}', f'${et[e]["usd"]["se"]:.2f}', f'${et[e]["usd_floor"]["mean"]:.2f}',
                f'${et[e]["usd_ceiling"]["mean"]:.2f}', f'${et[e]["usd_total"]:.2f}', f'{et[e]["raw_tokens"]["mean"] / 1e6:.2f}M',
                f'{et[e]["minutes"]["mean"]:.1f}'] for e in EFFORTS]
    records.append(["Full sweep", str(totals["runs"]), f'${totals["usd"] / totals["runs"]:.2f}', "", f'${totals["usd_floor"] / totals["runs"]:.2f}',
                    f'${totals["usd_ceiling"] / totals["runs"]:.2f}', f'${totals["usd"]:,.2f}', f'{totals["raw_tokens"] / 1e6:,.0f}M',
                    f'{totals["solver_hours"]:.1f} h'])
    table(["Effort", "Runs", "$/task", "SE", "Floor", "Ceiling", "Total", "Tokens/task", "Min/task"], records,
          [62, 34, 50, 42, 46, 50, 60, 64, 52], size=8.2, padding=3)
    heading("Limitations recorded with the estimates")
    for item in econ["limitations"]:
        p("&#8226; " + item, "small")

    # Page 6: beside Sonnet 5.5 and GPT-6.1 Sol, and the board
    story.append(PageBreak())
    p("Beside Claude Sonnet 5.5 and GPT-6.1 Sol", "h1")
    p("Sonnet 5.5 and GPT-6.1 Sol ran the same 23 tasks, judged by the same judges under v3.23 and v3.18; their numbers are the published "
      "rows and nothing was re-judged. The site's comparison page adds GPT-6 Luna. Harnesses (Claude Code 2.1.293 to 2.1.296, Claude Code "
      "2.1.291 to 2.1.293, Codex 0.159.0) and cost bases (Claude Code's own total for the Claude columns, API-equivalent from the token ledger "
      "for GPT-6.1 Sol) differ, so small gaps are confounded.")
    heading("Table 6. Haiku 5.5, Sonnet 5.5 and GPT-6.1 Sol by effort")
    records = [[label(e), f'{t[e]["combined_33"]["mean"]:.2f} / {s[e]["combined_33"]["mean"]:.2f} / {o[e]["combined_33"]["mean"]:.2f}',
                f'{t[e]["passed_all_runs"]} / {s[e]["passed_all_runs"]} / {o[e]["passed_all_runs"]}',
                f'{t[e]["code_quality"]["mean"]:.1f} / {s[e]["code_quality"]["mean"]:.1f} / {o[e]["code_quality"]["mean"]:.1f}',
                f'${et[e]["usd"]["mean"]:.2f} / ${es[e]["usd"]["mean"]:.2f} / ${eo[e]["usd"]["mean"]:.2f}',
                f'{et[e]["minutes"]["mean"]:.1f} / {es[e]["minutes"]["mean"]:.1f} / {eo[e]["minutes"]["mean"]:.1f}'] for e in EFFORTS]
    table(["Effort", "Combined", "Passed of 23", "Code quality", "$/task", "Min/task"], records, [56, 116, 62, 92, 110, 74], size=8.0, padding=3)
    p("Each cell reads Haiku 5.5 / Sonnet 5.5 / GPT-6.1 Sol. Combined scores and Code quality are over judged runs; pass counts, cost and "
      "minutes cover all 23 runs per cell.", "small")
    gap = t["max"]["combined_33"]["mean"] - s["max"]["combined_33"]["mean"]
    assert abs(gap) < t["max"]["combined_33"]["se"]
    p(f"At Max Haiku 5.5 and Sonnet 5.5 are effectively tied ({t['max']['combined_33']['mean']:.2f} against {s['max']['combined_33']['mean']:.2f}, "
      f"a {gap:.2f}-point gap far inside the error), with Haiku {es['max']['usd']['mean'] / et['max']['usd']['mean']:.1f} times cheaper per task "
      "there. Below Max Haiku rates higher on Code quality but passes fewer tasks than Sonnet 5.5 from Low to High. GPT-6.1 Sol solves more "
      "tasks than Haiku 5.5 at every level for less money, and Haiku scores about 3 points higher at Extra-high and Max.")
    heading("On the Frontier v4 board")
    above = sorted({r["model"] for r in board if r["rank"] < ranks[best]})
    assert above == ["Grok 4.7"], above
    same_panel = [r for r in board if r["key"] not in ("haiku55", "grok47cursor")]
    rival = max(same_panel, key=lambda r: r["combined"])
    p(f"Haiku 5.5's best level, {label(best)} at {t[best]['combined_33']['mean']:.2f} (SE {t[best]['combined_33']['se']:.2f}, n={t[best]['n']}), "
      f"ranks {ranks[best]} of the board's {len(board)} columns, behind only Grok 4.7's top three levels, which are judged by a different panel "
      f"(Muse Spark 1.3 and GPT-6.1 Sol). Among columns judged by Muse Spark 1.3 and Grok 4.6 it is the highest point estimate, "
      f"{t[best]['combined_33']['mean'] - rival['combined']:.2f} above {rival['model']} at {label(rival['effort'])} ({rival['combined']:.2f}, SE "
      f"{rival['combined_se']:.2f}), well within the errors. Its levels rank {', '.join(str(ranks[e]) for e in EFFORTS)} from Low to Max.")

    # Page 7: how it was run, evidence and reproduction
    story.append(PageBreak())
    p("How it was run", "h1")
    p("<b>From a tagged run worktree.</b> The sweep ran from bench/2026-10-07-haiku55-frontier-v4, so every run summary carries a clean "
      "source block and records the frozen suite lock's task hash; no hash bridge was needed. <b>Claude Code versions.</b> Low ran 22 tasks "
      "on 2.1.293 and 1 on 2.1.294; Medium 3 on 2.1.294 and 20 on 2.1.295; High on 2.1.295; Extra-high 2 on 2.1.295 and 21 on 2.1.296; Max on "
      "2.1.296. <b>Two pauses between tasks.</b> The sweep was stopped from October 9, 15:43 UTC, to October 10, 09:20 UTC, and from October "
      "10, 19:48 UTC, to October 11, 15:50 UTC. Each time the run in progress was set aside and re-run, and no counted run was in progress "
      "across a pause, so run timings are intact. The host's clock moved from PDT to CEST during the sweep; times are UTC. <b>Where and "
      "how.</b> --billing subscription on a Claude Max plan, the local sandbox on the owner's Mac, a flat 3-hour task timeout, one task at a "
      "time, from October 8, 10:40 UTC, to October 11, 22:49 UTC. Judging ran October 11, 22:52 UTC, to October 12, 10:11 UTC, with no sweep "
      "running. Anthropic's default effort for Haiku 5.5 is Medium on the API and in Claude Code. <b>One attempt per task and level</b>; "
      "effort labels are Claude Code's own.")
    heading("Evidence and reproduction")
    p(f"Public files: <font name='Mono'>runs.json</font> and <font name='Mono'>runs.csv</font> with every run's factors, hidden behaviours "
      f"fixed, integrity verdicts, task hash, Claude Code version, replies by serving model, cost with its tier floor and ceiling, and each "
      f"judge's six-dimension sub-scores and intent recovery; <font name='Mono'>groups.json</font>; <font name='Mono'>calibration.json</font> "
      f"with every gate value and control mean; <font name='Mono'>judge-protocols.json</font> with the exact rubric, system text, probe and "
      f"match instructions, schemas, weights and the judge settings and Cursor version record; <font name='Mono'>economics.json</font> with "
      f"cost and token aggregates, both price tiers and pricing limitations; and <font name='Mono'>provenance.json</font> with source hashes "
      f"and limits. <link href='{escape(args.github_url)}' color='#8B4513'>{escape(args.github_url)}</link>")
    p("Withheld: " + "; ".join(provenance["withheld"]) + ".")
    heading("Recompute the published numbers")
    p("Each judged run's Code quality is (0.24 x reviewed score + 0.09 x intent recovery) / 0.33, where both terms are the equal mean of the "
      "two judges. The combined score is 100 x (0.50 F + 0.085 Q + 0.085 S + 0.33 C / 100) with F, Q, S on a 0 to 1 scale. Group means weight "
      "the cell's judged tasks equally. The export script recomputes every row from the frozen summary, checks every run's cost against Claude "
      "Code's stream, every task hash against the suite lock, the recovered protocols and the Cursor version pin, and the harness card tables, "
      "and refuses to write if any value differs.")
    heading("What this report does not claim")
    p("No human rated anything; the scores are model judgment for a human reader, not human validation. Standard errors describe task "
      "sampling only. The measured-maintenance layer is unbuilt, so the 33 points are 24 reviewed plus 9 intent recovery. Runs were not "
      "repeated. Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.")

    # Page 8: per task appendix and source hashes
    story.append(PageBreak())
    p("Appendix. Per task at Low, Medium and Max", "h1")
    by = {(r["effort"], r["task"]): r for r in runs}
    tasks = sorted({r["task"] for r in runs})

    def cell(r, key, digits):
        if r[key] is None:
            return "n/a"
        return f"{r[key]:.{digits}f}"

    records = [[short(task), cell(by["low", task], "code_quality", 1), cell(by["max", task], "code_quality", 1),
                cell(by["low", task], "combined_33", 2), cell(by["medium", task], "combined_33", 2), cell(by["max", task], "combined_33", 2)]
               for task in tasks]
    table(["Task", "Low CQ", "Max CQ", "Low combined", "Medium combined", "Max combined"], records, [100, 60, 64, 80, 94, 84], size=7.8, padding=1.6)
    p("Per-task values from runs.json. Task names are shortened for width. n/a: no Code quality score (classifier stop or unpublished probe).", "small")
    heading("Source hashes")
    table(["Frozen artifact", "SHA-256"], [[k.replace("v3.24/calls/", "calls/"), v[:32] + "..."]
                                          for k, v in provenance["source_artifacts_sha256"].items()], [300, 190], size=6.8, padding=1.3)
    story.pop()  # no trailing spacer, so a full appendix page does not spill an empty page before the cards

    story.extend([NextPageTemplate("card"), PageBreak()])
    for card in (CARD, COMPARE_CARD):  # landscape page, scaled to the frame height
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
        canvas.drawRightString(width - 44, height - 33, "Technical report | Frontier v4 | Code quality protocol v3.24 | October 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | Claude Haiku 5.5 across every effort level")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / {PAGES}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench Frontier v4: Claude Haiku 5.5 across every effort level",
                          author="VulcanBench", subject="Code quality protocol v3.24: Muse Spark 1.3 and Grok 4.6, 33% weight, Claude Code effort sweep with price tiers")
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
