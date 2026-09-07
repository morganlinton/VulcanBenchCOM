# Reproducing the published record

## Recompute the measurements without model calls

Use the website commit linked by the report, then run from its repository root:

```sh
python3 scripts/verify_swe_v4_evidence.py
python3 scripts/verify_swe_v4_costs.py
python3 scripts/derive_swe_v4_sensitivity.py --check
python3 scripts/check_benchmark_index.py
python3 -m unittest discover -s scripts -p 'test_*.py'
```

These commands need Python 3.10 or newer and its standard library. They check
230 run records, score factors, selected-rating bindings, the 20% equal-panel
review weight, group statistics, cost formulas and derived flat CSV rows.
They do not contact a provider or incur inference charges.

The cost checker uses the frozen September 6, 2026 rate snapshot. It does not
fetch today's prices. Astra cached input is a subset of input; reasoning is
already included in output. Claude final cumulative model receipts own token
totals. Observed five-minute writes are priced at five minutes and remaining
writes at one hour, with the result checked against the CLI list-price receipt.
Thirteen of the 251 reconciled model receipts have stream TTL counts that
differ from final write totals; those counts are not added to the totals.
One further auxiliary Opus receipt lacks TTL evidence and is retained at its
reported $0.40398125, which matches five-minute pricing. Repricing these
published receipts does not independently validate provider metering.

## Inspect the exact task definitions

The public source directory retains its internal historical identifier. Its
reader-facing name is VulcanBench-SWE v4.

- [Suite, charter and candidates at the pinned commit](https://github.com/morganlinton/VulcanBench/tree/657ed20a2c69bc0efdcc29422ffe56f038ca0dbb/tasks/coding-intelligence-index-v4)
- [Public harness reference snapshot](https://github.com/morganlinton/VulcanBench/tree/18a3379650ea2ef8b7d7576b09619d2bf4181e9e)
- [Automated evaluator at that snapshot](https://github.com/morganlinton/VulcanBench/tree/18a3379650ea2ef8b7d7576b09619d2bf4181e9e/harness/evaluator)
- [Task hashing implementation](https://github.com/morganlinton/VulcanBench/blob/18a3379650ea2ef8b7d7576b09619d2bf4181e9e/harness/tasks.py)

All 23 task definitions at the pinned suite commit match the scoring-relevant
task hashes recorded for every published run. The harness snapshot is a
source reference, not a claim that every original invocation used that exact
commit. Original solver summaries did not record a harness Git commit and the
local checkout contained additional work. Exact execution reconstruction is
therefore not established. CLI versions are recorded per run in runs.csv.

With that harness checkout available, verify task hashes from the website root:

```sh
python3 scripts/verify_swe_v4_task_sources.py --harness-root /path/to/VulcanBench
```

This optional check imports the public harness task loader and needs its
supported Python version. It makes no model calls.

## Run a new comparison

The commands below require Python 3.12 or newer and illustrate the recorded invocation shape. They launch new
model calls and can consume paid quota; they do not reproduce the exact saved
outputs. Authenticate the appropriate subscriptions first, inspect the pinned
harness documentation, and establish an independently audited execution
boundary before evaluating untrusted agents. Original runs used local mode;
that is a limitation, not a recommended security boundary.

```sh
git clone https://github.com/morganlinton/VulcanBench.git
cd VulcanBench
git checkout 18a3379650ea2ef8b7d7576b09619d2bf4181e9e
python3 -m venv .venv
.venv/bin/pip install -e .
# Install the recorded CLI versions and authenticate separately.
# Run only after configuring and auditing the chosen execution boundary.
.venv/bin/vulcanbench run --suite coding-intelligence-index-v4 \
  --model gpt-6-astra --harness codex --billing subscription \
  --sandbox local --no-judges --effort low -o new-astra-low
.venv/bin/vulcanbench run --suite coding-intelligence-index-v4 \
  --model claude-code:claude-fable-5-1 --sandbox local \
  --no-judges --effort low -o new-fable-low
```

Repeat with medium, high, extra-high and max, using separate output directories.
Verify the effective 36,000-second solver limit before starting. The reported
10-hour limit is a solver budget, distinct from individual verifier timeouts.
Do not silently enable fallbacks or replace an unsuccessful attempt; publish
the actual routing and retry policy with new results. Effort labels are
harness-specific, not equal compute allocations.

Original Code quality ratings were applied retrospectively. The exact general
prompt, personas, requested reviewer models and efforts are in
[review-protocols.json](review-protocols.json); the selected ratings and all
call dispositions are in the adjacent JSON files. Use the public scoring
verifier to recompute the fixed formula. Task-specific review prompts, patches,
rationales and trajectories for these runs are not included in this release.
This bundle is an arithmetic audit record, not an unrestricted raw-run dump
or proof of no cheating, contamination or prohibited access.

## Sensitivity analysis

[sensitivity.json](sensitivity.json) is generated from runs.json. Each effort
uses 20,000 paired bootstrap resamples of the 23 tasks, with replacement,
seed 20260906 and percentile endpoints at 2.5% and 97.5%. The script records
ordering and interpolation so the result can be reproduced exactly.

The intervals describe sensitivity to sampling these tasks, not independent
repeated-run or reviewer uncertainty. They are exploratory, unadjusted for
multiple comparisons, and do not justify generalization to all software work.
Reviewer-only variants keep the review contribution at 20%. The nonfallback
variant removes the same task pairs from both models at each effort. It is
post-hoc, uses different task subsets by effort and is not an unbiased estimate
of a pure Fable model. All official scores retain the complete matched set.
