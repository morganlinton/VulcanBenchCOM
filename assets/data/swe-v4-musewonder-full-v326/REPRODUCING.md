# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest scripts/test_swe_v4_v326.py
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every judged run's Code quality, both combined scores, the
timeouts-as-0 figure and each judge's single-judge combined score from the
stored factors and judge sub-scores, rebuilds the four aggregates and their
standard errors, checks the two timed-out runs, the hidden-behaviour counts,
integrity verdicts, Muse Code versions and task hashes, re-prices every run
from its token usage at the stated rates, checks the flat CSVs and the report
page tables against them, checks the calibration verdicts, pins the card
image by hash, checks that the model page links the traces, and checks that
no dash characters or host paths appear in the published text. None of these
commands contacts a provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository.

- [Protocol document with amendments v3.1 to v3.26.3](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Decision log: Muse Wonder Full in Contributor mode (2026-10-12), the skill reminder off (2026-10-13), the v3.25 and v3.26 panels (2026-10-15), Muse Code 1.4.9 (2026-10-16), High and Extra-high judged without a new exam and transport stops rerun (2026-10-17), timeouts counted both ways (2026-09-28)](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Operations log](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md)
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- Runners: [v3.25](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v325.py), [v3.26](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v326.py), [v3.26.1](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3261.py), [v3.26.2](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3262.py) and [v3.26.3](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3263.py), which reuse the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry and recovery rules
- [Sweep runner](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/run_muse_wonder_sweep.py), [population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_musewonder_population.py) and [card generator](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_musewonder_frontier_card.py)
- [Population records, pricing check and card](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-musewonder-full-2026-10)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)
- [Redacted agent traces](https://github.com/morganlinton/vulcanbench-musewonder-full-traces)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of each
round's protocol file, the hashes by which the later rounds bind both exam
verdicts, the judge settings and binary pins, and the operator recoveries.
`provenance.json` carries the hashes of the frozen summaries, manifests,
calibration files, population records, card, pricing check, suite lock and
overlap logs the export was built from and checked against. The export
script, `scripts/export_swe_v4_v326_evidence.py`, recomputes every row from
the frozen summaries and refuses to write if any value differs from them or
from the harness card.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 scripts/cii-v4-board/build_musewonder_population.py
python3 -m harness.maintenance_review_v325 prepare
VB_MAINT_MODULE=harness.maintenance_review_v325 python3 -m harness.maintenance_review_v3_resume calibrate --panel sol
VB_MAINT_MODULE=harness.maintenance_review_v325 python3 -m harness.maintenance_review_v3_resume run --panel sol
VB_MAINT_MODULE=harness.maintenance_review_v325 python3 -m harness.maintenance_review_v3_resume probe --panel sol
python3 -m harness.maintenance_review_v326 prepare
VB_MAINT_MODULE=harness.maintenance_review_v326 python3 -m harness.maintenance_review_v3_resume calibrate --panel claude
VB_MAINT_MODULE=harness.maintenance_review_v326 python3 -m harness.maintenance_review_v3_resume run --panel claude
VB_MAINT_MODULE=harness.maintenance_review_v326 python3 -m harness.maintenance_review_v3_resume probe --panel claude
python3 -m harness.maintenance_review_v326 summarize
```

then `build_musewonder_population.py --top-up`, `--level high` and
`--level extra-high` with the v3.26.1, v3.26.2 and v3.26.3 runners in the
same way, without the calibrate step. Each runner refuses to start unless the
code and protocol document hashes match its frozen `protocol.json`. New judge
calls consume subscription quota and will not reproduce the exact saved
responses.
