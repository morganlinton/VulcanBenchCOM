# Reproducing the Verdict v1 Jev results

This bundle carries metrics only. The items themselves embed VulcanBench
Frontier v4 issues and agent patches, so they stay private and canaried.

## Files

- `results.json`: every published number, including per-family metrics for
  Jev and for the majority-answer floor, the confusion counts, the accuracy
  by input size, and the four-wording phrasing probe.
- `scores.csv`: the same per-family metrics as a table, one row per source
  and family, plus the ground-truth overall row.
- `report.md`: the full report as published on the site.

## Public arithmetic checks

All figures below come from `results.json`.

1. **Overall accuracy.** `results.jev-1.13.0.overall.accuracy` is the mean of
   the ground-truth families only, weighted by item count:
   (0.3732 x 611 + 0.3339 x 611 + 0.4975 x 611 + 1.0 x 19) / 1852 = 0.4077.
   `quality-preference` is excluded, and `agreement_only_families` names it.
2. **The floor.** `results.majority_floor` answers each family's most common
   dev-split label on every test item. On `patch-verdict` that is "passes",
   which is right for 383 of 611 items, so 0.6268.
3. **Jev said no to everything.** In
   `diagnostics.confusion.patch-verdict`, the only two keys are
   `true->false` (383) and `false->false` (228). No item was predicted to
   pass. `patch_verdict_mean_p_pass` is 0.2196.
4. **False alarms on regression.** In
   `diagnostics.confusion.patch-regression`, `false->true` is 403 against
   `true->true` of 32.
5. **The probe mirrors.** In `phrasing_probe.variants`, `original.mean_p_true`
   is 0.2202 and `inverted.mean_p_true` is 0.7795, and
   `phrasing_probe.agreement["original vs inverted"]` is 1.0 after folding the
   inverted answers back.
6. **Style is not explained by length.** `quality_preference_longer_patch_baseline`
   is 0.4469, and `quality_preference_answer_balance` is 180 A to 131 B
   against Jev's 183 A to 128 B.

## Re-running it

The harness code is in the [VulcanBench
repository](https://github.com/morganlinton/VulcanBench) under
`harness/verdict/` and `scripts/verdict-v1/`. With a TypeSafe API key in
`.env` and local Frontier v4 run directories:

```bash
python scripts/verdict-v1/build_items.py
python scripts/verdict-v1/run_typesafe.py
python scripts/verdict-v1/probe_phrasing.py
python scripts/verdict-v1/export_results.py
```

Items are rebuilt from local run directories, so anyone without those runs
cannot reproduce the item file. The metrics here are checkable from
`results.json` alone.

## What these numbers do not show

No other model has been run on these items, so the only reference points are
the majority floor and, for the style family, the Muse and Grok code-quality
panel. Jev is pinned to `jev-1.13.0`; a later version is a new measurement,
never an update of this one.
