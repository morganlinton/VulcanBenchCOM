# VulcanBench Frontier v4: Reflection Beam under Code quality protocol v3.28

Public record for the October 2026 Reflection Beam report: 115 solver runs
from the October 23 to 25, 2026 Mirror CLI effort sweep (23 tasks, one
attempt per task at each of Beam's five reasoning levels, Low to Max, on
Reflection's API, local sandbox, flat 3-hour task bound, one task at a time),
judged for Code quality by Muse Spark 1.3 and GPT-6.1 Sol, with Code quality
at 33% of the combined score. Functional, lint and complexity, and security
measurements come from the sweep. Every run finished inside the bound; 99 of
the 115 carry a published Code quality score.

Reflection Beam ran through Reflection's API as `Beam-1.0-501B-A23B`
(Reflection Beam 1.0, 501B total and 23B active parameters), the versioned id
Mirror uses by default; the API's model list shows the alias `Beam-501B-A23B`,
which the sweep checked before each level. Every inference in Mirror's
conversation database names the requested model, so model identity is
harness-recorded. Beam's `reasoning_effort` takes low, medium, high, xhigh and
max; Extra-high here is xhigh.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, status and, for an unjudged run, why; the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, with no-code runs as 0 and from each judge alone, integrity-audit verdicts, the task hash, the harness version and install hash, timing, raw tokens, model calls, failed requests, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: combined score over judged runs and with no-code runs as 0, per-judge means and single-judge combined scores, pass counts over all runs, hidden behaviours fixed, runtime and tokens |
| [calibration.json](calibration.json) | Each judge's calibration verdict under v3.28, every gate value, the allowance rule and control means |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, why GPT-6.1 Sol holds the second seat, judge settings and binary pins, counted calls, second attempts, every operator marker, transport retries and operator recoveries |
| [economics.json](economics.json) | Token, model-call and runtime aggregates per effort and sweep totals; no price exists for Beam |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol document, the decision record and the code |
| [Scores CSV](../swe-v4-beam-v328-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per judged run, with the judges that have a valid review weighted equally:

```
reviewed        = mean(reviewed_score of each scored panel)
intent_recovery = mean(intent_recovery of each scored panel)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33, or reviewed alone when the run passed no quirk family
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` (lint and complexity, stored as `automated_quality`)
and `security` are on a 0 to 1 scale and are the values recorded by the sweep.
Group means weight the cell's judged tasks equally; standard errors are one
sample standard error across them. The measured-maintenance layer (12 of the
33 points) is not built; the pre-registered split of 24 reviewed plus 9 intent
recovery is in force, so Frontier Code quality is the reviewed layer plus
intent recovery. It is never compared with Routine v1 Code quality.

| Effort | Judged | Combined | SE | No-code as 0 | Code quality | Passed of 23 | Behaviours fixed of 231 | Min/task | Tokens/task |
|---|---|---|---|---|---|---|---|---|---|
| low | 11 | 39.51 | 2.35 | 18.90 | 72.92 | 0 | 3 | 0.38 | 0.09M |
| medium | 20 | 44.79 | 1.90 | 38.95 | 70.46 | 0 | 26 | 1.93 | 0.44M |
| high | 23 | 55.01 | 2.79 | same | 68.52 | 0 | 93 | 9.20 | 3.39M |
| extra-high | 23 | 64.72 | 3.76 | same | 66.95 | 4 | 130 | 18.75 | 12.42M |
| max | 22 | 63.92 | 4.12 | same | 65.81 | 6 | 134 | 22.45 | 17.29M |

The combined score climbs about 25 points from Low to Extra-high; Beam passes
its first tasks at Extra-high. Tasks passed, behaviours fixed, minutes and
tokens count all 23 runs at every level.

## Which runs are judged

- 3 runs ended with an empty patch (Low blendcore and metercore, Medium
  granarycore). The population builder excludes them, as every round has since
  v3.15.
- 12 runs changed no source file, only file modes from `chmod` or scratch
  files (10 at Low, 2 at Medium), so the review evidence was the untouched
  starting code. On 2026-10-26 the owner excluded them like empty patches,
  after the judges had reviewed them; each panel's review is kept as
  `selected.excluded.json` under an `operator-invalid.json` marker with rule
  `no_source_change`, and is not used.
- These 15 runs have no code to judge and count as failed tasks.
  `combined_no_code_zero` counts them as 0 over all 23 runs: 18.90 at Low and
  38.95 at Medium, read like the board's timeouts-as-0 figure.
- Max hedgecore passed every hidden test but is unjudged: Beam left 6.5M
  characters of scratch files in its workspace, beyond GPT-6.1 Sol's input
  limit (owner decision 2026-10-25: no Sol vote), and Muse Spark 1.3's two
  reviews cited no code (rule `invalidate_unrecoverable_primary`). It counts
  as a passed task and is left out of both combined figures.
- Max payrollcore's evidence was also over GPT-6.1 Sol's input limit; it is
  published from Muse Spark 1.3 alone: the summary publishes a run from the judges with a valid review.
- 16 published runs passed no quirk family, so intent recovery has no
  denominator and their 9 points move to the reviewed score.

## Time and tokens

Reflection publishes no price for Beam (its public API beta is free to
start), so no run is priced: cost is unavailable, not zero. Tokens are summed
from Mirror's per-call usage records, input (cached included) plus output;
cached input is 82% to 97% of input by level, and Mirror reports no separate
reasoning count. The sweep used 773M tokens over 11,596 model calls and 20.2
solver hours. Six model requests in five runs failed (three "temporarily
unavailable", three HTTP 520); Mirror carried on and every run finished.
Judging is excluded.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI with its v3.4
settings and binary pin, and GPT-6.1 Sol (OpenAI) at medium effort through
Codex CLI 0.159.0, with equal weight. Grok 4.6, the second judge for most
Frontier v4 columns, runs through Cursor, and the Cursor account was still out
of usage on 2026-10-24; the owner kept GPT-6.1 Sol in the seat, the pair v3.27
used for DeepSeek V4.1 Flash. The rubric, prompts, schemas, seed, repeats,
gate allowance, weights and both judges' pins equal the published v3.27
record. The Muse binary is a byte-identical backup of the v3.4 binary matched
by sha256. Both judges retook the exam under v3.28 and passed every gate with
no allowance used.

Most other columns, Claude Opus 5.5, GPT-6.1 Sol and GPT-6 Astra included,
are judged by Muse Spark 1.3 and Grok 4.6. Scores from different panels are
not calibrated against each other, so Reflection Beam's Code quality and
combined score are not strictly comparable with those columns. GPT-6.1 Sol
therefore judges a column it is shown beside; its own column was judged
without it.

The two judges disagree in level: GPT-6.1 Sol rates Reflection Beam's reviewed
Code quality 10.1 to 17.6 points above Muse Spark 1.3 (15.2 at Low, 17.6 at
Medium, 14.0 at High, 10.7 at Extra-high, 10.1 at Max). The published score is
their mean; `combined_single_judge` gives the combined score from each judge
alone.

Each judge was sent 80 calibration calls, 112 primary reviews, 112 intent
probes, 5 repeats and 10 pairwise checks, and Muse 112 answer-key matches to
Sol's 111. Muse needed a second attempt on two calls and Sol on 39, under the
single-retry rule: 36 answer-key matches and three primary reviews that first
failed when Codex returned 429 after the ChatGPT usage window ran out. 24 of
Sol's answer-key matches are published through the standing
`recover_one_based_indexes` rule: both attempts failed only because the
departure indexes were one-based, so they were moved to zero-based with
statuses untouched and the original kept in the receipt. Neither judge
produced a reviewer fallback. Judging calls ran on 2026-10-25, 04:31 to 20:21
UTC; the summary was written on 2026-10-26 after the no-source-change
exclusions.

## Harness and run notes

- Mirror CLI (`reflection-mirror`, Reflection's open-source coding agent,
  Apache-2.0), version 0.1.1, an early beta, in its one-shot `exec` mode,
  pinned by exact version and a content hash of its installed package. It ran
  inside VulcanBench's macOS outer sandbox with Mirror's tool approvals
  automatic (Mirror's own sandbox workspaces need a microsandbox VM) and
  updates off. Each run had a private Mirror home with the usage notice
  acknowledged and only its workspace trusted (owner approved), analytics off
  and no web tools.
- Task files are staged without execute bits, as for every column. Where Beam
  met Permission denied on the legacy binary, Mirror appended a note calling
  it a sandbox denial; two Low runs ended saying the sandbox blocked the
  binary, which it does not. Two other Low answers said the full
  reconstruction was beyond the session's scope. The adapter archived model
  messages and usage but not tool calls, so how often Beam saw the note
  cannot be counted.
- Reflection's daily API token limit stopped the sweep on 2026-10-24 at 13:38
  UTC after 13 Max tasks. The 1,200 attempts it cut short hold no summary and
  were set aside; the sweep resumed after the 00:00 UTC reset. No finished run
  was affected.
- Every run summary carries a clean source block from
  `bench/2026-10-23-beam-mirror-frontier-v4` and records the frozen suite
  lock's task hash.
- The sweep ran 2026-10-23 21:15 to 2026-10-25 04:31 UTC. No run reached the
  3-hour bound (the longest took 57.1 minutes), and the sweep's per-minute
  overlap logger recorded no other benchmark job beside it.
- The API key was in the agent's environment and the shell network was not
  isolated, as recorded on every run. Every integrity audit is clean: no web
  access, no benchmark data or answer-key paths.
- One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, Mirror conversation databases and full solver
traces (a structure-only redacted trace of every run, with model calls, token
use and timing, is public at https://github.com/morganlinton/vulcanbench-beam-traces; this sweep's adapter recorded no tool
names, inputs or outputs), the 1,200 attempts cut short by the daily token limit, and host binary
paths.
