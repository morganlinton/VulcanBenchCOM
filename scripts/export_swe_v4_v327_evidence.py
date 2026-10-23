"""Export the public record of the DeepSeek V4.1 Flash effort sweep on Frontier v4, judged under v3.27.

Adapted from the v3.26 Muse Wonder Full export, with the same publication
scope: per-run scores, per-panel sub-scores, aggregates, judge protocol text,
calibration verdicts, raw tokens and cost. Raw prompts, patches, quirk answer
keys and host paths are withheld. Run from the site root:

    python3 scripts/export_swe_v4_v327_evidence.py --harness-root ../VulcanBench

--harness-root holds the frozen run directory (runs-effort-deepseek-flash-dsh),
the judging round (runs-code-quality-maintenance-v3.27), the population record,
pricing check and cards in docs/results/swe-v4-deepseek-flash-2026-10, the
comparator table and the sweep launcher.

What differs from the Muse Wonder Full export, all forced by the sweep or its judging:

- One judging round, the v3.20 panel. Grok 4.6, the usual second judge, runs
  through Cursor, whose account was out of usage on 2026-10-23, so the owner
  seated GPT-6.1 Sol (medium, Codex CLI 0.159.0) beside Muse Spark 1.3, the
  pair v3.20 used for Grok 4.7. Both took the exam under v3.27. Muse runs a
  byte-identical backup of the v3.4 binary, matched by sha256.
- Three levels. DeepSeek's API takes low, high and max reasoning; it has no
  medium and nothing maps to extra-high.
- No timeouts, no exclusions. All 69 runs finished inside the 3-hour bound and
  every one is published. The two runs a pause interrupted hold no summary and
  are not part of the population.
- Metered API spend, two cost figures. The runs billed an API key. list_usd
  prices every run's tokens at DeepSeek's off-peak list rate (the price table's
  rate, the board's figure); billed_usd is the adapter's per-call meter, which
  doubles calls made in DeepSeek's weekday peak hours. dsh's session-title call
  records no usage and is counted, not priced.
- Every number the harness card data shows is matched: combined score and its
  standard error, Code quality, each judge's reviewed score, tasks passed,
  functional score, minutes, list and billed cost per level.
"""

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DEST = SITE / "assets/data/swe-v4-deepseek-flash-v327"
SCORES = SITE / "assets/data/swe-v4-deepseek-flash-v327-scores.csv"
CARDS = {"1-summary.png": SITE / "assets/cards/swe-v4-deepseek-flash-v327.png",
         "2-combined-score.png": SITE / "assets/cards/swe-v4-deepseek-flash-v327-combined.png"}
EFFORTS = ("low", "high", "max")
MODEL = "dsflash"
NAMES = {MODEL: "DeepSeek V4.1 Flash"}
SOLVER = "dsh:deepseek-flash"
API_MODEL = "deepseek-flash"
SERVED_ALIAS = "DeepSeek-V4.1-Flash-1017"
PANELS = ("muse", "sol")
JUDGES = {"muse": "Muse Spark 1.3", "sol": "GPT-6.1 Sol"}
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
PROTOCOL_ID = "code-quality-maintenance-v3.27"
ROUND = "runs-code-quality-maintenance-v3.27"
RESULTS = "docs/results/swe-v4-deepseek-flash-2026-10"
COMPARATORS = "docs/results/swe-v4-gpt6-vs-gpt56-2026-09/gpt61sol-opus55-astra-efforts.csv"
LOCK = "tasks/coding-intelligence-index-v4/suite.lock.json"
SWEEP = "runs-effort-deepseek-flash-dsh"
LAUNCHER = "logs/deepseek-flash-dsh.launch.sh"
OVERLAP_LOG = "logs/deepseek-flash-dsh-overlap.log"  # the launcher's per-minute logger writes it only when another job runs
TAG, COMMIT = "bench/2026-10-20-deepseek-dsh-frontier-v4", "0a889ba11b2eb41353d55437906b946984b2c1dc"
DSH_VERSION = "0.2.1-rc.2"
CLI_LABEL = "DeepSeek Harness 0.2.1-rc.2"
INSTALL_TREE_SHA256 = "06663f5c634aafdabb59c921623595eba8c981a1baa8faeb681937b5228a2133"
# DeepSeek's pricing page, checked 2026-10-19 (harness pricing-check.json). USD per million, off-peak; weekday peak hours bill 2x.
RATES = {"input": 0.15, "cached_input": 0.003, "output": 0.60}
PEAK = "2x, 01:00 to 04:00 and 06:00 to 10:00 UTC, Monday to Friday"
PRICING_METHOD = ("list_usd: tokens at DeepSeek's off-peak list price for deepseek-flash ($0.15 input cache miss, $0.003 cache hit, "
                  "$0.60 output per million); billed_usd: the adapter's per-call meter, which applies DeepSeek's 2x weekday peak-hour rate "
                  "to calls made 01:00 to 04:00 and 06:00 to 10:00 UTC; dsh's session-title call records no usage and is not priced")
