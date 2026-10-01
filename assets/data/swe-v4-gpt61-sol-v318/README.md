# VulcanBench Frontier v4: GPT-6.1 Sol under Code quality protocol v3.18

Public record for the October 2026 GPT-6.1 Sol report: 115 solver runs from
the September 29 to 30, 2026 Codex effort sweep (23 tasks, one attempt per
task at each of the five effort levels Low to Max, through Codex CLI 0.159.0
on a ChatGPT Pro subscription), judged for Code quality by a neutral
two-model panel with Code quality at 33% of the combined score. Functional,
lint and complexity, and security measurements come from the sweep. All 115
runs finished inside the flat 3-hour task bound and all 115 carry a published
Code quality score under v3.18, judged September 30 to October 1. One run,
Medium paddockcore, is scored from one judge; its `judged` and
`scored_panels` fields say so.

GPT-6.1 Sol is a new model. It is not GPT-6 Sol, whose record is in
[../swe-v4-gpt6-sol-v317/](../swe-v4-gpt6-sol-v317/), or GPT-5.6 Sol, whose
record is in [../swe-v4-sol-v37/](../swe-v4-sol-v37/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the panels scored, the combined score under the 33% and prior 20% profiles, integrity-audit verdicts, timing, raw tokens and token usage, API-equivalent cost, CLI version, passed quirk families, evidence-rebuild flag and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: per-judge means, pass counts, hidden behaviours fixed, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.18, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.18 population record, the one-panel row, the one operator recovery and the three evidence rebuilds |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per effort, sweep totals, the rate table, sources and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and decision records |
| [Scores CSV](../swe-v4-gpt61-sol-v318-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with the judges in `scored_panels` weighted equally (both judges on
114 runs, Muse Spark 1.3 alone on Medium paddockcore):

```
reviewed        = mean(reviewed_score of each scored panel)
intent_recovery = mean(intent_recovery of each scored panel)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the
sweep. `combined_20` applies the prior 50/15/15/20 profile to the Code
quality scores for comparison only. Group means weight the cell's 23 tasks
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
score; no GPT-6.1 Sol run needed that rule. The designed measured-maintenance
layer (12 of the 33 points) is not built; the pre-registered fallback split of
24 reviewed plus 9 intent recovery is in force.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task |
|---|---|---|---|---|---|---|---|---|
| low | 23 | 86.22 | 0.82 | 70.79 | 20 | 225 | 6.9 | 0.31 |
| medium | 23 | 86.44 | 0.78 | 70.25 | 22 | 228 | 10.6 | 0.40 |
| high | 23 | 88.23 | 0.40 | 73.67 | 23 | 231 | 10.2 | 0.33 |
| extra-high | 23 | 88.78 | 0.40 | 74.99 | 23 | 231 | 15.4 | 0.43 |
| max | 23 | 88.35 | 0.33 | 73.80 | 23 | 231 | 14.5 | 0.46 |

No run reached the flat 3-hour task bound (the longest, medium paddockcore,
took 80 minutes), so no run is excluded and there is no second, timeouts-as-0
combined figure.

From High to Max every task passes every hidden test, so Frontier v4 no
longer separates GPT-6.1 Sol's top levels on correctness; Code quality, the
lint and security scans, and cost still do. Every run's integrity audit is
clean (no web access, no benchmark-data or answer-key paths; `integrity_audit`
in runs.json), and OpenAI's model page gives a knowledge cutoff of April 30,
2026, before the Frontier v4 tasks were built in August 2026.

## The one-panel Medium row

On paddockcore at Medium (`legacy-paddockcore-binary-parity`), Grok 4.6's
primary review has no valid response after the protocol's single retry: both
attempts quoted `self.standing[pony] += 2` as evidence where the code reads
`self.standing[parts[1]] += 2`, a changed token that no recovery rule
accepts. Following the owner's v3.14 decision on the same case, the wrapper
rule `invalidate_unrecoverable_primary` marked the call invalid
(`operator-invalid.json`), and the frozen summary, which publishes a
submission from the panels with a valid review, scores it from Muse Spark 1.3
alone: reviewed score 54.17, intent recovery 53.57, Code quality 54.00,
combined 80.76. The run passed its tests. Grok's probe answer for that run is
not used in any score and is not published; its panel entry in runs.json has
`scored` false and null fields. In `groups.json` Grok's Medium mean
(`by_panel.grok`) covers 22 runs; every other aggregate covers 23.

The harness score card's intent-recovery row at Medium shows 78.4: it averages
both judges' probes on paddockcore, including Grok's unused one. The published
Medium intent recovery, as in `groups.json` and on the report page, is 78.59.
Code quality and the combined score on the card agree with this bundle.

## Cost and tokens

Each run carries `raw_tokens` (Codex's total including cache reads),
`token_usage` (the receipt's breakdown of input, cached input, output and
reasoning tokens) and `estimated_usd`. Prices are list API rates checked on
2026-09-29 at developers.openai.com/api/docs/pricing and the model page
(GPT-6.1 Sol at $2.00 input, $0.10 cached input and $10.00 output per million
tokens), with cached input billed at the cache-read rate, solver inference
only; judging is excluded and subscription bills are not observable. OpenAI
bills prompts over 272K input tokens at a higher rate, but Codex keeps each
request within its 272K context window, so no long-context premium applies
and the export has no long-context branch. The sweep stamped each run at
those rates at run time; the export recomputes every run's cost from its
receipt and refuses to write on any mismatch with the population record. All
115 runs are priced; the sweep comes to $44.33, or $0.39 per task, at about
1.2M raw tokens per task.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort,
the v3.7 pair under the same pinned binaries. Neither lab has a model on this
board. Sessions are fresh, tools disabled, workspace empty, model identity
checked per call, solver labels withheld. Protocol v3.18 changes nothing in
the rubric, controls, quirk keys, gates, repeats, seed, weights or judges
from v3.7; both judges retook the ten-program, five-repeat, twenty-gate
calibration exam under v3.18 before scoring any submission, and both passed
every gate with no allowance used.

Each judge made 440 counted calls (80 in calibration, 115 primary reviews, 5
repeats, 10 pairwise checks, 115 intent probes and 115 answer-key matches);
one of Grok's primary reviews is the invalid one above. Muse needed a second
attempt on eight calls and Grok on nine. Grok's display label "Grok 4.6
Medium" was accepted by the wrapper's display-rename rule, as under earlier
amendments. Neither judge produced a reviewer fallback. Every attempt is
archived beside its replacement in the harness run directory.

One Muse probe is published through a new owner-approved wrapper rule,
`recover_escaped_excerpts`. On high codeccore (submission-083), attempt 1
wrote an invalid JSON escape, and attempt 2 quoted a code line with its string
escapes decoded into control characters, so the excerpt no longer matched the
source text. The owner treated this as a JSON-escaping slip rather than an
invented quote: the rule writes control characters back as the source's
escapes, after which the excerpt must be verbatim and the attempt must pass
the frozen validator otherwise. Attempt 2 was selected with one excerpt
respelled; the original is in the receipt and the earlier invalidation marker
is kept as `operator-invalid.superseded.json`. The record is in
`judge-protocols.json` under `operator_recoveries`.

## Population and run notes

- Codex CLI 0.159.0: 0.155.0, 0.157.0 and 0.158.0 refuse GPT-6.1 Sol on a
  ChatGPT account. 0.159.0 is the first release that serves it and runs from
  its own install for this column only (harness `docs/DECISIONS.md`,
  2026-09-29).
- The sweep ran September 29, 19:18 PDT, to September 30, 17:21 PDT. At the
  owner's request its first 11.5 hours, to September 30, 06:51 PDT,
  overlapped GPT-6 Sol's v3.17 Code quality judging on the same machine.
  Every Low, Medium and High run and the first five Extra-high runs started
  inside that window, which matters for wall-clock runtime.
- Three evidence rebuilds: low payrollcore and medium lodgecore add test
  fixtures git treats as binary, and low cellarcore's fixture text was
  altered by the text-mode capture, so the saved text patch cannot be
  re-applied. The v3.18 runner rebuilt their evidence from the saved
  workspace's index diff after checking it against the run's patch
  (`evidence_rebuilt_from_index_diff` in runs.json; method records under
  `evidence_rebuilds` in judge-protocols.json). Only test fixtures differ.
- The population froze on September 30 with 115 rows, none excluded and none
  missing. Judging ran September 30, 20:58 PDT, to October 1, 06:01 PDT, and
  06:04 to 12:52 PDT after the Grok finding above. No solver sweep ran during
  judging.
- One attempt per task and level; runs were not repeated or retried.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, and Grok's unused probe answer on medium
paddockcore.
