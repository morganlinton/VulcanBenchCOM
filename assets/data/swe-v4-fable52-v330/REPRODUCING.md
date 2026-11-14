# Reproducing the published record

## Recompute the measurements without model calls

From the website repository root:

```sh
python3 -m unittest discover -s scripts -p 'test_swe_v4_v330.py'
python3 scripts/check_benchmark_index.py
python3 scripts/build_swe_v4_board.py --check
```

The first command needs Python 3.9 or newer and its standard library. It
recomputes every run's Code quality, both combined scores and each judge's
single-judge combined score from the stored factors and judge sub-scores,
rebuilds the five aggregates and their standard errors, checks them against
the card table and the published figures, checks the flat CSVs and the report
page tables against them, checks the calibration verdicts (Grok 4.6's failed
exam included) and the operator recoveries, pins both card images by hash, and
checks that no dash characters or host paths appear in the published text.
None of these commands contacts a provider.

## Inspect the protocol and the code that ran it

All of the following live in the VulcanBench harness repository.

- [Protocol document with its amendments](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/code-quality-maintenance-v3.md), including v3.30 to v3.30.5
- [Decision log](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md): Claude Code 2.1.321 with thinking summaries (2026-11-09), the v3.30 panel (2026-11-10), and Muse alone for Max then GPT-6.1 Sol in Grok's seat (2026-11-11)
- [Operations log](https://github.com/morganlinton/VulcanBench/blob/main/docs/judging/maintenance-v3-operations.md), whose v3.30 sections record the judging windows, Grok's failed gate, the retries and the recoveries
- [The ten calibration controls and their verifier](https://github.com/morganlinton/VulcanBench/tree/main/docs/judging/controls-v3)
- The runners [v3.30](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v330.py), [v3.30.1](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3301.py), [v3.30.2](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3302.py) and [v3.30.3](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3303.py), which reuse the frozen [v3 implementation](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3.py), and the [operator wrapper](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3_resume.py) with its retry and recovery rules
- The comparison-only runners [v3.30.4](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3304.py) (Fable 5.1) and [v3.30.5](https://github.com/morganlinton/VulcanBench/blob/main/harness/maintenance_review_v3305.py) (Opus 5.5)
- [Claude Code adapter](https://github.com/morganlinton/VulcanBench/blob/main/harness/agent/cli_agents.py) and [solver receipts](https://github.com/morganlinton/VulcanBench/blob/main/harness/solver_receipts.py), which sum every result receipt
- [Sweep launcher](https://github.com/morganlinton/VulcanBench/blob/main/scripts/run_fable52_v4.sh), [population builder](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/build_fable52_population.py) and [card generator](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/make_fable52_vs_frontier_card.py)
- [Muse-alone table](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/fable52_muse_like_for_like.py), [behaviour analysis](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/fable52_vs_fable51_behaviour.py) and [memorization check](https://github.com/morganlinton/VulcanBench/blob/main/scripts/cii-v4-board/check_fable52_memorization.py)
- [Results, population records, cards and the recall probe](https://github.com/morganlinton/VulcanBench/tree/main/docs/results/swe-v4-fable52-2026-11)
- [Traces exporter](https://github.com/morganlinton/VulcanBench/blob/main/scripts/export_fable52_redacted_traces.py), which writes the [redacted traces repository](https://github.com/morganlinton/vulcanbench-fable52-traces)
- [Score composition](https://github.com/morganlinton/VulcanBench/blob/main/harness/evaluator/reviewed_score.py)

`provenance.json` in this folder carries the hashes of the frozen summaries,
manifests, protocols, calibration files, population records, card and its
table, Muse-alone table, memorization check and suite lock the export was
built from and checked against. The export script,
`scripts/export_swe_v4_v330_evidence.py`, recomputes every row from the frozen
summaries, the run summaries and the archived streams and refuses to write if
any value differs from them or from the harness card table.

## Run a new judging pass

Judging needs the private run archive (patches and reconstructed sources) and
the quirk answer keys, which are not published because they describe
hidden-test behaviour. The runners refuse to start unless the code and
protocol document hashes match their frozen `protocol.json`. New judge calls
consume subscription quota and will not reproduce the exact saved responses.
The operations log records the stage order for each round.