PAUSED = {"low-legacy-metercore-binary-parity-6f148f5d", "low-legacy-reflowcore-binary-parity-0f5af103"}
SECOND_RESUME = "2026-10-22T08:10:56+00:00"  # the sweep resumed after the second pause, on macOS 27.0.1
RECOVERY_METHOD = "one-based departure indexes moved to zero-based; statuses untouched"
INDEX_RECOVERIES = ("submission-021", "submission-032", "submission-042", "submission-045", "submission-068", "submission-069")
FORBIDDEN = (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/")
PUBLIC_V320 = SITE / "assets/data/swe-v4-grok47-cursor-v320/judge-protocols.json"


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


def list_price(tokens):
    cached = tokens["cached_input"]
    return ((tokens["prompt"] - cached) * RATES["input"] + cached * RATES["cached_input"] + tokens["completion"] * RATES["output"]) / 1e6


def trace_records(run_dir):
    """The run's one dsh_usage receipt and its one cli_agent_start record."""
    found = {}
    for line in (run_dir / "trace.jsonl").read_text().splitlines():
        if '"dsh_usage"' in line or '"cli_agent_start"' in line:
            event = json.loads(line)
            if event.get("type") in ("dsh_usage", "cli_agent_start"):
                assert event["type"] not in found, run_dir.name
                found[event["type"]] = event["data"]
    assert set(found) == {"dsh_usage", "cli_agent_start"}, run_dir.name
    return found["dsh_usage"], found["cli_agent_start"]


def solver_facts(run_dir, effort, lock):
    """Checks every run must pass, and the facts each row carries from the solver side."""
    solver = read(run_dir / "summary.json")
    assert solver["model"] == SOLVER and solver["effort"]["requested"] == effort and solver["effort"]["provider_value"] == effort
    agent = solver["cli_agent"]
    assert agent["harness"] == "dsh" and agent["harness_version"] == DSH_VERSION and agent["billing"] == "api", run_dir.name
    assert agent["requested_model"] == agent["reported_model"] == API_MODEL and agent["model_identity_confidence"] == "harness-recorded"
    assert "web tools off" in agent["execution_boundary"] and "session-log and telemetry upload off" in agent["execution_boundary"]
    source = solver["source"]
    assert source["harness"]["describe"] == TAG and source["harness"]["commit"] == COMMIT, run_dir.name
    assert not source["harness"]["dirty"] and not source["dirty"] and not source["allow_dirty"], run_dir.name
    assert solver["task_hash"] == lock[solver["task_id"]], run_dir.name
    audit = solver["integrity_audit"]
    assert audit["web"]["verdict"] == "no_web" and not audit["contaminated"] and not audit["web"]["contaminated"], run_dir.name
    fs = audit["filesystem"]
    assert fs["benchmark_data_paths"] == [] and fs["answer_key_paths"] == [] and not fs["contaminated"], run_dir.name
    assert solver["finished"] and solver["duration_s"] < 10800 and not solver["scores"].get("budget_exceeded"), run_dir.name
    usage, start = trace_records(run_dir)
    assert start["harness_version"] == DSH_VERSION and start["install_tree_sha256"] == INSTALL_TREE_SHA256, run_dir.name
    assert start["requested_model"] == start["api_model"] == API_MODEL and start["requested_effort"] == effort and start["billing"] == "api"
    tokens = solver["tokens"]
    assert tokens["prompt"] == usage["input"] + usage["cacheRead"] + usage["cacheWrite"] and usage["cacheWrite"] == 0, run_dir.name
    assert (tokens["completion"], tokens["cached_input"], tokens["reasoning_output"]) == (usage["output"], usage["cacheRead"], usage["reasoning"])
    assert solver["total_tokens"] == tokens["prompt"] + tokens["completion"] == tokens["total"]
    assert usage["calls"] > 0 and usage["retried_attempts"] == 0 and usage["unmetered_title_calls"] in (0, 1), run_dir.name
    economics = solver["economics"]
    assert economics["billing_mode"] == "api-metered", run_dir.name
    # The summary stores the list price rounded to six places in three fields (published as list_usd, as the card uses it);
    # recomputing it from the tokens agrees to that rounding. The billed meter equals the trace receipt.
    assert solver["cost_usd"] == economics["marginal_cash_usd"] == economics["api_equivalent_cost_usd"], run_dir.name
    list_usd = economics["marginal_cash_usd"]
    assert abs(list_price(tokens) - list_usd) <= 5e-7, run_dir.name
    assert agent["cli_reported_cost_usd"] == usage["metered_usd"], run_dir.name
    assert (usage["peak_calls"] == 0) == (abs(usage["metered_usd"] - economics["marginal_cash_usd"]) < 1e-5), run_dir.name
    hidden = solver["verifier"]["fail_to_pass"]
    return solver, {
        "solver_cli_version": CLI_LABEL, "install_tree_sha256": INSTALL_TREE_SHA256, "source_tag": TAG, "task_hash": solver["task_hash"],
        "requested_model": API_MODEL, "model_identity": "harness-recorded",
        "integrity_audit": {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False},
        "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v), "hidden_behaviours": len(hidden),
        "model_calls": usage["calls"], "unmetered_title_calls": usage["unmetered_title_calls"],
        "attempts_without_usage": usage["attempts_without_usage"], "peak_calls": usage["peak_calls"],
        "raw_tokens": solver["total_tokens"],
        "token_usage": {"input_tokens": tokens["prompt"], "cached_input_tokens": tokens["cached_input"],
                        "uncached_input_tokens": tokens["prompt"] - tokens["cached_input"], "output_tokens": tokens["completion"]},
        "list_usd": list_usd, "billed_usd": usage["metered_usd"], "pricing_method": PRICING_METHOD,
    }


def call_records(out):
    """Counted calls per stage, calls with a second attempt, operator markers and recoveries under calls/."""
    counts = {p.name: {s.name: sum(1 for d in s.iterdir() if d.is_dir()) for s in sorted(p.iterdir()) if s.is_dir()}
              for p in sorted((out / "calls").iterdir()) if p.is_dir()}
    retries = {p: sum(1 for d in (out / "calls" / p).glob("*/*") if len(list(d.glob("attempt-*.json"))) > 1) for p in counts}
    markers = [str(p.relative_to(out)) for p in (out / "calls").glob("*/*/*/operator-*.json")]
    reviews = [str(p.relative_to(out)) for p in (out / "calls").glob("*/*/*/attempt-*.json") if "operator_review" in read(p)]
    recoveries = []
    for p in sorted((out / "calls").glob("*/*/*/selected.json")):
        selected = read(p)
        if "operator_recovery" in selected:
            recoveries.append((p.parents[1].parent.name, p.parents[1].name, p.parent.name, selected["operator_recovery"]))
    completed = sorted(t for t in (read(p).get("completed_at") for p in (out / "calls").glob("*/*/*/attempt-*.json")) if t)
    return counts, retries, markers, reviews, recoveries, (completed[0], completed[-1])


def public_settings(settings):
    return {k: v for k, v in settings.items() if k not in ("claude", "codex", "native_binary", "cursor", "muse", "zcode")}


def main():  # noqa: PLR0912, PLR0915, one linear export
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--harness-root", type=Path, default=SITE.parent / "VulcanBench")
    args = parser.parse_args()
    root = args.harness_root.resolve()
    lock = read(root / LOCK)["tasks"]
    results = root / RESULTS
    out = root / ROUND
    summary, protocol = read(out / "summary.json"), read(out / "protocol.json")
    manifest = {r["id"]: r for r in read(out / "private-manifest.json")}
    comparison_path = results / "comparison.json"
    comparison = read(comparison_path)

    # The round: one protocol, both judges passing, every submission published, every binding hash intact.
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["ready_for_publication"] and summary["passing_panels"] == list(PANELS) and summary["failed_panels"] == []
    assert summary["fallback_reviews"] == {p: 0 for p in PANELS} and summary["self_preference"] == {}
    assert summary["expected_submissions"] == summary["published_submissions"] == len(manifest) == len(summary["rows"]) == 69
    assert not summary["human_calibrated"] and not summary["humans_involved"]
    assert protocol["source_comparison_sha256"] == digest(comparison_path)
    assert protocol["manifest_sha256"] == digest(out / "private-manifest.json")
    assert protocol["scored_siblings"] == {} and protocol["sensitivity_panels"] == {}
    assert set(protocol["reviewers"]) == set(PANELS)
    muse, sol = protocol["reviewers"]["muse"], protocol["reviewers"]["sol"]
    assert (muse["model"], muse["effort"], muse["lab"]) == ("muse-spark-1.3", "medium", "Meta")
    assert (sol["model"], sol["effort"], sol["codex_version"], sol["lab"]) == ("gpt-6.1-sol", "medium", "0.159.0", "OpenAI")
    assert "byte-identical backup of the v3.4 binary" in muse["binary_location"]
    pins = protocol["judge_pins"]
    assert pins["codex"]["launcher"]["sha256"] == sol["binary_sha256"] and pins["codex"]["native"]["sha256"] == sol["native_binary_sha256"]
    assert protocol["binaries"][muse["muse"]]["sha256"] == muse["binary_sha256"]
    # The rubric, prompts, schemas, seed, repeats, allowance, weights, retry rule and controls equal v3.20's as published, and so
    # do both judges' model, effort and binary pins: the same panel Grok 4.7 was judged by.
    v320 = json.loads(PUBLIC_V320.read_text())
    for key in ("rubric", "system", "pair_instruction", "probe_instruction", "match_instruction", "schemas", "seed", "repeats",
                "gate_allowance", "weights", "invalid_response_retries", "control_source_hashes"):
        assert protocol[key] == v320[key], key
    for key in ("model", "effort", "binary_sha256", "timeout", "tier", "prompt_delivery", "system_prompt", "sandbox", "identity"):
        assert muse[key] == v320["scored_panel"]["muse"][key], key
    for key in ("model", "effort", "codex_version", "binary_sha256", "timeout", "prompt_delivery", "system_prompt", "identity"):
        assert sol[key] == v320["scored_panel"]["sol"][key], key
    assert comparison["cells"] == protocol["population"]["cells"] == {f"{MODEL}/{e}": 23 for e in EFFORTS}
    assert comparison["excluded"] == comparison["missing"] == protocol["population"]["excluded"] == protocol["population"]["missing"] == []
    assert comparison["levels"] == {MODEL: list(EFFORTS)} and len(comparison["rows"]) == 69
    record_by_run = {r["run_id"]: r for r in comparison["rows"]}

    # Every finished solver summary in the sweep: 69 runs, 23 per level, no task twice; the paused attempts hold no summary.
    sweep = root / SWEEP
    found = {}
    for p in sorted(sweep.glob("*/legacy-*/summary.json")):
        effort = p.parent.parent.name
        assert effort in EFFORTS, p
        key = (effort, read(p)["task_id"])
        assert key not in found, key
        found[key] = p.parent
    assert all((d / "summary.json").exists() for d in sweep.glob("*/legacy-*"))
    assert len(found) == 69 and Counter(e for e, _ in found) == {e: 23 for e in EFFORTS}
    assert {p.name for p in (sweep / "paused-interrupted").iterdir()} == PAUSED
    assert not list((sweep / "paused-interrupted").glob("*/summary.json"))  # an interrupted attempt is never scored
    launcher = (root / LAUNCHER).read_text()
    assert "overlap_procs=" in launcher and OVERLAP_LOG in launcher.replace("$VB/", "") and INSTALL_TREE_SHA256 in launcher
    assert not (root / OVERLAP_LOG).exists()  # the per-minute logger never saw another benchmark job beside the sweep
    DEST.mkdir(parents=True, exist_ok=True)

    facts_by_key = {}
    behaviours = {}
    for key, run_dir in found.items():
        solver, facts = solver_facts(run_dir, key[0], lock)
        facts_by_key[key] = (solver, facts, run_dir)
        assert behaviours.setdefault(key[1], facts["hidden_behaviours"]) == facts["hidden_behaviours"], key

    rows = []
    for entry in summary["rows"]:
        run = manifest[entry["id"]]
        key = (run["effort"], run["task"])
        assert run["model"] == entry["model"] == MODEL and run["effort"] == entry["effort"] and run["task"] == entry["task"]
        assert not run.get("fallback") and not entry["fallback"]
        solver, facts, run_dir = facts_by_key[key]
        assert run_dir.name == run["run_id"] and digest(run_dir / "summary.json") == run["source_hashes"]["summary"], run["run_id"]
        assert run["solver_cli_version"] == DSH_VERSION and run["duration_s"] == solver["duration_s"]
        assert (run["functional"], run["quality"], run["security"]) == (solver["scores"]["functional"], solver["scores"]["quality"], solver["scores"]["security"])
        assert run["api_equivalent_cost_usd"] == solver["economics"]["marginal_cash_usd"] and run["billed_cost_usd"] == facts["billed_usd"]
        assert run["solver_receipt"]["raw_tokens"] == facts["raw_tokens"]
        record = record_by_run[run["run_id"]]
        assert {k: v for k, v in record.items() if k != "source_directory"} == {k: v for k, v in run.items() if k in record and k != "source_directory"}
        panels = entry["panels"]
        assert all(panels[p]["l1"] is not None and panels[p]["l2"] is not None and not panels[p]["reviewer_fallback"] for p in PANELS)
        published = entry["published"]
        assert not published["l2_redistributed"]
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in PANELS)
        l2 = statistics.mean(panels[p]["l2"] for p in PANELS)
        assert abs(l1 - published["l1"]) < 1e-9 and abs(l2 - published["l2"]) < 1e-9
        code_quality = (SPLIT_WITHOUT_L3["l1"] * l1 + SPLIT_WITHOUT_L3["l2"] * l2) / WEIGHTS["code_quality"]
        assert abs(code_quality - published["code_quality"]) < 1e-9, run["run_id"]
        combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
        combined_20 = composite(run, code_quality, 0.20)
        assert abs(combined_33 - published["composite_v3"]) < 1e-9 and abs(combined_20 - published["composite_v2_profile"]) < 1e-9
        single = {p: composite(run, (SPLIT_WITHOUT_L3["l1"] * panels[p]["l1"]["score"] + SPLIT_WITHOUT_L3["l2"] * panels[p]["l2"])
                               / WEIGHTS["code_quality"], WEIGHTS["code_quality"]) for p in PANELS}
        rows.append({
            "model": MODEL, "effort": run["effort"], "task": run["task"], "run_id": run["run_id"],
            "judged_under": PROTOCOL_ID, "judged": "published", "scored_panels": list(PANELS), "finished": True,
            "functional": run["functional"], "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": False, "code_quality": code_quality,
            "combined_33": combined_33, "combined_20_profile": combined_20, "combined_single_judge": single,
            "panels": {p: {"scored": True, "readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                           "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                           "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": False} for p in PANELS},
            "passed_quirk_families": len(run["passed_families"]), "duration_s": run["duration_s"],
            "started_at": run["started_at"], "finished_at": run["finished_at"], "evidence_sha256": run["evidence_sha256"], **facts,
        })
    assert len(rows) == 69 and {(r["effort"], r["task"]) for r in rows} == set(found)
    rows.sort(key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))
    # The sweep's two pauses: 13 Low runs finished before macOS went from 26 to 27.0.1; every other run started after.
    resume = datetime.fromisoformat(SECOND_RESUME)
    before = [r for r in rows if datetime.fromisoformat(r["finished_at"]) < resume]
    assert len(before) == 13 and all(r["effort"] == "low" for r in before)
    assert all(datetime.fromisoformat(r["started_at"]) >= resume for r in rows if r not in before)
    assert sum(behaviours.values()) == 231 and len(behaviours) == 23

    save("runs.json", {
        "runs": len(rows), "published": 69, "timeouts": 0, "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3, "judges": JUDGES,
        "judged_rule": "every run finished inside the 3-hour bound and the v3.27 summary publishes a Code quality score for each, the equal "
                       "mean of Muse Spark 1.3 (muse) and GPT-6.1 Sol (sol)",
        "single_judge_rule": "combined_single_judge recomputes the combined score with Code quality from one judge's reviewed score and "
                             "intent recovery alone; it is a sensitivity figure, not the published score",
        "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator; no DeepSeek V4.1 Flash run "
                                "needed that rule",
        "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests; hidden_behaviours_fixed counts those the run passed",
        "cost_fields": {"list_usd": "tokens at DeepSeek's off-peak list price, the board's $/task",
                        "billed_usd": "the adapter's per-call meter at the time of each call, 2x in DeepSeek's weekday peak hours",
                        "peak_calls": "model calls metered at the peak rate",
                        "unmetered_title_calls": "dsh's session-title call, which records no usage and is not priced",
                        "attempts_without_usage": "interrupted model replies that reported no usage, not priced"},
        "token_fields": {"raw_tokens": "input (cached included) plus output, as dsh's receipts report them",
                         "token_usage.output_tokens": "output tokens; dsh reports no separate reasoning count"},
        "model_identity": "harness-recorded: dsh records the model it requested (deepseek-flash), not the id in DeepSeek's response; "
                          "DeepSeek's pricing page mapped deepseek-flash to DeepSeek-V4.1-Flash-1017 before each level",
        "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "judged", "combined_33", "combined_20_profile",
                         "combined_muse_only", "combined_sol_only", "functional_pct", "automated_quality_pct", "security_pct",
                         "hidden_behaviours_fixed", "hidden_behaviours", "code_quality", "reviewed_score", "intent_recovery",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery",
                         "sol_reviewed", "sol_readability", "sol_maintainability", "sol_intent_recovery", "passed_quirk_families",
                         "model_calls", "peak_calls", "unmetered_title_calls", "duration_s", "raw_tokens", "cached_input_tokens", "output_tokens",
                         "list_usd", "billed_usd", "started_at", "finished_at", "solver_cli_version", "task_hash", "evidence_sha256"])
        for r in rows:
            p = r["panels"]
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"], r["judged"], fmt(r["combined_33"]),
                             fmt(r["combined_20_profile"]), fmt(r["combined_single_judge"]["muse"]), fmt(r["combined_single_judge"]["sol"]),
                             f'{100 * r["functional"]:.2f}', f'{100 * r["automated_quality"]:.2f}', f'{100 * r["security"]:.2f}',
                             r["hidden_behaviours_fixed"], r["hidden_behaviours"], fmt(r["code_quality"]), fmt(r["reviewed_score"]),
                             fmt(r["intent_recovery"]),
                             *[fmt(p[q][k]) for q in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             r["passed_quirk_families"], r["model_calls"], r["peak_calls"], r["unmetered_title_calls"], r["duration_s"],
                             r["raw_tokens"], r["token_usage"]["cached_input_tokens"], r["token_usage"]["output_tokens"],
                             fmt(r["list_usd"], 6), fmt(r["billed_usd"], 6), r["started_at"], r["finished_at"], r["solver_cli_version"],
                             r["task_hash"], r["evidence_sha256"]])

    card = read(results / "data.json")[MODEL]
    with (results / "deepseek-flash-vs-frontier-efforts.csv").open(newline="") as source:
        table = list(csv.DictReader(source))
    flash_table = {r["effort"]: r for r in table if r["model"] == MODEL}
    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        assert len(rs) == 23
        g = {
            "model": MODEL, "effort": effort, "n": len(rs), "runs": len(rs), "timeouts": 0,
            "combined_33": mean_se(r["combined_33"] for r in rs), "combined_20_profile": mean_se(r["combined_20_profile"] for r in rs),
            "combined_single_judge": {p: mean_se(r["combined_single_judge"][p] for r in rs) for p in PANELS},
            "code_quality": mean_se(r["code_quality"] for r in rs), "reviewed_score": mean_se(r["reviewed_score"] for r in rs),
            "intent_recovery": mean_se(r["intent_recovery"] for r in rs), "intent_recovery_redistributed_runs": 0,
            "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in PANELS) for r in rs),
            "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in PANELS) for r in rs),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in rs) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in rs), "functional_all_runs": mean_se(100 * r["functional"] for r in rs),
            "automated_quality": mean_se(100 * r["automated_quality"] for r in rs), "security": mean_se(100 * r["security"] for r in rs),
            "passed": sum(r["functional"] == 1 for r in rs), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
            "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_median": statistics.median(r["duration_s"] / 60 for r in rs),
            "priced_runs": len(rs), "cli_versions": {CLI_LABEL: len(rs)},
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "output_tokens": mean_se(r["token_usage"]["output_tokens"] for r in rs),
            "cached_input_share": mean_se(r["token_usage"]["cached_input_tokens"] / r["token_usage"]["input_tokens"] for r in rs),
            "model_calls": mean_se(r["model_calls"] for r in rs),
            "usd": mean_se(r["list_usd"] for r in rs), "usd_total": sum(r["list_usd"] for r in rs),
            "billed_usd": mean_se(r["billed_usd"] for r in rs), "billed_usd_total": sum(r["billed_usd"] for r in rs),
            "runs_with_peak_calls": sum(1 for r in rs if r["peak_calls"]), "peak_calls": sum(r["peak_calls"] for r in rs),
            "unmetered_title_calls": sum(r["unmetered_title_calls"] for r in rs),
            "attempts_without_usage": sum(r["attempts_without_usage"] for r in rs),
        }
        # The round's own summary aggregates this level; it must match exactly.
        entry = summary["groups"][f"{MODEL}/{effort}"]
        assert g["n"] == entry["n"] == entry["composite_v3"]["n"]
        for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
            assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9 and abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
        for p in PANELS:
            assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9 and abs(g["by_panel"][p]["se"] - entry["by_panel"][p]["se"]) < 1e-9
        # The harness card data (data.json) and its per-level table carry the same figures.
        c = card[effort]
        assert (c["n"], c["passed"]) == (g["n"], g["passed_all_runs"]), effort
        for field, value in (("combined", g["combined_33"]["mean"]), ("combined_se", g["combined_33"]["se"]), ("code_quality", g["code_quality"]["mean"]),
                             ("functional", g["functional"]["mean"]), ("minutes", g["minutes"]["mean"]), ("usd", g["usd"]["mean"]),
                             ("billed", g["billed_usd"]["mean"])):
            assert abs(c[field] - value) < 1e-9, (effort, field, c[field], value)
        for p in PANELS:
            assert abs(c["by_panel"][p] - g["by_panel"][p]["mean"]) < 1e-9, (effort, p)
        t = flash_table[effort]
        assert (int(t["runs"]), int(t["judged"]), int(t["passed"])) == (g["runs"], g["n"], g["passed_all_runs"])
        for column, value, tol in (("combined", g["combined_33"]["mean"], 5e-5), ("combined_se", g["combined_33"]["se"], 5e-5),
                                   ("usd_per_task", g["usd"]["mean"], 5e-7), ("billed_usd_per_task", g["billed_usd"]["mean"], 5e-7),
                                   ("minutes", g["minutes"]["mean"], 5e-3)):
            assert abs(float(t[column]) - value) <= tol, (effort, column)
        groups.append(g)
    assert [g["passed_all_runs"] for g in groups] == [21, 20, 20]
    assert [round(g["combined_33"]["mean"], 2) for g in groups] == [88.65, 88.61, 88.36]
    assert [round(g["combined_33"]["se"], 2) for g in groups] == [0.67, 0.96, 0.98]
    assert [round(g["code_quality"]["mean"], 1) for g in groups] == [73.1, 74.9, 74.0]
    assert [(round(g["by_panel"]["muse"]["mean"], 1), round(g["by_panel"]["sol"]["mean"], 1)) for g in groups] == [(64.9, 74.5), (68.4, 76.6), (67.1, 74.5)]
    assert [f'{g["minutes"]["mean"]:.2f}' for g in groups] == ["8.05", "8.66", "10.60"]
    assert [f'{g["usd"]["mean"]:.4f}' for g in groups] == ["0.0577", "0.0667", "0.0741"]
    assert [f'{g["billed_usd"]["mean"]:.4f}' for g in groups] == ["0.1010", "0.0680", "0.0741"]
    assert [g["hidden_behaviours"] for g in groups] == [231, 231, 231]
    assert [g["runs_with_peak_calls"] for g in groups] == [14, 1, 0]
    gaps = [g["by_panel"]["sol"]["mean"] - g["by_panel"]["muse"]["mean"] for g in groups]
    assert [round(x, 1) for x in gaps] == [9.6, 8.2, 7.3]  # the provenance limit quotes 7.3 to 9.6
    save("groups.json", groups)

    with SCORES.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "timeouts", "combined_33", "combined_33_se", "combined_20_profile", "combined_muse_only",
                         "combined_sol_only", "code_quality", "code_quality_se", "reviewed_score", "intent_recovery", "readability",
                         "maintainability", "muse_reviewed", "sol_reviewed", "functional", "automated_quality", "security", "passed_of_23",
                         "hidden_behaviours_fixed", "hidden_behaviours", "mean_minutes", "mean_minutes_se", "median_minutes", "mean_raw_tokens",
                         "mean_output_tokens", "mean_list_usd", "mean_list_usd_se", "total_list_usd", "mean_billed_usd", "total_billed_usd",
                         "cli_version"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"], g["timeouts"], f'{g["combined_33"]["mean"]:.4f}',
                             f'{g["combined_33"]["se"]:.4f}', f'{g["combined_20_profile"]["mean"]:.4f}',
                             f'{g["combined_single_judge"]["muse"]["mean"]:.4f}', f'{g["combined_single_judge"]["sol"]["mean"]:.4f}',
                             f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}', f'{g["reviewed_score"]["mean"]:.4f}',
                             f'{g["intent_recovery"]["mean"]:.4f}', f'{g["readability"]["mean"]:.4f}', f'{g["maintainability"]["mean"]:.4f}',
                             f'{g["by_panel"]["muse"]["mean"]:.4f}', f'{g["by_panel"]["sol"]["mean"]:.4f}', f'{g["functional"]["mean"]:.4f}',
                             f'{g["automated_quality"]["mean"]:.4f}', f'{g["security"]["mean"]:.4f}', g["passed_all_runs"], g["hidden_behaviours_fixed"],
                             g["hidden_behaviours"], f'{g["minutes"]["mean"]:.4f}', f'{g["minutes"]["se"]:.4f}', f'{g["minutes_median"]:.4f}',
                             f'{g["raw_tokens"]["mean"]:.1f}', f'{g["output_tokens"]["mean"]:.1f}', f'{g["usd"]["mean"]:.6f}', f'{g["usd"]["se"]:.6f}',
                             f'{g["usd_total"]:.6f}', f'{g["billed_usd"]["mean"]:.6f}', f'{g["billed_usd_total"]:.6f}', CLI_LABEL])

    pricing = read(results / "pricing-check.json")
    deepseek = pricing["deepseek"]
    assert deepseek["aliases"][API_MODEL] == SERVED_ALIAS and deepseek["alias_rechecked_before_each_level"] is True
    rates = deepseek["usd_per_million_off_peak"][API_MODEL]
    assert (rates["input_cache_miss"], rates["input_cache_hit"], rates["output"]) == tuple(RATES.values())
    assert deepseek["peak"] == PEAK
    assert f'grep -q "{SERVED_ALIAS}"' in launcher  # the pre-level alias check the sweep ran
    totals = {MODEL: {"runs": len(rows), "list_usd": sum(r["list_usd"] for r in rows), "billed_usd": sum(r["billed_usd"] for r in rows),
                      "raw_tokens": sum(r["raw_tokens"] for r in rows), "model_calls": sum(r["model_calls"] for r in rows),
                      "peak_calls": sum(r["peak_calls"] for r in rows), "unmetered_title_calls": sum(r["unmetered_title_calls"] for r in rows),
                      "attempts_without_usage": sum(r["attempts_without_usage"] for r in rows),
                      "solver_hours": sum(r["duration_s"] for r in rows) / 3600}}
    t = totals[MODEL]
    assert (f'{t["list_usd"]:.2f}', f'{t["billed_usd"]:.2f}') == ("4.56", "5.59")
    assert (t["model_calls"], t["peak_calls"], t["unmetered_title_calls"], t["attempts_without_usage"]) == (3939, 936, 66, 3)
    save("economics.json", {
        "scope": "Solver inference only. The sweep ran on a DeepSeek API key, so this is metered API spend: list_usd prices every run at "
                 "DeepSeek's off-peak list rate (the board's $/task), billed_usd is what each call was metered at the time it was made. "
                 "Judging is excluded.",
        "pricing_verified": pricing["checked"],
        "sources": {"deepseek": deepseek["source"]},
        "alias": {API_MODEL: SERVED_ALIAS, "rechecked_before_each_level": True},
        "rates_per_million_off_peak": {API_MODEL: RATES},
        "peak": PEAK,
        "pricing_method": PRICING_METHOD,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": g["usd"], "usd_total": g["usd_total"],
                    "billed_usd": g["billed_usd"], "billed_usd_total": g["billed_usd_total"], "runs_with_peak_calls": g["runs_with_peak_calls"],
                    "peak_calls": g["peak_calls"], "raw_tokens": g["raw_tokens"], "raw_tokens_total": g["raw_tokens_total"],
                    "output_tokens": g["output_tokens"], "cached_input_share": g["cached_input_share"], "model_calls": g["model_calls"],
                    "minutes": g["minutes"]} for g in groups],
        "totals": totals,
        "limitations": [
            "List-price cost uses DeepSeek's off-peak rate, the rate its price table lists. DeepSeek bills 2x on weekdays from 01:00 to "
            "04:00 and 06:00 to 10:00 UTC; the adapter meters each call at its own time, so billed_usd is higher wherever calls fell in "
            "those hours (most of Low and one High run).",
            "dsh titles a session with one small deepseek-flash call (input capped at 4 KiB) and records no usage for it. It appears in 66 "
            "of 69 runs, is counted in unmetered_title_calls and is not priced; it understates cost by well under a cent per run.",
            "Three runs each had one interrupted model reply that reported no usage (attempts_without_usage); those are not priced either.",
            "Cost per task covers all 23 runs at every level.",
        ],
        "pricing_check_sha256": digest(results / "pricing-check.json"),
    })

    calibration = {}
    for panel in PANELS:
        result = read(out / f"calibration-{panel}.json")
        assert result["protocol_sha256"] == digest(out / "protocol.json")
        assert result["passed"] and result["failing_gates"] == [] and not result["allowance_used"] and result["call_count"] == 80
        assert len(result["gates"]) == 20 and all(g["passed"] for g in result["gates"].values())
        calibration[panel] = {"judge": JUDGES[panel], "taken_under": PROTOCOL_ID,
                              **{k: result[k] for k in ("passed", "failing_gates", "call_count", "protocol_sha256", "allowance", "allowance_used",
                                                        "gates", "control_means")}}
    save("calibration.json", calibration)

    counts, retries, markers, reviews, recoveries, window = call_records(out)
    assert markers == [] and reviews == []
    assert counts == {p: {"calibration": 80, "match": 69, "pairwise": 6, "primary": 69, "probe": 69, "repeat": 3} for p in PANELS}, counts
    assert retries == {"muse": 2, "sol": 10}, retries
    assert [(p, s, i) for p, s, i, _ in recoveries] == [("sol", "match", s) for s in INDEX_RECOVERIES], recoveries
    assert all(rec["method"] == RECOVERY_METHOD and rec["source_attempt"] == 1 for *_, rec in recoveries)
    assert window[0].startswith("2026-10-23T09:34") and window[1].startswith("2026-10-23T12:36")
    save("judge-protocols.json", {
        "scored_panel": {p: public_settings(protocol["reviewers"][p]) for p in PANELS},
        "judge_names": JUDGES,
        "protocol_id": PROTOCOL_ID, "protocol_sha256": digest(out / "protocol.json"),
        "seat": "Grok 4.6 holds the usual second seat but judges through Cursor, whose account was out of usage on 2026-10-23; the owner "
                "chose GPT-6.1 Sol for the seat, the pair v3.20 used for Grok 4.7. Both judges took the exam under v3.27 before any counted call.",
        "same_as_v320": "rubric, system text, pair, probe and match instructions, schemas, seed, repeats, gate allowance, weights, retry rule, "
                        "control hashes, and both judges' model, effort and binary pins equal the published v3.20 record",
        "amends": protocol["amends"], "system": protocol["system"], "rubric": protocol["rubric"],
        "pair_instruction": protocol["pair_instruction"], "probe_instruction": protocol["probe_instruction"],
        "match_instruction": protocol["match_instruction"], "schemas": protocol["schemas"], "weights": protocol["weights"],
        "gate_allowance": protocol["gate_allowance"], "repeats": protocol["repeats"], "seed": protocol["seed"],
        "single_panel_rule": protocol["single_panel_rule"], "invalid_response_retries": protocol["invalid_response_retries"],
        "comparability": protocol["comparability"], "control_source_hashes": protocol["control_source_hashes"],
        "population": {"description": protocol["population"]["description"], "cells": protocol["population"]["cells"],
                       "excluded": protocol["population"]["excluded"], "missing": protocol["population"]["missing"]},
        "planned_calls": protocol["planned_calls"],
        "judge_pins": {
            "muse": {"cli": "Muse CLI", "sha256": muse["binary_sha256"], "settings_source": pins["muse_settings_source"],
                     "note": "a byte-identical backup of the v3.4 binary, because Muse Code's updater removed the original copy; re-hashed before every stage"},
            "sol": {"cli": "Codex", "version": pins["codex"]["version"], "launcher_sha256": pins["codex"]["launcher"]["sha256"],
                    "native_sha256": pins["codex"]["native"]["sha256"], "rule": pins["codex"]["rule"]},
        },
        "counted_calls": counts, "second_attempts": retries,
        "operator_recoveries": [{"panel": p, "stage": s, "submission": i, "rule": "recover_one_based_indexes", "method": rec["method"],
                                 "source_attempt": rec["source_attempt"],
                                 "condition": "both attempts failed the index range check, every cited index lay in 1..count and the "
                                              "highest equalled count; the shifted result must then validate",
                                 "score_effect": "none: intent scoring reads match statuses only"} for p, s, i, rec in recoveries],
        "judging_window_utc": {"first_call_completed": window[0], "last_call_completed": window[1]},
    })

    # The cards are copied byte for byte from the harness.
    for name, target in CARDS.items():
        assert target.read_bytes() == (results / name).read_bytes(), name

    save("provenance.json", {
        "source_artifacts_sha256": {
            **{f"v3.27/{f}": digest(out / f) for f in ("summary.json", "protocol.json", "private-manifest.json", "calibration-muse.json",
                                                       "calibration-sol.json")},
            **{f"v3.27/calls/sol/match/{s}/selected.json": digest(out / "calls/sol/match" / s / "selected.json") for s in INDEX_RECOVERIES},
            **{name: digest(results / name) for name in ("comparison.json", "data.json", "deepseek-flash-vs-frontier-efforts.csv",
                                                         "pricing-check.json", "1-summary.png", "2-combined-score.png", "3-time-per-task.png",
                                                         "4-cost-per-task.png")},
            "gpt61sol-opus55-astra-efforts.csv": digest(root / COMPARATORS),
            "suite.lock.json": digest(root / LOCK),
            "deepseek-flash-dsh.launch.sh": digest(root / LAUNCHER),
        },
        "export_checks": ["69 solver summaries in the sweep folder, 23 per level, no task twice; the two runs a pause interrupted hold no "
                          "summary and are not part of the population",
                          "every run is dsh:deepseek-flash at its requested level on DeepSeek Harness 0.2.1-rc.2, the install tree hash "
                          "equal to the pin, from bench/2026-10-20-deepseek-dsh-frontier-v4 with a clean source block and every task hash "
                          "equal to the frozen suite lock",
                          "every integrity audit: no web, no benchmark data or answer-key paths, not contaminated",
                          "each run's token totals equal its dsh_usage receipt; list cost recomputed from tokens at the off-peak rate equals "
                          "the summary's; billed cost equals the receipt's meter; no retried attempt",
                          "the population record's hash and the manifest's hash equal the ones frozen in the protocol, and every judged "
                          "run's summary hash equals its manifest entry",
                          "rubric, prompts, schemas, seed, repeats, gate allowance, weights, retry rule, control hashes and both judges' "
                          "pins equal the published v3.20 record",
                          "both judges passed calibration under v3.27 with no failing gate and no allowance used; no reviewer fallback; "
                          "no operator marker; six GPT-6.1 Sol answer-key matches recovered under recover_one_based_indexes",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary; each level's means "
                          "and standard errors, per-judge means included, matched to the summary's groups",
                          "combined score, its standard error, Code quality, each judge's reviewed score, tasks passed, functional score, "
                          "minutes, list and billed cost per level matched to the harness card data and its per-level table",
                          "the rates applied equal the pricing check; the cards are byte-identical to the harness copies; the sweep's "
                          "overlap logger recorded no other benchmark job; no dashes or host paths in exported text"],
        "limits": ["DeepSeek V4.1 Flash is judged by Muse Spark 1.3 and GPT-6.1 Sol, the pair v3.20 used for Grok 4.7, not by Muse Spark "
                   "1.3 and Grok 4.6 like most Frontier v4 columns (Claude Opus 5.5 and GPT-6.1 Sol included): Grok 4.6's Cursor account "
                   "was out of usage on 2026-10-23. Scores from different panels are not calibrated against each other.",
                   "GPT-6.1 Sol rates Flash's reviewed Code quality 7.3 to 9.6 points above Muse Spark 1.3. The published score is their "
                   "mean; combined_single_judge gives each judge alone.",
                   "GPT-6.1 Sol judged these runs and is also a compared model on the cards and the board; its own column comes from its "
                   "own round, judged by Muse Spark 1.3 and Grok 4.6.",
                   "Model identity is harness-recorded: dsh records the model it requested, not the id in DeepSeek's response. DeepSeek's "
                   "pricing page mapped deepseek-flash to DeepSeek-V4.1-Flash-1017 when checked before each level.",
                   "DeepSeek Harness 0.2.1-rc.2 is a developer preview prerelease, pinned by exact version and install tree hash. Its "
                   "default-on session-log upload and OpenTelemetry feedback upload were off; the model never sees either, and task "
                   "content still reaches DeepSeek in the model requests.",
                   "The owner paused the sweep twice between tasks; each run a pause interrupted was set aside and rerun, not judged. macOS "
                   "went from 26 to 27.0.1 during the second pause; re-grading the 13 Low runs finished before it on 27.0.1 gave identical "
                   "functional scores.",
                   "DeepSeek's API offers Low, High and Max reasoning only, so there is no Medium or Extra-high column.",
                   "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.",
                   "One attempt per task and level, on the owner's Mac, local sandbox, flat 3-hour task bound, one task at a time."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, raw tokens, model calls, list and billed cost.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts", "dsh session logs and solver traces", "the two pause-interrupted attempts",
                     "host binary paths"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
