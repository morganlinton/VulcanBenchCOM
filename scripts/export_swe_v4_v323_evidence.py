"""Export the public record of the v3.23 Claude Sonnet 5.5 effort sweep on Frontier v4.

Adapted from the v3.15 Claude Opus 5.5 export, with the same publication
scope: per-run scores, per-panel sub-scores, aggregates, judge protocol text,
calibration verdicts, raw tokens and Claude Code's own list-price cost. Raw
prompts, patches, quirk answer keys and host paths are withheld. Run from the
site root once runs-code-quality-maintenance-v3.23/summary.json exists:

    python3 scripts/export_swe_v4_v323_evidence.py --harness-root ../VulcanBench \\
        --docs-root ../VulcanBench-runs/bench-2026-10-08-sonnet55-judging-v323b

--harness-root holds the frozen run directories (runs-code-quality-maintenance-v3.23
and runs-effort-sonnet55). --docs-root is a harness checkout that carries the
population record docs/results/swe-v4-sonnet55-2026-10/comparison.json, the
committed hash bridge docs/judging/task-hash-bridge-sonnet55.json, the
judge pins docs/judging/judge-pins-v3.json and the frozen suite lock; it
defaults to --harness-root.

What differs from the Opus 5.5 export, all forced by the sweep or its judging:

- No exclusions. Every Sonnet 5.5 run finished inside the flat 3-hour bound, so
  the population has 115 rows and nothing is set aside before judging.
- Refusal fallback on, never used. Claude Code's refusal fallback stayed at its
  default (on), as for Opus 5.5, but every assistant reply in every stream came
  from claude-sonnet-5-5 and no other model appears in any final modelUsage.
- Three Claude Code versions. The CLI updated itself during the sweep: low ran
  21 tasks on 2.1.291 and 2 on 2.1.292; medium and high ran on 2.1.292;
  extra-high ran 22 on 2.1.292 and paddockcore on 2.1.293; max ran on 2.1.293.
  Each row carries its version, checked against the stream's init event.
- A hash bridge. The sweep was launched before the 2026-10-05 tagged-worktree
  rule, so run summaries carry no source block and record task hashes from an
  older task_hash that counted __pycache__ files. Every row is admitted through
  the committed bridge, which pairs each recorded hash with its lock hash; the
  export checks each pair against the bridge file and the suite lock.
- Judge settings and versions. v3.23 reads its reviewer settings from
  docs/judging/judge-pins-v3.json. The original v3.3 and v3.4 protocol files
  were recovered from the owner's private backup, their sha256 equal the
  published values, and the v3.23 settings are identical to them. The export
  checks that the public reviewer settings equal those published in the v3.4
  bundle and that Muse runs the same binary hash; given --recovered-protocols
  it also checks the recovered files themselves. The Cursor pin hashes only
  Cursor's launcher script, which is the same in every Cursor release, so it
  never fixed the version: every v3.23 Grok call ran on Cursor CLI
  2026.10.01-e373342 (Cursor updated itself on 2026-10-07 at 14:43 PDT), while
  the v3.3 round recorded 2026.09.02-c22c1a3. The model id is unchanged;
  Cursor reports the display name "Grok 4.6 Medium" (frozen: "Cursor Grok
  4.6 Medium"), a rename the wrapper accepts and records.
- One operator recovery: Grok's primary review of medium lodgecore, through
  the standing recover_excerpts rule (a quote re-wrapped to the source's line
  breaks, scores untouched).
- Calibration allowance. Both judges passed under v3.23, each using the one-gate
  allowance (Muse on g11_repeatability, Grok on g04_formatting_is_presentation).
- Cost. Sonnet 5.5's vendor pricing page gives two cache-read rates ($0.20 in
  the table, $0.10 in the caching section), so cost is Claude Code's own
  list-price total (economics.cli_reported_cost_usd), asserted equal to the
  stream's final total_cost_usd. The harness's receipt estimate is null for
  this solver ("Unknown solver") and is not used.
"""

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-sonnet55-v323"
SCORES = SITE / "assets/data/swe-v4-sonnet55-v323-scores.csv"
EFFORTS = ("low", "medium", "high", "extra-high", "max")
MODEL = "sonnet55"
LEVELS = {MODEL: EFFORTS}
NAMES = {MODEL: "Claude Sonnet 5.5"}
PANELS = ("muse", "grok")
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
PROTOCOL_ID = "code-quality-maintenance-v3.23"
MAIN_MODEL = "claude-sonnet-5-5"
SWEEP = "runs-effort-sonnet55"
COMPARISON = "docs/results/swe-v4-sonnet55-2026-10/comparison.json"
BRIDGE = "docs/judging/task-hash-bridge-sonnet55.json"
PINS = "docs/judging/judge-pins-v3.json"
LOCK = "tasks/coding-intelligence-index-v4/suite.lock.json"
V34_PROTOCOLS = SITE / "assets/data/swe-v4-astra-fable51-v34/judge-protocols.json"
# The original protocol files, recovered from the owner's private backup; their published hashes (provenance of the v3.4 bundle).
ORIGINAL_PROTOCOLS = {"v3.3": "b82da5987bb555443c9006e51e5a4d555c41858dc710140f0571bd90ed8a5eec",
                      "v3.4": "1d80e0974526f8d825f14921c9102c8eda47ec312a0981783475149e31fd8524"}
