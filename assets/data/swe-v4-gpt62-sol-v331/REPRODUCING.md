# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest discover -s scripts -p 'test_swe_v4_v331.py'
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every run's Code quality, both combined scores and each judge's
single-judge combined score from the stored factors and judge sub-scores
(from Muse Spark 1.3 alone for the one run Grok 4.6 has no valid review of),
rebuilds the five aggregates and their standard errors, recomputes every run's
API-equivalent cost from its token counts at the published rates, checks the
hidden-behaviour counts, integrity verdicts, Codex version and task hashes,
checks the flat CSVs and the report page tables against them, checks the
calibration verdicts and the one-judge record, pins the card image by hash,
and checks that no dash characters or host paths appear in the published text.
None of these commands contacts a provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository.

- [Protocol document with amendments v3.1 to v3.31](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md)
- [Decision log: GPT-6.2 Sol on the pinned Codex 0.166.0 (2026-11-17) and the v3.31 judges (2026-11-18)](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Operations log](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md), whose v3.31 section records the judging window, the retries, the Cursor usage-limit pause and the one-judge row
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [The v3.31 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v331.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry, quota, display-rename and invalidation rules
- [Codex adapter](https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/cli_agents.py): the Codex invocation, its receipt and the API-equivalent pricing
- [Sweep launcher](https://github.com/morganlinton/VulcanBench/blob/main/scripts/run_gpt62_sol_v4.sh), [population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_gpt62sol_population.py) and [card generator](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_gpt62sol_vs_frontier_card.py)
- [Population record, card and its per-level table](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-gpt62-sol-2026-11)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
protocol file, the judge settings and binary pins, the Cursor pin, the
display-rename record, counted calls and second attempts, the one-judge
record and the quota stop. `provenance.json` carries the hashes of the frozen
summary, manifest, calibration files, the invalidation marker, population
record, card and its table, sweep launcher and suite lock the export was built
from and checked against. The export script,
`scripts/export_swe_v4_v331_evidence.py`, recomputes every row from the frozen
summary and run summaries and refuses to write if any value differs from them,
from the harness card table, or, for the card's comparators, from the
published board.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 scripts/cii-v4-board/build_gpt62sol_population.py
python3 -m harness.maintenance_review_v331 prepare
export VB_MAINT_MODULE=harness.maintenance_review_v331
for panel in muse grok; do python3 -m harness.maintenance_review_v3_resume calibrate --panel $panel; done
for panel in muse grok; do
  python3 -m harness.maintenance_review_v3_resume run --panel $panel
  python3 -m harness.maintenance_review_v3_resume probe --panel $panel
done
python3 -m harness.maintenance_review_v331 summarize
```

The stages ran one after another in one chain, stopping at the first failed
stage. Grok 4.6's calibration paused on a Cursor usage limit and resumed on
the same call under the wrapper's quota rule, with no operator action beyond
signing in to the paid Cursor account. The runner refuses to start unless the
code and protocol document hashes match its frozen `protocol.json`. New judge
calls consume subscription quota and will not reproduce the exact saved
responses.
