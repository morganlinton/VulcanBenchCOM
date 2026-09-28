# VulcanBench Frontier v4: GPT-6 Luna under Code quality protocol v3.16

Public record for the September 2026 GPT-6 Luna report: 115 solver runs from
the September 25 to 28, 2026 Codex effort sweep (23 tasks, one attempt per
task at each of the five effort levels Codex offers for GPT-6 Luna, through
Codex CLI 0.155.0 on a ChatGPT Pro subscription), judged for Code quality by
a neutral two-model panel with Code quality at 33% of the combined score.
Functional, lint and complexity, and security measurements come from the
sweep. 109 runs were judged under v3.16 on September 28 and all 109 carry a
published Code quality score. The other six hit the flat 3-hour task bound
and have no finished submission. Each run's `judged` field says which.

GPT-6 Luna is a new model. It is not GPT-5.6 Luna, whose record is in
[../swe-v4-gpt55-luna-v35/](../swe-v4-gpt55-luna-v35/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, whether it finished, the four score factors, both judges' reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, the timeouts-as-0 combined score, timing, raw tokens and token usage, API-equivalent cost, CLI version, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: both combined figures, per-judge means, pass counts over all 23 runs, timeouts, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.16, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes and the v3.16 population record (host paths removed) |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort over priced runs, runtime over all runs, sweep totals, the unpriced timeouts, the rate table, source and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and decision records |
| [Scores CSV](../swe-v4-gpt6-luna-v316-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with both judges weighted equally:

```
reviewed        = mean(muse.reviewed_score, grok.reviewed_score)
intent_recovery = mean(muse.intent_recovery, grok.intent_recovery)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
combined_timeouts_zero = combined_33 for a judged run, 0 for a timeout
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the
sweep. `combined_20` applies the prior 50/15/15/20 profile to the Code
quality scores for comparison only. Group means weight the cell's tasks
equally. Standard errors are one sample standard error across tasks.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
When a submission passed none, `intent_recovery` is null,
`intent_recovery_redistributed` is true and Code quality equals the reviewed
score. Fourteen GPT-6 Luna runs needed that rule: 10 at Low, 3 at Medium and 1
at High. The designed measured-maintenance layer (12 of the 33 points) is not
built; the pre-registered fallback split of 24 reviewed plus 9 intent recovery
is in force.

## Six timeouts and two combined figures

Six runs hit the flat 3-hour task bound while still working: extra-high
depotcore and paddockcore; max cellarcore, depotcore, lodgecore and
paddockcore. Each trace shows continuous work to the bound, with no idle gap
over four minutes. A timed-out run has no finished submission, so v3.16
cannot judge it and the population record excludes it, as v3.15 excluded
Claude Opus 5.5's incomplete high depotcore run. In `runs.json` these rows
have `finished` false, a `judged` field that gives the reason, and null
judge-derived, token and cost fields.

With four of 23 max runs out of the judged set, all of them failures, the
judged mean alone flatters the top levels, so every cell carries two
combined figures (owner decision, harness `docs/DECISIONS.md`, 2026-09-28):

- `combined_33`: the standard combined score over judged runs (n 23, 23, 23,
  21, 19 from low to max), computed as for every other Frontier v4 column.
  This is the leaderboard cell value.
- `combined_timeouts_zero`: each timed-out run counted as a combined score
  of 0, over all 23 runs.

| Effort | Judged | Combined, judged runs | Combined, timeouts as 0 | Passed of 23 | Timeouts |
|---|---|---|---|---|---|
| low | 23 | 40.83 | 40.83 | 0 | 0 |
| medium | 23 | 45.72 | 45.72 | 0 | 0 |
| high | 23 | 57.35 | 57.35 | 2 | 0 |
| extra-high | 21 | 78.79 | 71.94 | 11 | 2 |
| max | 19 | 81.42 | 67.26 | 12 | 4 |

Pass counts always count timeouts as failures (`passed_all_runs` in
`groups.json`, which equals `passed` because no timeout can pass). Code
quality and its components are means over judged runs. Runtime covers all 23
runs, each timeout at its recorded duration of about 180 minutes.

## Cost and tokens

Each priced run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens) and `estimated_usd`. Prices are list API rates checked on
2026-09-25 at developers.openai.com/api/docs/pricing (GPT-6 Luna at $0.10
input, $0.01 cached input and $0.50 output per million tokens), with cached
input billed at the cache-read rate, solver inference only; judging is
excluded and subscription bills are not observable. OpenAI bills prompts over
272K input tokens at a higher rate, but Codex keeps each request within its
272K context window, so no long-context premium applies and the export has no
long-context branch. The sweep stamped each run at those rates at run time;
the export recomputes every priced run's cost from its receipt and refuses to
write on any mismatch with the population record.

The six timeouts ended before Codex reported usage. They are unpriced, not $0:
cost and token means and totals cover the 109 priced runs, so extra-high and
max spend is understated. The sweep prices at $7.26 in all.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort,
the v3.7 pair under the same pinned binaries. Neither lab has a model on this
board. Sessions are fresh, tools disabled, workspace empty, model identity
checked per call, solver labels withheld. Protocol v3.16 changes nothing in
the rubric, controls, quirk keys, gates, repeats, seed, weights or judges
from v3.7; both judges retook the ten-program, five-repeat, twenty-gate
calibration exam under v3.16 before scoring any submission. Both passed, each
using the pre-registered one-gate allowance: Muse Spark 1.3 on gate 11
(repeatability, shortfall 0.06) and Grok 4.6 on gate 4 (formatting is
presentation, shortfall 0.10), both inside the 0.5 bound.

Each judge made 420 counted calls (80 in calibration, 109 primary reviews, 5
repeats, 8 pairwise checks, 109 intent probes and 109 answer-key matches).
Muse needed a second attempt on six calls: four primary reviews (two
unsupported evidence excerpts, two malformed JSON responses) and two probes
(unsupported excerpts). Grok needed a second attempt on two primary reviews,
both unsupported excerpts. Every Grok call reported the display label
"Grok 4.6 Medium" for the pinned model id, which the operator wrapper's
display-rename rule accepts, as under v3.15. All 109 submissions are
published: no invalid probe and no reviewer fallback.

## Population and run notes

- Codex CLI 0.155.0: 0.153.4, used by every other Codex column, refuses
  GPT-6 Luna on a ChatGPT account. 0.155.0 is the lowest release that serves
  it and was installed beside the global CLI for this sweep only (harness
  `docs/DECISIONS.md`, 2026-09-25).
- Extra-high pacecore: the first attempt stalled after a Codex reconnect
  message and made no progress for about 88 minutes; the operator stopped
  it, the harness re-queued it, and the retry is the counted run. The
  stalled attempt is archived and is not part of any cell.
- The population froze on September 28 at 00:32 PDT with 109 rows and six
  excluded timeouts, none missing. Judging ran September 28, 00:32 to 14:32
  PDT, alongside the GPT-6 Sol solver sweep at the owner's request.
- One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), and reviewer session
identifiers and usage receipts.
