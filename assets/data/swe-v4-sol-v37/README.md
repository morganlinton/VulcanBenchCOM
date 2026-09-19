# VulcanBench Frontier v4: GPT-5.6 Sol under Code quality protocol v3.7

Public record for the September 2026 GPT-5.6 Sol report: 115 solver runs
from the September 17 to 18, 2026 Codex effort sweep (23 tasks, one attempt
per task at each of the five effort levels the API offers, through the Codex
CLI on a ChatGPT Pro subscription), judged for Code quality by a neutral
two-model panel with Code quality at 33% of the combined score. Functional,
lint and complexity, and security measurements come from the sweep. All 115
runs were judged under v3.7 on September 18 to 19; 114 carry a published
Code quality score. Each run's `judged` field says which.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, both judges' reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, timing, raw tokens and token usage, API-equivalent cost, CLI version, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors, per-judge means, pass counts, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.7, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.7 population record and the unpublished-row finding |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort, sweep totals, the rate table, source and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and operator wrapper |
| [Scores CSV](../swe-v4-sol-v37-scores.csv) | Aggregate values for spreadsheets |

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
score; no Sol run needed that rule. The designed measured-maintenance layer
(12 of the 33 points) is not built; the pre-registered fallback split of 24
reviewed plus 9 intent recovery is in force.

## The unpublished Max row

Sol at Max is judged on 22 of 23 tasks. On codeccore
(`legacy-codeccore-binary-parity`), Grok 4.6's intent probe quoted
`memo = record[31:46].rstrip(".",")` on both attempts where the source line is
`memo = record[31:46].rstrip(".,")`. A character is inserted inside the string
literal; it is neither a re-wrap, an omission nor an escape spelling, so no
recovery rule accepts it and none was added. No answer-key match was made and
the frozen summary, which requires a valid match from every passing panel,
leaves the row unpublished. Both judges' reviews and the Muse probe are
retained in the harness archive but are not published here; the row's
judge-derived fields are null and its `judged` field carries the reason. The
run passed its tests (the sweep itself passed 22 of 23 at Max) and its
runtime, tokens and cost are included in every economics figure. In
`groups.json` the Max cell has `n` 22 for Code quality and the combined
scores and `runs` 23 for runtime, tokens and cost. The frozen summary's
`ready_for_publication` flag is false only because of its strict 115-of-115
count; the export asserts the shortfall is exactly this row and that it is the
row whose Grok probe folder carries the operator's `operator-invalid.json`
marker.

## Cost and tokens

Each run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens) and `estimated_usd`. Prices are list API rates checked on
the date in `economics.json` (Sol at $4.00 input, $0.40 cached input and
$20.00 output per million tokens), with cached input billed at the
cache-read rate, solver inference only; judging is excluded and subscription
bills are not observable. The sweep stamped each run at those rates at run
time; the export recomputes every run's cost from its receipt and refuses to
write on any mismatch with the population record.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort.
Neither lab has a model on this board. Sessions are fresh, tools disabled,
workspace empty, model identity checked per call, solver labels withheld.
Protocol v3.7 changes nothing in the rubric, controls, quirk keys, gates,
repeats, seed or judge settings from v3.6; both judges retook the
ten-program, five-repeat, twenty-gate calibration exam under v3.7 before
scoring any submission, and both passed every gate with no allowance used.

Under v3.7 Muse Spark 1.3 made 440 calls (80 in calibration, 115 primary
reviews, 5 repeats, 10 pairwise checks, 115 intent probes and 115 answer-key
matches) and Grok 4.6 made 439 (the same, with 114 matches, since no match
was made for the invalid probe). Muse needed a second attempt on nine calls
(six primary reviews, three probes): four unsupported excerpts and five
malformed JSON responses. Grok needed a second attempt on nine: five
unsupported excerpts (two primary reviews, one calibration control and two
probes, one of them the codeccore probe above, which was unsupported on both
attempts), one malformed JSON probe, two transport faults when the Cursor
CLI could not resolve its API host (a primary review and a calibration
pair), each retried under the network-fault rule, and one calibration probe
the provider blocked before any model output, retried once under the
retry_provider_block rule recorded in the operations log. Neither judge
produced a reviewer fallback. Every attempt is archived in the harness run
directory.

## Population note

The sweep ran September 17 to 18, 2026 on a ChatGPT Pro account throughout;
no account change occurs inside it. The population froze on September 18
with 115 rows, none missing and none excluded.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), and reviewer session
identifiers and usage receipts.
