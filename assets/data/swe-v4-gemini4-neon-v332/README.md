# VulcanBench Frontier v4: Gemini 4 Neon under Code quality protocol v3.32

Public record for the November 2026 Gemini 4 Neon report: 92 solver runs from
the November 20 and 21, 2026 Antigravity effort sweep (23 tasks, one attempt
per task at each of the four effort levels Antigravity offers for Neon, Low to
Extra high, through Antigravity CLI 1.5.12 on a Google AI Pro subscription),
judged for Code quality by Muse Spark 1.3 and Grok 4.6 with Code quality at
33% of the combined score. Functional, lint and complexity, and security
measurements come from the sweep. Every run finished inside the flat 3-hour
task bound. 90 runs carry a published Code quality score under v3.32, judged
on November 21 and 22 (UTC); the other two, low and extra-high codeccore, are
unpublished, and their `judged` field says why.

Gemini 4 Neon (`gemini-4-neon`) is the first Google model on the board.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles and from each judge alone, integrity-audit verdicts, tool-call counts by tool, timing, raw tokens and token usage, API-equivalent cost, CLI version, task hash, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 92 records flat for spreadsheets |
| [groups.json](groups.json) | Four effort aggregates with sample standard errors: per-judge means, judged and unpublished counts, pass counts, hidden behaviours fixed, runtime, tool calls, cost, tokens and the quota-refused attempts per level |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.32, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.32 population record, judge pins, the Cursor pin and display-rename record, counted calls, second attempts, the two unpublished rows and the judging windows |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort, sweep totals, the rate table, sources and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and decision records |
| [Scores CSV](../swe-v4-gemini4-neon-v332-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per published run, with both judges weighted equally:

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
figure, not the published score. Group means weight the cell's judged tasks
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
Every published Gemini 4 Neon run passed at least one quirk family, so no run
needed its intent points moved to the reviewed score. The designed
measured-maintenance layer (12 of the 33 points) is not built; the
pre-registered fallback split of 24 reviewed plus 9 intent recovery is in
force.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task |
|---|---|---|---|---|---|---|---|---|
| low | 22 | 84.32 | 1.09 | 66.15 | 17 | 220 | 5.1 | 0.73 |
| medium | 23 | 87.48 | 0.49 | 67.87 | 23 | 231 | 5.9 | 0.92 |
| high | 23 | 87.87 | 0.46 | 69.07 | 23 | 231 | 6.4 | 1.19 |
| extra-high | 22 | 87.70 | 0.51 | 68.69 | 23 | 231 | 10.1 | 1.80 |

Passed, behaviours fixed, minutes and cost count all 23 runs in a cell, the
unpublished one included. No run reached the flat 3-hour task bound (the
longest, medium granarycore, took 19.0 minutes), so there is no second,
timeouts-as-0 combined figure. Every run's integrity audit is clean (no web
search or fetch, no benchmark-data or answer-key paths; `integrity_audit` in
runs.json), and every archived tool call is one of the custom agent's four
tools.

## The two unpublished rows

