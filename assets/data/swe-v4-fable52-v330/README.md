# VulcanBench Frontier v4: Claude Fable 5.2 under Code quality protocols v3.30.2 and v3.30.3

Public record for the November 2026 Claude Fable 5.2 report: 115 solver runs
from the November 9 to 11, 2026 Claude Code effort sweep (23 tasks, one
attempt per task at each of the five effort levels Low to Max, through Claude
Code 2.1.321 on a Claude subscription), judged for Code quality by Muse Spark
1.3 and GPT-6.1 Sol with Code quality at 33% of the combined score.
Functional, lint and complexity, and security measurements come from the
sweep. All 115 runs finished inside the flat 3-hour task bound, all 115 passed
every hidden test, and all 115 carry a published Code quality score.

Claude Fable 5.2 (`claude-fable-5-2`) is a new model. It is not Fable 5.1,
whose record is in [../swe-v4-astra-fable51-v34/](../swe-v4-astra-fable51-v34/).

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, hidden behaviours fixed, each judge's reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles and from each judge alone, integrity-audit verdicts, result receipts, tool-call count, timing, raw and thinking tokens, list-price cost, CLI version, task hash, passed quirk families and evidence hash |
| [runs.csv](runs.csv) | The same 115 records flat for spreadsheets |
| [groups.json](groups.json) | Five effort aggregates with sample standard errors: per-judge means, pass counts, hidden behaviours fixed, runtime, cost, tokens, thinking tokens and tool calls |
| [calibration.json](calibration.json) | Each judge's calibration verdict, every gate value, the allowance rule and control means, and Grok 4.6's failed v3.30 exam |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule, retry rule, control source hashes, the two published protocols and their Muse siblings, both population records, judge pins, counted calls, second attempts and every operator recovery |
| [economics.json](economics.json) | List-price cost and token aggregates per effort, sweep totals, the pricing method and its limits |
| [card-table.csv](card-table.csv) | The harness card's per-level table, byte for byte: Fable 5.2 as published, Fable 5.1 and Opus 5.5 under the matched Muse and Sol panel (comparison only), GPT-6 Astra as published |
| [muse-like-for-like.csv](muse-like-for-like.csv) | Code quality and combined score from Muse Spark 1.3 alone for all four models, byte for byte from the harness |
| [provenance.json](provenance.json) | Frozen source hashes, the memorization check summary, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, runners and decision records |
| [Scores CSV](../swe-v4-fable52-v330-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with the two judges weighted equally:

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
figure, not the published score. Group means weight the cell's 23 tasks
equally. Standard errors are one sample standard error across tasks. Every
Claude Fable 5.2 run passed at least one quirk family, so intent recovery is
scored for every run.

| Effort | Judged | Combined | SE | Code quality | Muse reviewed | Sol reviewed | Passed of 23 | Behaviours fixed of 231 | Min/task | $/task |
|---|---|---|---|---|---|---|---|---|---|---|
| low | 23 | 91.92 | 0.39 | 80.63 | 76.4 | 83.1 | 23 | 231 | 4.6 | 1.72 |
| medium | 23 | 92.25 | 0.44 | 81.49 | 77.1 | 84.6 | 23 | 231 | 4.3 | 1.72 |
| high | 23 | 92.76 | 0.43 | 82.95 | 78.4 | 86.4 | 23 | 231 | 7.8 | 2.86 |
| extra-high | 23 | 93.25 | 0.45 | 84.25 | 80.4 | 87.7 | 23 | 231 | 14.2 | 4.99 |
| max | 23 | 93.85 | 0.42 | 86.02 | 82.2 | 89.6 | 23 | 231 | 37.1 | 10.88 |

GPT-6.1 Sol rates the reviewed layer 6.7 to 8.1 points above Muse Spark 1.3.
Every run's integrity audit is clean (no web access, no benchmark-data or
answer-key paths; `integrity_audit` in runs.json); the files the audit saw
written outside the workspace were all scratch space under the temporary
directory.

## The judge panel

