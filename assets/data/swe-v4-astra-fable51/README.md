# VulcanBench-SWE v4: Astra and Fable 5.1

Public run record for the September 2026 effort comparison: 23 matched tasks,
five effort levels, two model-and-harness combinations, 230 solver runs.
GPT-6 Astra ran in Codex; Fable 5.1 ran in Claude Code with disclosed Opus
fallbacks. This is not a comparison of isolated base models.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, all four score factors, two reviewer-panel means, total score, timing, CLI version, usage and source hashes |
| [groups.json](groups.json) | Ten model/effort aggregates, sample standard errors, tokens and fallback counts |
| [ratings.json](ratings.json) | All 1,380 selected persona ratings, requested judge, effort, prompt/response hashes and format recovery flags |
| [reviewer-calls.json](reviewer-calls.json) | All 1,386 reviewer calls, including six excluded calls, selection flags, usage, fallback identities and hashes |
| [review-protocols.json](review-protocols.json) | Reviewer system instructions, personas, fixed rubric, model and effort settings |
| [costs.json](costs.json) | Per-run estimates, model-specific cache accounting, rate snapshot, effort totals and long-context sensitivity bounds |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [Scores CSV](../swe-v4-astra-fable51-scores.csv) | Aggregate metric values for spreadsheets |
| [Costs CSV](../swe-v4-astra-fable51-costs.csv) | Aggregate API-equivalent costs for spreadsheets |

## Scoring

All run-level factors are on a 0 to 1 scale. Displayed total percentages are:

`100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * panel)`

Functional scores retain partial credit. `quality` is automated quality.
`panel` is Code quality, not the same metric: it is the equal mean of the
Astra and Claude reviewer-panel scores. Each reviewer panel contains three
personas, correctness, readability and maintainability. The original
calculation rounds each three-persona panel mean to four decimals before
averaging the panels. Group means weight the 23 tasks equally.

The 20% Code quality weight is fixed, not chosen to maximize model separation.
`passed` in aggregate files is a separate functional count and must not be
substituted for total score. Whiskers are one sample standard error across
tasks, not judge uncertainty, a significance test or independent repeated runs.

## Execution and review

There is one original solver attempt per task and effort. The five labels are
low, medium, high, extra-high and max. They are harness-specific controls, not
matched compute budgets. All tasks repair Python replacements for C-built
opaque binaries. The suite is different from the older Eval Suite 3 and its
scores should not be pooled with that suite.

Astra solver CLI was 0.153.4. Fable solver CLI versions were 2.1.259 through
2.1.261. Astra's stream identifies the requested model only. Fable model
identities and Opus fallback usage were checked in assistant-message receipts.
Eleven Fable solver runs include fallbacks: low 1, medium 3, high 2,
extra-high 3, max 2. No score-based exclusions were applied.

Review was retrospective, at medium effort, with separate sessions and tools
disabled. Judges received the issue, complete saved patch and verifier result;
solver model and effort labels were omitted. The external Claude reviewer was
Opus 5, with 10 selected ratings using Opus 4.8 after refusal fallback. The
Claude reviewer CLI differed between populations (2.1.260 and 2.1.261).
The rating protocol is shared, but this does not make LLM ratings objective
human judgments or eliminate model preference.

All four solver/reviewer pairings retain 345 selected ratings. Two pairings
required extra calls: Astra/Claude 347 calls and Fable/Claude 349 calls.
Two selected Fable/Claude ratings required deterministic format recovery.
For High QueueCore readability, the first returned rating, 70, is retained;
the later retry, 72, is excluded. Recovery preserved the rating rather than
choosing the higher value. Hashes and selection flags remain in the record.

## Time and API-equivalent cost

Summed solver time is 12.0030 hours for Astra and 58.7456 hours for Fable,
70.7486 hours combined. First-start to last-finish spans are 12.0088 hours for
Astra and 80.3194 hours for Fable. Spans include gaps, overlap across models,
and must not be added or described as active compute. Neither measure includes
post-hoc judging. Run timestamps are UTC.

The standard-rate estimates are $225.04 for Astra and $1,159.10 for Fable,
not subscription charges. Judging and local infrastructure are excluded.
Prices are a frozen September 6, 2026 snapshot, not a live pricing quote.
Sources and precise rates are included in costs.json.

Astra per-request context sizes are unavailable. Its central estimate assumes
short-context rates; a conservative long-context bound is $419.42. This is a
sensitivity scenario, not a confidence interval. At that bound Astra remains
cheaper at every matched effort and 63.82% cheaper over the full sweep.

Astra input already includes cached input, and output already includes
reasoning. Fable raw token totals include cache reads and writes. Its old
summary units were cache-price-weighted, not raw tokens. The published costs
use final cumulative per-session modelUsage receipts, with actual per-model
rates and observed cache durations. Earlier cumulative receipts are not added
again. Fable auxiliary and fallback calls are included. One internal Opus 5
call lacks cache-duration trace evidence; its saved $0.40398125 list receipt
matches the five-minute cache-write rate and is explicitly retained.

## Verify the published calculations

From a checkout of this repository, with Python 3.10 or newer:

```sh
python3 scripts/verify_swe_v4_evidence.py
python3 scripts/check_benchmark_index.py
```

The verifier recomputes all total scores, reviewer means, group means and
standard errors; checks task/effort coverage, selected-call bindings and cost
totals; and scans the public bundle for forbidden dash characters and host
paths. It makes no model calls and needs no private run directory.

`scripts/export_swe_v4_evidence.py` documents the allowlisted transformation
from retained local evidence. Re-exporting needs those original private
artifacts; verifying the public arithmetic does not.

## What is not published, and what this proves

This is a public measurement record, not an unrestricted raw-transcript dump.
Task-specific prompts, patches, reviewer rationales, hidden graders, raw
trajectories, host paths and session identifiers are withheld. Source hashes
bind the export to retained evidence but cannot independently verify artifacts
that are not public. The export checked 230 solver-stream hashes and 1,386
reviewer-stream hashes against the saved records.

Hash consistency and calculation checks do not establish absence of cheating,
prohibited solver access, training-data overlap or judge bias. No claim of
training-data exclusion or comprehensive access isolation is made here.
One attempt per cell also cannot establish run-to-run reliability. A stronger
follow-up would use repeated paired runs, fixed CLI versions, returned model
identity receipts, request-level usage, and independently audited confinement.
