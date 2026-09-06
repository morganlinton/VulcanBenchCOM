# SWE v4 comparison sources

The two CSV files are unchanged copies of the completed Astra/Fable comparison
artifacts in the VulcanBench harness repository, under
`docs/results/swe-v4-astra-fable51-2026-09/`:

- `effort-comparison.csv` becomes `swe-v4-astra-fable51-scores.csv`.
- `api-equivalent-costs.csv` becomes `swe-v4-astra-fable51-costs.csv`.

`combined` is the total percentage score using 50% functional, 15% automated
quality, 15% security and 20% Code quality. `passed` is a separate functional
count, not the total score. `raw_tokens` is a sum over 23 runs; divide by `n`
for tokens per task. `historical_summary_units` preserves the old receipt field
for provenance and must not be presented as raw tokens or dollars.

Costs are frozen USD API-equivalent estimates at Standard rates checked
September 6, 2026, not subscription charges or a current pricing quote.
They include exposed solver auxiliary/fallback calls but exclude judges and
infrastructure. Astra per-request context sizes are unavailable, so the costs
CSV also contains a conservative long-context sensitivity bound.

The PNG is the exact user-selected 2400 by 1620 card, not regenerated:
SHA-256 `138c96d9fdffab4845d1b373c035b71d180272a9901fcb98bb7ad04ef8dd84b3`.
Its score panel is a focused-scale dot-and-interval comparison; runtime uses
zero-based grouped bars. Both show five matched effort levels, n=23 per cell,
with sample SE whiskers. Green circles and clay diamonds/hatching distinguish
models without relying on color alone. The index retains full-size access,
an HTML table for exact lookup, and visible estimation/fallback caveats.

Run `python3 scripts/check_benchmark_index.py` to check the card hash, table
values, weights, comparative claims, local links and archive coverage.
