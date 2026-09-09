# VulcanBench-SWE v4: Astra and Fable 5.1 under Code quality protocol v3.4

Public record for the September 9, 2026 Astra and Fable 5.1 comparison: 230
solver runs from the September 2026 effort sweep (23 matched tasks, five effort
levels, GPT-6 Astra in Codex and Fable 5.1 in Claude Code with disclosed Opus
fallbacks), judged for Code quality by a neutral two-model panel with Code
quality at 33% of the combined score. No solver ran for this report;
functional, automated quality and security measurements come from the sweep.

## Files

| File | What readers can inspect |
|---|---|
| [runs.json](runs.json) | Every run: task, effort, the four score factors, both judges' reviewed score, human readability, maintainability and intent recovery, the combined score under the 33% and prior 20% profiles, timing, raw tokens and token usage, API-equivalent cost with Astra's long-context upper bound, CLI version, fallback flag and evidence hash |
| [runs.csv](runs.csv) | The same 230 records flat for spreadsheets |
| [groups.json](groups.json) | Ten model/effort aggregates with sample standard errors, per-judge means, pass counts, runtime and fallback counts |
| [calibration.json](calibration.json) | Each judge's calibration verdict, every gate value, control means and the operator record; GLM 5.3's failed attempt is included |
| [judge-protocols.json](judge-protocols.json) | The exact system text, rubric, pair instruction, probe and match instructions, schemas, weights, repeats, seed, allowance rule and control source hashes for both frozen protocol versions |
| [economics.json](economics.json) | API-equivalent cost and raw-token aggregates per model and effort, sweep totals, the rate tables, sources and pricing limitations |
| [provenance.json](provenance.json) | Frozen source hashes, export checks and publication limits |
| [REPRODUCING.md](REPRODUCING.md) | Public arithmetic checks and links to the protocol documents, controls, runner and operator wrapper |
| [Scores CSV](../swe-v4-astra-fable51-v34-scores.csv) | Aggregate values for spreadsheets |

## Scoring

Per run, with both judges weighted equally:

```
reviewed        = mean(muse.reviewed_score, grok.reviewed_score)
intent_recovery = mean(muse.intent_recovery, grok.intent_recovery)
code_quality    = (0.24 * reviewed + 0.09 * intent_recovery) / 0.33
combined_33     = 100 * (0.50 * functional + 0.085 * quality + 0.085 * security + 0.33 * code_quality / 100)
combined_20     = 100 * (0.50 * functional + 0.15 * quality + 0.15 * security + 0.20 * code_quality / 100)
```

`functional`, `quality` and `security` are on a 0 to 1 scale and are the
values recorded by the effort sweep. `combined_20` applies the prior
50/15/15/20 profile to the new Code quality scores for comparison only.
Group means weight the 23 tasks equally. Standard errors are one sample
standard error across tasks.

The reviewed score is the mean of six dimensions each scored 0 to 4, scaled to
100: naming, presentation and intent (human readability) and structure,
changeability and verifiability (maintainability). Intent recovery is the share
of a task's documented specification departures that the judge recovered from
the specification and the code alone, matched against a frozen answer key, with
the denominator limited to departures the submission actually passed tests for.
The designed measured-maintenance layer (12 of the 33 points) is not built; the
pre-registered fallback split of 24 reviewed plus 9 intent recovery is in force.

## Cost and tokens

Each run carries `raw_tokens` (the solver CLI's total including cache reads),
`token_usage` (the receipt's breakdown), `estimated_usd` and, for Astra,
`long_context_upper_usd`. Prices are list API rates checked on the date in
`economics.json`, cache-aware, solver inference only; judging is excluded and
subscription bills are not observable. `cli_summary_units` keeps the CLI's own
summary count, which for Claude Code is cache-price-weighted units rather than
tokens; do not treat it as a token count.

## Judges

The scored panel is Muse Spark 1.3 (Meta) through the Muse CLI on its
Standard tier, and Grok 4.6 (xAI) through the Cursor CLI at medium effort.
Neither lab has a model on this board. Sessions are fresh, tools disabled,
workspace empty, model identity checked per call, solver labels withheld.
Both judges passed a ten-program, five-repeat, twenty-gate calibration exam
with no allowance used before scoring any submission. GLM 5.3 failed the exam
on validity. Astra and Claude Opus 5 passed under an earlier protocol version
but are not part of the published score; their reviews are withheld.

Muse completed 690 judge calls with two excerpt recoveries and one retry after
an outside SIGTERM. Grok completed 960 calls with five excerpt recoveries and
six rate-limit resumes. Neither judge produced a reviewer fallback. Every
operator intervention is recorded in the run logs and receipts in the harness
repository.

## Withheld

Raw prompts and responses, submitted patches and reconstructed sources, the
quirk answer keys (they describe hidden-test behaviour), reviewer session
identifiers and usage receipts, and the retired Astra and Opus 5 reviews.
