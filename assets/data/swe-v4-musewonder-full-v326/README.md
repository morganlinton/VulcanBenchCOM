# VulcanBench Frontier v4: Muse Wonder Full under Code quality protocol v3.26

Public record for the October 2026 Muse Wonder Full report: 92 solver runs
from the October 13 to 17, 2026 Muse Code effort sweep (23 tasks, one attempt
per task at each of the four effort levels Muse Code offers in Contributor
mode, Low to Extra-high, on the owner's Muse Code subscription, local sandbox,
flat 3-hour task bound, one sweep at a time), judged for Code quality by
Claude Opus 5.5 and GPT-6.1 Sol, with Code quality at 33% of the combined
score. Functional, lint and complexity, and security measurements come from
the sweep. 90 runs carry a published Code quality score, each the equal mean
of both judges; the other two hit the 3-hour bound and count in tasks passed,
time and cost.

Muse Wonder Full (`muse-wonder-full-1.0`) is Meta's model, run through Muse
Code as `muse-code:muse-wonder-full-1.0-contributor` in Contributor mode,
where Meta may train on submitted content. The owner accepted that, so
Frontier v4 task content may enter future Meta training data. Muse Code's
skill-reminder plugin was off for every run. Muse Code does not offer Max in
Contributor mode, so these four levels are every level that could be run.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, the timeouts-as-0 figure, the combined score from each judge alone, the round that judged it, integrity-audit verdicts, the task hash, timing, logged overlap minutes, raw tokens, model calls by model, reminder-observer usage, the estimated cost, Muse Code version, passed quirk families and evidence hash; the two timed-out rows say why they have no score |
| [runs.csv](runs.csv) | The same 92 records flat for spreadsheets |
| [groups.json](groups.json) | Four effort aggregates with sample standard errors: both combined figures, per-judge means and single-judge combined scores, judged and all-run pass counts, hidden behaviours fixed, Muse Code versions, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict (Claude Opus 5.5 under v3.26, GPT-6.1 Sol under v3.25), every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the five rounds and how they bind each other, the excluded and replaced judges, judge settings and binary pins, counted calls, second attempts and operator recoveries |
| [economics.json](economics.json) | Estimated cost and raw-token aggregates per effort, sweep totals, the rates applied, the pricing method and its limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol document, the decision record and the code |
| [Scores CSV](../swe-v4-musewonder-full-v326-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per judged run, with both judges weighted equally:

```
reviewed        = mean(reviewed_score of each panel)
intent_recovery = mean(intent_recovery of each panel)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the sweep.
Group means weight the cell's judged tasks equally; standard errors are one
sample standard error across them. `combined_timeouts_zero` counts each
timed-out run as 0 over all 23 runs (harness decision record, 2026-09-28).
Tasks passed counts all 23 runs. The measured-maintenance layer (12 of the 33
points) is not built; the pre-registered split of 24 reviewed plus 9 intent
recovery is in force, so Frontier Code quality is the reviewed layer plus
intent recovery. It is never compared with Routine v1 Code quality.

| Effort | Judged | Combined | SE | Timeouts as 0 | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task (estimate) |
|---|---|---|---|---|---|---|---|---|---|
| low | 23 | 86.95 | 1.16 | 86.95 | 72.25 | 18 | 221 | 27.3 | 3.93 |
| medium | 23 | 88.27 | 0.95 | 88.27 | 72.29 | 21 | 227 | 27.3 | 4.09 |
| high | 22 | 88.19 | 1.04 | 84.36 | 73.58 | 19 | 210 | 36.2 | 4.72 |
| extra-high | 22 | 87.59 | 0.96 | 83.78 | 71.84 | 19 | 211 | 33.3 | 5.08 |

pass@1 is 0.783, 0.913, 0.826 and 0.826 from Low to Extra-high. Runtime and
cost cover every run, the two timeouts included, as on the harness card.
Every run's integrity audit is clean: no web access, no benchmark data or
answer-key paths, and nothing touched outside the workspace except Muse
Code's own per-run session folder.

## Two runs without a Code quality score

- High paddockcore and Extra-high depotcore ran for the full 3 hours while
  still working and were stopped by the task bound, so there is no finished
  submission to judge. They count as failed tasks, are timed at 180 minutes
  and priced from the usage Muse Code reported before the bound. Their
  `judged` field says so.

High and Extra-high are therefore judged on 22 runs. The combined score at
those levels is over judged runs; `combined_timeouts_zero` gives 84.36 at High
and 83.78 at Extra-high with each timeout counted as 0.

## Two Muse Code versions

Low (23 tasks) and the first 21 Medium tasks ran on Muse Code 1.4.6 from the
tagged run worktree `bench/2026-10-13-musewonder-full-v2-low`. The Muse Code
weekly limit then stopped the sweep (Muse returned "Subscription quota
exhausted" at 2026-10-14 22:20 UTC), with cellarcore and paddockcore still to
run at Medium; the interrupted cellarcore attempt was never scored. On
October 16 Meta reset the quota and released Muse Code 1.4.9, which the owner
chose for the rest of the sweep, keeping what had already run. The last two
Medium tasks, High and Extra-high ran on 1.4.9 from
`bench/2026-10-16-musewonder-full-149`, a second run root that continues the
first and skips the tasks it completed. Medium therefore mixes versions: 21
runs on 1.4.6 and 2 on 1.4.9.

Muse Code 1.4.9 runs its end-of-run goal and verify reminder observers on
Muse Spark 1.3, not on the main model as 1.4.6 did. Those calls are recorded
apart (`reminder_observer_usage`, on 46 of the 48 1.4.9 runs; the two
timeouts reached no end of run); every other call was Muse Wonder Full, which
the adapter enforces per run.

## Cost

Meta lists no API price for Muse Wonder Full: it is not served on the Model
API. Cost is therefore an estimate. Muse Wonder Full's tokens are priced at
the Muse Wonder 1.0 list price checked on 2026-10-15 ($4.00 uncached input,
$0.20 cached input, $20.00 output per million, the same at any context
length), and the 1.4.9 reminder-observer tokens at Muse Spark 1.3's list
price checked on 2026-10-16 ($1.25, $0.15 and $4.25), exactly as the harness
card does. The sweep comes to an estimated $409.79, of which $5.97 is
reminder observers. Solver inference only; judging is excluded and
subscription bills are not observable.

## Judges

The scored panel is Claude Opus 5.5 (Anthropic) at medium effort through
Claude Code 2.1.300, and GPT-6.1 Sol (OpenAI) at medium effort through Codex
CLI 0.159.0. The other Frontier v4 columns, except Grok 4.7, are judged by
Muse Spark 1.3 and Grok 4.6. Muse Spark 1.3 is a Meta model and is not
neutral for a Meta submission, so it was excluded, as Grok 4.6 was for
Grok 4.7. Scores from different panels are not calibrated against each
other, so Muse Wonder Full's Code quality and combined score are not strictly
comparable with the other columns.

The panel came about in two rounds. Under v3.25 the owner chose Grok 4.7 and
GPT-6.1 Sol. GPT-6.1 Sol passed the exam and finished every review, probe
and match for Low and the first 21 Medium runs; Grok 4.7 stopped on its first
exam call when the Cursor account ran out of usage, a stop and not an exam
failure, so no Grok 4.7 vote exists. v3.26 seats Claude Opus 5.5 in its
place and attaches GPT-6.1 Sol's v3.25 work as a scored sibling: v3.26
refuses to prepare unless the manifest, evidence, signals, controls, quirk
keys, diagnostic selection and calibration order are byte-identical to
v3.25's, and it re-checks Sol's protocol hash before every stage. Opus 5.5
took the exam under v3.26. v3.26.1 (the two Medium runs on 1.4.9), v3.26.2
(High) and v3.26.3 (Extra-high) reuse both verdicts with no new exam, each
binding them by hash; every round's rubric, prompts, schemas, seed, repeats,
gate allowance and weights equal v3.25's. Both judges passed every gate with
no allowance used. Claude Opus 5.5 is also a compared model on the harness
card and the board; its own column comes from its own round, judged by Muse
Spark 1.3 and Grok 4.6.

The two judges disagree in level, not much in order: Claude Opus 5.5 rates
Muse Wonder Full's reviewed Code quality about 17 points below GPT-6.1 Sol at
every level (58.9 against 76.0 at Low, 58.2 and 75.3 at Medium, 59.6 and 77.1
at High, 57.8 and 74.9 at Extra-high). The published score is their mean;
`combined_single_judge` gives the combined score from each judge alone, 85.02
to 86.24 from Opus 5.5 and 88.88 to 90.30 from Sol.

Opus 5.5 made 80 calibration calls under v3.26; GPT-6.1 Sol made 80 under
v3.25. Across the rounds each judge made 90 primary reviews, 90 intent
probes and 90 answer-key matches, 6 repeats and 4 pairwise checks. Opus
needed a second attempt on one call and Sol on twelve, under the single-retry
rule. Nine of Sol's answer-key matches are published through the standing
`recover_one_based_indexes` rule: both attempts failed only because the
departure indexes were one-based, so they were moved to zero-based with
statuses untouched and the original kept in the receipt. Neither judge
produced a reviewer fallback.

## Population and run notes

- Every run summary carries a clean source block from its bench tag and
  records the frozen suite lock's task hash, so no hash bridge is needed.
- One High snapcore attempt stopped 8 minutes in on a Meta API transport
  error (the API unreachable after Muse Code's own retries); under the
  owner's rule it is an infrastructure stop, not a result, so it was kept
  apart unscored and the task was rerun.
- The sweep ran 2026-10-13 20:31 to 2026-10-14 22:20 UTC (Low and 21 Medium
  tasks), paused for the quota, and resumed 2026-10-16 11:31 to 2026-10-17
  16:11 UTC. Judging ran in four rounds, on October 15, 16 and 17.
- A per-minute log recorded any other local benchmark process beside the
  sweep from Medium on. It flags 9 of 23 Medium runs, 14 of 23 High runs and
  5 of 23 Extra-high runs (`overlap_minutes_logged`). The harness decision
  record and card say Extra-high ran alone; the log records one matching
  process beside five Extra-high tasks on October 17, 10:08 to 15:46 UTC.
  Overlap can lengthen minutes and does not change scores.
- One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, the quota-stopped and transport-stopped
attempts, and host binary paths. Redacted agent traces are published
separately at https://github.com/morganlinton/vulcanbench-musewonder-full-traces.
