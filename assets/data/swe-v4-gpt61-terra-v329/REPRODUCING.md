# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest discover -s scripts -p 'test_swe_v4_v329.py'
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.10 or newer and its standard library. It
recomputes every run's Code quality, both combined scores and each judge's
single-judge combined score from the stored factors and judge sub-scores
(with intent recovery moved to the reviewed score where a run passed no quirk
family), rebuilds the five aggregates and their standard errors, recomputes
every run's API-equivalent cost from its token counts at the published rates,
checks the hidden-behaviour counts, integrity verdicts, Codex version and
notices and task hashes, checks the flat CSVs and the report page tables
against them, checks the calibration verdicts and the Max settlecore recovery
record, pins the card image by hash, and checks that no dash characters or
host paths appear in the published text. None of these commands contacts a
provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository.

- [Protocol document with amendments v3.1 to v3.29](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md), including the v3.29 recovery note
- [Decision log: GPT-6.1 Terra on the pinned Codex 0.159.0 (2026-10-26) and the v3.29 judges (2026-10-28)](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
- [Operations log](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md), whose v3.29 section records the judging window, the retries and the Max settlecore recovery
- [Plain-language system summary](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-system-summary.md)
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- [The v3.29 runner](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v329.py), which reuses the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry, display-rename and recovery rules
- [Codex adapter](https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/cli_agents.py): the Codex invocation, its receipt and the API-equivalent pricing
- [Sweep launcher](https://github.com/morganlinton/VulcanBench/blob/main/scripts/run_gpt61_terra_v4.sh), [population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_gpt61terra_population.py) and [card generator](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_gpt61terra_vs_frontier_card.py)
- [Population record, card and its per-level table](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-gpt61-terra-2026-10)
- [Traces exporter](https://github.com/morganlinton/VulcanBench/blob/main/scripts/export_gpt61terra_redacted_traces.py), which writes the [redacted traces repository](https://github.com/morganlinton/vulcanbench-gpt61-terra-traces)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`judge-protocols.json` in this folder carries the exact rubric, system text,
probe and match instructions and schemas as frozen, with the SHA-256 of the
protocol file, the judge settings and binary pins, the Cursor pin, the
display-rename record, counted calls and second attempts, and the operator
recovery. `provenance.json` carries the hashes of the frozen summary,
manifest, calibration files, the recovered probe and its superseded marker,
population record, card and its table, comparator tables, sweep launcher and
suite lock the export was built from and checked against. The export script,
`scripts/export_swe_v4_v329_evidence.py`, recomputes every row from the frozen
summary and run summaries and refuses to write if any value differs from them
or from the harness card table.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. With those, the recorded invocation shape was:

```sh
python3 scripts/cii-v4-board/build_gpt61terra_population.py
python3 -m harness.maintenance_review_v329 prepare
export VB_MAINT_MODULE=harness.maintenance_review_v329
for panel in muse grok; do python3 -m harness.maintenance_review_v3_resume calibrate --panel $panel; done
for panel in muse grok; do
  python3 -m harness.maintenance_review_v3_resume run --panel $panel
  python3 -m harness.maintenance_review_v3_resume probe --panel $panel
done
python3 -m harness.maintenance_review_v329 summarize
```

The stages ran one after another, stopping at the first failed stage. The
Max settlecore recovery then ran from a later tag whose wrapper tries both
spellings of a decoded NUL: the call's `operator-invalid.json` was renamed
`operator-invalid.superseded.json`, the Muse probe stage was rerun alone
(`probe --panel muse`), which selected the recovered attempt and made the one
missing answer-key match, and the summary was rebuilt. The runner refuses to
start unless the code and protocol document hashes match its frozen
`protocol.json`. New judge calls consume subscription quota and will not
reproduce the exact saved responses.
