"""Export the public record of the Claude Fable 5.2 effort sweep on Frontier v4, judged under v3.30.2 and v3.30.3.

Adapted from the v3.27 DeepSeek V4.1 Flash export (the same panel, Muse Spark
1.3 and GPT-6.1 Sol) and the v3.24 Claude Haiku 5.5 export (the same harness,
Claude Code, priced at its own list-price total). Same publication scope:
per-run scores, per-panel sub-scores, aggregates, judge protocol text,
calibration verdicts, raw tokens and cost. Raw prompts, patches, thinking
summaries, quirk answer keys and host paths are withheld. Run from the site
root:

    python3 scripts/export_swe_v4_v330_evidence.py --harness-root ../VulcanBench \\
        --results-root <VulcanBench checkout at main> \\
        --judging-root ../VulcanBench-runs/bench-2026-11-11-fable52-judging-v3301 \\
        --muse-root ../VulcanBench-runs/bench-2026-11-10-fable52-judging-v330

--harness-root holds the sweep (runs-effort-fable52), its launcher log and the
Max resume script. --results-root is a harness checkout carrying the merged
results folder docs/results/swe-v4-fable52-2026-11 and the frozen suite lock.
--judging-root holds the published rounds v3.30.2 (Low to Extra-high) and
v3.30.3 (Max) beside Muse Spark 1.3's Max round v3.30.1; --muse-root holds
v3.30, Muse Spark 1.3's round for Low to Extra-high and the exam Grok 4.6 failed.

What differs from the earlier exports, all forced by the sweep or its judging:

- Four rounds, two published. v3.30 seated Muse Spark 1.3 and Grok 4.6. Grok
  failed calibration gate g14_pair_2_1 and judged nothing; Muse passed and
  judged Low to Extra-high, and judged Max under v3.30.1. On the owner's choice
  GPT-6.1 Sol took Grok's seat, passed every gate under v3.30.2, and judged Low
  to Extra-high (v3.30.2) and Max (v3.30.3) on byte-copied freezes of the same
  populations. The published rounds score Sol themselves and read Muse from its
  own rounds as a scored sibling.
- Claude Code 2.1.321 can emit a second result receipt when a background task
  resumes a session after the model stops (two runs). Tokens, thinking tokens
  and cost sum every receipt, as the population record does; the run summary
  kept only the last one.
- The run summaries record no thinking tokens (adapter bug, grading
  unaffected); the export takes them from the raw streams and checks them
  against the population record.
- Max waited for the Fable usage limit. The first Max attempts were refused by
  the limit and did no work; they hold no summary, are kept apart under
  infra-aborted, and are not part of the population.
- Thirteen judge answers were published through frozen recovery rules: twelve
  GPT-6.1 Sol answer-key matches through recover_one_based_indexes and one Muse
  Spark 1.3 probe excerpt re-wrapped to its source line breaks. None changes a
  score.
"""

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-fable52-v330"
SCORES = SITE / "assets/data/swe-v4-fable52-v330-scores.csv"
RESULTS = "docs/results/swe-v4-fable52-2026-11"
CARDS = {"fable52-vs-frontier.png": SITE / "assets/cards/swe-v4-fable52-v330.png",
         "fable52-no-memorization.png": SITE / "assets/cards/swe-v4-fable52-v330-memorization.png"}
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PROVIDER_EFFORT = {"low": "low", "medium": "medium", "high": "high", "extra-high": "xhigh", "max": "max"}
MODEL = "fable52"
NAMES = {MODEL: "Claude Fable 5.2"}
SOLVER = "claude-code:claude-fable-5-2"
MAIN_MODEL = "claude-fable-5-2"
CLI_VERSION = "2.1.321 (Claude Code)"
PANELS = ("muse", "sol")
JUDGES = {"muse": "Muse Spark 1.3", "sol": "GPT-6.1 Sol"}
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
ROUNDS = {"v3.30.2": ("runs-code-quality-maintenance-v3.30.2", ("low", "medium", "high", "extra-high"), "comparison.json"),
          "v3.30.3": ("runs-code-quality-maintenance-v3.30.3", ("max",), "comparison-max.json")}
MUSE_ROUNDS = {"v3.30.2": "runs-code-quality-maintenance-v3.30", "v3.30.3": "runs-code-quality-maintenance-v3.30.1"}
LOCK = "tasks/coding-intelligence-index-v4/suite.lock.json"
SWEEP = "runs-effort-fable52"
SWEEP_LOG = "logs/fable52-v4.log"
MAX_RESUME = "logs/fable52-max-resume.sh"
TAG, COMMIT = "bench/2026-11-09-fable52-frontier-v4", "58e4bb3b7b2d0e4ed2c340e45c337a0931f485eb"
LIMIT_REFUSED_ATTEMPTS = 69
TWO_RECEIPT_RUNS = {("low", "legacy-matchcore-order-book-parity"), ("extra-high", "legacy-reflowcore-binary-parity")}
INDEX_METHOD = "one-based departure indexes moved to zero-based; statuses untouched"
INDEX_RECOVERIES = {"v3.30.2": 8, "v3.30.3": 4}
MUSE_REWRAP = ("probe", "excerpt re-wrapped to source line breaks")
PUBLIC_V327 = SITE / "assets/data/swe-v4-deepseek-flash-v327/judge-protocols.json"
SEAT_NOTES = {"neutrality", "seat", "binary_location"}  # descriptive text that names the submission lab or seat
PRICING_METHOD = ("Claude Code's own list-price total for the session (the last result receipt's total_cost_usd, which is "
                  "cumulative over the session's receipts), the cost basis of every Claude column; the adapter's own estimate prices cached prompt tokens at the full "
                  "input rate and is not used")
