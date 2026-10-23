# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest discover -s scripts -p 'test_swe_v4_v327.py'
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every run's Code quality, both combined scores and each judge's
single-judge combined score from the stored factors and judge sub-scores,
rebuilds the three aggregates and their standard errors, checks the
hidden-behaviour counts, integrity verdicts, harness version and task hashes,
re-prices every run from its token usage at the stated off-peak rates, checks
that billed cost is never below list price, checks the flat CSVs and the
report page tables against them, checks the calibration verdicts, pins the
card images by hash, and checks that no dash characters or host paths appear
in the published text. None of these commands contacts a provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository.

- [Protocol document with amendments v3.1 to v3.27](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Decision log: DeepSeek V4.1 Flash and V4 Pro through DeepSeek Harness (2026-10-19), the v3.27 judges (2026-10-23)](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Operations log](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md)
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [The v3.27 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v327.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry and recovery rules
- [DeepSeek Harness adapter](https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/deepseek_harness.py): the settings overlay, the install pin and the usage and cost accounting
- [Sweep runner](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/run_effort_sweep.sh), [population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_deepseek_flash_population.py) and [card generator](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_deepseek_flash_cards.py)
- [Population record, pricing check and cards](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-deepseek-flash-2026-10)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
protocol file, the judge settings and binary pins, and the operator
recoveries. `provenance.json` carries the hashes of the frozen summary,
manifest, calibration files, population record, card data, pricing check,
cards, comparator table, sweep launcher and suite lock the export was built
from and checked against. The export script,
`scripts/export_swe_v4_v327_evidence.py`, recomputes every row from the frozen
summary and run summaries and refuses to write if any value differs from them
or from the harness card data.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 scripts/cii-v4-board/build_deepseek_flash_population.py
python3 -m harness.maintenance_review_v327 prepare
export VB_MAINT_MODULE=harness.maintenance_review_v327
for stage in calibrate run probe; do python3 -m harness.maintenance_review_v3_resume $stage --panel muse; done
for stage in calibrate run probe; do python3 -m harness.maintenance_review_v3_resume $stage --panel sol; done
python3 -m harness.maintenance_review_v327 summarize
```

The two panel chains ran side by side, each stopping at its first failed
stage, and the summary ran only after both finished. The runner refuses to
start unless the code and protocol document hashes match its frozen
`protocol.json`. New judge calls consume subscription quota and will not
reproduce the exact saved responses.