CURSOR_CLI = {"v3.23": "2026.10.01-e373342", "v3.3": "2026.09.02-c22c1a3"}
CURSOR_UPDATED = "2026-10-07 14:43 PDT"
# Claude Code version per run, from each stream's init event (harness DECISIONS.md, 2026-10-07).
CLI_VERSIONS = {"low": {"2.1.291": 21, "2.1.292": 2}, "medium": {"2.1.292": 23}, "high": {"2.1.292": 23},
                "extra-high": {"2.1.292": 22, "2.1.293": 1}, "max": {"2.1.293": 23}}
CLI_293_EXTRA_HIGH = "legacy-paddockcore-binary-parity"
# platform.claude.com pricing page, checked 2026-10-07. The page disagrees with itself on cache reads, so neither rate prices a run:
# every run's cost is Claude Code's own reported total.
PRICING_VERIFIED = "2026-10-07"
RATES_PER_MILLION = {MAIN_MODEL: {"input": 2.00, "cache_write_5m": 2.50, "cache_write_1h": 4.00, "output": 10.00,
                                  "cache_hit_pricing_table": 0.20, "cache_hit_caching_section": 0.10}}
PRICING_METHOD = "Claude Code's own list-price total for the session (economics.cli_reported_cost_usd, equal to the stream's total_cost_usd)"
# Operator records the v3 wrapper can leave in calls/. The export refuses to write if the round left any it does not name here, so a
# surprise in the frozen summary is described on the page before it is published. Fill these in from the round's log if needed.
INVALID_MARKER = "operator-invalid.json"
SUPERSEDED_MARKER = "operator-invalid.superseded.json"
EXPECTED_INVALID: dict = {}  # {(panel, stage, submission id): one-line reason}
# The one recovery this round: Grok's primary review of medium lodgecore (submission-095) quoted a hard-wrapped line joined into one;
# the standing recover_excerpts rule (since v3, September 7) selected attempt 1 with the quote re-wrapped to the source's line breaks.
EXPECTED_RECOVERIES: dict = {("grok", "primary", "submission-095"): "recover_excerpts"}  # {(panel, stage, submission id): rule name}
DISPLAY_FROZEN, DISPLAY_REPORTED = "Cursor Grok 4.6 Medium", "Grok 4.6 Medium"
DISPLAY_RENAMES = 439  # selected Grok calls whose operator_review records the accepted rename
EXPECTED_REBUILDS: dict = {}  # {run_id: (effort, task)} for evidence rebuilt from the saved index diff
FORBIDDEN = (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    assert not any(mark in text for mark in FORBIDDEN), name
    assert "SWE v4" not in text and "ultra" not in text.lower(), name
    (DEST / name).write_text(text)


def mean_se(values):
    values = list(values)
    return {"n": len(values), "mean": statistics.mean(values),
            "se": statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0}


def composite(row, code_quality, weight):
    other = (0.5 - weight) / 2
    return 100 * (.5 * row["functional"] + other * row["quality"] + other * row["security"] + weight * code_quality / 100)


def stream_facts(run_dir):
    """Replies by serving model, final modelUsage, final CLI cost and the init event's Claude Code version."""
    replies, final, version = Counter(), None, None
    for line in (run_dir / "cli-agent-stream.jsonl").open(errors="replace"):
        if '"assistant"' not in line and '"result"' not in line and '"init"' not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            replies[event["message"].get("model")] += 1
        elif event.get("type") == "result":
            final = event
        elif event.get("type") == "system" and event.get("subtype") == "init":
            version = event.get("claude_code_version")
    assert final is not None and version is not None, run_dir.name
    usage = final.get("modelUsage") or {}
    per_model = {m: {"input_tokens": u.get("inputTokens", 0), "cache_read_tokens": u.get("cacheReadInputTokens", 0),
                     "cache_creation_tokens": u.get("cacheCreationInputTokens", 0), "output_tokens": u.get("outputTokens", 0),
                     "cli_cost_usd": u.get("costUSD", 0.0)} for m, u in sorted(usage.items())}
    raw = sum(v["input_tokens"] + v["cache_read_tokens"] + v["cache_creation_tokens"] + v["output_tokens"] for v in per_model.values())
    return dict(sorted(replies.items())), per_model, raw, final["total_cost_usd"], version


def call_records(v323):
    """Operator markers, superseded markers and recoveries the v3 wrapper left under calls/, keyed (panel, stage, submission)."""
    def key(p):
        return (p.parents[1].parent.name, p.parents[1].name, p.parent.name)
    invalid = {key(p): read(p) for p in (v323 / "calls").glob(f"*/*/*/{INVALID_MARKER}")}
    superseded = {key(p): read(p) for p in (v323 / "calls").glob(f"*/*/*/{SUPERSEDED_MARKER}")}
    recoveries = {}
    for p in (v323 / "calls").glob("*/*/*/selected.json"):
        selected = read(p)
        if "operator_recovery" in selected:
            recoveries[key(p)] = selected["operator_recovery"]
    return invalid, superseded, recoveries


def main():  # noqa: PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness-root", type=Path, default=SITE.parent / "VulcanBench")
    parser.add_argument("--docs-root", type=Path, default=None)
    parser.add_argument("--recovered-protocols", type=Path, default=None,
                        help="folder holding code-quality-maintenance-v3.3-protocol.json and -v3.4-protocol.json, the frozen originals "
                             "recovered from the private backup (harness docs/judging/recovered)")
    args = parser.parse_args()
    root = args.harness_root.resolve()
    docs = (args.docs_root or args.harness_root).resolve()
    v323 = root / "runs-code-quality-maintenance-v3.23"
    sweep = root / SWEEP
    summary = read(v323 / "summary.json")
    manifest = {r["id"]: r for r in read(v323 / "private-manifest.json")}
    protocol = read(v323 / "protocol.json")
    comparison_path = docs / COMPARISON
    comparison = read(comparison_path)
    bridge_path, pins_path = docs / BRIDGE, docs / PINS
    bridge = read(bridge_path)["tasks"]
    lock = read(docs / LOCK)["tasks"]

    # The frozen protocol, population and judges.
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["expected_submissions"] == len(manifest) == 115
    assert summary["passing_panels"] == list(PANELS) and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {"muse": 0, "grok": 0}
    assert digest(comparison_path) == protocol["source_comparison_sha256"]
    assert comparison["excluded"] == [] and comparison["missing"] == [] and len(comparison["rows"]) == 115
    assert comparison["cells"] == {f"{MODEL}/{e}": 23 for e in EFFORTS} == protocol["population"]["cells"]
    assert protocol["population"]["excluded"] == [] and protocol["population"]["missing"] == []
    assert comparison["task_hash_bridge"] == BRIDGE
    assert digest(pins_path) == protocol["judge_pins"]["source_sha256"]
    assert protocol["sensitivity_panels"] == {} and protocol["scored_siblings"] == {}
    public_reviewers = {p: {k: v for k, v in protocol["reviewers"][p].items() if k not in ("muse", "cursor", "zcode", "claude", "codex")}
                        for p in PANELS}
    # The v3.23 settings equal the ones the v3.4 bundle published; Muse is the same binary by hash.
    assert public_reviewers == read(V34_PROTOCOLS)["scored_panel"]
    assert protocol["reviewers"]["muse"]["binary_sha256"] == read(V34_PROTOCOLS)["scored_panel"]["muse"]["binary_sha256"]
    assert protocol["judge_pins"]["lost_sources"] == {f"runs-code-quality-maintenance-{v}/protocol.json": h for v, h in ORIGINAL_PROTOCOLS.items()}
    recovered_checked = False
    if args.recovered_protocols:  # the original files: published hashes, and the same reviewer settings as v3.23
        for version, sha in ORIGINAL_PROTOCOLS.items():
            original = args.recovered_protocols / f"code-quality-maintenance-{version}-protocol.json"
            assert digest(original) == sha, version
            for p, settings in read(original)["reviewers"].items():
                if p in PANELS:
                    assert {k: v for k, v in settings.items() if k not in ("muse", "cursor")} == public_reviewers[p], (version, p)
        recovered_checked = True
    # Every task's bridge pair: the recorded hash is the sweep's, the lock hash is the frozen suite's.
    assert set(bridge) == set(lock) and len(bridge) == 23
    assert all(bridge[t]["lock"] == lock[t] for t in bridge)

    invalid, superseded, recoveries = call_records(v323)
    assert set(invalid) == set(EXPECTED_INVALID), invalid
    assert set(recoveries) == set(EXPECTED_RECOVERIES), recoveries
    assert {k: (EXPECTED_RECOVERIES[k], v["method"]) for k, v in recoveries.items()} == {
        ("grok", "primary", "submission-095"): ("recover_excerpts", "excerpt re-wrapped to source line breaks")}
    # Every selected Grok call reported the renamed display label for the pinned model id; the wrapper recorded the accepted rename.
    grok_calls = [read(q) for q in (v323 / "calls/grok").glob("*/*/selected.json")]
    assert len(grok_calls) == 440 and {c["model_reported"] for c in grok_calls} == {DISPLAY_REPORTED}
    assert protocol["reviewers"]["grok"]["display_name"] == DISPLAY_FROZEN
    assert sum("label renamed by the provider" in json.dumps(c.get("operator_review")) for c in grok_calls) == DISPLAY_RENAMES
    rebuild_paths = sorted((v323 / "reconstruction").glob("*.json"))
    assert {p.stem for p in rebuild_paths} == set(EXPECTED_REBUILDS), [p.stem for p in rebuild_paths]

    # Every solver summary in the sweep folder is a population row: 115 in all, no orphan attempt folder.
    summaries = {p.parent.name: p for p in sweep.glob("*/legacy-*/summary.json")}
    record = {r["run_id"]: r for r in comparison["rows"]}
    assert len(summaries) == 115 and set(summaries) == set(record)
    assert not [p for p in sweep.glob("*/legacy-*") if p.is_dir() and not (p / "summary.json").exists()]
    DEST.mkdir(parents=True, exist_ok=True)

    one_panel_rows = []
    rows = []
    for entry in summary["rows"]:
        run = manifest[entry["id"]]
        assert run["model"] == entry["model"] == MODEL and run["effort"] == entry["effort"] and run["task"] == entry["task"]
        run_dir = sweep / run["effort"] / run["run_id"]
        # The manifest's source_directory points into the judging worktree, whose runs folder links here; match by summary hash.
        assert digest(run_dir / "summary.json") == run["source_hashes"]["summary"], run["run_id"]
        solver = read(run_dir / "summary.json")
        replies, per_model, raw, cli_total, init_version = stream_facts(run_dir)
        assert abs(solver["economics"]["cli_reported_cost_usd"] - cli_total) < 1e-9, run["run_id"]
        assert solver["economics"]["api_equivalent_cost_usd"] is None and run["api_equivalent_cost_usd"] is None
        assert replies == run["fallback_replies"] == {MAIN_MODEL: sum(replies.values())} and not run["fallback"], run["run_id"]
        assert list(per_model) == [MAIN_MODEL], run["run_id"]
        assert solver["cli_agent"]["harness_version"] == run["solver_cli_version"] == f"{init_version} (Claude Code)", run["run_id"]
        assert solver["cli_agent"]["requested_model"] == solver["cli_agent"]["reported_model"] == MAIN_MODEL
        assert solver["finished"] is True and solver["duration_s"] < 10800, run["run_id"]
        assert "source" not in solver, run["run_id"]  # pre tagged-worktree sweep: no source block
        pair = bridge[run["task"]]
        assert solver["task_hash"] == pair["recorded"] and run["task_hash_bridge"] == {"lock": pair["lock"], "recorded": pair["recorded"]}
        audit = solver["integrity_audit"]
        assert audit["web"]["verdict"] == "no_web" and not audit["contaminated"]
        assert audit["filesystem"]["benchmark_data_paths"] == [] and audit["filesystem"]["answer_key_paths"] == []
        hidden = solver["verifier"]["fail_to_pass"]
        panels = entry["panels"]
        assert not any(panels[p]["reviewer_fallback"] for p in PANELS)
        scored = [p for p in PANELS if panels[p]["l1"] is not None]
        assert scored, run["run_id"]  # summary rows exist only for published submissions
        if scored == list(PANELS):
            judged = "published"
        else:
            judged = (f"published from {'Muse Spark 1.3' if scored == ['muse'] else 'Grok 4.6'} alone: the other judge has no valid "
                      "review, so the v3.23 summary scores this run from the one valid review, as it does for any such submission")
            one_panel_rows.append(entry["id"])
        published = entry["published"]
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in scored)
        redistributed = published["l2_redistributed"]
        if redistributed:
            l2, code_quality = None, l1
        else:
            l2 = statistics.mean(panels[p]["l2"] for p in scored if panels[p]["l2"] is not None)
            code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
        assert abs(code_quality - published["code_quality"]) < 1e-9, run["run_id"]
        combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
        combined_20 = composite(run, code_quality, 0.20)
        assert abs(combined_33 - published["composite_v3"]) < 1e-9, run["run_id"]
        assert abs(combined_20 - published["composite_v2_profile"]) < 1e-9, run["run_id"]
        panel_record = {}
        for p in PANELS:
            if p in scored:
                panel_record[p] = {"scored": True, "readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                                   "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                                   "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": panels[p]["reviewer_fallback"]}
            else:
                panel_record[p] = {"scored": False, "readability": None, "maintainability": None, "reviewed_score": None, "intent_recovery": None,
                                   "scored_quirks": None, "reviewer_fallback": False}
        rows.append({
            "model": MODEL, "effort": entry["effort"], "task": entry["task"], "run_id": run["run_id"],
            "judged_under": PROTOCOL_ID, "judged": judged, "scored_panels": scored, "finished": True,
            "solver_fallback": False, "replies_by_model": replies,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v), "hidden_behaviours": len(hidden),
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": redistributed, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20, "panels": panel_record,
            "passed_quirk_families": len(run["passed_families"]),
            "evidence_rebuilt_from_index_diff": run["run_id"] in EXPECTED_REBUILDS,
            "integrity_audit": {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False},
            "task_hash_bridge": {"recorded": pair["recorded"], "lock": pair["lock"]},
            "duration_s": run["duration_s"], "raw_tokens": raw,
            "token_usage": {"output_tokens": sum(v["output_tokens"] for v in per_model.values()), "by_model": per_model},
            "estimated_usd": cli_total, "pricing_method": PRICING_METHOD,
            "started_at": run["started_at"], "finished_at": run["finished_at"], "solver_cli_version": run["solver_cli_version"],
            "evidence_sha256": run["evidence_sha256"],
        })
    rows.sort(key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 115 and len({(r["effort"], r["task"]) for r in rows}) == 115
    # No exclusions: every population row is in the frozen summary.
    assert summary["published_submissions"] == len(rows) == 115 and summary["ready_for_publication"]
    for effort, versions in CLI_VERSIONS.items():
        got = Counter(r["solver_cli_version"].split()[0] for r in rows if r["effort"] == effort)
        assert got == Counter(versions), (effort, got)
    assert [r["task"] for r in rows if r["effort"] == "extra-high" and r["solver_cli_version"].startswith("2.1.293")] == [CLI_293_EXTRA_HIGH]

    save("runs.json", {"runs": len(rows), "published": len(rows), "unpublished": 0, "one_panel": len(one_panel_rows), "weights": WEIGHTS,
                       "code_quality_split": SPLIT_WITHOUT_L3,
                       "judged_rule": "judged is \"published\" where both judges have a valid review; any other row is also published, from the "
                                      "one judge with a valid review, and its judged field says why",
                       "panel_rule": "reviewed_score and intent_recovery are the equal mean of the panels in scored_panels; a panel with no valid "
                                     "review has scored false and null fields, and nothing from it enters the score",
                       "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator, intent_recovery is "
                                               "null, intent_recovery_redistributed is true and Code quality equals the reviewed score",
                       "fallback_rule": "Claude Code's refusal fallback was on (its default). solver_fallback would be true if any assistant reply "
                                        "came from a model other than claude-sonnet-5-5; replies_by_model counts them. No Sonnet 5.5 run used it.",
                       "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests (the documented behaviours the "
                                                  "fix must produce); hidden_behaviours_fixed counts those the run passed",
                       "task_hash_rule": "The sweep predates tagged run worktrees and recorded task hashes from an older task_hash that counted "
                                         "__pycache__ files. task_hash_bridge pairs each recorded hash with the frozen suite lock's hash, from the "
                                         "harness's committed docs/judging/task-hash-bridge-sonnet55.json.",
                       "token_fields": {"raw_tokens": "input, cache reads, cache writes and output from the final modelUsage",
                                        "token_usage.output_tokens": "output tokens, reasoning included"},
                       "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "scored_panels", "combined_33", "combined_20_profile",
                         "functional_pct", "automated_quality_pct", "security_pct", "hidden_behaviours_fixed", "hidden_behaviours", "code_quality",
                         "reviewed_score", "intent_recovery", "intent_recovery_redistributed",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery", "grok_reviewed", "grok_readability",
                         "grok_maintainability", "grok_intent_recovery", "passed_quirk_families", "solver_fallback", "all_replies",
                         "duration_s", "raw_tokens", "output_tokens", "estimated_usd", "started_at", "finished_at", "solver_cli_version",
                         "evidence_sha256"])
        for r in rows:
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"],
                             "published" if r["judged"] == "published" else "published, one panel", "+".join(r["scored_panels"]),
                             fmt(r["combined_33"]), fmt(r["combined_20_profile"]),
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             r["hidden_behaviours_fixed"], r["hidden_behaviours"],
                             fmt(r["code_quality"]), fmt(r["reviewed_score"]), fmt(r["intent_recovery"]), r["intent_recovery_redistributed"],
                             *[fmt(r["panels"][p][k]) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], r["solver_fallback"], sum(r["replies_by_model"].values()),
                             r["duration_s"], r["raw_tokens"], r["token_usage"]["output_tokens"], fmt(r["estimated_usd"], 6),
                             r["started_at"], r["finished_at"], r["solver_cli_version"], r["evidence_sha256"]])

    def panel_mean(r, key):
        return statistics.mean(r["panels"][p][key] for p in r["scored_panels"])

    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        scored_ir = [r for r in rs if r["intent_recovery"] is not None]
        assert len(rs) == 23
        g = {
            "model": MODEL, "effort": effort, "n": len(rs), "runs": len(rs), "unpublished_runs": 0,
            "one_panel_runs": sum(len(r["scored_panels"]) == 1 for r in rs),
            "combined_33": mean_se(r["combined_33"] for r in rs), "combined_20_profile": mean_se(r["combined_20_profile"] for r in rs),
            "code_quality": mean_se(r["code_quality"] for r in rs), "reviewed_score": mean_se(r["reviewed_score"] for r in rs),
            "intent_recovery": mean_se(r["intent_recovery"] for r in scored_ir),
            "intent_recovery_redistributed_runs": len(rs) - len(scored_ir),
            "readability": mean_se(panel_mean(r, "readability") for r in rs),
            "maintainability": mean_se(panel_mean(r, "maintainability") for r in rs),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in rs if r["panels"][p]["scored"]) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in rs), "automated_quality": mean_se(100 * r["automated_quality"] for r in rs),
            "security": mean_se(100 * r["security"] for r in rs),
            "passed": sum(r["functional"] == 1 for r in rs), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
            "minutes": mean_se(r["duration_s"] / 60 for r in rs),
            "solver_fallback_runs": 0, "priced_runs": len(rs),
            "cli_versions": dict(sorted(Counter(r["solver_cli_version"].split()[0] for r in rs).items())),
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
        }
        entry = summary["groups"][f"{MODEL}/{effort}"]
        assert g["n"] == entry["n"] == entry["composite_v3"]["n"]
        for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
            assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9, (effort, field)
            assert abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
        assert g["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
        for p in PANELS:
            assert g["by_panel"][p]["n"] == entry["by_panel"][p]["n"]
            assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9
        groups.append(g)
    # Facts fixed by the sweep before judging (harness DECISIONS.md, 2026-10-07): pass@1 0.652, 0.739, 0.870, 0.957 and 1.000.
    assert [g["passed_all_runs"] for g in groups] == [15, 17, 20, 22, 23]
    assert [g["hidden_behaviours_fixed"] for g in groups] == [214, 219, 223, 230, 231] and all(g["hidden_behaviours"] == 231 for g in groups)
    assert [round(g["minutes"]["mean"], 1) for g in groups] == [20.0, 20.8, 14.8, 21.6, 38.0]
    assert [f'{g["usd"]["mean"]:.2f}' for g in groups] == ["2.88", "3.00", "2.39", "3.38", "5.52"]
    # The harness score card's table (docs/results/swe-v4-sonnet55-2026-10/sonnet55-v323-efforts.csv) carries the same figures.
    card_table = docs / "docs/results/swe-v4-sonnet55-2026-10/sonnet55-v323-efforts.csv"
    with card_table.open(newline="") as source:
        card = {r["effort"]: r for r in csv.DictReader(source)}
    for g in groups:
        c = card[g["effort"]]
        assert int(c["n"]) == g["n"] and int(c["passed"]) == g["passed_all_runs"] and c["fallbacks"] == "0"
        for column, value in (("combined_v3", g["combined_33"]["mean"]), ("combined_v3_se", g["combined_33"]["se"]),
                              ("combined_20pct", g["combined_20_profile"]["mean"]), ("code_quality", g["code_quality"]["mean"]),
                              ("code_quality_se", g["code_quality"]["se"]), ("readability", g["readability"]["mean"]),
                              ("maintainability", g["maintainability"]["mean"]), ("intent_recovery", g["intent_recovery"]["mean"]),
                              ("muse_l1", g["by_panel"]["muse"]["mean"]), ("grok_l1", g["by_panel"]["grok"]["mean"]), ("minutes", g["minutes"]["mean"])):
            assert abs(float(c[column]) - value) < 1e-4, (g["effort"], column)
    save("groups.json", groups)

    with SCORES.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "combined_33", "combined_33_se", "combined_20_profile", "code_quality", "code_quality_se",
                         "reviewed_score", "intent_recovery", "intent_recovery_redistributed_runs", "readability", "maintainability",
                         "muse_reviewed", "grok_reviewed", "functional", "automated_quality", "security", "passed_of_23",
                         "hidden_behaviours_fixed_of_231", "mean_minutes", "mean_minutes_se", "mean_raw_tokens", "mean_usd", "mean_usd_se", "total_usd",
                         "cli_versions"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"],
                             f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"], f'{g["readability"]["mean"]:.4f}',
                             f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}', f'{g["by_panel"]["grok"]["mean"]:.4f}',
                             f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}',
                             g["passed_all_runs"], g["hidden_behaviours_fixed"], f'{g["minutes"]["mean"]:.4f}', f'{g["minutes"]["se"]:.4f}',
                             f'{g["raw_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}', f'{g["usd"]["se"]:.6f}', f'{g["usd_total"]:.6f}',
                             " ".join(f"{v}x{k}" for k, v in g["cli_versions"].items())])

    totals = {MODEL: {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "raw_tokens": sum(r["raw_tokens"] for r in rows),
                      "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    assert f'{totals[MODEL]["usd"]:.2f}' == "394.77" and f'{totals[MODEL]["usd"] / 115:.2f}' == "3.43"
    save("economics.json", {
        "scope": "Solver inference only, API-equivalent at list rates; the model ran on a Claude Max subscription through Claude Code "
                 "(--billing subscription), so these are estimates, not bills. Judging is excluded. Every run in the sweep is priced.",
        "pricing_verified": PRICING_VERIFIED,
        "sources": {"anthropic": "https://platform.claude.com/docs/en/about-claude/pricing"},
        "rates_per_million": RATES_PER_MILLION,
        "pricing_method": PRICING_METHOD,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "minutes": g["minutes"],
                    "solver_fallback_runs": 0} for g in groups],
        "totals": totals,
        "limitations": [
            "Cost is Claude Code's own list-price total for each session (cli_reported_cost_usd), checked against the stream's final "
            "total_cost_usd. Every reply came from claude-sonnet-5-5 and no other model appears in any run's usage.",
            "Anthropic's pricing page lists Sonnet 5.5 cache reads at $0.20 per million tokens in its table and at 0.05x input ($0.10) in "
            "its prompt caching section. The export does not re-price runs at either rate; if Anthropic corrects the page, the CLI-reported "
            "figure stays the published one unless the owner decides otherwise (harness DECISIONS.md, 2026-10-07).",
            "Claude Code prices cache writes by their observed TTL; the export takes its total as reported.",
            "No Batch, Fast or priority pricing is applied.",
        ],
        "comparison_sha256": digest(comparison_path),
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    for panel in PANELS:
        result = read(v323 / f"calibration-{panel}.json")
        assert result["passed"] and result["allowance_used"] and len(result["failing_gates"]) == 1
        assert result["protocol_sha256"] == digest(v323 / "protocol.json") and result["call_count"] == 80
        [gate] = result["failing_gates"]
        assert 0 < result["gates"][gate]["shortfall"] <= result["allowance"]["max_shortfall"]
        calibration[panel] = {k: result[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used",
                                                     "gates", "control_means")}
    assert calibration["muse"]["failing_gates"] == ["g11_repeatability"]
    assert calibration["grok"]["failing_gates"] == ["g04_formatting_is_presentation"]
    save("calibration.json", calibration)

    save("judge-protocols.json", {
        "scored_panel": public_reviewers,
        "protocol_ids": {p: protocol["id"] for p in PANELS}, "protocol_sha256": {p: digest(v323 / "protocol.json") for p in PANELS},
        "amends": protocol["amends"], "system": protocol["system"], "rubric": protocol["rubric"],
        "pair_instruction": protocol["pair_instruction"], "probe_instruction": protocol["probe_instruction"],
        "match_instruction": protocol["match_instruction"], "schemas": protocol["schemas"], "weights": protocol["weights"],
        "gate_allowance": protocol["gate_allowance"], "repeats": protocol["repeats"], "seed": protocol["seed"],
        "single_panel_rule": protocol["single_panel_rule"], "invalid_response_retries": protocol["invalid_response_retries"],
        "control_source_hashes": protocol["control_source_hashes"],
        "population": protocol["population"],
        "judge_pins": {
            "source": protocol["judge_pins"]["source"], "source_sha256": protocol["judge_pins"]["source_sha256"],
            "original_protocol_sha256": ORIGINAL_PROTOCOLS,
            "originals": "The original v3.3 and v3.4 protocol files were recovered from the owner's private backup; their sha256 equal the "
                         "published values, and the v3.23 judge settings are identical to them.",
            "originals_checked_by_this_export": recovered_checked,
            "binary_sha256": {"muse": protocol["reviewers"]["muse"]["binary_sha256"],
                              "cursor_launcher": protocol["binaries"][protocol["reviewers"]["grok"]["cursor"]]["sha256"]},
            "muse": "same binary as every earlier round (sha256 match)",
            "cursor": f"The Cursor pin hashes only Cursor's launcher script, which is identical across Cursor releases, so it does not fix the "
                      f"version. Cursor updated itself on {CURSOR_UPDATED}; every v3.23 Grok call ran on Cursor CLI {CURSOR_CLI['v3.23']}, "
                      f"while the v3.3 round recorded {CURSOR_CLI['v3.3']}. The Grok model id (cursor-grok-4.6-medium) is the same; Cursor "
                      f"reports its display name as \"{DISPLAY_REPORTED}\" where the frozen settings say \"{DISPLAY_FROZEN}\", a rename the "
                      f"wrapper accepts and records. Grok 4.6 passed calibration under v3.23.",
            "settings_match_v3_4_bundle": True,
            "frozen_wording_note": "The frozen v3.23 protocol describes these files as lost and the Cursor binary as re-pinned; that "
                                   "wording predates the recovery and is superseded by the fields above.",
        },
        "task_hash_bridge": {"file": BRIDGE, "sha256": digest(bridge_path), "tasks": len(bridge)},
        "unpublished": [],
        "one_panel": [{"effort": manifest[i]["effort"], "task": manifest[i]["task"]} for i in one_panel_rows],
        "invalid_calls": [{"panel": k[0], "stage": k[1], "submission": k[2], "reason": EXPECTED_INVALID[k], "rule": v.get("rule")}
                          for k, v in sorted(invalid.items())],
        "superseded_markers": [{"panel": k[0], "stage": k[1], "submission": k[2]} for k in sorted(superseded)],
        "operator_recoveries": [{"panel": k[0], "stage": k[1], "submission": k[2], "effort": manifest[k[2]]["effort"], "task": manifest[k[2]]["task"],
                                 "rule": EXPECTED_RECOVERIES.get(k), "method": v.get("method"), "source_attempt": v.get("source_attempt"),
                                 "respelled_excerpts": len(v.get("original_excerpts", {})),
                                 "checks": "both attempts failed only the excerpt rule; every rejected excerpt matches the source once whitespace "
                                           "and line breaks are collapsed; scores untouched, original excerpt kept in the receipt"}
                                for k, v in sorted(recoveries.items())],
        "display_name": {"frozen": DISPLAY_FROZEN, "reported": DISPLAY_REPORTED, "model_id": "cursor-grok-4.6-medium",
                         "accepted_renames_recorded": DISPLAY_RENAMES, "selected_grok_calls": 440,
                         "note": "Cursor has reported the display name \"Grok 4.6 Medium\" for the pinned model id since 2026-09-21; the "
                                 "frozen settings say \"Cursor Grok 4.6 Medium\". The wrapper accepts the rename and records it per call."},
        "evidence_rebuilds": [{"effort": EXPECTED_REBUILDS[p.stem][0], "task": EXPECTED_REBUILDS[p.stem][1], "method": read(p)["method"]}
                              for p in rebuild_paths],
    })
    save("provenance.json", {
        "source_artifacts_sha256": {
            **{f"v3.23/{n}": digest(v323 / n) for n in ("summary.json", "protocol.json", "private-manifest.json",
                                                        "calibration-muse.json", "calibration-grok.json")},
            **{f"v3.23/calls/{'/'.join(k)}/{INVALID_MARKER}": digest(v323 / "calls" / "/".join(k) / INVALID_MARKER) for k in sorted(invalid)},
            **{f"v3.23/reconstruction/{p.name}": digest(p) for p in rebuild_paths},
            "comparison.json": digest(comparison_path), "task-hash-bridge-sonnet55.json": digest(bridge_path),
            "sonnet55-v323-efforts.csv": digest(card_table),
            "judge-pins-v3.json": digest(pins_path), "suite.lock.json": digest(docs / LOCK),
        },
        "export_checks": ["115 solver summaries in the sweep folder, one per population row, all finished inside the 3-hour bound; none "
                          "missing, excluded or retried",
                          "every run's summary hash matches the frozen manifest; every run's integrity audit is clean: no web access, no "
                          "benchmark-data or answer-key paths",
                          "every run's recorded task hash is the bridge's recorded hash for its task, and every bridge lock hash equals the "
                          "frozen suite lock",
                          "every reply in every stream came from claude-sonnet-5-5; no other model appears in any final modelUsage",
                          "every run's Claude Code version matches its stream's init event and the per-level mix in the decision record",
                          "both scored panels passed calibration under v3.23, each with the one-gate allowance; no reviewer fallbacks",
                          "the published reviewer settings equal those in the v3.4 bundle, and Muse's binary hash equals the v3.4 pin",
                          "the judge pins file's hash matches the one frozen in the protocol, and the protocol records the published "
                          "v3.3 and v3.4 protocol hashes" + (", which the recovered original files match, with identical reviewer "
                                                              "settings" if recovered_checked else ""),
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary",
                          "five-cell means and standard errors matched to the frozen summary's groups, per-judge means included",
                          "combined score, Code quality and its components, pass counts and runtime matched to the harness score card table",
                          "every run's cost equals Claude Code's final total_cost_usd in its stream and the run summary's cli_reported_cost_usd",
                          "the population record's hash matches the one frozen in the protocol", "no dashes or host paths in exported text"],
        "limits": ["The sweep was launched on October 6, 2026, before the harness's October 5 tagged-worktree rule reached the checkout it ran "
                   "from, so run summaries carry no source block and record task hashes from an older task_hash that counted __pycache__ "
                   "files. Task content was verified identical to the frozen suite lock, judging admitted runs through the committed hash "
                   "bridge, and all 107 cached .pyc files an agent could see were byte-identical to compiling the starting source.",
                   "Judge settings: the original v3.3 and v3.4 judge protocol files were recovered from the owner's private backup, their "
                   "sha256 equal the published values, and the v3.23 settings are identical to them. Muse Spark 1.3 ran the same binary "
                   f"(sha256 match). Grok 4.6 ran through a newer Cursor CLI: the Cursor pin hashes only Cursor's launcher script, which is "
                   f"the same in every release, so it never fixed the version; Cursor updated itself on {CURSOR_UPDATED}, and every v3.23 "
                   f"Grok call ran on {CURSOR_CLI['v3.23']}, while the v3.3 round recorded {CURSOR_CLI['v3.3']}. The Grok model id is the "
                   f"same; Cursor reports the display name \"{DISPLAY_REPORTED}\" (frozen: \"{DISPLAY_FROZEN}\") since 2026-09-21, and the "
                   f"wrapper accepted and recorded that rename {DISPLAY_RENAMES} times. Grok 4.6 passed calibration under v3.23.",
                   "One operator recovery: Grok 4.6's primary review of medium lodgecore quoted a hard-wrapped line joined into one on both "
                   "attempts; the standing recover_excerpts rule selected attempt 1 with the quote re-wrapped to the source's line "
                   "breaks, scores untouched. Invalid-response retries under the frozen rule: Muse Spark 1.3 10, Grok 4.6 2.",
                   "Claude Code versions: low ran 21 tasks on 2.1.291 and 2 on 2.1.292; medium and high on 2.1.292; extra-high 22 on "
                   "2.1.292 and paddockcore on 2.1.293; max on 2.1.293. Earlier Claude columns used older Claude Code releases.",
                   "Both judges passed calibration under v3.23 using the one-gate allowance: Muse Spark 1.3 missed only g11_repeatability "
                   "and Grok 4.6 only g04_formatting_is_presentation, each within the half-point shortfall.",
                   "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.",
                   "One attempt per task and level. The solver sweep ran October 6, 06:49 PDT, to October 8, 03:38 PDT, serially, on the "
                   "owner's Mac with the local sandbox and a flat 3-hour task bound. Judging ran October 8, 05:02 to 18:02 PDT; the Claude "
                   "Haiku 5.5 solver sweep, which started at 03:40 PDT after the last Sonnet 5.5 run had finished, ran on the same "
                   "machine during judging, which does not touch Sonnet 5.5's runtime figures."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, task hash bridge pairs, raw tokens, replies by serving model and Claude Code's "
                             "list-price cost.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts", "host binary paths"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
