# VulcanBench Frontier v4: GPT-6 Sol under Code quality protocol v3.17

Public record for the September 2026 GPT-6 Sol report: 115 solver runs from
the September 28 to 29, 2026 Codex effort sweep (23 tasks, one attempt per
task at each of the five effort levels Low to Max, through Codex CLI 0.155.0
on a ChatGPT Pro subscription), judged for Code quality by a neutral
two-model panel with Code quality at 33% of the combined score. Functional,
lint and complexity, and security measurements come from the sweep. All 115
runs finished inside the flat 3-hour task bound and all 115 were judged
under v3.17 on September 29 to 30; 114 carry a published Code quality score.
Each run's `judged` field says which.

GPT-6 Sol is a new model. It is not GPT-5.6 Sol, whose record is in
[../swe-v4-sol-v37/](../swe-v4-sol-v37/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, both judges' reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, timing, raw tokens and token usage, API-equivalent cost, CLI version, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: per-judge means, pass counts over all 23 runs, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.17, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.17 population record, the unpublished-row finding and the one operator recovery |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort, sweep totals, the rate table, source and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and decision records |
| [Scores CSV](../swe-v4-gpt6-sol-v317-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with both judges weighted equally:

```
reviewed        = mean(muse.reviewed_score, grok.reviewed_score)
intent_recovery = mean(muse.intent_recovery, grok.intent_recovery)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the
sweep. `combined_20` applies the prior 50/15/15/20 profile to the Code
quality scores for comparison only. Group means weight the cell's judged
tasks equally. Standard errors are one sample standard error across tasks.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
When a submission passed none, `intent_recovery` is null,
`intent_recovery_redistributed` is true and Code quality equals the reviewed
score; no GPT-6 Sol run needed that rule. The designed measured-maintenance
layer (12 of the 33 points) is not built; the pre-registered fallback split of
24 reviewed plus 9 intent recovery is in force.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Min/task | $/task |
|---|---|---|---|---|---|---|---|
| low | 23 | 67.62 | 3.59 | 62.53 | 4 | 13.0 | 1.02 |
| medium | 22 | 80.60 | 2.59 | 66.79 | 13 | 17.5 | 1.76 |
| high | 23 | 82.83 | 2.43 | 70.09 | 15 | 23.8 | 2.33 |
| extra-high | 23 | 85.94 | 1.38 | 70.77 | 18 | 20.9 | 2.00 |
| max | 23 | 86.82 | 0.91 | 70.78 | 19 | 24.5 | 2.52 |

No run reached the flat 3-hour task bound (the longest, max paddockcore, took
129 minutes), so no run is excluded and there is no second, timeouts-as-0
combined figure: every combined score here is over judged runs, as for every
other Frontier v4 column.

## The unpublished Medium row

GPT-6 Sol at Medium is judged on 22 of 23 tasks. On codeccore
(`legacy-codeccore-binary-parity`), Grok 4.6's intent probe produced no valid
answer after the protocol's single retry: attempt 1 was not valid JSON (a
missing comma), and attempt 2 quoted
`memo = record[31:46].rstrip(". ,".replace(" ", "")) if False else record[31:46].rstrip(".,")`,
which is not in the code. No recovery rule accepts an invented excerpt, so no
answer-key match was made and the frozen summary, which requires a valid match
from every passing panel, leaves the row unpublished. This is the same
codeccore line Grok 4.6 misquoted under v3.7 for GPT-5.6 Sol at Max, and the
same outcome. Both judges' reviews and the Muse probe are retained in the
harness archive but are not published here; the row's judge-derived fields
are null and its `judged` field carries the reason. The run failed its tests
(functional 0.70), so it counts as a failed task, and its runtime, tokens and
cost are included in every economics figure. In `groups.json` the Medium cell
has `n` 22 for Code quality and the combined scores and `runs` 23 for pass
counts, runtime, tokens and cost. The frozen summary's `ready_for_publication`
flag is false only because of its strict 115-of-115 count; the export asserts
the shortfall is exactly this row and that it is the row whose Grok probe
folder carries the operator's `operator-invalid.json` marker.

## Cost and tokens

Each run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens) and `estimated_usd`. Prices are list API rates checked on
2026-09-25 at developers.openai.com/api/docs/pricing (GPT-6 Sol at $2.00
input, $0.20 cached input and $10.00 output per million tokens), with cached
input billed at the cache-read rate, solver inference only; judging is
excluded and subscription bills are not observable. OpenAI bills prompts over
272K input tokens at a higher rate, but Codex keeps each request within its
272K context window, so no long-context premium applies and the export has no
long-context branch. The sweep stamped each run at those rates at run time;
the export recomputes every run's cost from its receipt and refuses to write
on any mismatch with the population record. All 115 runs are priced; the
sweep comes to $221.38, or $1.93 per task.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort,
the v3.7 pair under the same pinned binaries. Neither lab has a model on this
board. Sessions are fresh, tools disabled, workspace empty, model identity
checked per call, solver labels withheld. Protocol v3.17 changes nothing in
the rubric, controls, quirk keys, gates, repeats, seed, weights or judges
from v3.7; both judges retook the ten-program, five-repeat, twenty-gate
calibration exam under v3.17 before scoring any submission, and both passed
every gate with no allowance used.

Muse Spark 1.3 made 440 counted calls (80 in calibration, 115 primary reviews,
5 repeats, 10 pairwise checks, 115 intent probes and 115 answer-key matches)
and Grok 4.6 made 439 (the same, with 114 matches, since no match was made
for the invalid probe). Muse needed a second attempt on six calls, all
unsupported evidence excerpts: three primary reviews and three probes. Grok
needed a second attempt on five: three primary reviews whose first reply was
a complete JSON review followed by a stray closing brace, and two probes (one
unsupported excerpt, then a valid answer; and the codeccore probe above).
Every Grok call reported the display label "Grok 4.6 Medium" for the pinned
model id, which the operator wrapper's display-rename rule accepts. Neither
judge produced a reviewer fallback. Every attempt is archived beside its
replacement in the harness run directory.

One Grok primary review is published through a new formatting-only wrapper
rule, `recover_trailing_braces`. On high payrollcore (submission-035) both
attempts returned a complete, valid JSON review followed by one stray closing
brace, so parsing failed before any protocol check. The rule decodes the first
JSON object, drops a remainder that is only whitespace and closing braces, and
then applies every normal check (session, subscription guard, no tool use,
usage, display label, schema and excerpts). Attempt 1 passed and was selected,
reviewed score 79.17; no field was edited, and the dropped text is recorded in
the receipt. The finding is in `judge-protocols.json` under
`operator_recoveries`. The owner may instead invalidate that call and score
the submission from Muse alone before any republication.

## Population and run notes

- Codex CLI 0.155.0: 0.153.4, used by the earlier Codex columns, refuses
  GPT-6 Sol on a ChatGPT account. 0.155.0 is the lowest release that serves
  it and was installed beside the global CLI for the GPT-6 Luna and Sol
  sweeps only (harness `docs/DECISIONS.md`, 2026-09-25).
- The sweep ran September 28, 00:31 PDT, to September 29, 14:53 PDT. At the
  owner's request it overlapped GPT-6 Luna's Code quality judging (September
  28, 00:32 to 14:32 PDT), which matters for wall-clock runtime.
- Max depotcore: the first attempt ended after eight minutes when the API
  answered "Selected model is at capacity". The harness records that as an
  infrastructure error and re-queues the task; the retry is the counted run.
  The failed attempt left no summary and is not part of any cell.
- The population froze on September 29 at 14:54 PDT with 115 rows, none
  excluded and none missing. Judging ran September 29, 14:54 PDT, to September
  30, 06:51 PDT, resumed after two operator stops (the two Grok findings
  above). GPT-6.1 Sol's solver sweep ran during that window at the owner's
  request; the judges share no quota with it, and the GPT-6 Sol runs had
  finished.
- One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), and reviewer session
identifiers and usage receipts.
