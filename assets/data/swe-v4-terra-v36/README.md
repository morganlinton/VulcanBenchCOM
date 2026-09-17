# VulcanBench-SWE v4: GPT-5.6 Terra under Code quality protocol v3.6

Public record for the September 2026 GPT-5.6 Terra report: 115 solver
runs from the September 2026 Codex effort sweep (23 tasks, one attempt per
task at each of the five effort levels the API offers, through the Codex CLI
on a ChatGPT subscription), judged for Code quality by a neutral two-model
panel with Code quality at 33% of the combined score. Functional, lint and
complexity, and security measurements come from the sweep. 114 runs were
judged under v3.6 on September 16; the one Max run that could not start
before the subscription's quota window closed (paddockcore) ran on September
17 on a second ChatGPT account and was judged under the v3.6.1 top-up, which
reuses both judges' v3.6 calibration. Each run's `judged_under` says which.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, both judges' reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, timing, raw tokens and token usage, API-equivalent cost (re-priced) and the frozen record's original stamp, CLI version, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors, per-judge means, pass counts, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.6, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, control source hashes, the v3.6 population record, the run it recorded missing, and the v3.6.1 top-up record |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort, sweep totals, the rate table, source and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and operator wrapper |
| [Scores CSV](../swe-v4-terra-v36-scores.csv) | Aggregate values for spreadsheets |

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
score; the affected runs are flagged per row. The group
mean of intent recovery covers the scored runs only, and
`intent_recovery_redistributed_runs` counts the rest. The designed
measured-maintenance layer (12 of the 33 points) is not built; the
pre-registered fallback split of 24 reviewed plus 9 intent recovery is in
force.

## Cost and tokens

Each run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens), `estimated_usd` and `frozen_record_usd`. Prices are list
API rates checked on the date in `economics.json`, with cached input billed
at the cache-read rate, solver inference only; judging is excluded and
subscription bills are not observable. The sweep had stamped each run at a
stale Terra list price; those stamps are what the frozen population record
carries (`frozen_record_usd`), and every run was re-priced from its receipt
at the published rates on September 16, 2026 (`estimated_usd`). The export
recomputes every run's cost from its receipt and refuses to write on any
mismatch with the re-priced summary.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort.
Neither lab has a model on this board. Sessions are fresh, tools disabled,
workspace empty, model identity checked per call, solver labels withheld.
Protocol v3.6 changes nothing in the rubric, controls, gates, repeats, seed
or judge settings from v3.5; both judges retook the ten-program, five-repeat,
twenty-gate calibration exam under v3.6 before scoring any submission. Grok
4.6 passed every gate. Muse Spark 1.3 passed using the pre-registered
allowance, as under v3.5: its repeats on one control spread 0.02 of a point
more than gate 11 permits, within the half-point allowance.

Under v3.6 each judge made 437 calls: 80 in calibration, 114 primary reviews,
5 repeats, 10 pairwise checks, 114 intent probes and 114 answer-key matches. Muse needed
a second attempt on six calls, all for an unsupported excerpt; on one of them
both attempts quoted the same line with its whitespace collapsed and the
first response was selected with the excerpt re-wrapped to the source under
the standing recovery rule. Grok needed a second attempt on eight: five
unsupported excerpts, one match that cited a departure not on its own list,
and two transport faults when the Cursor CLI could not resolve its API host,
each retried under the network-fault rule. The v3.6.1 top-up added four
calls per judge for paddockcore at Max. Neither judge produced a reviewer
fallback. Every attempt is archived in the harness run directory.

## Population note

Paddockcore at Max had no attempt when v3.6 froze: from 06:00 PDT on
September 15, 2026 every launch was refused by the Codex API with "You've
hit your usage limit ... try again at Sep 19th, 2026 1:10 AM" before any
work. The cell froze at 22 on the owner's decision to publish and top up
later. On September 17 the owner switched the Codex CLI to a second ChatGPT
account (Pro plan) and the run was made under the same CLI version, harness
and task hash; the account is the only difference and is recorded in the
v3.6.1 amendment. The v3.6.1 freeze refuses any run already judged under
v3.6 or not on its missing list, and its protocol record pins the v3.6
protocol, summary, manifest and calibration files by hash. No run was
excluded.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), and reviewer session
identifiers and usage receipts.
