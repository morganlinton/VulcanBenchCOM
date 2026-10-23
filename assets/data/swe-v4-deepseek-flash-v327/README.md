# VulcanBench Frontier v4: DeepSeek V4.1 Flash under Code quality protocol v3.27

Public record for the October 2026 DeepSeek V4.1 Flash report: 69 solver runs
from the October 20 to 22, 2026 DeepSeek Harness effort sweep (23 tasks, one
attempt per task at each of the three reasoning levels DeepSeek's API offers,
Low, High and Max, billed to a DeepSeek API key, local sandbox, flat 3-hour
task bound, one task at a time), judged for Code quality by Muse Spark 1.3
and GPT-6.1 Sol, with Code quality at 33% of the combined score. Functional,
lint and complexity, and security measurements come from the sweep. Every run
finished inside the bound and every run carries a published Code quality
score, the equal mean of both judges.

DeepSeek V4.1 Flash ran through DeepSeek's API as `deepseek-flash`, which
DeepSeek's pricing page mapped to DeepSeek-V4.1-Flash-1017 when it was checked
before each level. DeepSeek Harness records the model it requested, not the id
in DeepSeek's response, so model identity is harness-recorded. DeepSeek's API
has no Medium and nothing maps to Extra-high, so these three levels are every
level that could be run.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, the combined score from each judge alone, integrity-audit verdicts, the task hash, the harness version and install hash, timing, raw tokens, model calls, peak-hour calls, unpriced title calls, list and billed cost, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 69 records flat for spreadsheets |
| [groups.json](groups.json) | Three effort aggregates with sample standard errors: combined score, per-judge means and single-judge combined scores, pass counts, hidden behaviours fixed, runtime, tokens, list and billed cost |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.27, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, why GPT-6.1 Sol holds the second seat, judge settings and binary pins, counted calls, second attempts and operator recoveries |
| [economics.json](economics.json) | List-price and billed cost and raw-token aggregates per effort, sweep totals, the rates applied, the peak-hour rule, the pricing method and its limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol document, the decision record and the code |
| [Scores CSV](../swe-v4-deepseek-flash-v327-scores.csv) | Aggregate values for spreadsheets |

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
Group means weight the cell's 23 tasks equally; standard errors are one sample
standard error across them. The measured-maintenance layer (12 of the 33
points) is not built; the pre-registered split of 24 reviewed plus 9 intent
recovery is in force, so Frontier Code quality is the reviewed layer plus
intent recovery. It is never compared with Routine v1 Code quality.

| Effort | Judged | Combined | SE | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task (list) | $/task (billed) |
|---|---|---|---|---|---|---|---|---|---|
| low | 23 | 88.65 | 0.67 | 73.11 | 21 | 228 | 8.05 | 0.0577 | 0.1010 |
| high | 23 | 88.61 | 0.96 | 74.87 | 20 | 225 | 8.66 | 0.0667 | 0.0680 |
| max | 23 | 88.36 | 0.98 | 74.01 | 20 | 226 | 10.60 | 0.0741 | 0.0741 |

pass@1 is 0.913, 0.870 and 0.870 from Low to Max. The combined score is flat
across levels (a 0.3-point spread, inside one standard error), and each step
up adds minutes and under a cent per task without more solves.

## Cost

