# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest scripts/test_swe_v4_v311.py
python3 scripts/verify_swe_v4_v311_pdf.py
python3 scripts/check_benchmark_index.py
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every published run's Code quality and both combined scores from
the stored factors and the judge's sub-scores, rebuilds the three aggregates
and their standard errors from the runs (23 judged at medium, 20 at high, 22
at max; 68 runs timed and counted for tokens), checks the flat CSVs and the
report page tables against them, checks all three calibration verdicts,
checks that the four excluded runs are exactly the four the population record
lists and that each is a functional fail, checks that every run carries a zero
cost and zero Devin counters, and checks that no dash characters or host paths
appear in the published text. The PDF check needs `pypdf`. None of these
commands contacts a provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository:

- [Protocol document with amendments v3.1 to v3.11](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Operations log: every freeze, calibration verdict and operator intervention, including the v3.9, v3.10 and v3.11 entries](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md)
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [v3.11 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v311.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry rules
- [Population records and card generators](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-devin-swe2-2026-09)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
frozen protocol file, the single-panel rule and the population record with its
four exclusions. `calibration.json` carries all three verdicts, Muse's passing
one and the two failures that left one judge scoring. `provenance.json`
carries the hashes of the frozen summary, manifest, protocol, calibration and
population files the export was built from. The export script,
`scripts/export_swe_v4_v311_evidence.py`, recomputes every row from the frozen
summary and refuses to write if any value differs.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 -m harness.maintenance_review_v311 prepare
VB_MAINT_MODULE=harness.maintenance_review_v311 python3 -m harness.maintenance_review_v3_resume run --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v311 python3 -m harness.maintenance_review_v3_resume probe --panel muse
python3 -m harness.maintenance_review_v311 summarize
```

No calibration step appears here: `prepare` checks Muse's frozen v3.9 verdict
and refuses to freeze unless it passed, on the v3.6.1 precedent, because the
exam is per judge and control set and neither changed. The failed exams that
left one judge are reproduced from their own freezes, `prepare` and
`calibrate --panel grok` under
[the v3.9 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v39.py)
and `calibrate --panel sol` under
[the v3.10 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v310.py).

The runner refuses to start unless the code and protocol document hashes match
the frozen `protocol.json`, so an older protocol version must run from a
checkout at its freeze commit. New judge calls consume subscription quota and
will not reproduce the exact saved responses. Admitting a second judge for
this population would need a protocol amendment; the two failed exams are
retained as frozen records.
