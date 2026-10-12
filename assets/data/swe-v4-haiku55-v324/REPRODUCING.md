# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest scripts/test_swe_v4_v324.py
python3 scripts/verify_swe_v4_v324_pdf.py
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every judged run's Code quality and both combined scores from the
stored factors and judge sub-scores, rebuilds the five aggregates and their
standard errors, checks the four runs without a score, the hidden-behaviour
counts, integrity verdicts, Claude Code versions and task hashes, recomputes
every run's tier floor and ceiling from its token usage, checks that every
reply came from `claude-haiku-5-5`, checks the flat CSVs and the report page
tables against them, checks the calibration verdicts, pins the card images by
hash, and checks that no dash characters or host paths appear in the
published text. The PDF check needs `pypdf`. None of these commands contacts a
provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository. The v3.24
runner and population builder arrived on `main` with harness pull request
[#186](https://github.com/morganlinton/VulcanBench/pull/186); the card generators,
population record, cards and decision records arrive with
[#187](https://github.com/morganlinton/VulcanBench/pull/187).

- [Protocol document with amendments v3.1 to v3.24](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Decision log: Haiku 5.5 published, the pauses, the clock change and the resume stubs (2026-10-12); v3.24 pins Cursor by version (2026-10-10); Haiku pricing (2026-10-07)](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Recovered original v3.3 and v3.4 judge protocols](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/recovered)
- [Operations log](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md)
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [v3.24 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v324.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), reads the recovered protocols and pins Cursor by version, and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry, display-rename, excerpt-recovery and invalid-call rules
- [Population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_haiku55_population.py) and card generators ([score card](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_haiku55_v324_card.py), [comparison cards](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_haiku55_vs_card.py), [beside GPT-6 Luna](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_haiku55_vs_luna_card.py))
- [Population record and card tables](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-haiku55-2026-10)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)
- [Redacted agent traces](https://github.com/morganlinton/vulcanbench-haiku55-traces)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
frozen protocol file, the judge settings and Cursor version record, the
unpublished probe and the operator recovery. `provenance.json` carries the
hashes of the frozen summary, manifest, calibration and population files, the
invalid-probe marker, the suite lock and the four harness card tables the
export was built from and checked against. The export script,
`scripts/export_swe_v4_v324_evidence.py`, recomputes every row from the frozen
summary and refuses to write if any value differs.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 scripts/cii-v4-board/build_haiku55_population.py
python3 -m harness.maintenance_review_v324 prepare
VB_MAINT_MODULE=harness.maintenance_review_v324 python3 -m harness.maintenance_review_v3_resume calibrate --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v324 python3 -m harness.maintenance_review_v3_resume run --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v324 python3 -m harness.maintenance_review_v3_resume probe --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v324 python3 -m harness.maintenance_review_v3_resume calibrate --panel grok
VB_MAINT_MODULE=harness.maintenance_review_v324 python3 -m harness.maintenance_review_v3_resume run --panel grok
VB_MAINT_MODULE=harness.maintenance_review_v324 python3 -m harness.maintenance_review_v3_resume probe --panel grok
python3 -m harness.maintenance_review_v324 summarize
```

The runner refuses to start unless the code and protocol document hashes match
the frozen `protocol.json`, and before every stage it re-checks the digest of
the pinned Cursor version directory. New judge calls consume subscription
quota and will not reproduce the exact saved responses.
