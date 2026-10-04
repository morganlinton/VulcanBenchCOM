# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest scripts/test_swe_v4_v320.py
python3 scripts/verify_swe_v4_v320_pdf.py
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every judged run's Code quality and both combined scores from the
stored factors and both judges' sub-scores, rebuilds the four aggregates and
their standard errors from the runs (the medium timeout counted as a failed
task and in runtime, and left out of every score), checks the hidden-behaviour
counts, integrity verdicts and token sums, checks that no run carries a cost,
recomputes the shared-judge sensitivity (Muse Spark 1.3 alone) for every
Frontier v4 column from the public bundles, checks the flat CSVs, the report
page tables and the Safety v1 aggregates against them, checks the calibration
verdicts, pins the four card images by hash, and checks that no dash
characters, host paths or Safety v1 task names appear in the published text.
The PDF check needs `pypdf`. None of these commands contacts a provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository. The v3.20
files arrive on `main` with harness pull request
[#165](https://github.com/morganlinton/VulcanBench/pull/165).

- [Protocol document with amendments v3.1 to v3.20](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Operations log: every freeze, calibration verdict and operator intervention, including the v3.20 capacity retry and the one-based index recovery](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md)
- [Decision log: judging Grok 4.7 with Muse Spark 1.3 and GPT-6.1 Sol, and the flat 3-hour timeout for every suite](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [v3.20 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v320.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py) with v3.10's Sol seat transport, and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry, display-rename, trailing-brace, escaped-excerpt, invalid-call and one-based index rules
- [Population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_grok47cursor_population.py) and [card generators](https://github.com/morganlinton/VulcanBench/tree/main/scripts/cii-v4-board): `make_grok47cursor_v320_card.py` (score card), `make_grok47cursor_usage_card.py` (time and tokens card, in place of the economics card), `make_grok47_frontier_comparison_card.py` (beside GPT-6.1 Sol, Claude Opus 5.5 and GPT-6 Astra) and `make_grok47_safety_card.py` (Safety v1, beside Claude Opus 5.5)
- [Population record and card tables](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-grok47-cursor-2026-10) and the [Safety v1 card table](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/safety-v1-grok47-2026-10)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
frozen protocol file, the counted calls, the capacity retry and the six index
recoveries. `provenance.json` carries the hashes of the frozen summary,
manifest, calibration and population files, the capacity receipt, the six
recovered match calls and the harness card tables the export was built from
and checked against. The export script,
`scripts/export_swe_v4_v320_evidence.py`, recomputes every row from the frozen
summary, re-derives the Safety v1 counts from the VulcanConduct audit files
(a private repository), and refuses to write if any value differs.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 -m harness.maintenance_review_v320 prepare
VB_MAINT_MODULE=harness.maintenance_review_v320 python3 -m harness.maintenance_review_v3_resume calibrate --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v320 python3 -m harness.maintenance_review_v3_resume run --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v320 python3 -m harness.maintenance_review_v3_resume probe --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v320 python3 -m harness.maintenance_review_v3_resume calibrate --panel sol
VB_MAINT_MODULE=harness.maintenance_review_v320 python3 -m harness.maintenance_review_v3_resume run --panel sol
VB_MAINT_MODULE=harness.maintenance_review_v320 python3 -m harness.maintenance_review_v3_resume probe --panel sol
python3 -m harness.maintenance_review_v320 summarize
```

The two panels ran in parallel under per-panel locks. The runner refuses to
start unless the code and protocol document hashes match the frozen
`protocol.json`, so an older protocol version must run from a checkout at its
freeze commit. New judge calls consume subscription quota and will not
reproduce the exact saved responses.
