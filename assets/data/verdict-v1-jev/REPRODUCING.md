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

1. **Overall accuracy.** `results.jev-1.13.0.overall` covers the
   ground-truth families only, weighted by item count. At the withdrawn 0.5
   cutoff: (0.3732 x 611 + 0.3339 x 611 + 0.4975 x 611 + 1.0 x 19) / 1852 =
   0.4077. At the fitted cutoffs, the same arithmetic over 0.6285, 0.9313,
   0.4975 and 1.0 gives `accuracy_at_threshold` 0.6890.
   `quality-preference` is excluded, and `agreement_only_families` names it.
2. **The floor.** `results.majority_floor` answers each family's most common
   dev-split label on every test item. On `patch-verdict` that is "passes",
   which is right for 383 of 611 items, so 0.6268.
3. **The probabilities never reach the boundary.** In
   `results["jev-1.13.0"].families["patch-verdict"]`, `p_true_min` is 0.09
   and `p_true_max` is 0.42, so the 0.5 cutoff the first version of this
   report used could never fire: `diagnostics.confusion.patch-verdict` has
   only `true->false` (383) and `false->false` (228).
   `patch_verdict_mean_p_pass` is 0.2196.
4. **The ranking, which needs no cutoff.** The same block gives `auroc`
   0.6899, against 0.5 for chance. `accuracy` (0.3732) is the withdrawn
   0.5-cutoff figure; `accuracy_at_threshold` (0.6285) uses `threshold`
   0.17, fitted on the development split and recorded in
   `thresholds.values`. The floor for the family is
   `majority_label_share`, 0.6268.
5. **Size does not explain anything.** In
   `diagnostics.patch_verdict_by_input_tokens`, every bucket's
   `accuracy_at_threshold` equals its `majority_baseline` exactly, and
   `pass_rate` climbs from 0.5433 to 0.8846 to 0.8947. The withdrawn
   "accuracy falls with patch length" finding was that climb, seen through
   the broken cutoff.
6. **False alarms on regression.** In
   `diagnostics.confusion.patch-regression`, `false->true` is 403 against
   `true->true` of 32.
7. **The probe mirrors.** In `phrasing_probe.variants`, `original.mean_p_true`
   is 0.2202 and `inverted.mean_p_true` is 0.7795, and
   `phrasing_probe.agreement["original vs inverted"]` is 1.0 after folding the
   inverted answers back.
8. **Style is not explained by length.** `quality_preference_longer_patch_baseline`
   is 0.4469, and `quality_preference_answer_balance` is 180 A to 131 B
   against Jev's 183 A to 128 B.

9. **The control.** `controls.runs` holds two runs of GPT-6 Astra (high
   effort) on the pass question, one per split, each with Jev scored on the
   same items. On the test run, `control.auroc` is 0.8664 with
   `auroc_ci95` [0.837, 0.894] against `jev_same_items.auroc` 0.6899
   [0.648, 0.730]; `control.accuracy_at_dev_cutoff` is 0.7250 at
   `dev_cutoff` 0.2, against `jev_same_items.accuracy_at_dev_cutoff` 0.6285
   at 0.17 and a `majority_baseline` of 0.6268. `tool_calls` is 0. The dev
   run reports no cutoff accuracy, because its cutoff was fitted on those
   same items.

10. **The diff-size baseline.** `baselines.diff_size` ranks the 611
    published pass questions by lines changed: `auroc` 0.7846, with
    `auroc_ci95` [0.745, 0.823]; `dev_cutoff_lines` 127 gives
    `accuracy_at_dev_cutoff` 0.6514. `size_tracking_auroc.jev` is 0.8159, the
    extent to which Jev's stated probability follows fix size. In `by_size`,
    the 50 to 199 line band (417 fixes) has `auroc_jev` 0.5583 against
    `auroc_control` 0.8132.

## Re-running it

The harness code is in the [VulcanBench
repository](https://github.com/morganlinton/VulcanBench) under
`harness/verdict/` and `scripts/verdict-v1/`. With a TypeSafe API key in
`.env` and local Frontier v4 run directories:

```bash
python scripts/verdict-v1/build_items.py
python scripts/verdict-v1/run_typesafe.py
python scripts/verdict-v1/probe_phrasing.py
python scripts/verdict-v1/run_llm_control.py --split dev
python scripts/verdict-v1/run_llm_control.py --split test
python scripts/verdict-v1/export_results.py
```

Items are rebuilt from local run directories, so anyone without those runs
cannot reproduce the item file. The metrics here are checkable from
`results.json` alone.

## The correction of September 23, 2026

The first published version scored yes/no families at a 0.5 cutoff, which
Jev never crosses, so its headline (40.8% overall against a 72.4% floor)
measured the decision rule rather than the model. Both figures are in
`results.json`: `accuracy` is the withdrawn one and `accuracy_at_threshold`
the corrected one. Nothing was re-queried; every number here was recomputed
from the same stored predictions.

## What these numbers do not show

Apart from the GPT-6 Astra control on the pass question, no other model has
been run on these items; the style family's only references are the majority
floor and the Muse and Grok code-quality panel. Jev is pinned to `jev-1.13.0`; a later version is a new measurement,
never an update of this one.
