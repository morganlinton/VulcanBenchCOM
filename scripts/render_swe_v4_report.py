"""Render the technical PDF from the public evidence, without model calls.

Requires reportlab and the existing VulcanBench rankings-chart font folder.
The original card is embedded unchanged, not redrawn or recalculated.
"""

import argparse
import json
from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/swe-v4-astra-fable51"
OUTPUT = ROOT / "assets/reports/vulcanbench-swe-v4-astra-fable51-report.pdf"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
INK = colors.HexColor("#171917")
GREY = colors.HexColor("#555551")
RULE = colors.HexColor("#ccccC4")
GREEN = colors.HexColor("#10A37F")
CLAY = colors.HexColor("#D97757")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fonts", type=Path, required=True)
    parser.add_argument("--github-url", required=True)
    args = parser.parse_args()
    assert args.github_url.startswith("https://github.com/morganlinton/VulcanBenchCOM/tree/")
    for name, file in (("Body", "geist-400.ttf"), ("Bold", "geist-600.ttf"),
                       ("Display", "chakra-600.ttf"), ("Mono", "ibm-plex-mono-400.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(args.fonts / file)))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Bold", italic="Body", boldItalic="Bold")
    rows = json.loads((DATA / "runs.json").read_text())["rows"]
    groups = json.loads((DATA / "groups.json").read_text())
    cost = json.loads((DATA / "costs.json").read_text())
    calls = json.loads((DATA / "reviewer-calls.json").read_text())
    sensitivity = json.loads((DATA / "sensitivity.json").read_text())
    cg = {(r["model"], r["effort"]): r for r in cost["groups"]}
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

    def table(headers, records, widths=None, size=9.0, padding=5):
        values = [[Paragraph(escape(h), styles["th"]) for h in headers]] + records
        t = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
        commands = [("FONTNAME", (0, 1), (-1, -1), "Body"),
                    ("FONTSIZE", (0, 1), (-1, -1), size),
                    ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), padding),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
                    ("LINEABOVE", (0, 0), (-1, 0), 1, INK),
                    ("LINEBELOW", (0, 0), (-1, 0), .7, INK),
                    ("LINEBELOW", (0, -1), (-1, -1), 1, INK),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f2")])]
        t.setStyle(TableStyle(commands))
        story.extend([t, Spacer(1, 9)])

    def name(model):
        return "Astra" if model == "astra" else "Fable*"

    p("GPT-6 Astra and Fable 5.1", "h1")
    p("VulcanBench-SWE v4 | Five effort levels | September 2026", "small")
    heading("Abstract")
    p("Across 230 runs on 23 matched tasks, total scores span 90.97% to 92.90%. "
      "Astra in Codex has lower mean runtime and estimated API cost at every matched effort than "
      "Fable 5.1 in Claude Code with disclosed fallbacks. The highest observed total score is "
      "Fable at max (92.90%); Astra peaks at extra-high (92.39%). These are descriptive results "
      "from one attempt per task and effort, not a statistically established overall winner.")
    p("Total score combines functional correctness (50%), automated quality (15%), security (15%) "
      "and retrospective Code quality review (20%). Time and cost are separate. n=23 for every "
      "model/effort row; all ten rows use the same tasks and scoring protocol.")
    heading("Table 1. Performance by effort")
    records = []
    for g in groups:
        c = cg[g["model"], g["effort"]]
        records.append([name(g["model"]), g["effort"].title(), f'{g["combined"]["mean"]:.2f}%',
                        f'{g["combined"]["se"]:.2f}', f'{g["panel"]["mean"]:.2f}',
                        f'{g["minutes"]["mean"]:.1f}', f'{g["raw_tokens"] / 23 / 1e6:.2f}M',
                        f'${c["mean_usd"]:.2f}'])
    table(["Model", "Effort", "Total", "SE (pts)", "Code quality", "Min/task", "Tokens/task", "API $/task"],
          records, [46, 60, 56, 48, 64, 55, 66, 56], size=8.9)
    p("SE is one sample standard error across tasks, not judge uncertainty or a significance test. "
      "Code quality is out of 100. Runtime, raw tokens and costs are means per task. "
      "API estimates use a frozen September 6, 2026 rate snapshot, not subscription charges.", "small")
    heading("Findings")
    p("<b>Effort buys different tradeoffs.</b> Astra medium reaches 91.73% at 3.8 minutes and $1.48 "
      "per task. Extra-high adds 0.66 score points at 8.1 minutes and $2.30. For Fable, max "
      "scores 1.86 points above low at nearly the same mean runtime, but costs $9.06 rather than $7.96.")
    p("<b>Code quality rises more than total score.</b> Low-to-max Code quality gains are 4.65 points "
      "for both models, while automated quality and security also move. More effort is not a "
      "uniform improvement across all four factors.")
    p("<b>Costs separate these runs more than scores.</b> Full-sweep estimates are $225.04 for "
      "Astra and $1,159.10 for Fable. Astra's conservative long-context estimate is $419.42. "
      "Missing request-level context sizes limit the precision of that comparison.")

    story.append(PageBreak())
    p("Score components and reviewer calibration", "h1")
    p("Partial-credit functional scores and all non-functional factors contribute to every total. "
      "A perfect functional result is not a 100% total score. The fixed 20% review weight is a "
      "benchmark policy, not an empirically calibrated measure of production value.")
    heading("Table 2. Four factors, mean score out of 100")
    table(["Model", "Effort", "Functional", "Auto quality", "Security", "Code quality"],
          [[name(g["model"]), g["effort"].title(), *[f'{g[k]["mean"]:.2f}' for k in
             ("functional", "quality", "security", "panel")]] for g in groups],
          [60, 73, 91, 91, 73, 123], padding=3)
    p("Functional correctness carries half the weight. Automated quality uses static quality "
      "indicators; security uses static analysis. Neither guarantees production readiness or "
      "freedom from vulnerabilities. Code quality is a separate model-reviewed measure.")
    heading("Table 3. Reviewer-panel means, score out of 100")
    table(["Solver", "Effort", "Astra reviewer", "Claude reviewer", "Equal-panel mean"],
          [[name(g["model"]), g["effort"].title(), *[f'{g[k]["mean"]:.2f}' for k in
             ("astra", "claude", "panel")]] for g in groups], [60, 73, 116, 126, 136], padding=3)
    p("Claude's panel scores are lower for both solver populations. This is a systematic calibration "
      "difference, not evidence that either panel is objective. Equal weighting reduces reliance "
      "on one panel but does not remove self-preference, shared bias or rubric sensitivity.")
    p("Each panel averages correctness, readability and maintainability personas, rounds that "
      "0-to-1 mean to four decimals, and then receives half the Code quality weight. The public "
      "record includes all selected numerical ratings and the exact general review rubric.", "small")

    story.append(PageBreak())
    p("API-equivalent cost and elapsed time", "h1")
    p("Costs describe hypothetical Standard API inference charges for exposed solver usage. "
      "They are not subscription cash charges. Post-hoc judges and local infrastructure are "
      "excluded; no Batch, Flex, Fast or regional modifiers are assumed.")
    heading("Table 4. Cost of each 23-task effort sweep, USD")
    table(["Effort", "Astra", "Astra upper bound", "Fable with fallbacks"],
          [[e.title(), f'${cg["astra", e]["total_usd"]:.2f}',
            f'${cg["astra", e]["long_context_upper_total_usd"]:.2f}',
            f'${cg["fable", e]["total_usd"]:.2f}'] for e in EFFORTS] +
          [["All efforts", "$225.04", "$419.42", "$1,159.10"]], [105, 102, 141, 163], padding=3)
    p("Astra input already contains cached input and its output already contains reasoning tokens. "
      "The central estimate assumes requests at or below 272,000 input tokens. Individual request "
      "sizes are absent; cumulative task tokens are not treated as a single request. The upper "
      "scenario applies long-context rates to all usage in runs whose cumulative input exceeds "
      "that threshold. It is a sensitivity bound, not a confidence interval.")
    heading("Table 5. Frozen Standard rates, USD per million tokens")
    table(["Model", "Input", "Cache read", "Write 5m", "Write 1h", "Output"],
          [["Astra", "10.00", "1.00", "12.50*", "n/a", "50.00"],
           ["Fable 5.1", "10.00", "0.25", "12.50", "20.00", "50.00"],
           ["Opus 5 / 4.8", "5.00", "0.50", "6.25", "10.00", "25.00"],
           ["Haiku 4.5", "1.00", "0.10", "1.25", "2.00", "5.00"]], [121, 65, 78, 82, 82, 83], padding=3)
    p("*Astra cache-write rate; zero cache writes were reported. Its long-context rates multiply "
      "input/cache prices by 2 and output by 1.5. Claude cache durations are priced separately. "
      'Sources: <link href="https://developers.openai.com/api/docs/models/gpt-6-astra" color="#171917">'
      '<u>OpenAI pricing</u></link> and <link href="https://platform.claude.com/docs/en/about-claude/pricing" '
      'color="#171917"><u>Anthropic pricing</u></link>, checked September 6, 2026.', "small")
    p("Fable costs use final cumulative modelUsage receipts per session, not the sum of repeated "
      "cumulative snapshots. Actual Fable, Opus and Haiku rates are used for 252 model-level "
      "entries. Of these, 251 reconcile to the published cache policy and CLI list receipt; one internal "
      "Opus 5 receipt ($0.40398125) lacks that trace and matches five-minute cache pricing.")
    p("Final receipts own write totals: observed five-minute writes use that rate; the remainder uses one hour. "
      "Thirteen entries have different stream TTL counts, which are not added to receipt totals.", "small")
    heading("Table 6. Solver time, hours")
    timings = []
    for model in ("astra", "fable"):
        rs = [r for r in rows if r["model"] == model]
        start = min(datetime.fromisoformat(r["started_at"]) for r in rs)
        end = max(datetime.fromisoformat(r["finished_at"]) for r in rs)
        timings.append([name(model), f'{sum(r["duration_s"] for r in rs) / 3600:.2f}',
                        f'{(end - start).total_seconds() / 3600:.2f}'])
    table(["Model", "Summed solver time", "First-start to last-finish"], timings, [111, 180, 220], padding=3)
    p("Summed solver time is 70.75 hours across both sweeps. Calendar spans include gaps and "
      "overlap across models, so they must not be added. These figures exclude post-hoc judging. "
      "Run timestamps and exact seconds are available in the GitHub record.", "small")

    story.append(PageBreak())
    p("Method, audit scope and limitations", "h1")
    heading("Matched tasks and recorded submissions")
    p("Both sweeps use the same 23 behavioral-reconstruction tasks and five requested effort "
      "settings, with one original attempt per task and effort and a 10-hour per-task limit. "
      "The agent repairs a Python replacement for an opaque C-built binary. This is one "
      "implementation language, not evidence of broad multi-language coverage.")
    p("Astra used Codex CLI 0.153.4. Fable used Claude Code 2.1.259 through 2.1.261. Effort labels "
      "are harness-specific controls, not equal compute budgets. Eleven Fable runs include "
      "Opus fallbacks after refusal events: low 1, medium 3, high 2, extra-high 3 and max 2. "
      "Those runs remain included and labeled, not silently described as pure Fable results.")
    heading("Retrospective review with two panels")
    p("Each saved solution receives three Astra and three Claude ratings at medium effort. "
      "Reviewers receive the issue, full saved patch and verifier outcome; solver identity and "
      "effort labels are omitted. Tools are disabled and sessions are separate. Review changes "
      "neither the solution nor the original functional grade. Claude's reviewer is Opus 5, "
      "with 10 selected ratings using Opus 4.8; this is not a Fable reviewer panel.")
    table(["Solver / reviewer", "Calls", "Selected", "Excluded", "Fallback ratings"],
          [[f'{name(s)} / {r.title()}', sum(c["solver"] == s and c["reviewer"] == r for c in calls),
            345, sum(c["solver"] == s and c["reviewer"] == r and not c["included_in_score"] for c in calls),
            sum(c["solver"] == s and c["reviewer"] == r and c["included_in_score"] and c["fallback"] for c in calls)]
           for s in ("astra", "fable") for r in ("astra", "claude")], [170, 60, 70, 70, 141])
    p("All 1,380 selected ratings are retained from 1,386 calls. Two Fable/Claude ratings used "
      "deterministic format recovery. For High QueueCore readability, the first rating (70) "
      "is selected and the later retry (72) is excluded. Selection was not based on a higher score.")
    heading("What the checks do and do not establish")
    p("The export verified saved hashes for all 230 solver streams and 1,386 reviewer streams. "
      "Public checks recompute scores, panel means, task aggregates, standard errors and token-based cost formulas. "
      "Hash consistency does not prove absence of prohibited access, cheating or training-data "
      "overlap. Astra's stream reports the requested model only, not a returned model identity.")
    p("One attempt per cell cannot establish run-to-run reliability. Task SE is not reviewer "
      "uncertainty or a test of significance. Reviewer calibration differs, static analysis is "
      "imperfect, CLI versions vary, and native auxiliary accounting differs across providers. "
      "Scores are not directly comparable with the older Eval Suite 3.")
    heading("Public evidence and follow-up")
    p(f'<link href="{escape(args.github_url)}" color="#171917"><u>Open the immutable GitHub run record</u></link>: '
      "230 run records, selected ratings, all reviewer-call dispositions, rate assumptions, "
      "source hashes and verification scripts. Raw task prompts, patches, rationales, hidden "
      "graders and trajectories are withheld; the bundle does not independently prove those contents.")
    p("Use these results to shortlist an effort setting, then validate it on your own workload. "
      "A stronger follow-up would repeat paired runs with fixed CLI versions, returned model "
      "identities, per-request token accounting and independently audited confinement.", "small")

    story.append(PageBreak())
    p("Appendix. Score sensitivity", "h1")
    p("All five exploratory paired intervals include zero. These results do not establish a clear "
      "matched-effort score winner; this does not prove equivalence. Official scores, all 23 task "
      "pairs and the fixed 20% Code quality weight remain unchanged.")
    heading("Table 7. Fable minus Astra, total-score points")
    table(["Effort", "Observed difference", "Exploratory 95% paired interval"],
          [[r["effort"].title(), f'{r["fable_minus_astra_points"]:+.2f}',
            f'{r["paired_bootstrap_95_low"]:+.2f} to {r["paired_bootstrap_95_high"]:+.2f}']
           for r in sensitivity["rows"]], [110, 170, 231], padding=3)
    p("20,000 paired task bootstrap resamples per effort, with replacement; seed 20260906. "
      "Percentile endpoints use linear interpolation at 2.5% and 97.5%. This is task-sampling "
      "sensitivity, not repeated-run or judge uncertainty. Intervals have no multiple-comparison "
      "adjustment, and curated tasks are not a random sample of all software work.")
    heading("Table 8. Alternative totals, Fable minus Astra points")
    table(["Effort", "Astra-only judge", "Claude-only judge", "Nonfallback pairs", "Pairs"],
          [[r["effort"].title(), f'{r["fable_astra_only"]-r["astra_astra_only"]:+.2f}',
            f'{r["fable_claude_only"]-r["astra_claude_only"]:+.2f}',
            f'{r["fable_matched_nonfallback"]-r["astra_matched_nonfallback"]:+.2f}',
            str(r["matched_nonfallback_n"])] for r in sensitivity["rows"]], [90, 108, 108, 135, 70], padding=3)
    p("The Medium ordering reverses under Claude-only review. Reviewer-only variants substitute "
      "one panel for the Code quality factor while keeping its 20% weight. Nonfallback results "
      "remove the same task pairs from both models at each effort, retaining equal-panel review. "
      "Those subsets are post-hoc, change by effort and are not unbiased pure-model estimates.")
    heading("Table 9. Median runtime, minutes per task")
    table(["Effort", "Astra", "Fable with fallbacks"],
          [[r["effort"].title(), f'{r["astra_median_minutes"]:.2f}', f'{r["fable_median_minutes"]:.2f}']
           for r in sensitivity["rows"]], [151, 160, 200], padding=3)
    p("Astra is faster in medians at every matched effort, as well as in means. The mean-runtime "
      "difference is not solely a consequence of Fable outliers. Timing still measures each "
      "model-and-harness combination under its observed execution conditions.")
    p("Source: public sensitivity.json, deterministically generated from runs.json. The public "
      "script records task order, seed, sample count, aggregation and excluded task identifiers.", "small")

    story.append(PageBreak())
    p("Appendix. Review and reproduction", "h1")
    heading("What the existing Code quality scores mean")
    p("The actual rubric asks how human-like and high-quality the solution is on a 0 to 100 scale. "
      "Correctness, readability and maintainability personas each provide one score per reviewer "
      "model. It has no anchored score bands: a 90 is a model judgment, not a calibrated measure "
      "of engineering value, human authorship or production readiness.")
    p("The report retains the exact original prompts and ratings. Equal panel weights reduce "
      "reliance on one reviewer but do not eliminate calibration differences or possible "
      "self-preference. The public review-protocols.json contains the general instructions "
      "and personas; the rating ledger preserves every selected numerical vote.")
    heading("An anchored rubric is a proposed follow-up")
    p("The linked calibration plan proposes observable criteria and score anchors, from major "
      "defects through strong implementations with minor concerns. Before adoption, qualified "
      "engineers should independently score a separate calibration set with model and effort "
      "labels withheld. Compare agreement, absolute error and ordering stability on held-out "
      "examples, then freeze the protocol before scoring a new sweep.")
    p("That proposal was not used here and does not change the 20% weight or any published score. "
      "Do not calibrate to a desired leaderboard spread or pool new-protocol scores with this study.")
    heading("What readers can reproduce")
    p(f'<link href="{escape(args.github_url)}/REPRODUCING.md" color="#171917"><u>The reproduction guide</u></link> '
      "provides verification commands and pinned suite, harness and automated-evaluator source links. "
      "All 23 task definitions at the pinned suite commit match the recorded task hashes. "
      "Original solver summaries did not record the harness Git commit; the public harness "
      "snapshot is a source reference, not a verified lockfile for each invocation.")
    p("The new flat runs.csv contains all 230 runs with factor percentages, reviewer means, "
      "runtime, raw tokens, estimated API cost, fallback flags and source hashes. Public checks "
      "need no model access. They verify arithmetic and receipt consistency, not independently "
      "observed provider metering or the contents of withheld raw artifacts.")
    heading("Stronger evidence for the next study")
    p("Repeat paired runs with fixed CLI versions and counterbalanced task and effort order. "
      "Record host load, returned model identities and per-request usage, preserve audit-ready "
      "artifacts, and independently test the execution boundary. Use human calibration to test "
      "whether Code quality predicts useful engineering outcomes.")
    p("Open questions: how stable are scores across repeated runs and reviewer versions, and how "
      "well do these ratings predict maintenance effort on other workloads? This study cannot "
      "settle those questions.", "small")

    for model in ("astra", "fable"):
        story.append(PageBreak())
        p(f'Appendix. {"GPT-6 Astra" if model == "astra" else "Fable 5.1 with fallbacks"}', "h1")
        p("Total score by task and effort (%)", "h2")
        p("Every cell combines the same four weighted factors, including 20% Code quality. "
          "These are total scores, not binary pass counts. Full-precision component scores, "
          "timing, token usage and cost records are available on GitHub.")
        records = []
        for task in sorted({r["task"] for r in rows}):
            label = task.removeprefix("legacy-").split("-")[0]
            values = []
            for effort in EFFORTS:
                r = next(r for r in rows if (r["model"], r["effort"], r["task"]) == (model, effort, task))
                values.append(f'{100 * r["combined"]:.2f}' + ("*" if r["fallback"] else ""))
            records.append([label, *values])
        table(["Task", "Low", "Medium", "High", "Extra-high", "Max"], records,
              [141, 74, 74, 74, 74, 74], size=10, padding=5.4)
        if model == "astra":
            p("PaddockCore at low has a 93.33% functional component; it is not a perfect "
              "functional result. The total score still incorporates its quality, security "
              "and reviewer values. A strong total does not erase partial correctness.", "small")
        else:
            p("*Includes solver fallback usage. The label marks the original run identity and "
              "does not change its score. Partial functional results remain partial in the "
              "public component records; no missing factor is imputed.", "small")
        p("Source: public runs.json. Display rounding only; calculations use full precision. "
          "Each column contains the same 23 tasks and one attempt per task.", "small")

    story.extend([NextPageTemplate("card"), PageBreak()])
    story.append(Image(str(ROOT / "assets/cards/swe-v4-astra-fable51.png"), width=720, height=486))

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
        canvas.drawRightString(width - 44, height - 33, "Technical report | SWE v4 | September 2026")
        canvas.setStrokeColor(RULE)
        canvas.line(44, height - 49, width - 44, height - 49)
        canvas.line(44, 32, width - 44, 32)
        canvas.setFillColor(GREY)
        canvas.setFont("Body", 8.5)
        canvas.drawString(44, 19, "vulcanbench.com | Astra and Fable 5.1 with fallbacks")
        canvas.drawRightString(width - 44, 19, f"{doc.page} / 9")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, title="VulcanBench-SWE v4: GPT-6 Astra and Fable 5.1",
                          author="VulcanBench", subject="Effort, total score, Code quality, runtime and API-equivalent cost")
    doc.addPageTemplates([
        PageTemplate(id="report", frames=Frame(44, 40, A4[0] - 88, A4[1] - 102,
                                                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
                     onPage=furniture, pagesize=A4),
        PageTemplate(id="card", frames=Frame(44, 40, landscape(A4)[0] - 88, landscape(A4)[1] - 102,
                                              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
                     onPage=furniture, pagesize=landscape(A4)),
    ])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
