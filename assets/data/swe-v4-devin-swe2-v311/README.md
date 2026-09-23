# VulcanBench Frontier v4: Devin SWE-2 under Code quality protocol v3.11

Public record for the September 2026 Devin SWE-2 report: the September 18 to
21, 2026 effort sweep through the Devin CLI (`devin 3000.10.31`) on a Devin
subscription, 23 tasks at each of the three effort levels SWE-2 offers
(medium, high and max), 69 runs attempted and 68 finished. 65 of those runs
carry a judgeable submission and were judged for Code quality under protocol
v3.11 on September 21, with Code quality at 33% of the combined score.
Functional, lint and complexity, and security measurements come from the
sweep. Each run's `judged` field says whether it was published or excluded and
why.

## Code quality here comes from one judge

Every other Frontier v4 entry is scored by a two-judge neutral panel, Muse
Spark 1.3 (Meta) and Grok 4.6 (xAI). Devin SWE-2 is not. Grok 4.6 failed the
calibration exam under v3.9 and GPT-5.6 Sol, brought in under v3.10 to fill
the second seat for this population, failed under v3.10. Both failed the same
gate, gate 16, the probe on the clear control: a program with no documented
departure from its specification must draw an empty probe on at least four of
five repeats, and each judge reported invented departures instead (Grok on two
repeats, Sol on four). Gate 16 is boolean, so the pre-registered one-gate
allowance cannot excuse it, and under the protocol's pre-registered
single-panel rule no judge retakes a gate it failed. Devin's Code quality is
therefore Muse Spark 1.3 alone. Both failing verdicts are published in
[calibration.json](calibration.json) beside Muse's passing one.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every finished run: task, effort, the four score factors, the judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, timing, raw tokens and token usage, Devin's credit and ACU counters, CLI version, passed quirk families and evidence hash; plus `did_not_finish` for the one run without a receipt |
| [runs.csv](runs.csv) | The same 68 records flat for spreadsheets |
| [groups.json](groups.json) | Three effort aggregates with sample standard errors, pass counts, runtime and tokens, with the judged count and the finished count kept apart |
| [calibration.json](calibration.json) | All three calibration verdicts, every gate value, the allowance rule and control means: Muse's passing v3.9 verdict, which gates this pass, and Grok's and Sol's failures |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the single-panel rule and the v3.11 population record with its exclusions |
| [economics.json](economics.json) | Raw-token, output-token and runtime aggregates per effort and for the sweep, the record of why cost is unavailable, and the limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and operator wrapper |
| [Scores CSV](../swe-v4-devin-swe2-v311-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with a single scored panel:

```
reviewed        = muse.reviewed_score
intent_recovery = muse.intent_recovery
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the sweep.
`combined_20` applies the prior 50/15/15/20 profile to the Code quality scores
for comparison only. Group means weight the cell's judged tasks equally.
Standard errors are one sample standard error across tasks.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
When a submission passed none, `intent_recovery` is null,
`intent_recovery_redistributed` is true and Code quality equals the reviewed
score; one high run needed that rule. The designed measured-maintenance layer
(12 of the 33 points) is not built; the pre-registered fallback split of 24
reviewed plus 9 intent recovery is in force.

## The judged population

65 of 69 runs are judged. 69 were attempted, 23 at each level; four are
excluded from judging, each with its reason in the population record:

| Effort | Task | Reason |
|---|---|---|
| high | cellarcore | Reached the 3-hour task budget before verification, so the run did not finish and has no receipt |
| high | snapcore | Changed no recognized source file, only file modes on the legacy binaries |
| high | vaultcore | Changed no recognized source file |
| max | freightcore | Changed no recognized source file |

A run that produced no code has nothing to judge, and the sweep's automated
quality and security metrics are undefined for it by construction, so the
v3.11 population builder excludes such a run the way it excludes an unfinished
one. Every one of the four scored 0 functionally and counts as a fail, so the
sweep's pass counts are unchanged by the exclusions: 15 of 23 at medium, 15 of
23 at high and 21 of 23 at max. The judged cells are 23 at medium, 20 at high
and 22 at max, and `groups.json` keeps `n` (judged), `runs` (finished) and
`runs_attempted` apart: Code quality and the combined scores use `n`, runtime
and tokens use `runs`.

## Cost and tokens

Cost is **unavailable**, not zero. Cognition publishes no per-token rate for
SWE-2, and the cost tier "Free" in Devin's catalog is a promotion dated
through 2026-10-10 rather than a published rate, so any figure taken from it
would read as a measured price and would stop being true when the promotion
ends. `estimated_usd` is null on every run, matching the `api_equivalent_cost_usd`
the population record carries, and the aggregate cost column reads
`unavailable`. If Cognition publishes a rate, these runs can be repriced from
their receipts.

What is measured instead is tokens, runtime and Devin's own counters. The
receipts' credit and ACU counters read zero on every run and are recorded per
run as `devin_credits` and `devin_acu`; a zero counter on a subscription is a
counter, not a price.

Each finished run carries `raw_tokens` (the Devin CLI's total including cache
reads, deduplicated by request id) and `token_usage` (the receipt's breakdown
of input, cache-read, cache-creation and output tokens). The sweep used 776
million raw tokens and 53.66 hours of solver wall clock over its 68 finished
runs; judging is excluded, and the unfinished run's 3.0 hours are not in that
total.

## Judges

The scored panel is Muse Spark 1.3 (Meta) alone, through the Muse CLI on its
Standard tier, which does not train on prompts. Meta has no model on this
board, so the judge does not grade a relative. Sessions are fresh, tools
disabled, workspace empty, model identity checked per call, solver labels
withheld.

Protocol v3.11 changes nothing in the rubric, controls, quirk keys, gates,
repeats, seed or judge settings. Muse's v3.9 calibration verdict gates this
pass and no calibration call is repeated: the exam is per judge and control
set, and neither changed between v3.9 and v3.11, so the v3.6.1 precedent
applies and `prepare` refuses to freeze unless that verdict passed under the
frozen v3.9 protocol. Muse passed 19 of the 20 gates outright and used the
pre-registered one-gate allowance on the repeatability gate, within the
allowance as written.

Under v3.11 Muse made 204 counted calls: 65 primary reviews, 3 repeats, 6
pairwise checks, 65 intent probes and 65 answer-key matches. No call needed a
second attempt, no operator rule was invoked, and no reviewer fallback
occurred. The v3.9 and v3.10 calls against the earlier freeze stay archived in
the harness run directories.

## Population note

The sweep ran September 18 to 21, 2026 on one Devin subscription throughout;
no account change occurs inside it. The judged population froze on September
21 with 65 rows, none missing, four excluded.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), and reviewer session
identifiers and usage receipts.
