# VulcanBench-SWE v4: GPT-5.5 and GPT-5.6 Luna under Code quality protocol v3.5

Public record for the September 15, 2026 GPT-5.5 and GPT-5.6 Luna comparison:
207 solver runs from the September 2026 Codex effort sweeps (23 tasks, one
attempt per task at every effort level each API accepts: four for GPT-5.5,
five for Luna, both through the Codex CLI on a ChatGPT subscription), judged
for Code quality by a neutral two-model panel with Code quality at 33% of the
combined score. Functional, lint and complexity, and security measurements
come from the sweeps.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, both judges' reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, timing, raw tokens and token usage, API-equivalent cost, CLI version, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 207 records flat for spreadsheets |
| [groups.json](groups.json) | Nine model/effort aggregates with sample standard errors, per-judge means, pass counts, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.5, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, control source hashes and the population record as frozen |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per model and effort, sweep totals, the rate table, source and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and operator wrapper |
| [Scores CSV](../swe-v4-gpt55-luna-v35-scores.csv) | Aggregate values for spreadsheets |

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
sweeps. `combined_20` applies the prior 50/15/15/20 profile to the Code
quality scores for comparison only. Group means weight the 23 tasks equally.
Standard errors are one sample standard error across tasks.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
When a submission passed none, `intent_recovery` is null,
`intent_recovery_redistributed` is true and Code quality equals the reviewed
score; this applies to nine Luna Low runs and one Luna Medium run. The group
mean of intent recovery covers the scored runs only, and
`intent_recovery_redistributed_runs` counts the rest. The designed
measured-maintenance layer (12 of the 33 points) is not built; the
pre-registered fallback split of 24 reviewed plus 9 intent recovery is in
force.

## Cost and tokens

Each run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens) and `estimated_usd`. Prices are list API rates checked on
the date in `economics.json`, with cached input billed at the cache-read rate,
solver inference only; judging is excluded and subscription bills are not
observable. The export recomputes every run's cost from its receipt at the
published rates and refuses to write on any mismatch.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort.
Neither lab has a model on this board. Sessions are fresh, tools disabled,
workspace empty, model identity checked per call, solver labels withheld.
Protocol v3.5 changes nothing in the rubric, controls, gates, repeats, seed
or judge settings from v3.4; both judges retook the ten-program, five-repeat,
twenty-gate calibration exam under v3.5 before scoring any submission. Grok
4.6 passed every gate. Muse Spark 1.3 passed using the pre-registered
allowance: its repeats on one control spread 0.02 of a point more than gate
11 permits, within the half-point allowance.

Each judge made 718 calls: 80 in calibration, 207 primary reviews, 9 repeats,
8 pairwise checks, 207 intent probes and 207 answer-key matches. Muse needed
a second attempt on five calls (two unsupported excerpts, two malformed JSON
responses, one missing consequence in calibration) and Grok on six (four
unsupported excerpts, one malformed response, and one transport fault when
the Cursor CLI could not resolve its API host). The transport fault stopped
the run for a person; the operator wrapper gained a rule that gives one fresh
attempt after a judge CLI network fault, with the receipt retained, and the
call was retried under it. Neither judge produced a reviewer fallback. Every
attempt is archived in the harness run directory.

## Population note

One GPT-5.5 Extra-high task (paddockcore) overran the ten-hour cap on its
first attempt because a harness fault left the Codex worker alive after the
launcher was killed. The task was re-run once at Extra-high under the fixed
harness, as the protocol amendment pre-registered; the re-run is the priced
and judged run and the capped attempt is set aside. No run was excluded.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), and reviewer session
identifiers and usage receipts.