On codeccore (`legacy-codeccore-binary-parity`) at low (submission-048) and
again at extra-high (submission-069), Grok 4.6's intent probe returned a reply
that was not valid JSON on both attempts ("Expecting ',' delimiter"): it quoted
the codeccore memo line with its double quotes unescaped, the line it also
broke on under v3.7 (GPT-5.6 Sol) and v3.17 (GPT-6 Sol). Judging stopped at
submission-048, since no wrapper rule covered two malformed replies. The owner
chose to extend `invalidate_unrecoverable_probe` to mark such a probe invalid
(harness PR #328 and `docs/DECISIONS.md`, 2026-11-21) and to leave the
submission unpublished, which is what the frozen summary does when a judge's
primary review stands but its probe is invalid, rather than to score it from
Muse Spark 1.3 alone. The Grok probes then resumed from a recovery tag, and
submission-069 was marked the same way. Both runs passed every hidden test and
are timed and priced; their judge-derived fields are null. The markers are in
the harness run directory, their hashes in `provenance.json`, and the record in
`judge-protocols.json` under `unpublished`.

## Cost and tokens

Each run carries `raw_tokens` (Antigravity's total, input with cached input
included plus output), `token_usage` (the receipt's breakdown of input, cached
input, output and thinking tokens; output includes thinking) and
`estimated_usd`. Prices are list API rates checked on 2026-11-19 at
ai.google.dev (Gemini 4 Neon at $3.00 input, $0.15 cached input and $15.00
output per million tokens), with cached input billed at the cache-read rate,
solver inference only; judging is excluded and subscription bills are not
observable. The sweep stamped each run at those rates at run time; the export
recomputes every run's cost from its receipt and refuses to write on any
mismatch. All 92 runs are priced; the sweep comes to $106.84, or $1.16 per
task, at about 1.5M raw tokens per task. The 40 attempts the AI Pro quota
refused are not population rows and are not priced.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort,
with the settings and Muse binary of the published v3.24 record, chosen by
the owner on November 21, 2026. Grok 4.6 ran through the Cursor CLI pinned to
version 2026.10.01-e373342, with a digest of its version directory checked
before every stage. Neither lab is Google. Sessions are fresh, tools disabled,
workspace empty, model identity checked per call, solver labels withheld.
Protocol v3.32 changes nothing in the rubric, controls, quirk keys, gates,
repeats, seed, weights or judges from v3.24; both judges retook the
ten-program, five-repeat, twenty-gate calibration exam under v3.32 before
scoring any submission. Muse Spark 1.3 passed with the one-gate allowance
(repeatability, g11, 0.02 short, within the half point allowed for one gate);
Grok 4.6 passed every gate.

Each judge was planned for 368 counted calls (80 in calibration, 92 primary
reviews, 4 repeats, 8 pairwise checks, 92 intent probes and 92 answer-key
matches); Grok's two invalid probes have no answer-key match, so it has 364
selected calls. Muse needed a second attempt on 2 calls and Grok on 7, under
the frozen single-retry rule. Cursor reports the display name "Grok 4.6
Medium" for the pinned model id where the frozen settings say "Cursor Grok 4.6
Medium"; the wrapper accepts the rename and records it on all 364 selected
Grok calls. Neither judge produced a reviewer fallback, and no call waited on
a usage limit. Every attempt is archived beside its replacement in the harness
run directory.

## Population and run notes

- Antigravity CLI 1.5.12, pinned by file hash and checked before every run,
  signed in with the owner's Google AI Pro subscription, headless, with a
  private home folder per run inside the harness's macOS sandbox. Antigravity
  takes the level as part of the model name (`gemini-4-neon-low` to
  `gemini-4-neon-xhigh`) and offers no Max level.
- A custom main agent limited to the default file and shell tools (read_file,
  write_file, edit_file, run_command), whose prompt body is Antigravity's own
  identity text, verbatim; the default agent's web search tool cannot be
  switched off by permissions, so it was left out this way, and URL, browser
  and MCP tools were also denied (harness `docs/DECISIONS.md`, 2026-11-19).
- Antigravity reports the model it served, `gemini-4-neon`, on every run
  (`model_identity: harness-recorded`).
- The AI Pro plan refused 40 attempts on its usage quota (10 medium, 8 high,
  22 extra-high; four of the extra-high ones cut off mid-task). Each was
  classified as infrastructure, set aside in the sweep's `infra-aborted`
  folder and rerun from scratch after the quota reset; the sweep waited about
  nine hours in all.
- A first launch on November 19 was stopped after one low run: shell
  heredocs failed inside the sandbox. The fix (harness PR #323) went in, the
  voided run was set aside, and the sweep restarted from low on the tag
  `bench/2026-11-20-gemini4-neon-frontier-v4`, running from November 20,
  13:50 UTC, to November 21, 09:58 UTC; every run's source block is clean and
  its task hash equals the frozen suite lock.
- During setup, before any run, Antigravity updated itself to 1.6.1 in
  place; the pinned 1.5.12 binary was restored by hash and its folder made
  read-only, which the updater skips. Run receipts written from the sweep tag
  still describe the update control as an environment variable, which did not
  stop the updater.
- The population froze on November 21 with 92 rows, none excluded and none
  missing. Judging ran on November 21 from 14:58 to 21:19 UTC, stopping at
  submission-048, and resumed on November 22 from 02:19 to 03:31 UTC.
- One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, the model's thinking text, submitted patches and
reconstructed sources, the quirk answer keys (they describe hidden-test
behaviour), reviewer session identifiers and usage receipts, solver event
streams and tool-call inputs, and host binary paths.
