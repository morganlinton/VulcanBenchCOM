# Reproducing the Verdict v2 Jev results

This bundle carries metrics only. The item files stay private and
gitignored, because the software items embed benchmark tasks and hidden
tests. The code, the freeze record, the pilot gate table and every published
number are public.

## Files

- `results.json`: every published number, per family and per index, for
  Jev 1.13.0 and for the GPT-6 Astra (high effort) reference row, with the
  shortcut baselines, probability ranges, run totals and the freeze record.
- `scores.csv`: one row per family plus the four indices. Columns: `area`,
  `family`, `pillar`, `test_items`, `floor` (percent), `jev_skill`,
  `jev_ci_low` and `jev_ci_high` (95% interval), `jev_ranking` (AUROC, blank
  where the options differ per item), `reference_skill` and
  `best_shortcut_skill`. Values use the report's rounding. The Calibration
  Index row is a Brier skill score on a 0 to 1 scale, not a skill on 0 to
  100.
- `report.md`: the full report as published on the site.

## How the numbers are computed

- **Skill** per family is `100 * (accuracy - floor) / (1 - floor)`, using
  each model's top answer. The floor is the best of always giving the most
  common answer, guessing uniformly, and every shortcut baseline recorded
  for that family, measured on the published test split. 0 is no better
  than that, 100 is perfect. Negative values are published, not clipped.
- **Verdict Index** is the mean skill over the 20 families. **Software** and
  **General** are the same mean over the 12 software and 8 general families.
- **Calibration Index** is the mean Brier skill score against forecasting
  each family's answer frequencies, shown beside the Verdict Index and never
  folded into it.
- **Intervals** are 95% bootstrap intervals that resample source units
  (tasks, repositories or generator seed groups) 2,000 times, keeping each
  family's floor strategy fixed at the one chosen on the real data.
- **Ranking** is AUROC for families with a fixed set of options.

## Public arithmetic checks

From `scores.csv` alone:

1. **Verdict Index.** The mean of the 20 family `jev_skill` values is 45.91,
   which rounds to the published 45.9. The same mean over
   `reference_skill` is 91.735, published as 91.7.
2. **Software sub-index.** The mean of the 12 rows with `pillar` software is
   49.58 for Jev (published 49.6) and 86.225 for the reference (published
   86.2).
3. **General sub-index.** The mean of the 8 rows with `pillar` general is
   40.40 for Jev (published 40.4). Every general `reference_skill` is 100.0,
   so the reference's General sub-index is 100.0: it answered all 1,920
   general test items correctly.
4. **Item counts.** `test_items` sums to 4,774 over the 20 families, 2,854
   over the software ones and 1,920 over the general ones.
5. **Separation.** On every index row, Jev's `jev_ci_high` is below the
   reference's value, and in `results.json` the reference's lower bound
   (`results["gpt-6-astra-high (reference)"].indices.*.ci95[0]`) is above
   Jev's upper bound. `separated` records true for all three skill indices.
6. **The shortcut caveat.** `best_shortcut_skill` is measured on the test
   split. It is 15 or below for every family except "Which version is
   vulnerable?", where choosing the shorter version reads 20.0 on the test
   split against 11.6 on the full build the gate checked. Jev's 22.9 on that
   family is above it, but only just.

From `results.json`:

7. **Skill from accuracy and floor.** In
   `results["jev-1.13.0"].families["code-output"]`, `accuracy` is 0.5536 and
   `floor` is 0.2575, so `100 * (0.5536 - 0.2575) / (1 - 0.2575)` gives
   39.9, the published `skill`.
8. **Calibration Index.** The mean of the 20 `brier_skill` values in
   `results["jev-1.13.0"].families` is 0.3306, which matches
   `indices.calibration_index.value` and is published as 0.33.
9. **Cost and latency.** `run["jev-1.13.0"]` records 4,774 answers,
   `total_cost_usd` 0.5768 (published $0.58, about $0.12 per 1,000
   questions), `latency_ms_p50` 294.6 (0.29 s) and `latency_ms_p95` 415.1
   (0.42 s). The reference's `total_cost_usd` is null because it ran on a
   ChatGPT subscription.

## Freeze record

The item set was frozen before the test split was run:

- Items: 5,926 (4,774 in the published test split), seed 20260924, 300
  requested per family, built 2026-09-25.
- Item file SHA-256:
  `ab5a28280bf80e97b0aa91583a95c1ece8402130520614402f5696543be4481e`
- Commit: `693377075baf8d3b7f77efbd359b82b72970387d` (clean tree)

The same SHA-256, commit and seed appear under `freeze` in `results.json`.

## Re-running it

The code is in the [VulcanBench
repository](https://github.com/morganlinton/VulcanBench): the suite in
`harness/verdict/v2/`, the spec in `docs/VERDICT_V2.md`, and the decisions,
including the gate amendment, in `docs/DECISIONS.md` (September 24 and 25,
2026).

```bash
python scripts/verdict-v2/build_items.py --per-family 300
python scripts/verdict-v2/audit_ground_truth.py
python scripts/verdict-v2/run_jev.py
python scripts/verdict-v2/run_reference.py
python scripts/verdict-v2/export_results.py
```

The software families are built from private local run archives, so anyone
without them cannot rebuild the item file. The metrics here are
checkable from `scores.csv` and `results.json` alone.

## What these numbers do not show

The reference row shows that each family is answerable from the same
inputs; it is not a leaderboard entry. The general families have no
headroom for the reference, so they cannot rank two strong reasoning models
against each other. Jev is pinned to `jev-1.13.0`; a later version is a new
measurement, never an update of this one. Verdict and Frontier scores
measure different things and are not comparable.