The sweep billed a DeepSeek API key, so this is metered API spend. `list_usd`
prices each run's tokens at DeepSeek's off-peak list price for
`deepseek-flash`, checked 2026-10-19 ($0.15 input cache miss, $0.003 cache
hit, $0.60 output per million); it is the board's $/task. DeepSeek bills 2x on
weekdays from 01:00 to 04:00 and 06:00 to 10:00 UTC, and the harness meters
each call at its own time, so `billed_usd` is what DeepSeek charged: higher on
the 14 Low runs and 1 High run that had calls in those hours. The sweep came to
$4.56 at list price and $5.59 billed. dsh titles each session with one small
`deepseek-flash` call that records no usage (66 of 69 runs); it is counted in
`unmetered_title_calls` and not priced, which understates cost by well under a
cent per run. Three runs each had one interrupted reply that reported no
usage, also unpriced. Solver inference only; judging is excluded.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI with its v3.4
settings and binary pin, and GPT-6.1 Sol (OpenAI) at medium effort through
Codex CLI 0.159.0, with equal weight. Grok 4.6, the second judge for most
Frontier v4 columns, runs through Cursor, and the Cursor account was out of
usage on 2026-10-23; the owner chose GPT-6.1 Sol for the seat rather than
wait, as v3.20 did for Grok 4.7. The rubric, prompts, schemas, seed, repeats,
gate allowance, weights and both judges' pins equal the published v3.20
record. Muse Code's updater had removed the v3.4 Muse binary, so the round ran
a byte-identical backup matched by sha256. Both judges retook the exam under
v3.27 and passed every gate with no allowance used.

Most other columns, Claude Opus 5.5 and GPT-6.1 Sol included, are judged by
Muse Spark 1.3 and Grok 4.6. Scores from different panels are not calibrated
against each other, so DeepSeek V4.1 Flash's Code quality and combined score
are not strictly comparable with those columns. GPT-6.1 Sol therefore judges a
column it is shown beside; its own column was judged without it.

The two judges disagree in level: GPT-6.1 Sol rates DeepSeek V4.1 Flash's
reviewed Code quality about 8 points above Muse Spark 1.3 (74.5 against 64.9
at Low, 76.6 and 68.4 at High, 74.5 and 67.1 at Max, a gap of 7.3 to 9.6). The
published score is their mean; `combined_single_judge` gives the combined
score from each judge alone, 87.14 to 87.24 from Muse and 89.57 to 90.10 from
Sol.

Each judge made 80 calibration calls, 69 primary reviews, 69 intent probes,
69 answer-key matches, 3 repeats and 6 pairwise checks. Muse needed a second
attempt on two calls and Sol on ten, under the single-retry rule. Six of Sol's
answer-key matches are published through the standing
`recover_one_based_indexes` rule: both attempts failed only because the
departure indexes were one-based, so they were moved to zero-based with
statuses untouched and the original kept in the receipt. Neither judge
produced a reviewer fallback. Judging ran on 2026-10-23, 09:34 to 12:36 UTC.

## Harness and run notes

- DeepSeek Harness (`@deepseek-ai/dsh`, DeepSeek's official open-source agent,
  MIT), version 0.2.1-rc.2, a developer preview prerelease, in its headless
  profile, pinned by exact version and a hash of its whole install tree. It
  ran inside VulcanBench's macOS outer sandbox with dsh's own sandbox and
  approvals off and a fresh home folder per run. Web tools were off, as for
  every harness. dsh's default-on session-log upload to DeepSeek and its
  OpenTelemetry feedback upload were off (owner choice); the model never sees
  either, and task content still reaches DeepSeek in the model requests.
  Everything else was as shipped.
- Every run summary carries a clean source block from
  `bench/2026-10-20-deepseek-dsh-frontier-v4` and records the frozen suite
  lock's task hash, so no hash bridge is needed.
- The sweep ran 2026-10-20 07:11 to 2026-10-22 17:19 UTC. The owner paused it
  twice between tasks during Low; each run a pause interrupted (Low metercore
  and Low reflowcore) was set aside unscored and the task rerun. macOS went
  from 26 to 27.0.1 during the second pause; re-grading the 13 Low runs
  finished before it on 27.0.1 gave identical functional scores, and the
  pinned dsh install hash was unchanged.
- No run reached the 3-hour bound, and the sweep's per-minute overlap logger
  recorded no other benchmark job beside it.
- The API key was in the agent's environment and the shell network was not
  isolated, as recorded on every run. Every integrity audit is clean: no web
  access, no benchmark data or answer-key paths.
- One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, dsh session logs and solver traces, the two
pause-interrupted attempts, and host binary paths.
