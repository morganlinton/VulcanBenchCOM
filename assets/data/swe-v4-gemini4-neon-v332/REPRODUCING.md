# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest discover -s scripts -p 'test_swe_v4_v332.py'
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every published run's Code quality, both combined scores and each
judge's single-judge combined score from the stored factors and judge
sub-scores, checks that the two unpublished rows carry no judge-derived
values, rebuilds the four aggregates and their standard errors, recomputes
every run's API-equivalent cost from its token counts at the published rates,
checks the hidden-behaviour counts, integrity verdicts, tool-call allowlist,
Antigravity version and task hashes, checks the flat CSVs and the report page
tables against them, checks the calibration verdicts and the unpublished-row
records, pins the card image by hash, and checks that no dash characters or
host paths appear in the published text. None of these commands contacts a
provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository.

- [Protocol document with amendments v3.1 to v3.32](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Decision log: Gemini 4 Neon through a custom Antigravity agent (2026-11-19), the sandbox heredoc fix (2026-11-20), the v3.32 judges and the malformed-probe rule (2026-11-21)](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Operations log](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md), whose v3.32 section records the judging windows, the retries, the stop at submission-048, the recovery and the two unpublished rows
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [The v3.32 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v332.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry, display-rename and invalidation rules
- [Antigravity adapter](https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/antigravity_cli.py): the custom agent, the Antigravity invocation, its receipt and the API-equivalent pricing
- [Population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_neon_population.py) and [card generator](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_gemini4neon_vs_frontier_card.py)
- [Population record, card and its per-level table](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-gemini4-neon-2026-11)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
protocol file, the judge settings and binary pins, the Cursor pin, the
display-rename record, counted calls and second attempts, the two unpublished
rows and the judging windows. `provenance.json` carries the hashes of the
frozen summary, manifest, calibration files, the two invalidation markers,
population record, card and its table, sweep launcher and suite lock the
export was built from and checked against. The export script,
`scripts/export_swe_v4_v332_evidence.py`, recomputes every row from the frozen
summary and run summaries and refuses to write if any value differs from them,
from the harness card table, or, for the card's comparators, from the
published board.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 scripts/cii-v4-board/build_neon_population.py
python3 -m harness.maintenance_review_v332 prepare
export VB_MAINT_MODULE=harness.maintenance_review_v332
for panel in muse grok; do python3 -m harness.maintenance_review_v3_resume calibrate --panel $panel; done
for panel in muse grok; do
  python3 -m harness.maintenance_review_v3_resume run --panel $panel
  python3 -m harness.maintenance_review_v3_resume probe --panel $panel
done
python3 -m harness.maintenance_review_v332 summarize
```

The stages ran one after another in one chain, stopping at the first failed
stage. The chain stopped at Grok 4.6's probe of submission-048; after the
wrapper rule was extended, the Grok probe stage alone was resumed from the
tag `bench/2026-11-21-gemini4-neon-judging-v332-recovery`, followed by
`summarize`. The runner refuses to start unless the code and protocol document
hashes match its frozen `protocol.json`. New judge calls consume subscription
quota and will not reproduce the exact saved responses.
