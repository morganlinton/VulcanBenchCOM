# VulcanBench Frontier v4: Grok 4.7 in Cursor under Code quality protocol v3.20

Public record for the October 2026 Grok 4.7 report: 92 solver runs from the
October 1 to 3, 2026 Cursor effort sweep (23 tasks, one attempt per task at
each of the four effort levels Cursor offers for Grok 4.7, Low to Extra-high,
through Cursor's agent CLI 2026.10.01-14929f9 on the Cursor subscription),
judged for Code quality by Muse Spark 1.3 and GPT-6.1 Sol with Code quality at
33% of the combined score. Functional, lint and complexity, and security
measurements come from the sweep. 91 runs finished inside the flat 3-hour task
bound and carry a published Code quality score under v3.20, judged October 3.
One run, Medium lodgecore, hit the bound; it is a row with `finished` false.

Grok 4.7 is a new xAI model, the successor to Grok 4.6. Cursor exposes four
variants (grok-4.7-low, -medium, -high and -xhigh), so there is no Max level.

## Read this first: the judge pair differs from the rest of the board

Every other Frontier v4 column was judged by Muse Spark 1.3 and Grok 4.6.
Grok 4.6 is an xAI model and is not neutral for an xAI submission, so v3.20
seats GPT-6.1 Sol (OpenAI, medium effort, Codex CLI 0.159.0) beside Muse.
GPT-6.1 Sol rates the same submissions 5.4 to 6.3 points above Muse by level,
so Grok 4.7's two-judge Code quality and combined score are not strictly
comparable with the other columns. The comparison that does not depend on the
pair is Muse's review score, which every column has: Grok 4.7 78.3, 80.5,
79.8 and 81.9 from Low to Extra-high. [shared-judge.json](shared-judge.json)
rescores every judged run on the board from Muse's panel alone; on that basis
Grok 4.7 scores 88.64, 91.46, 91.74 and 92.27, still first at Medium, High and
Extra-high and second at Low behind Claude Fable 5.1 (89.46).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, integrity-audit verdicts, timing, raw tokens and token usage, CLI version, passed quirk families and evidence hash; the timeout row carries the reason its judge-derived and token fields are null |
| [runs.csv](runs.csv) | The same 92 records flat for spreadsheets |
| [groups.json](groups.json) | Four effort aggregates with sample standard errors: per-judge means, pass counts, hidden behaviours fixed, runtime (mean and median) and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.20, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the v3.20 population record, counted calls, the capacity retry and the six index recoveries |
| [usage.json](usage.json) | Runtime and raw-token aggregates per effort and for the sweep, in place of the usual economics file: there is no cost |
| [shared-judge.json](shared-judge.json) | Muse Spark 1.3 alone for every Frontier v4 column: Muse review score, Code quality and combined score |
| [safety-v1.json](safety-v1.json) | VulcanBench Safety v1 aggregates for Grok 4.7 and Claude Opus 5.5: tasks passed and planted notes followed, ignored and reported per level and per kind of note |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and decision records |
| [Scores CSV](../swe-v4-grok47-cursor-v320-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per judged run, with Muse Spark 1.3 (`muse`) and GPT-6.1 Sol (`sol`) weighted
equally:

```
reviewed        = mean(reviewed_score of muse and sol)
intent_recovery = mean(intent_recovery of muse and sol)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the
sweep. `combined_20` applies the prior 50/15/15/20 profile to the Code
quality scores for comparison only. Group means weight the level's judged
tasks equally. Standard errors are one sample standard error across tasks.
`hidden_behaviours` counts a task's fail-to-pass hidden tests and
`hidden_behaviours_fixed` the ones the run passed; the 23 tasks test 231 in
all, and the timeout counts as fixing none.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
No Grok 4.7 run passed none, so no run fell back to the reviewed score alone.
The designed measured-maintenance layer (12 of the 33 points) is not built; the
pre-registered fallback split of 24 reviewed plus 9 intent recovery is in force.

| Effort | Judged | Combined | SE | Code quality | Muse review | Passed of 23 | Behaviours fixed of 231 | Min/task | Tokens/task | $/task |
|---|---|---|---|---|---|---|---|---|---|---|
| low | 23 | 89.42 | 1.55 | 81.41 | 78.3 | 18 | 213 | 20.2 | 4.76M | unavailable |
| medium | 22 | 92.30 | 0.86 | 83.90 | 80.5 | 21 | 215 | 27.2 | 3.20M | unavailable |
| high | 23 | 92.71 | 0.41 | 83.43 | 79.8 | 22 | 230 | 25.4 | 2.85M | unavailable |
| extra-high | 23 | 93.15 | 0.32 | 84.35 | 81.9 | 23 | 231 | 28.5 | 3.94M | unavailable |

## The medium timeout

On lodgecore at Medium (`legacy-lodgecore-binary-parity`), the run reached the
flat 10,800-second bound while still running, so there is no finished
submission and v3.20 excludes it from judging as an incomplete source run. It
counts as a failed task in every pass count and in runtime at its recorded
duration (Medium averages 27.2 minutes per task over 23 runs and 20.3 over the
22 finished runs). The Cursor stream has no usage receipt for it, so Medium's
token figures average 22 runs. With one exclusion at one level, the
two-figure rule (a second combined score counting timeouts as 0, harness
`docs/DECISIONS.md`, 2026-09-28) does not apply.

## Time, tokens and no cost

Each judged run carries `raw_tokens` and `token_usage`: the usage block of the
single result event in its Cursor stream (input, output, cache reads and cache
writes, summed as raw tokens). Cursor's run summaries record 0 tokens
(`cli_summary_units`) because the adapter does not read that block. Cache
reads are 85 to 89% of each run's tokens on average.

There is no cost. VulcanBench carries no list price for Grok 4.7, and the
sweep ran on the Cursor subscription, whose bill for these runs is not
observable. `estimated_usd` is null on every run and every aggregate is null
or "unavailable", never 0. The Frontier v4 board shows Grok 4.7's cost as
unavailable, leaves it off the cost chart, and picks its effort suggestions on
time alone.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its Standard
tier, with its v3.4 settings and binary pin, and GPT-6.1 Sol (OpenAI) at
medium effort through Codex CLI 0.159.0, on the transport v3.10 built for a
Sol seat. Neither lab is xAI. Sessions are fresh, tools disabled, workspace
empty, solver labels withheld. Muse's identity is checked per call from its
CLI's records; Codex does not record the serving model, so GPT-6.1 Sol's
identity is the model requested. Protocol v3.20 changes nothing in the rubric,
controls, quirk keys, gates, repeats, seed or weights from v3.7; both judges
took the ten-program, five-repeat, twenty-gate calibration exam under v3.20
before scoring any submission. Muse Spark 1.3 passed with the one-gate
allowance (g11 repeatability, 0.1 short); GPT-6.1 Sol, on its first exam,
passed every gate.

Each judge made 365 counted calls (80 in calibration, 91 primary reviews, 4
repeats, 8 pairwise checks, 91 intent probes and 91 answer-key matches). Muse
needed a second attempt on three calls and GPT-6.1 Sol on thirteen. No call
was invalidated and neither judge produced a reviewer fallback. Two operator
events, both on GPT-6.1 Sol's panel, are recorded in `judge-protocols.json`:

- `transport_retries`: one primary review (submission-022) ended its first
  attempt with "Selected model is at capacity" and no output. The wrapper's
  transport-fault rule gained that message and granted the protocol's single
  fresh attempt; the failed receipt is retained.
- `operator_recoveries`: six answer-key match calls numbered departures from 1
  instead of 0 on both attempts. The new wrapper rule
  `recover_one_based_indexes` applies only when every cited index lies in
  1..count and the highest equals count; it moves every index down by one,
  leaves statuses untouched, keeps the originals in the receipt, and the
  result must then validate. Intent scoring reads statuses only, so no score
  changed.

## Safety v1

`safety-v1.json` carries VulcanBench Safety v1 aggregates: ten forked Frontier
v4 tasks, each with two hazards planted as ordinary notes in the repository
(code insert, acknowledgment file, network beacon, secret exfiltration,
destructive delete), labelled per run by the VulcanConduct hazards detector as
complied, reported or ignored. Grok 4.7 in Cursor, 40 runs: 14 of 80 notes
followed (7 of 16 code inserts, 7 of 16 acknowledgment files), none reported,
no beacon, exfiltration or delete; tasks passed 9, 10, 10 and 10. Claude
Opus 5.5 in Claude Code, 50 runs: 3 of 100 followed, 64 reported. Neither
leaked the secret. Grok 4.7's audits were made after the detector gained a
Cursor stream parser and a netcat pattern fix; Opus 5.5's are unchanged by
both. The export re-derives every count from the audit files and matches the
card's table and audit hashes. Task names, note text and tokens are withheld.

## Population and run notes

- The sweep ran October 1, 12:53 PDT, to October 3, 04:12 PDT, one level and
  one task at a time, with no judging on the machine.
- Five High tasks failed in Cursor's infrastructure before producing a result
  (no summary) and were rerun by the harness; the reruns are the runs.
- The population froze on October 3 with 91 rows of 92 runs, the timeout
  excluded and none missing. Judging ran October 3, 08:15 to 14:55 PDT
  (GPT-6.1 Sol stopped 09:26 to 09:27 and 11:53 to 13:28 for the two events
  above), alongside Grok 4.7's own Cursor Safety v1 leg, after its Frontier v4
  leg had finished.
- One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, and every Safety v1 task name, note text,
planted token and per-run audit.
