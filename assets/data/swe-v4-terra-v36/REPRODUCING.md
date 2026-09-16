# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest scripts/test_swe_v4_v36.py
python3 scripts/verify_swe_v4_v36_pdf.py
python3 scripts/check_benchmark_index.py
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every run's Code quality and both combined scores from the stored
factors and judge sub-scores, re-prices every run from its token receipt at
the published rates, rebuilds the five aggregates and their standard errors
from the runs, checks the flat CSVs and the report page tables against them,
checks the calibration verdicts, and checks that no dash characters or host
paths appear in the published text. The PDF check needs `pypdf`. None of
these commands contacts a provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository:

- [Protocol document with amendments v3.1 to v3.6](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Operations log: every freeze, calibration verdict and operator intervention](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md)
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [v3.6 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v36.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py)
- [Population record and card generators](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-terra-2026-09)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
frozen protocol file. `provenance.json` carries the hashes of the frozen
summary, manifest, calibration and population files the export was built
from. The export script, `scripts/export_swe_v4_v36_evidence.py`, recomputes
every row from the frozen summary and refuses to write if any value differs.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 -m harness.maintenance_review_v36 prepare
VB_MAINT_MODULE=harness.maintenance_review_v36 python3 -m harness.maintenance_review_v3_resume calibrate --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v36 python3 -m harness.maintenance_review_v3_resume calibrate --panel grok
VB_MAINT_MODULE=harness.maintenance_review_v36 python3 -m harness.maintenance_review_v3_resume run --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v36 python3 -m harness.maintenance_review_v3_resume probe --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v36 python3 -m harness.maintenance_review_v3_resume run --panel grok
VB_MAINT_MODULE=harness.maintenance_review_v36 python3 -m harness.maintenance_review_v3_resume probe --panel grok
python3 -m harness.maintenance_review_v36 summarize
```

The runner refuses to start unless the code and protocol document hashes match
the frozen `protocol.json`, so an older protocol version must run from a
checkout at its freeze commit. New judge calls consume subscription quota and
will not reproduce the exact saved responses.
