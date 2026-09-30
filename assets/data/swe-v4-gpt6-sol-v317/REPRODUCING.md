# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest scripts/test_swe_v4_v317.py
python3 scripts/verify_swe_v4_v317_pdf.py
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every published run's Code quality and both combined scores from
the stored factors and judge sub-scores, re-prices every run from its token
receipt at the published rates, rebuilds the five aggregates and their
standard errors from the runs, checks that exactly one row (Medium codeccore)
is unpublished and still counts for pass counts, runtime and cost, checks the
flat CSVs and the report page tables against them, checks the calibration
verdicts, pins the four card images by hash, and checks that no dash
characters or host paths appear in the published text. The PDF check needs
`pypdf`. None of these commands contacts a provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository. The v3.17
files arrive on `main` with harness pull request
[#161](https://github.com/morganlinton/VulcanBench/pull/161).

- [Protocol document with amendments v3.1 to v3.17](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Operations log: every freeze, calibration verdict and operator intervention, including the two v3.17 stops](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md)
- [Decision log: the Codex CLI 0.155.0 pin and judging GPT-6 Sol before Grok 4.7](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [v3.17 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v317.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry, display-rename, invalid-probe and trailing-brace rules
- [Population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_gpt6sol_population.py) and [card generators](https://github.com/morganlinton/VulcanBench/tree/main/scripts/cii-v4-board), including the GPT-6 vs. GPT-5.6 comparison cards
- [Population record and card tables](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-gpt6-sol-2026-09) and [comparison card tables](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-gpt6-vs-gpt56-2026-09)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
frozen protocol file, the operator's finding on the unpublished row and the
one trailing-brace recovery. `provenance.json` carries the hashes of the
frozen summary, manifest, calibration and population files, the invalid-probe
marker, the recovered review and the harness card tables the export was built
from and checked against. The export script,
`scripts/export_swe_v4_v317_evidence.py`, recomputes every row from the frozen
summary and refuses to write if any value differs.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 -m harness.maintenance_review_v317 prepare
VB_MAINT_MODULE=harness.maintenance_review_v317 python3 -m harness.maintenance_review_v3_resume calibrate --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v317 python3 -m harness.maintenance_review_v3_resume run --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v317 python3 -m harness.maintenance_review_v3_resume probe --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v317 python3 -m harness.maintenance_review_v3_resume calibrate --panel grok
VB_MAINT_MODULE=harness.maintenance_review_v317 python3 -m harness.maintenance_review_v3_resume run --panel grok
VB_MAINT_MODULE=harness.maintenance_review_v317 python3 -m harness.maintenance_review_v3_resume probe --panel grok
python3 -m harness.maintenance_review_v317 summarize
```

The runner refuses to start unless the code and protocol document hashes match
the frozen `protocol.json`, so an older protocol version must run from a
checkout at its freeze commit. New judge calls consume subscription quota and
will not reproduce the exact saved responses.
