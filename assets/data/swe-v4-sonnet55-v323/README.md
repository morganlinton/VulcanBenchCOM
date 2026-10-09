# VulcanBench Frontier v4: Claude Sonnet 5.5 under Code quality protocol v3.23

Public record for the October 2026 Claude Sonnet 5.5 report: 115 solver runs
from the October 6 to 8, 2026 Claude Code effort sweep (23 tasks, one attempt
per task at each of the five effort levels Low to Max, through Claude Code
2.1.291 to 2.1.293 on a Claude Max subscription, `--billing subscription`,
local sandbox, flat 3-hour task bound, one task at a time), judged for Code
quality by a neutral two-model panel with Code quality at 33% of the combined
score. Functional, lint and complexity, and security measurements come from
the sweep. All 115 runs finished inside the 3-hour bound and none was
excluded. All 115 carry a published Code quality score under v3.23, judged October 8, each the equal mean of both judges.

Claude Sonnet 5.5 (`claude-sonnet-5-5`) is a new model. It is not Claude
Opus 5.5, whose record is in [../swe-v4-opus55-v315/](../swe-v4-opus55-v315/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the panels scored, the combined score under the 33% and prior 20% profiles, integrity-audit verdicts, the task hash bridge pair, timing, raw tokens and token usage by serving model, replies by serving model, Claude Code's cost, Claude Code version, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: per-judge means, pass counts, hidden behaviours fixed, Claude Code versions, runtime, cost and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.23, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.23 population record, the judge settings and version record and the task hash bridge reference |
| [economics.json](economics.json) | Cost and raw-token aggregates per effort, sweep totals, the list rates as published (both cache-read figures), the pricing method and its limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, the hash bridge, the judge settings file and the decision record |
| [Scores CSV](../swe-v4-sonnet55-v323-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with the judges in `scored_panels` weighted equally:

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
quality scores for comparison only. Group means weight the cell's tasks
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
score. The designed measured-maintenance layer (12 of the 33 points) is not
built; the pre-registered fallback split of 24 reviewed plus 9 intent recovery
is in force. Frontier Code quality is therefore the reviewed layer plus intent
recovery; it is never compared with Routine v1 Code quality.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task |
|---|---|---|---|---|---|---|---|---|
| low | 23 | 81.63 | 1.38 | 61.67 | 15 | 214 | 20.0 | 2.88 |
| medium | 23 | 84.10 | 1.20 | 65.35 | 17 | 219 | 20.8 | 3.00 |
| high | 23 | 86.79 | 1.15 | 70.84 | 20 | 223 | 14.8 | 2.39 |
| extra-high | 23 | 90.20 | 0.57 | 75.78 | 22 | 230 | 21.6 | 3.38 |
| max | 23 | 92.02 | 0.35 | 81.72 | 23 | 231 | 38.0 | 5.52 |

pass@1 with one standard error: 0.652 (0.102), 0.739 (0.094), 0.870 (0.072),
0.957 (0.043) and 1.000 from Low to Max. No run reached the flat 3-hour task
bound (the longest, medium lodgecore, took 137 minutes), so no run is excluded
and there is no second, timeouts-as-0 combined figure. Max passes every hidden
test on every task. Every run's integrity audit is clean (no web access, no
benchmark-data or answer-key paths; `integrity_audit` in runs.json).

## Refusal fallback

Claude Code's refusal fallback stayed at its default (on), as for Opus 5.5,
following Artificial Analysis's Default Fallback convention. No run used it:
every assistant reply in every stream came from `claude-sonnet-5-5` and no
other model appears in any run's final usage record. `solver_fallback` is
false on every row and `replies_by_model` counts the replies.

## Cost and tokens

Each run carries `raw_tokens` (input, cache reads, cache writes and output
from Claude Code's final usage record), `token_usage` (the same by serving
model, plus output tokens) and `estimated_usd`, which is Claude Code's own
list-price total for the session (`cli_reported_cost_usd` in the run summary,
checked against the stream's final `total_cost_usd`). Anthropic's pricing page,
checked on 2026-10-07, lists Sonnet 5.5 at $2 input, $2.50 for 5-minute cache
writes, $4 for 1-hour cache writes and $10 output per million tokens, but gives
two cache-read prices: $0.20 in its pricing table and 0.05x input ($0.10) in
its prompt caching section. The export therefore does not re-price runs at
either rate; both figures are recorded in `economics.json`. Solver inference
only; judging is excluded and subscription bills are not observable. All 115
runs are priced; the sweep comes to $394.77, or $3.43 per task, at about 9.7M
raw tokens per task.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort.
Neither lab has a model on this board, and both are neutral for an Anthropic
submission. Sessions are fresh, tools disabled, workspace empty, model
identity checked per call, solver labels withheld. Protocol v3.23 changes
nothing in the rubric, controls, quirk keys, gates, repeats, seed, weights or
judge settings from v3.15; both judges retook the ten-program, five-repeat,
twenty-gate calibration exam under v3.23 before scoring any submission. Both
passed using the one-gate allowance: Muse Spark 1.3 missed only
`g11_repeatability` (short by 0.02) and Grok 4.6 only
`g04_formatting_is_presentation` (short by 0.10), each inside the half-point
limit.

Each judge made 440 counted calls (80 in calibration, 115 primary reviews, 5
repeats, 10 pairwise checks, 115 intent probes and 115 answer-key matches).
Muse needed a second attempt on ten calls and Grok on two; no call was marked
invalid. One Grok review is published through the standing `recover_excerpts`
rule: on medium lodgecore (submission-095) both attempts failed only because a
quoted code line is hard-wrapped in the source, so attempt 1 was selected with
the quote re-wrapped to the source's line breaks, scores untouched and the
original quote kept in the receipt (`operator_recoveries` in
judge-protocols.json). Neither judge produced a reviewer fallback.

### Judge settings and versions

The original v3.3 and v3.4 judge protocol files were recovered from the
owner's private backup, and their sha256 equal the published values (v3.3
`b82da598...`, v3.4 `1d80e097...`, in the provenance of
[../swe-v4-astra-fable51-v34/](../swe-v4-astra-fable51-v34/)). The judge
settings used in v3.23 are identical to them; the export also checks that they
equal the settings published in the v3.4 bundle. Muse Spark 1.3 ran the same
binary as every earlier round (sha256 match). Grok 4.6 ran on a newer Cursor
CLI: the Cursor "pin" hashes only Cursor's launcher script, which is the same
in every Cursor release, so it never fixed the version. Cursor updated itself
on October 7, 2026 at 14:43 PDT, and every v3.23 Grok call ran on Cursor CLI
2026.10.01-e373342, while the v3.3 round recorded 2026.09.02-c22c1a3. The
Grok model id (`cursor-grok-4.6-medium`) is the same. Its display name
changed: since September 21 Cursor reports "Grok 4.6 Medium" where the frozen
settings say "Cursor Grok 4.6 Medium", a rename the judging wrapper accepts
and records (439 times in this round; `display_name` in
judge-protocols.json), and
Grok 4.6 passed calibration under v3.23. The record is in
`judge-protocols.json` under `judge_pins`.

## Population and run notes

- Before the tagged-worktree rule: the sweep was launched on October 6 from a
  checkout that predates the harness's October 5 rule that every sweep runs
  from a tagged worktree. Run summaries therefore carry no source block, and
  their recorded task hashes use an older format that counted `__pycache__`
  files. Task content was verified identical to the frozen suite lock, and
  judging admitted the runs through the committed hash bridge
  `docs/judging/task-hash-bridge-sonnet55.json` (harness repo), which pairs
  each task's recorded hash with its lock hash. All 107 cached `.pyc` files an
  agent could see were byte-identical to compiling the starting source. Each
  row's `task_hash_bridge` field carries its pair. The owner chose to publish
  with disclosure rather than rerun (harness `docs/DECISIONS.md`,
  2026-10-07).
- Claude Code versions, from each run's own start-up record: low ran 21 tasks
  on 2.1.291 and 2 on 2.1.292; medium and high on 2.1.292; extra-high 22 on
  2.1.292 and paddockcore on 2.1.293; max on 2.1.293. Earlier Claude columns
  used older releases (Opus 5.5 on 2.1.280).
- The sweep ran October 6, 06:49 PDT, to October 8, 03:38 PDT, serially, on
  the owner's Mac (the host of every published Frontier v4 column). Judging
  began October 8 at 05:02 PDT and finished at 18:02 PDT the same day, in one window with no stops. The
  Claude Haiku 5.5 solver sweep started at 03:40 PDT on October 8, after the
  last Sonnet 5.5 run had finished, and ran on the same machine during
  judging; it does not touch Sonnet 5.5's runtime figures.
- The population froze with 115 rows, none excluded and none missing.
- One attempt per task and level; runs were not repeated or retried.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, and host binary paths.