FORBIDDEN = (chr(0x2014), chr(0x2013), chr(0), "/Users/", "/home/", "/private/", "/var/folders/")


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


def code_quality_of(reviewed, intent):
    return reviewed if intent is None else (SPLIT_WITHOUT_L3["l1"] * reviewed + SPLIT_WITHOUT_L3["l2"] * intent) / WEIGHTS["code_quality"]


def stream_facts(run_dir):
    """Replies by serving model, every result receipt summed, and the init event's Claude Code version."""
    replies, version = Counter(), None
    usage = {"input_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 0}
    thinking, receipts, session_cost = 0, 0, {}
    for line in (run_dir / "cli-agent-stream.jsonl").open():
        event = json.loads(line)
        kind = event.get("type")
        if kind == "assistant":
            replies[event["message"].get("model")] += 1
        elif kind == "result":
            receipts += 1
            u = event["usage"]
            for k in usage:
                usage[k] += u[k]
            thinking += u.get("output_tokens_details", {}).get("thinking_tokens", 0)
            # total_cost_usd is cumulative within a session (usage is per invocation): keep each session's last total.
            session_cost[event.get("session_id")] = event["total_cost_usd"]
        elif kind == "system" and event.get("subtype") == "init":
            version = event.get("claude_code_version")
    assert receipts >= 1 and version is not None and len(session_cost) == 1, run_dir.name
    return dict(replies), usage, thinking, sum(session_cost.values()), receipts, version


def solver_facts(run_dir, effort, task, lock, receipt):
    """Checks every run must pass, and the facts each row carries from the solver side."""
    solver = read(run_dir / "summary.json")
    assert solver["model"] == SOLVER and solver["task_id"] == task, run_dir.name
    assert solver["effort"]["requested"] == effort and solver["effort"]["provider_value"] == PROVIDER_EFFORT[effort], run_dir.name
    agent = solver["cli_agent"]
    assert (agent["harness"], agent["harness_version"], agent["billing"]) == ("claude-code", CLI_VERSION, "subscription"), run_dir.name
    assert agent["requested_model"] == agent["reported_model"] == MAIN_MODEL, run_dir.name
    assert agent["execution_boundary"] == "host-workspace; permission-mode=auto; safe-mode", run_dir.name
    assert solver["served_models"] == {MAIN_MODEL: solver["served_models"][MAIN_MODEL]} and solver["served_model_switches"] == 0
    source = solver["source"]  # tagged run worktree, clean: no hash bridge needed
    assert source["harness"]["describe"] == TAG and source["harness"]["commit"] == COMMIT, run_dir.name
    assert not source["harness"]["dirty"] and not source["dirty"] and not source["allow_dirty"], run_dir.name
    assert solver["task_hash"] == lock[task], run_dir.name
    audit = solver["integrity_audit"]
    assert audit["web"]["verdict"] == "no_web" and not audit["contaminated"] and not audit["web"]["contaminated"], run_dir.name
    fs = audit["filesystem"]
    assert fs["benchmark_data_paths"] == [] and fs["answer_key_paths"] == [] and not fs.get("contaminated"), run_dir.name
    assert solver["finished"] is True and solver["duration_s"] < 10800 and not solver["scores"].get("budget_exceeded"), run_dir.name
    replies, usage, thinking, cost, receipts, version = stream_facts(run_dir)
    assert f"{version} (Claude Code)" == CLI_VERSION and list(replies) == [MAIN_MODEL], (run_dir.name, replies)
    assert digest(run_dir / "cli-agent-stream.jsonl") == receipt["stream_sha256"], run_dir.name
    assert usage == receipt["usage"] and thinking == receipt["thinking_tokens"] and receipts == receipt["result_receipts"], run_dir.name
    assert abs(cost - receipt["cli_api_equivalent_estimate_usd"]) < 1e-9, run_dir.name
    assert (receipts == 2) == ((effort, task) in TWO_RECEIPT_RUNS) and receipts in (1, 2), (run_dir.name, receipts)
    raw = sum(usage.values())
    assert raw == receipt["raw_tokens"], run_dir.name
    calls = solver["tool_calls"]
    assert calls["file"] == "tool-calls.jsonl" and calls["capture"] == "recorded", run_dir.name
    hidden = solver["verifier"]["fail_to_pass"]
    return solver, {
        "solver_cli_version": CLI_VERSION, "source_tag": TAG, "task_hash": solver["task_hash"],
        "requested_model": MAIN_MODEL, "requested_effort": PROVIDER_EFFORT[effort], "solver_fallback": False, "replies_by_model": replies,
        "integrity_audit": {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False,
                            "writes_outside_workspace": fs["verdict"] == "out_of_workspace"},
        "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v), "hidden_behaviours": len(hidden),
        "result_receipts": receipts, "tool_calls": calls["count"],
        "raw_tokens": raw,
        "token_usage": {"input_tokens": usage["input_tokens"], "cache_read_tokens": usage["cache_read_input_tokens"],
                        "cache_creation_tokens": usage["cache_creation_input_tokens"], "output_tokens": usage["output_tokens"],
                        "thinking_tokens": thinking},
        "estimated_usd": cost, "pricing_method": PRICING_METHOD,
    }


def call_records(out):
    counts = {p.name: {s.name: sum(1 for d in s.iterdir() if d.is_dir()) for s in sorted(p.iterdir()) if s.is_dir()}
              for p in sorted((out / "calls").iterdir()) if p.is_dir()}
    retries = {p: sum(1 for d in (out / "calls" / p).glob("*/*") if len(list(d.glob("attempt-*.json"))) > 1) for p in counts}
    markers = [str(p.relative_to(out)) for p in (out / "calls").glob("*/*/*/operator-*.json")]
    recoveries = []
    for p in sorted((out / "calls").glob("*/*/*/selected.json")):
        selected = read(p)
        if "operator_recovery" in selected:
            recoveries.append((p.parents[1].parent.name, p.parents[1].name, p.parent.name, selected["operator_recovery"]))
    completed = sorted(t for t in (read(p).get("completed_at") for p in (out / "calls").glob("*/*/*/attempt-*.json")) if t)
    return counts, retries, markers, recoveries, (completed[0], completed[-1]) if completed else None


def public_settings(settings):
    return {k: v for k, v in settings.items() if k not in ("claude", "codex", "native_binary", "cursor", "muse", "zcode")}


def main():  # noqa: PLR0912, PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness-root", type=Path, default=SITE.parent / "VulcanBench")
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--judging-root", type=Path, required=True)
    parser.add_argument("--muse-root", type=Path, required=True)
    args = parser.parse_args()
    root, docs = args.harness_root.resolve(), args.results_root.resolve()
    results = docs / RESULTS
    lock = read(docs / LOCK)["tasks"]
    v327 = read(PUBLIC_V327)

    # The rounds: Sol scored in each published round, Muse read from its own round, both passing; every binding hash intact.
    rounds = {}
    for version, (dirname, efforts, comparison_name) in ROUNDS.items():
        out = args.judging_root.resolve() / dirname
        summary, protocol = read(out / "summary.json"), read(out / "protocol.json")
        manifest = {r["id"]: r for r in read(out / "private-manifest.json")}
        comparison_path = results / comparison_name
        comparison = read(comparison_path)
        n = 23 * len(efforts)
        assert summary["protocol"] == protocol["id"] == f"code-quality-maintenance-{version}"
        assert summary["ready_for_publication"] and set(summary["passing_panels"]) == set(PANELS) and summary["failed_panels"] == []
        assert summary["fallback_reviews"] == {p: 0 for p in PANELS} and summary["self_preference"] == {}
        assert summary["expected_submissions"] == summary["published_submissions"] == len(manifest) == len(summary["rows"]) == n
        assert not summary["human_calibrated"] and not summary["humans_involved"]
        assert protocol["source_comparison_sha256"] == digest(comparison_path)
        assert protocol["manifest_sha256"] == digest(out / "private-manifest.json")
        assert set(protocol["reviewers"]) == set(PANELS) and protocol["sensitivity_panels"] == {}
        sibling = protocol["scored_siblings"]["muse"]
        muse_out = (args.muse_root if version == "v3.30.2" else args.judging_root).resolve() / MUSE_ROUNDS[version]
        assert sibling["directory"] == MUSE_ROUNDS[version] and sibling["protocol_sha256"] == digest(muse_out / "protocol.json")
        muse_summary = read(muse_out / "summary.json")
        assert muse_summary["passing_panels"] == ["muse"] and muse_summary["published_submissions"] == n
        assert digest(muse_out / "private-manifest.json") == digest(out / "private-manifest.json")  # byte-copied freeze
        assert protocol["failed_panels_disclosed"]["grok"]["outcome"].startswith("failed calibration gate g14_pair_2_1 under v3.30")
        for key in ("rubric", "system", "pair_instruction", "probe_instruction", "match_instruction", "schemas", "seed", "repeats",
                    "gate_allowance", "weights", "invalid_response_retries", "control_source_hashes"):
            assert protocol[key] == v327[key], (version, key)
        for p in PANELS:
            mine, published = public_settings(protocol["reviewers"][p]), v327["scored_panel"][p]
            assert {k: v for k, v in mine.items() if k not in SEAT_NOTES} == {k: v for k, v in published.items() if k not in SEAT_NOTES}, (version, p)
        assert comparison["cells"] == protocol["population"]["cells"] == {f"{MODEL}/{e}": 23 for e in efforts}
        assert comparison["excluded"] == comparison["missing"] == protocol["population"]["excluded"] == protocol["population"]["missing"] == []
        assert comparison["levels"] == {MODEL: list(efforts)} and len(comparison["rows"]) == n
        rounds[version] = {"out": out, "muse_out": muse_out, "summary": summary, "protocol": protocol, "manifest": manifest,
                           "comparison": comparison, "comparison_path": comparison_path, "efforts": efforts}

    # Every solver summary in the sweep folder is a population row: 115, 23 per level; the limit-refused Max attempts hold none.
    sweep = root / SWEEP
    found = {}
    for p in sorted(sweep.glob("*/legacy-*/summary.json")):
        effort = p.parent.parent.name
        assert effort in EFFORTS, p
        key = (effort, read(p)["task_id"])
        assert key not in found, key
        found[key] = p.parent
    assert len(found) == 115 and Counter(e for e, _ in found) == {e: 23 for e in EFFORTS}
    assert not [p for p in sweep.glob("*/legacy-*") if p.is_dir() and not (p / "summary.json").exists()]
    refused = [p for p in (sweep / "infra-aborted/max").iterdir() if p.is_dir()]
    assert len(refused) == LIMIT_REFUSED_ATTEMPTS and not list((sweep / "infra-aborted").rglob("summary.json"))
    log = (root / SWEEP_LOG).read_text()
    assert f"({TAG})" in log and log.count("COMPLETE (23/23)") == 5 and "quota exhausted at 0/23" in log
    assert "MAX RESUME" in log and "LEVELS=max" in (root / MAX_RESUME).read_text()
    record_by_run = {r["run_id"]: r for rd in rounds.values() for r in rd["comparison"]["rows"]}
    assert {d.name for d in found.values()} == set(record_by_run)
    DEST.mkdir(parents=True, exist_ok=True)

    rows = []
    for version, rd in rounds.items():
        for entry in rd["summary"]["rows"]:
            run = rd["manifest"][entry["id"]]
            key = (run["effort"], run["task"])
            assert run["model"] == entry["model"] == MODEL and run["effort"] == entry["effort"] and run["task"] == entry["task"]
            assert not run.get("fallback") and not entry["fallback"] and run["solver_cli_version"] == CLI_VERSION
            run_dir = found[key]
            assert run_dir.name == run["run_id"] and digest(run_dir / "summary.json") == run["source_hashes"]["summary"], run["run_id"]
            solver, facts = solver_facts(run_dir, *key, lock, run["solver_receipt"])
            assert run["duration_s"] == solver["duration_s"]
            assert (run["functional"], run["quality"], run["security"]) == (solver["scores"]["functional"], solver["scores"]["quality"],
                                                                             solver["scores"]["security"])
            record = record_by_run[run["run_id"]]
            assert {k: v for k, v in record.items() if k != "source_directory"} == {k: v for k, v in run.items() if k in record and k != "source_directory"}
            panels = entry["panels"]
            assert all(panels[p]["l1"] is not None and not panels[p]["reviewer_fallback"] for p in PANELS), entry["id"]
            published = entry["published"]
            l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
            intents = [panels[p]["l2"] for p in PANELS if panels[p]["l2"] is not None]
            assert len(intents) in (0, 2), entry["id"]
            l2 = statistics.mean(intents) if intents else None
            assert published["l2_redistributed"] == (l2 is None) == (len(run["passed_families"]) == 0), entry["id"]
            assert abs(l1 - published["l1"]) < 1e-9 and (l2 is None and published["l2"] is None or abs(l2 - published["l2"]) < 1e-9)
            code_quality = code_quality_of(l1, l2)
            assert abs(code_quality - published["code_quality"]) < 1e-9, run["run_id"]
            combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
            combined_20 = composite(run, code_quality, 0.20)
            assert abs(combined_33 - published["composite_v3"]) < 1e-9 and abs(combined_20 - published["composite_v2_profile"]) < 1e-9
            single = {p: composite(run, code_quality_of(panels[p]["l1"]["score"], panels[p]["l2"]), WEIGHTS["code_quality"]) for p in PANELS}
            rows.append({
                "model": MODEL, "effort": run["effort"], "task": run["task"], "run_id": run["run_id"], "finished": True,
                "judged_under": f"code-quality-maintenance-{version}", "judged": "published", "scored_panels": list(PANELS),
                "muse_round": f"code-quality-maintenance-{'v3.30' if version == 'v3.30.2' else 'v3.30.1'}",
                "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
                "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": l2 is None, "code_quality": code_quality,
                "combined_33": combined_33, "combined_20_profile": combined_20, "combined_single_judge": single,
                "panels": {p: {"readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                               "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                               "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": False} for p in PANELS},
                "passed_quirk_families": len(run["passed_families"]),
                "duration_s": run["duration_s"], "started_at": run["started_at"], "finished_at": run["finished_at"],
                "evidence_sha256": run["evidence_sha256"], **facts,
            })
    rows.sort(key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))
    assert len(rows) == 115 and {(r["effort"], r["task"]) for r in rows} == set(found)
    assert all(r["functional"] == 1 for r in rows)
    redistributed = sum(r["intent_recovery_redistributed"] for r in rows)

    save("runs.json", {
        "runs": len(rows), "published": 115, "unpublished": 0, "timeouts": 0, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3,
        "judges": JUDGES,
        "judged_rule": "every run is published: Code quality is the equal mean of Muse Spark 1.3 (muse, judged under v3.30 for Low to "
                       "Extra-high and v3.30.1 for Max) and GPT-6.1 Sol (sol, judged under v3.30.2 and v3.30.3), who each reviewed every run",
        "single_judge_rule": "combined_single_judge recomputes the combined score with Code quality from one judge's reviewed score and "
                             "intent recovery alone; it is a sensitivity figure, not the published score",
        "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator and its 9 points move to the "
                                f"reviewed score for that submission (intent_recovery_redistributed); {redistributed} Claude Fable 5.2 runs needed it",
        "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests; hidden_behaviours_fixed counts those the run passed",
        "cost_fields": {"estimated_usd": PRICING_METHOD},
        "token_fields": {"raw_tokens": "input, cache read, cache creation and output tokens, summed over every result receipt",
                         "token_usage.thinking_tokens": "the part of output Claude Code reports as thinking, from the raw stream (the run "
                                                        "summaries do not record it)",
                         "result_receipts": "result receipts in the stream: two where a background task resumed the session after the "
                                            "model stopped, both counted"},
        "integrity_fields": {"writes_outside_workspace": "the audit saw files written outside the workspace; every one was scratch space "
                                                         "under the temporary directory, none is a benchmark data or answer-key path"},
        "model_identity": "harness-recorded: Claude Code reports the serving model on every reply, and every reply in every run is "
                          "claude-fable-5-2; the refusal fallback never answered",
        "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "combined_33", "combined_20_profile", "combined_muse_only",
                         "combined_sol_only", "functional_pct", "automated_quality_pct", "security_pct", "hidden_behaviours_fixed",
                         "hidden_behaviours", "code_quality", "reviewed_score", "intent_recovery", "intent_recovery_redistributed",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery",
                         "sol_reviewed", "sol_readability", "sol_maintainability", "sol_intent_recovery", "passed_quirk_families",
                         "duration_s", "result_receipts", "tool_calls", "raw_tokens", "output_tokens", "thinking_tokens", "estimated_usd",
                         "started_at", "finished_at", "solver_cli_version", "task_hash", "evidence_sha256"])
        for r in rows:
            u = r["token_usage"]
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"], fmt(r["combined_33"]),
                             fmt(r["combined_20_profile"]), fmt(r["combined_single_judge"]["muse"]), fmt(r["combined_single_judge"]["sol"]),
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             r["hidden_behaviours_fixed"], r["hidden_behaviours"], fmt(r["code_quality"]), fmt(r["reviewed_score"]),
                             fmt(r["intent_recovery"]), r["intent_recovery_redistributed"],
                             *[fmt(r["panels"][p][k]) for p in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], r["duration_s"], r["result_receipts"], r["tool_calls"], r["raw_tokens"],
                             u["output_tokens"], u["thinking_tokens"], fmt(r["estimated_usd"], 6), r["started_at"], r["finished_at"],
                             r["solver_cli_version"], r["task_hash"], r["evidence_sha256"]])

    with (results / "fable52-vs-frontier-efforts.csv").open(newline="") as source:
        table = {r["effort"]: r for r in csv.DictReader(source) if r["model"] == MODEL}

    def panel_mean(r, key):
        return statistics.mean(r["panels"][p][key] for p in PANELS)

    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        assert len(rs) == 23
        g = {
            "model": MODEL, "effort": effort, "n": len(rs), "runs": len(rs), "timeouts": 0, "unpublished_runs": 0,
            "judged_under": rs[0]["judged_under"],
            "combined_33": mean_se(r["combined_33"] for r in rs), "combined_20_profile": mean_se(r["combined_20_profile"] for r in rs),
            "combined_single_judge": {p: mean_se(r["combined_single_judge"][p] for r in rs) for p in PANELS},
            "code_quality": mean_se(r["code_quality"] for r in rs), "reviewed_score": mean_se(r["reviewed_score"] for r in rs),
            "intent_recovery": mean_se(r["intent_recovery"] for r in rs if r["intent_recovery"] is not None),
            "intent_recovery_redistributed_runs": sum(r["intent_recovery_redistributed"] for r in rs),
            "readability": mean_se(panel_mean(r, "readability") for r in rs),
            "maintainability": mean_se(panel_mean(r, "maintainability") for r in rs),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in rs) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in rs), "automated_quality": mean_se(100 * r["automated_quality"] for r in rs),
            "security": mean_se(100 * r["security"] for r in rs),
            "passed": sum(r["functional"] == 1 for r in rs), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
            "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_median": statistics.median(r["duration_s"] / 60 for r in rs),
            "priced_runs": len(rs), "cli_versions": {CLI_VERSION: len(rs)}, "solver_fallback_runs": 0,
            "two_receipt_runs": sum(r["result_receipts"] == 2 for r in rs),
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "output_tokens": mean_se(r["token_usage"]["output_tokens"] for r in rs),
            "thinking_tokens": mean_se(r["token_usage"]["thinking_tokens"] for r in rs),
            "tool_calls": mean_se(r["tool_calls"] for r in rs),
            "usd": mean_se(r["estimated_usd"] for r in rs), "usd_total": sum(r["estimated_usd"] for r in rs),
        }
        version = next(v for v, rd in rounds.items() if effort in rd["efforts"])
        entry = rounds[version]["summary"]["groups"][f"{MODEL}/{effort}"]
        assert g["n"] == entry["n"] == entry["composite_v3"]["n"] == 23 and g["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
        for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
            assert g[field]["n"] == entry[key]["n"], (effort, field)
            assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9 and abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
        for p in PANELS:
            assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9 and abs(g["by_panel"][p]["se"] - entry["by_panel"][p]["se"]) < 1e-9
        t = table[effort]
        assert (int(t["n"]), int(t["judged"]), int(t["passed"]), t["fallback_runs"], t["judges"]) == (23, 23, 23, "0", "muse+sol"), effort
        for column, value in (("combined", g["combined_33"]["mean"]), ("combined_se", g["combined_33"]["se"]),
                              ("code_quality", g["code_quality"]["mean"]), ("minutes", g["minutes"]["mean"]),
                              ("usd_per_task", g["usd"]["mean"])):
            assert abs(float(t[column]) - value) <= 5e-5, (effort, column)
        groups.append(g)
    FINAL_CHECKS(groups)
    save("groups.json", groups)

    with SCORES.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "combined_33", "combined_33_se", "combined_20_profile", "combined_muse_only",
                         "combined_sol_only", "code_quality", "code_quality_se", "reviewed_score", "intent_recovery",
                         "intent_recovery_redistributed_runs", "readability", "maintainability", "muse_reviewed", "sol_reviewed", "functional",
                         "automated_quality", "security", "passed_of_23", "hidden_behaviours_fixed", "hidden_behaviours", "mean_minutes",
                         "mean_minutes_se", "median_minutes", "mean_raw_tokens", "mean_output_tokens", "mean_thinking_tokens", "mean_usd",
                         "total_usd", "cli_version"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"], f'{g["combined_33"]["mean"]:.4f}', f'{g["combined_33"]["se"]:.4f}',
                             f'{g["combined_20_profile"]["mean"]:.4f}', f'{g["combined_single_judge"]["muse"]["mean"]:.4f}',
                             f'{g["combined_single_judge"]["sol"]["mean"]:.4f}', f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}',
                             f'{g["reviewed_score"]["mean"]:.4f}', f'{g["intent_recovery"]["mean"]:.4f}', g["intent_recovery_redistributed_runs"],
                             f'{g["readability"]["mean"]:.4f}', f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}',
                             f'{g["by_panel"]["sol"]["mean"]:.4f}', f'{g["functional"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}',
                             f'{g["security"]["mean"]:.4f}', g["passed_all_runs"], g["hidden_behaviours_fixed"], g["hidden_behaviours"],
                             f'{g["minutes"]["mean"]:.4f}', f'{g["minutes"]["se"]:.4f}', f'{g["minutes_median"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}',
                             f'{g["output_tokens"]["mean"]:.1f}', f'{g["thinking_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}',
                             f'{g["usd_total"]:.6f}', CLI_VERSION])

    totals = {MODEL: {"runs": len(rows), "usd": sum(r["estimated_usd"] for r in rows), "raw_tokens": sum(r["raw_tokens"] for r in rows),
                      "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    assert round(totals[MODEL]["usd"], 2) == 509.85 and round(totals[MODEL]["solver_hours"], 1) == 26.1
    save("economics.json", {
        "scope": "Solver inference only. The model ran on a Claude Max subscription through Claude Code, so these are list-price "
                 "estimates, not bills: Claude Code's own list-price total for each session, the basis of every Claude column on the "
                 "board. Judging is excluded. Every run in the sweep is priced.",
        "pricing_method": PRICING_METHOD,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"], "output_tokens": g["output_tokens"],
                    "thinking_tokens": g["thinking_tokens"], "minutes": g["minutes"], "solver_fallback_runs": 0} for g in groups],
        "totals": totals,
        "limitations": [
            "Claude Code computes the total at its own list rates from the session's usage and reports it cumulatively on each result "
            "receipt; the export takes the session's last total (two runs have two receipts) and matched every run to the population record.",
            "The adapter's own run-time estimate prices cached prompt tokens at the full input rate and reads higher (Max $14.01 a task "
            "against $10.88); it is not used.",
            "The estimate covers the solver's exposed receipts, not an independently observed invoice.",
        ],
        "note": "Per-run estimates are in runs.json (estimated_usd, raw_tokens, token_usage). Judging is excluded.",
    })

    calibration = {}
    for panel, path, taken in (("muse", args.muse_root.resolve() / MUSE_ROUNDS["v3.30.2"] / "calibration-muse.json", "code-quality-maintenance-v3.30"),
                               ("sol", rounds["v3.30.2"]["out"] / "calibration-sol.json", "code-quality-maintenance-v3.30.2")):
        result = read(path)
        assert result["passed"] and result["failing_gates"] == [] and not result["allowance_used"] and result["call_count"] == 80
        assert len(result["gates"]) == 20 and all(g["passed"] for g in result["gates"].values())
        calibration[panel] = {"judge": JUDGES[panel], "taken_under": taken,
                              **{k: result[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used",
                                                        "gates", "control_means")}}
    grok = read(args.muse_root.resolve() / MUSE_ROUNDS["v3.30.2"] / "calibration-grok.json")
    assert not grok["passed"] and grok["failing_gates"] == ["g14_pair_2_1"] and not grok["allowance_used"] and grok["call_count"] == 80
    calibration["grok_failed"] = {"judge": "Grok 4.6", "taken_under": "code-quality-maintenance-v3.30", "passed": False,
                                  "failing_gates": grok["failing_gates"], "call_count": grok["call_count"],
                                  "gate_g14_pair_2_1": grok["gates"]["g14_pair_2_1"],
                                  "outcome": "failed one gate with no allowance available for it; judged no submission; GPT-6.1 Sol took the seat"}
    for version, rd in rounds.items():
        assert rd["protocol"]["calibration"].startswith("automated held-out controls" if version == "v3.30.2" else "no new exam")
    save("calibration.json", calibration)

    records = {}
    for version, rd in rounds.items():
        counts, retries, markers, recoveries, window = call_records(rd["out"])
        assert markers == [] and list(counts) == ["sol"]
        assert [(p, s) for p, s, _, _ in recoveries] == [("sol", "match")] * INDEX_RECOVERIES[version], recoveries
        assert all(rec["method"] == INDEX_METHOD for *_, rec in recoveries)
        muse_counts, muse_retries, muse_markers, muse_recoveries, muse_window = call_records(rd["muse_out"])
        assert muse_markers == []
        expected_muse = 1 if version == "v3.30.2" else 0
        assert [(p, s) for p, s, _, _ in muse_recoveries] == [("muse", MUSE_REWRAP[0])] * expected_muse
        assert all(rec["method"] == MUSE_REWRAP[1] for *_, rec in muse_recoveries)
        records[version] = {"sol_counted_calls": counts["sol"], "sol_second_attempts": retries["sol"],
                            "muse_round": MUSE_ROUNDS[version].replace("runs-", ""), "muse_counted_calls": muse_counts["muse"],
                            "muse_second_attempts": muse_retries["muse"],
                            "sol_window_utc": window, "muse_window_utc": muse_window,
                            "operator_recoveries": [{"panel": p, "stage": s, "submission": i, "rule": "recover_one_based_indexes",
                                                     "method": rec["method"], "score_effect": "none: intent scoring reads match statuses only"}
                                                    for p, s, i, rec in recoveries]
                            + [{"panel": p, "stage": s, "submission": i, "rule": "excerpt line re-wrap", "method": rec["method"],
                                "score_effect": "none: the excerpt must then be verbatim in the code and the attempt pass the frozen validator"}
                               for p, s, i, rec in muse_recoveries]}
    assert sum(len(r["operator_recoveries"]) for r in records.values()) == 13
    p2 = rounds["v3.30.2"]["protocol"]
    save("judge-protocols.json", {
        "scored_panel": {p: public_settings(p2["reviewers"][p]) for p in PANELS},
        "judge_names": JUDGES,
        "protocols": {v: {"id": rd["protocol"]["id"], "sha256": digest(rd["out"] / "protocol.json"), "efforts": list(rd["efforts"]),
                          "muse_sibling": rd["protocol"]["scored_siblings"]["muse"]["directory"].replace("runs-", ""),
                          "muse_sibling_sha256": rd["protocol"]["scored_siblings"]["muse"]["protocol_sha256"],
                          "comparability": rd["protocol"]["comparability"], "calibration": rd["protocol"]["calibration"]}
                      for v, rd in rounds.items()},
        "seat": "v3.30 seated Muse Spark 1.3 and Grok 4.6, the panel of the Claude Opus 5.5 column. Grok failed calibration gate "
                "g14_pair_2_1 and judged nothing. On the owner's choice GPT-6.1 Sol took the seat, passed every gate under v3.30.2, and "
                "judged every run; Muse Spark 1.3's reviews come from its own rounds on byte-copied freezes of the same populations.",
        "same_as_v327": "rubric, system text, pair, probe and match instructions, schemas, seed, repeats, gate allowance, weights, retry "
                        "rule, control hashes, and both judges' model, effort and binary pins equal the published v3.27 record (Muse Spark "
                        "1.3 and GPT-6.1 Sol, the DeepSeek V4.1 Flash round); only the neutrality and seat notes differ",
        "failed_panel": p2["failed_panels_disclosed"],
        "system": p2["system"], "rubric": p2["rubric"], "pair_instruction": p2["pair_instruction"],
        "probe_instruction": p2["probe_instruction"], "match_instruction": p2["match_instruction"], "schemas": p2["schemas"],
        "weights": p2["weights"], "gate_allowance": p2["gate_allowance"], "repeats": p2["repeats"], "seed": p2["seed"],
        "single_panel_rule": p2["single_panel_rule"], "invalid_response_retries": p2["invalid_response_retries"],
        "control_source_hashes": p2["control_source_hashes"],
        "population": {v: {k: rd["protocol"]["population"][k] for k in ("description", "cells", "excluded", "missing")} for v, rd in rounds.items()},
        "planned_calls": {v: rd["protocol"]["planned_calls"] for v, rd in rounds.items()},
        "judge_pins": {"sol": {"cli": "Codex", "version": p2["judge_pins"]["codex"]["version"],
                               "launcher_sha256": p2["judge_pins"]["codex"]["launcher"]["sha256"],
                               "native_sha256": p2["judge_pins"]["codex"]["native"]["sha256"], "rule": p2["judge_pins"]["codex"]["rule"]},
                       "muse": {"cli": "Muse CLI", "sha256": p2["reviewers"]["muse"]["binary_sha256"]}},
        "calls": records,
    })

    # The cards are copied byte for byte from the harness; the card record names the published rounds.
    for name, target in CARDS.items():
        assert target.read_bytes() == (results / name).read_bytes(), name
    card = read(results / "fable52-vs-frontier.json")
    assert card["final"] and card["png_sha256"] == digest(results / "fable52-vs-frontier.png") and card["best"][MODEL] == "max"
    for version, rd in rounds.items():
        assert card["sources"][f"{version}_summary_sha256"] == digest(rd["out"] / "summary.json")
    (DEST / "card-table.csv").write_bytes((results / "fable52-vs-frontier-efforts.csv").read_bytes())
    (DEST / "muse-like-for-like.csv").write_bytes((results / "muse-like-for-like.csv").read_bytes())
    memo = read(results / "memorization-check.json")
    assert memo["inspecting"][NAMES[MODEL]]["inspected_first"] == memo["inspecting"][NAMES[MODEL]]["runs"] == 115

    save("provenance.json", {
        "source_artifacts_sha256": {
            **{f"{v}/{f}": digest(rd["out"] / f) for v, rd in rounds.items() for f in ("summary.json", "protocol.json", "private-manifest.json")},
            "v3.30.2/calibration-sol.json": digest(rounds["v3.30.2"]["out"] / "calibration-sol.json"),
            **{f"{MUSE_ROUNDS[v].replace('runs-code-quality-maintenance-', '')}/{f}": digest(rd["muse_out"] / f)
               for v, rd in rounds.items() for f in ("summary.json", "protocol.json")},
            "v3.30/calibration-muse.json": digest(args.muse_root.resolve() / MUSE_ROUNDS["v3.30.2"] / "calibration-muse.json"),
            "v3.30/calibration-grok.json": digest(args.muse_root.resolve() / MUSE_ROUNDS["v3.30.2"] / "calibration-grok.json"),
            **{name: digest(results / name) for name in ("comparison.json", "comparison-max.json", "fable52-vs-frontier-efforts.csv",
                                                         "fable52-vs-frontier.json", "fable52-vs-frontier.png", "muse-like-for-like.csv",
                                                         "memorization-check.json", "fable52-no-memorization.png", "README.md")},
            "suite.lock.json": digest(docs / LOCK),
        },
        "memorization_check": {"file": "memorization-check.json", "sha256": digest(results / "memorization-check.json"),
                               "copied_reference_lines_pct": round(memo["copying"][NAMES[MODEL]]["lines_pct"], 1),
                               "other_models_copied_lines_pct": [round(min(v["lines_pct"] for k, v in memo["copying"].items() if k != NAMES[MODEL]), 1),
                                                                 round(max(v["lines_pct"] for k, v in memo["copying"].items() if k != NAMES[MODEL]), 1)],
                               "inspected_binary_before_first_edit": f'{memo["inspecting"][NAMES[MODEL]]["inspected_first"]} of '
                                                                     f'{memo["inspecting"][NAMES[MODEL]]["runs"]}',
                               "recall_answers_saying_not_remembered": f'{memo["recall"]["recall_answers_saying_not_remembered"]} of '
                                                                       f'{len(memo["recall"]["recall_tasks"])}'},
        "export_checks": ["115 solver summaries in the sweep folder, 23 per level, no task twice and no orphan attempt folder; the 69 Max "
                          "attempts the Fable usage limit refused hold no summary and are kept apart; the sweep log shows each level "
                          "complete and the Max resume after the limit reset",
                          "every run is claude-code:claude-fable-5-2 at its requested level on Claude Code 2.1.321 in auto permission mode "
                          "with safe mode, from bench/2026-11-09-fable52-frontier-v4 with a clean source block and every task hash equal to "
                          "the frozen suite lock; every reply in every stream was served by claude-fable-5-2",
                          "every integrity audit: no web, no benchmark data or answer-key paths, not contaminated",
                          "each run's tokens and thinking tokens summed over every result receipt in the archived stream (whose hash "
                          "matches), and its session list-price total, equal the population record; exactly two runs have two receipts",
                          "the population records' hashes and the manifests' hashes equal those frozen in v3.30.2 and v3.30.3, Muse's "
                          "manifests are byte-identical, and every run's summary hash equals its manifest entry",
                          "rubric, prompts, schemas, seed, repeats, gate allowance, weights, retry rule, control hashes and both judges' "
                          "pins equal the published v3.27 record",
                          "Muse Spark 1.3 (v3.30) and GPT-6.1 Sol (v3.30.2) passed every calibration gate with no allowance; Grok 4.6 "
                          "failed g14_pair_2_1 under v3.30 and judged nothing; no reviewer fallback; no operator marker; twelve Sol "
                          "answer-key matches recovered under recover_one_based_indexes and one Muse probe excerpt re-wrapped",
                          "per-row Code quality, both combined scores and each judge's single-judge score recomputed and matched to the "
                          "frozen summaries; each level's means and standard errors, per-judge means included, matched to the summaries' groups",
                          "combined score, its standard error, Code quality, tasks passed, minutes and cost per level matched to the harness "
                          "card table; the cards are byte-identical to the harness copies and the card record names both published summaries",
                          "no dashes, NUL characters or host paths in exported text"],
        "limits": ["Claude Fable 5.2 is judged by Muse Spark 1.3 and GPT-6.1 Sol. The Claude Fable 5.1 and Claude Opus 5.5 board rows "
                   "keep their published Muse Spark 1.3 and Grok 4.6 scores; the comparison card shows them under a matched Muse and Sol "
                   "panel from comparison-only rounds v3.30.4 and v3.30.5, and GPT-6 Astra with its published Muse and Grok scores, "
                   "because Sol shares its lab. Scores from different panels are not calibrated against each other.",
                   "GPT-6.1 Sol reviews Fable 5.2 about 7 points higher than Muse Spark 1.3 does at every level; the published score is "
                   "their mean and combined_single_judge gives each judge alone.",
                   "Grok 4.6 failed its v3.30 calibration exam (gate g14_pair_2_1), so the usual Muse and Grok panel could not judge.",
                   "Runs used --thinking-display summarized so traces keep thinking summaries, a run condition earlier Claude columns did "
                   "not have; the summaries are withheld because they describe the reference programs.",
                   "The Fable usage limit refused the first Max attempts; they did no work and are not part of the population. Max ran "
                   "from November 10 at 23:14 to November 11 at 13:28 PST after the limit reset.",
                   "Two run summaries count only the last of two result receipts and no summary records thinking tokens (adapter "
                   "issues); every figure here is summed from the raw streams, and grading is unaffected.",
                   "Thirteen judge answers went through frozen recovery rules (twelve Sol index shifts, one Muse excerpt re-wrap); none "
                   "changes a score.",
                   "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.",
                   "One attempt per task and level, on the owner's Mac, local sandbox, flat 3-hour task bound, one task at a time."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, raw and thinking tokens, tool-call counts and list-price cost.",
        "withheld": ["raw prompts and responses", "thinking summaries", "submitted patches and reconstructed sources",
                     "quirk answer keys (they describe hidden-test behaviour)", "reviewer session identifiers and usage receipts",
                     "solver event streams (a structure-only redacted trace of every run is public in the vulcanbench-fable52-traces "
                     "repository)", "host binary paths"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


# The published figures as the report prints them: combined, its standard error, Code quality, minutes and cost per task.
PUBLISHED = {"low": (91.92, 0.39, 80.63, 4.6, 1.72), "medium": (92.25, 0.44, 81.49, 4.3, 1.72), "high": (92.76, 0.43, 82.95, 7.8, 2.86),
             "extra-high": (93.25, 0.45, 84.25, 14.2, 4.99), "max": (93.85, 0.42, 86.02, 37.1, 10.88)}


def FINAL_CHECKS(groups):  # noqa: N802
    assert [g["effort"] for g in groups] == list(EFFORTS)
    for g in groups:
        combined, se, code_quality, minutes, usd = PUBLISHED[g["effort"]]
        assert (round(g["combined_33"]["mean"], 2), round(g["combined_33"]["se"], 2), round(g["code_quality"]["mean"], 2),
                round(g["minutes"]["mean"], 1), round(g["usd"]["mean"], 2)) == (combined, se, code_quality, minutes, usd), g["effort"]
        assert g["passed_all_runs"] == 23 and g["solver_fallback_runs"] == 0
    assert sum(g["two_receipt_runs"] for g in groups) == 2


if __name__ == "__main__":
    main()