Round v3.30 seated Muse Spark 1.3 and Grok 4.6, the panel of the Claude Opus
5.5 column. Grok 4.6 failed calibration gate `g14_pair_2_1` and judged
nothing; Muse Spark 1.3 passed every gate, judged Low to Extra-high under
v3.30 and Max under v3.30.1 (gated by its v3.30 verdict). On the owner's
choice GPT-6.1 Sol, through Codex CLI 0.159.0 at medium effort, took the
seat, passed every gate under v3.30.2, and judged Low to Extra-high under
v3.30.2 and Max under v3.30.3, on byte-copied freezes of the same
populations. The published rounds score Sol themselves and read Muse from its
own rounds as a scored sibling, matched by protocol hash. The rubric,
prompts, schemas, seed, repeats, gate allowance, weights, retry rule, control
hashes and both judges' pins equal the published v3.27 record; only the
neutrality and seat notes differ.

Most other Frontier v4 columns, Claude Fable 5.1 and Claude Opus 5.5
included, are judged by Muse Spark 1.3 and Grok 4.6, so the published scores
come from different panels. The harness also ran comparison-only rounds
v3.30.4 and v3.30.5 in which GPT-6.1 Sol reviewed the frozen Fable 5.1 and
Opus 5.5 patches; their figures appear on the card and in `card-table.csv`,
and the board keeps both models' published scores. GPT-6 Astra cannot be
judged by Sol, which shares its lab. `muse-like-for-like.csv` gives the only
panel that judged all four.

Sol made 368 counted calls under v3.30.2 (80 calibration, 92 primary, 4
repeats, 8 pairwise, 92 probes, 92 matches) and 70 under v3.30.3; Muse made
the same counts under v3.30 and v3.30.1. Twelve Sol answer-key matches
numbered departures from one instead of zero and were published through the
frozen rule `recover_one_based_indexes`, which leaves every score unchanged.
One Muse probe excerpt under v3.30 was re-wrapped to the source's line breaks
and then had to be verbatim and pass the frozen validator. No operator
marker, no reviewer fallback.

## Cost and tokens

Each run carries `raw_tokens` (input, cache read, cache creation and output,
summed over the run's result receipts), `token_usage` (the breakdown, with
thinking tokens from the raw stream) and `estimated_usd`, Claude Code's own
list-price total for the session, the cost basis of every Claude column.
Claude Code reports that total cumulatively on each receipt; two runs (low
matchcore and extra-high reflowcore) have two receipts because a background
task resumed the session after the model stopped, and the export takes the
session's last total and sums tokens over both. The run summaries kept only
the last receipt and recorded no thinking tokens (adapter issues, grading
unaffected); every figure here comes from the archived streams, whose hashes
match the population record. The sweep comes to $509.85 and 26.07 solver
hours; judging is excluded.

## Population and run notes

- Claude Code 2.1.321, pinned by hash with auto-updates off, permission mode
  auto, safe mode, no web access, refusal fallback on and never used: every
  reply in every stream is `claude-fable-5-2`.
- Runs used `--thinking-display summarized`, so the streams keep summaries of
  the model's thinking, a run condition earlier Claude columns did not have.
  The summaries are withheld because they describe the reference programs.
- From the tag `bench/2026-11-09-fable52-frontier-v4`; every run's source
  block is clean and its task hash equals the frozen suite lock.
- Low to Extra-high ran on November 9 and 10. The Fable usage limit refused
  the first 69 Max attempts; they did no work, hold no summary and are kept
  apart. Max ran from November 10 at 23:15 to November 11 at 13:28 PST.
- No run reached the 3-hour bound; the longest, max reflowcore, took 52.1
  minutes. One attempt per task and level; runs were not repeated.

## Withheld

Raw prompts and responses, thinking summaries, submitted patches and
reconstructed sources, the quirk answer keys (they describe hidden-test
behaviour), reviewer session identifiers and usage receipts, solver event
streams and host binary paths. A structure-only redacted trace of every run
is public in
[vulcanbench-fable52-traces](https://github.com/morganlinton/vulcanbench-fable52-traces).
