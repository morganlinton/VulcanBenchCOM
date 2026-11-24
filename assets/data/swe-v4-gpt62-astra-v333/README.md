# VulcanBench Frontier v4: GPT-6.2 Astra under Code quality protocol v3.33

Public record for the November 2026 GPT-6.2 Astra report: 115 solver runs from
the November 22 to 23, 2026 Codex effort sweep (23 tasks, one attempt per task
at each of the five effort levels Low to Max, through Codex CLI 0.166.0 on a
ChatGPT subscription), judged for Code quality by Muse Spark 1.3 and Grok 4.6
with Code quality at 33% of the combined score. Functional, lint and
complexity, and security measurements come from the sweep. All 115 runs passed
every hidden test, finished inside the flat 3-hour task bound and carry a
published Code quality score under v3.33, judged on November 23 from both
judges' reviews.

GPT-6.2 Astra (`gpt-6.2-astra`) is a new model. It follows GPT-6 Astra, whose
record is in [../swe-v4-astra-fable51-v34/](../swe-v4-astra-fable51-v34/). It
ran on the same Codex CLI build as GPT-6.2 Sol, whose record is in
[../swe-v4-gpt62-sol-v331/](../swe-v4-gpt62-sol-v331/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles and from each judge alone, the judges that count for the run, integrity-audit verdicts, Codex notices, timing, raw tokens and token usage, API-equivalent cost, CLI version, task hash, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: per-judge means, pass counts, hidden behaviours fixed, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.33, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.33 population record, judge pins, the Cursor pin and display-rename record, counted calls and second attempts with their causes |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort, sweep totals, the rate table, sources and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and decision records |
| [Scores CSV](../swe-v4-gpt62-astra-v333-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with both judges weighted equally:

```
reviewed        = mean(reviewed_score of Muse Spark 1.3 and Grok 4.6)
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
figure, not the published score. Group means weight the cell's 23 tasks
equally. Standard errors are one sample standard error across tasks.
`hidden_behaviours` counts a task's fail-to-pass hidden tests and
`hidden_behaviours_fixed` the ones the run passed; the 23 tasks test 231 in
all, and every GPT-6.2 Astra run fixed all of its task's.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
Every GPT-6.2 Astra run passed at least one quirk family, so no run needed its
intent points moved to the reviewed score. The designed measured-maintenance
layer (12 of the 33 points) is not built; the pre-registered fallback split of
24 reviewed plus 9 intent recovery is in force.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task |
|---|---|---|---|---|---|---|---|---|
| low | 23 | 87.68 | 0.44 | 67.27 | 23 | 231 | 1.7 | 0.52 |
| medium | 23 | 88.89 | 0.33 | 70.65 | 23 | 231 | 2.4 | 0.67 |
| high | 23 | 89.26 | 0.31 | 72.88 | 23 | 231 | 3.6 | 1.00 |
| extra-high | 23 | 89.05 | 0.36 | 72.98 | 23 | 231 | 5.7 | 1.30 |
| max | 23 | 89.42 | 0.41 | 74.53 | 23 | 231 | 14.0 | 2.42 |

No run reached the flat 3-hour task bound (the longest, max quotacore, took
18.4 minutes), so no run is excluded and there is no second, timeouts-as-0
combined figure. With every task passed at every level, Frontier v4 separates
GPT-6.2 Astra's levels only on Code quality, the lint and security scans,
time and cost. The security scan (bandit) found no medium or high severity
issue in any run; runs with low-severity findings score 0.9 or 0.85 and grow
with effort, from 2 runs at low to 21 at max, so the security factor falls
from 99.13 at low to 90.87 at max. Every run's integrity audit is clean (no
web access, no benchmark-data or answer-key paths; `integrity_audit` in
runs.json).

## Cost and tokens

Each run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens) and `estimated_usd`. Prices are list API rates checked on
2026-11-22 at developers.openai.com/api/docs/pricing and the model page
(GPT-6.2 Astra at $8.00 input, $0.40 cached input and $40.00 output per
million tokens, standard tier, short context), with cached input billed at the
cache-read rate, solver inference only; judging is excluded and subscription
bills are not observable. OpenAI bills prompts over 272K input tokens at a
higher rate, but Codex keeps each request within its context window, so no
long-context premium is modelled, as for every Codex column since GPT-6 Luna.
The sweep stamped each run at those rates at run time; the export recomputes
every run's cost from its receipt and refuses to write on any mismatch. All
115 runs are priced; the sweep comes to $135.69, or $1.18 per task, at about
0.79M raw tokens per task.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort,
with the settings and Muse binary of the published v3.24 record, chosen by
the owner on November 23, 2026, the panel that judged GPT-6.2 Sol (v3.31) and
Gemini 4 Neon (v3.32). Grok 4.6 ran through the Cursor CLI pinned to version
2026.10.01-e373342, the build v3.23 to v3.32 used, with a digest of its
version directory checked before every stage; Cursor's shared launcher had
since updated itself to 2026.11.22-e9042b2, which was not used. Neither lab is
OpenAI. Sessions are fresh, tools disabled, workspace empty, model identity
checked per call, solver labels withheld. Protocol v3.33 changes nothing in
the rubric, controls, quirk keys, gates, repeats, seed, weights or judges from
v3.24; both judges retook the ten-program, five-repeat, twenty-gate
calibration exam under v3.33 before scoring any submission, and both passed
all 20 gates without the one-gate allowance.

Each judge made 440 counted calls (80 in calibration, 115 primary reviews, 5
repeats, 10 pairwise checks, 115 intent probes and 115 answer-key matches),
all of them selected. Muse needed a second attempt on 9 calls (seven
unsupported excerpts, two JSON syntax errors) and Grok on 7 (six unsupported
excerpts, one JSON syntax error), under the frozen single-retry rule; every
second attempt was valid, so no call was marked invalid and no submission is
scored by one judge. No call stopped on a usage limit. Cursor reports the
display name "Grok 4.6 Medium" for the pinned model id where the frozen
settings say "Cursor Grok 4.6 Medium"; the wrapper accepts the rename and
records it on all 440 selected Grok calls. Neither judge produced a reviewer
fallback. Every attempt is archived beside its replacement in the harness run
directory.

## Population and run notes

- Codex CLI 0.166.0, pinned by version from the install the GPT-6.2 Sol
  column used, so the two GPT-6.2 columns differ only in the model, in
  `codex exec` with the `workspace-write` sandbox, network access off, user
  configuration ignored and no saved session (harness `docs/DECISIONS.md`,
  2026-11-22).
- The ChatGPT login reported plan `prolite`, the plan GPT-6.2 Sol ran on. The
  plan sets usage limits, not the model served, and no run waited on a usage
  limit.
- The sweep ran from November 23, 2026, 02:08 UTC, to 12:38 UTC the same day
  (November 22, 18:08, to November 23, 04:38, Pacific time), from the tag
  `bench/2026-11-22-gpt62-astra-frontier-v4`; every run's source block is
  clean and its task hash equals the frozen suite lock. Each level completed
  on its first attempt, and no run printed a Codex notice.
- Codex does not report the serving model, so model identity is the model
  requested (`model_identity: requested-only`).
- The population froze on November 23 with 115 rows, none excluded and none
  missing. Judging ran from November 23, 15:25 UTC, to November 24, 03:13 UTC,
  in one window, from the tag `bench/2026-11-23-gpt62-astra-judging-v333`.
- One attempt per task and level; runs were not repeated or retried.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, solver event streams and host binary paths.
