# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest scripts/test_swe_v4_v323.py
python3 scripts/verify_swe_v4_v323_pdf.py
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every run's Code quality and both combined scores from the stored
factors and judge sub-scores, rebuilds the five aggregates and their standard
errors from the runs, checks the hidden-behaviour counts, integrity verdicts,
Claude Code versions and task hash bridge pairs, checks that every reply came
from `claude-sonnet-5-5`, checks the flat CSVs and the report page tables
against them, checks the calibration verdicts, pins the card images by hash,
and checks that no dash characters or host paths appear in the published
text. The PDF check needs `pypdf`. None of these commands contacts a provider.

Cost is Claude Code's own reported total per run, so there is no rate
arithmetic to redo; `economics.json` records the list rates as published,
including both of Anthropic's cache-read figures.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository. The v3.23
runner, hash bridge and judge settings file arrived on `main` with harness pull
requests [#176](https://github.com/morganlinton/VulcanBench/pull/176) and
[#179](https://github.com/morganlinton/VulcanBench/pull/179); the population
record and card tables arrive with [#181](https://github.com/morganlinton/VulcanBench/pull/181).

- [Protocol document with amendments v3.1 to v3.23](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Decision log: Sonnet 5.5 published with disclosure, judging on the new host, the hash bridge and the cost source (2026-10-07)](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Task hash bridge for the Sonnet 5.5 sweep](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/task-hash-bridge-sonnet55.json)
- [Judge settings file](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/judge-pins-v3.json)
- [Operations log](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md)
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [v3.23 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v323.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), reads the judge settings file and installs the hash bridge in every stage, and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry, display-rename and invalid-call rules
- [Population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_sonnet55_population.py) and card generators ([score card](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_sonnet55_v323_card.py), [beside Opus 5.5 and Fable 5.1](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_sonnet55_vs_claude_card.py))
- [Population record and card tables](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-sonnet55-2026-10)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
frozen protocol file, the judge settings and version record (the published
v3.3 and v3.4 protocol hashes, the Muse binary and Cursor launcher hashes, and
the Cursor CLI versions) and the hash
bridge reference. `provenance.json` carries the hashes of the frozen summary,
manifest, calibration and population files, the hash bridge, the judge settings
file and the suite lock the export was built from and checked against. The
export script, `scripts/export_swe_v4_v323_evidence.py`, recomputes every row
from the frozen summary and refuses to write if any value differs.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 scripts/cii-v4-board/build_sonnet55_population.py
python3 -m harness.maintenance_review_v323 prepare
VB_MAINT_MODULE=harness.maintenance_review_v323 python3 -m harness.maintenance_review_v3_resume calibrate --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v323 python3 -m harness.maintenance_review_v3_resume run --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v323 python3 -m harness.maintenance_review_v3_resume probe --panel muse
VB_MAINT_MODULE=harness.maintenance_review_v323 python3 -m harness.maintenance_review_v3_resume calibrate --panel grok
VB_MAINT_MODULE=harness.maintenance_review_v323 python3 -m harness.maintenance_review_v3_resume run --panel grok
VB_MAINT_MODULE=harness.maintenance_review_v323 python3 -m harness.maintenance_review_v3_resume probe --panel grok
python3 -m harness.maintenance_review_v323 summarize
```

The runner refuses to start unless the code and protocol document hashes match
the frozen `protocol.json`, so an older protocol version must run from a
checkout at its freeze commit. It also refuses any run whose recorded task
hash is not the bridge's recorded hash for that task. New judge calls consume
subscription quota and will not reproduce the exact saved responses.
