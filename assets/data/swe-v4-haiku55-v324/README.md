# VulcanBench Frontier v4: Claude Haiku 5.5 under Code quality protocol v3.24

Public record for the October 2026 Claude Haiku 5.5 report: 115 solver runs
from the October 8 to 11, 2026 Claude Code effort sweep (23 tasks, one attempt
per task at each of the five effort levels Low to Max, through Claude Code
2.1.293 to 2.1.296 on a Claude Max subscription, `--billing subscription`,
local sandbox, flat 3-hour task bound, one task at a time), judged for Code
quality by a two-model panel from labs other than Anthropic, with Code quality
at 33% of the combined score. Functional, lint and complexity, and security
measurements come from the sweep. All 115 runs finished inside the 3-hour
bound. 111 carry a published Code quality score under v3.24, judged October 11
to 12, each the equal mean of both judges; the other four are explained below
and count in tasks passed, time and cost.

Claude Haiku 5.5 (`claude-haiku-5-5`) is a new model. It is not Claude Sonnet
5.5, whose record is in [../swe-v4-sonnet55-v323/](../swe-v4-sonnet55-v323/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, integrity-audit verdicts, the task hash, timing, raw tokens and token usage by serving model, replies by serving model, Claude Code's cost with the tier floor and ceiling, Claude Code version, passed quirk families and evidence hash; the four rows without a score say why |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: per-judge means, judged and all-run pass counts, hidden behaviours fixed, Claude Code versions, runtime, cost with floor and ceiling, and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.24, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.24 population record, the runs not judged, the judge settings and Cursor version record, the display-name record, counted calls and retries, the unpublished probe and the one operator recovery |
| [economics.json](economics.json) | Cost, floor, ceiling and raw-token aggregates per effort, sweep totals, both price tiers as published, the pricing method and its limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, the recovered judge protocols and the decision record |
| [Scores CSV](../swe-v4-haiku55-v324-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per judged run, with both judges weighted equally:

```
reviewed        = mean(reviewed_score of each panel)
intent_recovery = mean(intent_recovery of each panel)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the sweep.
Group means weight the cell's judged tasks equally; standard errors are one
sample standard error across them. Tasks passed counts all 23 runs. The
measured-maintenance layer (12 of the 33 points) is not built; the
pre-registered split of 24 reviewed plus 9 intent recovery is in force, so
Frontier Code quality is the reviewed layer plus intent recovery. It is never
compared with Routine v1 Code quality.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task | Floor | Ceiling |
|---|---|---|---|---|---|---|---|---|---|---|
| low | 23 | 84.42 | 1.97 | 74.83 | 13 | 202 | 22.9 | 1.04 | 0.24 | 1.20 |
| medium | 22 | 84.03 | 2.50 | 76.07 | 13 | 195 | 24.0 | 1.36 | 0.31 | 1.53 |
| high | 23 | 88.01 | 1.42 | 77.60 | 17 | 215 | 26.8 | 1.25 | 0.28 | 1.40 |
| extra-high | 22 | 91.83 | 0.39 | 80.13 | 22 | 216 | 19.0 | 0.84 | 0.20 | 0.98 |
| max | 21 | 92.16 | 0.37 | 81.30 | 22 | 216 | 27.7 | 1.54 | 0.33 | 1.65 |

pass@1 is 0.565, 0.565, 0.739, 0.957 and 0.957 from Low to Max. No run reached
the 3-hour bound (the longest, medium depotcore, took 126 minutes). Runtime and
cost cover every run; the harness cards average the judged runs instead, so
their minutes and cost at medium, extra-high and max differ slightly
(`minutes_judged_runs` and `usd_judged_runs` in groups.json). Every run's
integrity audit is clean.

## Four runs without a Code quality score

- paddockcore at medium, extra-high and max: a safety classifier stopped each
  session while the model probed the legacy binary, and the run ended with an
  empty patch, so there is no code to review and no lint or security score.
  As for Claude Opus 5.5's high depotcore, they are excluded from judging,
  count as failed tasks, and are priced and timed. Their `judged` field says
  so.
- max codeccore (submission-030): Grok 4.6's intent probe gave no valid answer
  after the protocol's single retry (attempt 1 quoted a line absent from the
  run, attempt 2 was not valid JSON). `invalidate_unrecoverable_probe` marked
  it invalid, so no answer-key match was made and the frozen summary publishes
  no Code quality score, as for the same task under v3.7 and v3.17. The run
  passed its tests and counts as passed; it is priced and timed.

Max is judged on 21 runs and medium and extra-high on 22. Because the three
excluded runs failed, the combined score at those levels is over judged runs
only; read it beside tasks passed.

## Refusal fallback

Claude Code's refusal fallback stayed at its default (on). No run used it:
every assistant reply came from `claude-haiku-5-5`, and no other model appears
in any run's final usage record.

## Cost and Haiku's price tiers

Anthropic's pricing page, checked on 2026-10-07, prices Haiku 5.5 by prompt
length. For prompts up to 100,000 tokens: $0.10 input, $0.125 5-minute cache
write, $0.20 1-hour cache write, $0.01 cache read and $0.50 output per million
tokens; over 100,000 tokens, five times as much ($0.50, $0.625, $1, $0.05 and
$2.50). Claude Code receipts hold cumulative session usage, not per-request
prompt sizes, so each run carries three figures: `estimated_usd`, Claude
Code's own list-price total (`cli_reported_cost_usd`, which prices each
request at its own tier and is the published cost); `usd_floor`, every request
at the standard tier; and `usd_ceiling`, every request at the over-100k tier.
Floor and ceiling price cache writes at the 5-minute rate, as the harness cards
do, so two runs (medium lodgecore and max depotcore), which wrote 1-hour cache
entries, sit up to 0.4% above their ceiling (`runs_above_ceiling` in
economics.json). Solver inference only; judging is excluded and subscription
bills are not observable. The sweep comes to $138.31 as Claude Code reports
it, between a floor of $31.10 and a ceiling of $155.50.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its Standard
tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort. Both are from
labs other than Anthropic. Sessions are fresh, tools disabled, workspace empty,
model identity checked per call, solver labels withheld. Protocol v3.24 changes
nothing in the rubric, controls, quirk keys, gates, repeats, seed, weights or
judge settings from v3.23; both judges retook the calibration exam under v3.24
before scoring any submission and passed every gate with no allowance used.

The judge settings are read from the original v3.3 and v3.4 protocol files,
recovered from the owner's private backup, whose sha256 equal the published
values (`b82da598...` and `1d80e097...`); the export checks them and that the
settings equal those published in the v3.4 bundle. Muse Spark 1.3 ran the same
binary as every earlier round (sha256 match). Grok 4.6 ran through Cursor CLI
2026.10.01-e373342, pinned by version for the whole round: v3.24 judged through
that version's own launcher and froze a digest of its version directory
(`dedbb877...`), re-checked before every stage; the export re-checks the
digest when the directory is present. It is the same CLI that judged Sonnet
5.5 under v3.23. The Grok model id (`cursor-grok-4.6-medium`) is the same as
in every round; Cursor reports its display name as "Grok 4.6 Medium" where the
frozen settings say "Cursor Grok 4.6 Medium", a rename the judging wrapper
accepts and recorded 426 times in this round.

Each judge made 80 calibration calls, 112 primary reviews, 5 repeats, 8
pairwise checks and 112 intent probes; Muse made 112 answer-key matches and
Grok 111. Muse needed a second attempt on nine calls and Grok on five. One Grok
review is published through the standing `recover_excerpts` rule: on
extra-high vaultcore (submission-087) both attempts failed only because a
quoted code line is hard-wrapped in the source, so attempt 1 was selected with
the quote re-wrapped to the source's line breaks, scores untouched and the
original quote kept in the receipt. Neither judge produced a reviewer fallback.

## Population and run notes

- The sweep ran from the tagged worktree `bench/2026-10-07-haiku55-frontier-v4`:
  every run summary carries a clean source block and records the frozen suite
  lock's task hash, so no hash bridge is needed.
- Claude Code versions, from each run's own start-up record: low 22 tasks on
  2.1.293 and 1 on 2.1.294; medium 3 on 2.1.294 and 20 on 2.1.295; high on
  2.1.295; extra-high 2 on 2.1.295 and 21 on 2.1.296; max on 2.1.296.
- The sweep was stopped between tasks twice: 2026-10-09 15:43 to 2026-10-10
  09:20 UTC, and 2026-10-10 19:48 to 2026-10-11 15:50 UTC. Each time the run in
  progress was set aside and re-run, and no counted run was in progress across
  a pause, so run timings are intact. The host's clock moved from PDT to CEST
  during the sweep; times here are UTC. As the first pause ended, Claude Code
  replaced itself (2.1.295 to 2.1.296) and left 25 extra-high folders holding
  only a start record; every one of those tasks then ran in its own folder,
  and the stubs are not part of the population.
- The sweep ran 2026-10-08 10:40 to 2026-10-11 22:49 UTC. The population froze
  on October 11 with 112 judgeable rows (3 excluded, none missing). Judging ran
  2026-10-11 22:52 to 2026-10-12 10:11 UTC, in one window, with no sweep
  running.
- One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, the unused Grok probe attempts on max
codeccore, and host binary paths. Redacted agent traces are published
separately at https://github.com/morganlinton/vulcanbench-haiku55-traces.
