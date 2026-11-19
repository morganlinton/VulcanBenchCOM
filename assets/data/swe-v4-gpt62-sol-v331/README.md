# VulcanBench Frontier v4: GPT-6.2 Sol under Code quality protocol v3.31

Public record for the November 2026 GPT-6.2 Sol report: 115 solver runs from
the November 18, 2026 Codex effort sweep (23 tasks, one attempt per task at
each of the five effort levels Low to Max, through Codex CLI 0.166.0 on a
ChatGPT subscription, starting on the evening of OpenAI's November 17 release
in Pacific time), judged for Code quality by Muse Spark 1.3 and Grok 4.6 with
Code quality at 33% of the combined score. Functional, lint and complexity,
and security measurements come from the sweep. All 115 runs passed every
hidden test, finished inside the flat 3-hour task bound and carry a published
Code quality score under v3.31, judged on November 19. One run, low
granarycore, is scored from Muse Spark 1.3 alone; its `one_panel_note` and
`scored_panels` fields say so.

GPT-6.2 Sol (`gpt-6.2-sol`) is a new model. It follows GPT-6.1 Sol, whose
record is in [../swe-v4-gpt61-sol-v318/](../swe-v4-gpt61-sol-v318/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles and from each judge alone, the judges that count for the run, integrity-audit verdicts, Codex notices, timing, raw tokens and token usage, API-equivalent cost, CLI version, task hash, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: per-judge means, pass counts, hidden behaviours fixed, runtime, cost, tokens and one-judge run counts |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.31, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.31 population record, judge pins, the Cursor pin and display-rename record, counted calls, second attempts, the one-judge record and the quota stop |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort, sweep totals, the rate table, sources and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and decision records |
| [Scores CSV](../swe-v4-gpt62-sol-v331-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with the judges that hold a valid review weighted equally:

```
reviewed        = mean(reviewed_score of each judge with a valid review)
intent_recovery = mean(intent_recovery of the same judges)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the
sweep. `combined_20` applies the prior 50/15/15/20 profile to the Code
quality scores for comparison only. `combined_single_judge` recomputes the
combined score with Code quality from one judge alone; it is a sensitivity
figure, not the published score, and it is null for Grok 4.6 on low
granarycore. Group means weight the cell's 23 tasks equally. Standard errors
are one sample standard error across tasks. `hidden_behaviours` counts a
task's fail-to-pass hidden tests and `hidden_behaviours_fixed` the ones the
run passed; the 23 tasks test 231 in all, and every GPT-6.2 Sol run fixed all
of its task's.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
Every GPT-6.2 Sol run passed at least one quirk family, so no run needed its
intent points moved to the reviewed score. The designed measured-maintenance
layer (12 of the 33 points) is not built; the pre-registered fallback split of
24 reviewed plus 9 intent recovery is in force.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task |
|---|---|---|---|---|---|---|---|---|
| low | 23 | 88.44 | 0.35 | 70.31 | 23 | 231 | 2.8 | 0.23 |
| medium | 23 | 88.94 | 0.47 | 71.78 | 23 | 231 | 4.4 | 0.33 |
| high | 23 | 88.86 | 0.33 | 71.43 | 23 | 231 | 5.1 | 0.41 |
| extra-high | 23 | 89.01 | 0.43 | 71.91 | 23 | 231 | 8.2 | 0.46 |
| max | 23 | 88.74 | 0.40 | 71.06 | 23 | 231 | 11.3 | 0.55 |

No run reached the flat 3-hour task bound (the longest, extra-high lodgecore,
took 23.6 minutes), so no run is excluded and there is no second,
timeouts-as-0 combined figure. With every task passed at every level, Frontier
v4 separates GPT-6.2 Sol's levels only on Code quality, the lint and security
scans, time and cost. Every run's integrity audit is clean (no web access, no
benchmark-data or answer-key paths; `integrity_audit` in runs.json).

## The one-judge row

On granarycore at low (`legacy-granarycore-binary-parity`, submission-069),
Grok 4.6's primary review quoted code the submission does not contain on both
attempts: one quote had a bracket in the wrong place, the other a renamed
variable. The wrapper rule `invalidate_unrecoverable_primary` (owner
precedent, September 23, 2026, first applied under v3.14) marks such a review
invalid when no excerpt can be recovered by re-wrapping or escape respelling.
The frozen summary then scores the run's reviewed layer and intent recovery
from Muse Spark 1.3 alone, as it does for any submission without two valid
reviews; GPT-6.1 Sol's medium paddockcore was published the same way under
v3.18. Granarycore scores 85.62 with Code quality 65.50. The marker is in
the harness run directory, its hash in `provenance.json`, and the record in
`judge-protocols.json` under `one_panel`.

## Cost and tokens

Each run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens) and `estimated_usd`. Prices are list API rates checked on
2026-11-17 at developers.openai.com/api/docs/pricing and the model page
(GPT-6.2 Sol at $2.00 input, $0.10 cached input and $10.00 output per million
tokens, the same as GPT-6.1 Sol), with cached input billed at the cache-read
rate, solver inference only; judging is excluded and subscription bills are
not observable. Codex keeps each request within its context window, so no
long-context premium is modelled. The sweep stamped each run at those rates
at run time; the export recomputes every run's cost from its receipt and
refuses to write on any mismatch. All 115 runs are priced; the sweep comes to
$45.38, or $0.39 per task, at about 1.1M raw tokens per task.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort,
with the settings and Muse binary of the published v3.24 record, chosen by
the owner on November 18, 2026. Grok 4.6 ran through the Cursor CLI pinned to
version 2026.10.01-e373342, the build v3.23 to v3.29 used, with a digest of
its version directory checked before every stage. Neither lab is OpenAI.
Sessions are fresh, tools disabled, workspace empty, model identity checked
per call, solver labels withheld. Protocol v3.31 changes nothing in the
rubric, controls, quirk keys, gates, repeats, seed, weights or judges from
v3.24; both judges retook the ten-program, five-repeat, twenty-gate
calibration exam under v3.31 before scoring any submission. Muse Spark 1.3
passed with the one-gate allowance (repeatability, g11, 0.1 short, within the
half point allowed for one gate); Grok 4.6 passed every gate, after failing
one gate of the same exam under v3.30.

Each judge was planned for 440 counted calls (80 in calibration, 115 primary
reviews, 5 repeats, 10 pairwise checks, 115 intent probes and 115 answer-key
matches); Grok's granarycore review has no valid response, so it has 439
selected calls. Muse needed a second attempt on 8 calls and Grok on 4, under
the frozen single-retry rule. During its exam, Grok's calls stopped on a
Cursor usage limit (the Cursor account signed in at the time was on the free
plan); the wrapper archived five stopped attempts of the same call in its
`quota-stops` folder and retried it with identical inputs under the quota
rule, and after the owner signed in to the paid account the exam continued
with no answer discarded. Cursor reports the display name "Grok 4.6 Medium"
for the pinned model id where the frozen settings say "Cursor Grok 4.6
Medium"; the wrapper accepts the rename and records it on all 439 selected
Grok calls. Neither judge produced a reviewer fallback. Every attempt is
archived beside its replacement in the harness run directory.

## Population and run notes

- Codex CLI 0.166.0, pinned by version, the earliest release that runs
  `gpt-6.2-sol` on a ChatGPT login (0.165.0 and older refuse it), in
  `codex exec` with the `workspace-write` sandbox, network access off, user
  configuration ignored and no saved session (harness `docs/DECISIONS.md`,
  2026-11-17).
- The ChatGPT login reported plan `prolite`; earlier GPT columns ran on
  ChatGPT Pro. The plan sets usage limits, not the model served, and no run
  waited on a usage limit.
- The sweep ran on November 18, 2026, from 00:34 to 12:44 UTC, from the tag
  `bench/2026-11-17-gpt62-sol-frontier-v4`; every run's source block is clean
  and its task hash equals the frozen suite lock. Each level completed on its
  first attempt, and no run printed a Codex notice.
- Codex does not report the serving model, so model identity is the model
  requested (`model_identity: requested-only`).
- The population froze on November 19 with 115 rows, none excluded and none
  missing. Judging ran on November 19 from 00:04 to 13:39 UTC.
- One attempt per task and level; runs were not repeated or retried.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, solver event streams and host binary paths.
