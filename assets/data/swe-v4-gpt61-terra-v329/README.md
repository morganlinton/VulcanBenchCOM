# VulcanBench Frontier v4: GPT-6.1 Terra under Code quality protocol v3.29

Public record for the October 2026 GPT-6.1 Terra report: 115 solver runs from
the October 27, 2026 Codex effort sweep (23 tasks, one attempt per task at
each of the five effort levels Low to Max, through Codex CLI 0.159.0 on a
ChatGPT subscription, the day after OpenAI released the model), judged for
Code quality by Muse Spark 1.3 and Grok 4.6 with Code quality at 33% of the
combined score. Functional, lint and complexity, and security measurements
come from the sweep. All 115 runs finished inside the flat 3-hour task bound
and all 115 carry a published Code quality score under v3.29, judged on
October 28 with one recovered call on October 30. One run, Max settlecore, is
published through an operator recovery; its `operator_recovery` field says so.

GPT-6.1 Terra (`gpt-6.1-terra`) is a new model. It is not GPT-5.6 Terra,
whose record is in [../swe-v4-terra-v36/](../swe-v4-terra-v36/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles and from each judge alone, integrity-audit verdicts, Codex notices, timing, raw tokens and token usage, API-equivalent cost, CLI version, task hash, passed quirk families, operator recovery and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: per-judge means, pass counts, hidden behaviours fixed, runtime, cost, tokens and Codex notice counts |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.29, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.29 population record, judge pins, the Cursor pin and display-rename record, counted calls, second attempts and the one operator recovery |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort, sweep totals, the rate table, sources and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and decision records |
| [Scores CSV](../swe-v4-gpt61-terra-v329-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with the two judges weighted equally:

```
reviewed        = mean(reviewed_score of each judge)
intent_recovery = mean(intent_recovery of each judge)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the
sweep. `combined_20` applies the prior 50/15/15/20 profile to the Code
quality scores for comparison only. `combined_single_judge` recomputes the
combined score with Code quality from one judge alone; it is a sensitivity
figure, not the published score. Group means weight the cell's 23 tasks
equally. Standard errors are one sample standard error across tasks.
`hidden_behaviours` counts a task's fail-to-pass hidden tests and
`hidden_behaviours_fixed` the ones the run passed; the 23 tasks test 231 in
all.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
When a submission passed none, `intent_recovery` is null,
`intent_recovery_redistributed` is true and Code quality equals the reviewed
score; three GPT-6.1 Terra runs needed that rule (low granarycore and
paddockcore, medium granarycore). The designed measured-maintenance layer (12
of the 33 points) is not built; the pre-registered fallback split of 24
reviewed plus 9 intent recovery is in force.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task |
|---|---|---|---|---|---|---|---|---|
| low | 23 | 74.95 | 3.90 | 66.55 | 13 | 170 | 2.8 | 0.11 |
| medium | 23 | 80.10 | 2.61 | 67.29 | 12 | 188 | 3.1 | 0.14 |
| high | 23 | 79.19 | 3.38 | 69.96 | 15 | 176 | 3.2 | 0.13 |
| extra-high | 23 | 83.68 | 2.09 | 70.94 | 16 | 205 | 4.9 | 0.24 |
| max | 23 | 90.00 | 0.39 | 76.59 | 23 | 231 | 6.9 | 0.36 |

No run reached the flat 3-hour task bound (the longest, extra-high
paddockcore, took 19.5 minutes), so no run is excluded and there is no
second, timeouts-as-0 combined figure.

At Max every task passes every hidden test, so Frontier v4 no longer
separates GPT-6.1 Terra's Max level from the other columns at the ceiling on
correctness; Code quality, the lint and security scans, and cost still do.
Every run's integrity audit is clean (no web access, no benchmark-data or
answer-key paths; `integrity_audit` in runs.json).

## The Max settlecore recovery

On settlecore at Max (`legacy-settlecore-binary-parity`, submission-011),
Muse Spark 1.3's intent probe quoted a byte-string line from the code with
its escapes decoded into control characters, on both attempts, so the excerpt
no longer matched the source text. This is the JSON-escaping slip the
owner-approved wrapper rule `recover_escaped_excerpts` was written for under
v3.18 (Muse's probe of GPT-6.1 Sol at high codeccore): the rule writes
control characters back as the source's escapes, after which the excerpt must
be verbatim and the attempt must pass the frozen validator otherwise. The
rule spelled a decoded NUL only as `\0`, and this source writes `\x00`, so
`invalidate_unrecoverable_probe` first marked the call invalid and the first
summary published 114 of 115 submissions, with max on 22.

The owner chose on October 29, 2026 to recover it under the rule. The rule
now tries a decoded NUL as `\0` first and then as `\x00` (harness PR #239).
The invalidation marker is kept as `operator-invalid.superseded.json`; the
Muse probe stage was rerun alone from a tag carrying the fix, which selected
attempt 1 with one excerpt respelled and made the one missing answer-key
match on October 30, and the summary was rebuilt: 115 of 115 published. Max
moved from 89.95 on 22 runs to 90.00 on 23; settlecore scores 91.11 with Code
quality 80.30. The original excerpt is in the receipt, and the record is in
`judge-protocols.json` under `operator_recoveries` and in the row's
`operator_recovery` field.

## Cost and tokens

Each run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens) and `estimated_usd`. Prices are list API rates checked on
2026-10-26 at developers.openai.com/api/docs/pricing and the model page
(GPT-6.1 Terra at $1.00 input, $0.05 cached input and $5.00 output per
million tokens), with cached input billed at the cache-read rate, solver
inference only; judging is excluded and subscription bills are not
observable. Codex keeps each request within its context window, so no
long-context premium is modelled. The sweep stamped each run at those rates
at run time; the export recomputes every run's cost from its receipt and
refuses to write on any mismatch. All 115 runs are priced; the sweep comes to
$22.49, or $0.20 per task, at about 1.4M raw tokens per task.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort,
with the settings and Muse binary of the published v3.24 record. Grok 4.6 ran
through the Cursor CLI pinned to version 2026.10.01-e373342, the build v3.23
and v3.24 used, with a digest of its version directory checked before every
stage. Neither lab is OpenAI. Sessions are fresh, tools disabled, workspace
empty, model identity checked per call, solver labels withheld. Protocol
v3.29 changes nothing in the rubric, controls, quirk keys, gates, repeats,
seed, weights or judges from v3.24; both judges retook the ten-program,
five-repeat, twenty-gate calibration exam under v3.29 before scoring any
submission. Muse Spark 1.3 passed with the one-gate allowance (repeatability,
g11, 0.26 short, within the half point allowed for one gate); Grok 4.6 passed
every gate.

Each judge made 440 counted calls (80 in calibration, 115 primary reviews, 5
repeats, 10 pairwise checks, 115 intent probes and 115 answer-key matches).
Muse needed a second attempt on 12 calls and Grok on 4, under the frozen
single-retry rule. Cursor reports the display name "Grok 4.6 Medium" for the
pinned model id where the frozen settings say "Cursor Grok 4.6 Medium"; the
wrapper accepts the rename and records it on all 440 selected Grok calls.
Neither judge produced a reviewer fallback. Every attempt is archived beside
its replacement in the harness run directory.

## Population and run notes

- Codex CLI 0.159.0, pinned by version, the release GPT-6.1 Sol ran on, in
  `codex exec` with the `workspace-write` sandbox, network access off, user
  configuration ignored and no saved session (harness `docs/DECISIONS.md`,
  2026-10-26).
- The sweep ran on October 27, 2026, from 15:14 to 23:16 UTC, from the
  tag `bench/2026-10-27-gpt61-terra-frontier-v4`; every run's source block is
  clean and its task hash equals the frozen suite lock. Each level completed
  on its first attempt.
- Three extra-high runs (hedgecore, pacecore and tallycore) printed Codex's
  notice that it had no model metadata for `gpt-6.1-terra` and used fallback
  metadata (`codex_notices` in runs.json). All three passed every hidden test
  and stay in the population.
- Codex does not report the serving model, so model identity is the model
  requested (`model_identity: requested-only`).
- The population froze on October 28 with 115 rows, none excluded and none
  missing. Judging ran on October 28 from 13:57 to 23:26 UTC; the recovery's
  match call ran on October 30 at 22:58 UTC.
- One attempt per task and level; runs were not repeated or retried.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, solver event streams and host binary paths. A
structure-only redacted trace of every run is public in
[vulcanbench-gpt61-terra-traces](https://github.com/morganlinton/vulcanbench-gpt61-terra-traces).
