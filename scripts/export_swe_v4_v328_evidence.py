"""Export the public record of the Reflection Beam effort sweep on Frontier v4, judged under v3.28.

Adapted from the v3.27 DeepSeek V4.1 Flash export, with the same publication
scope: per-run scores, per-panel sub-scores, aggregates, judge protocol text,
calibration verdicts and raw tokens. Raw prompts, patches, quirk answer keys
and host paths are withheld. Run from the site root:

    python3 scripts/export_swe_v4_v328_evidence.py --harness-root ../VulcanBench

--harness-root holds the frozen run directory (runs-effort-beam-mirror), the
judging round (runs-code-quality-maintenance-v3.28), the population record and
card in docs/results/swe-v4-beam-2026-10, the comparator tables, the suite lock
and the sweep launcher and resume script under logs/.

What differs from the DeepSeek V4.1 Flash export, all forced by the sweep or its judging:

- The same panel, a new round. Grok 4.6's Cursor account was still out of
  usage, so the owner kept GPT-6.1 Sol beside Muse Spark 1.3, as in v3.27.
  Both retook the exam under v3.28.
- Five levels. Beam's reasoning_effort takes low, medium, high, xhigh and max;
  the board's Extra high is xhigh.
- Not every run is judged. 115 runs finished; 99 carry a published Code
  quality score. Three ended with an empty patch and twelve changed no source
  file (only file modes or scratch files); neither has code to review, so
  neither is judged and each counts as a failed task (owner decision
  2026-10-26 for the second kind). Max hedgecore is unjudged because neither
  judge could review its evidence: Beam left 6.5M characters of scratch files
  in its workspace, beyond GPT-6.1 Sol's input limit, and Muse's two attempts
  cited no code. Max payrollcore is published from Muse alone for the same
  input-limit reason. combined_no_code_zero counts the fifteen runs with no
  code as 0, as the board does for timeouts.
- No price. Reflection publishes no Beam price, so cost is unavailable and
  economics.json carries tokens and minutes only.
- Every number the harness card data shows is matched: combined score and its
  standard error, Code quality, tasks passed and minutes per level.
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
DEST = SITE / "assets/data/swe-v4-beam-v328"
SCORES = SITE / "assets/data/swe-v4-beam-v328-scores.csv"
CARDS = {"beam-vs-frontier-card.png": SITE / "assets/cards/swe-v4-beam-v328.png"}
EFFORTS = ("low", "medium", "high", "extra-high", "max")
PROVIDER_EFFORT = {"low": "low", "medium": "medium", "high": "high", "extra-high": "xhigh", "max": "max"}
MODEL = "beam"
NAMES = {MODEL: "Reflection Beam"}
SOLVER = "mirror:Beam-1.0-501B-A23B"
API_MODEL = "Beam-1.0-501B-A23B"
API_ALIAS = "Beam-501B-A23B"
PANELS = ("muse", "sol")
JUDGES = {"muse": "Muse Spark 1.3", "sol": "GPT-6.1 Sol"}
WEIGHTS = {"functional": 0.50, "quality": 0.085, "security": 0.085, "code_quality": 0.33}
SPLIT_WITHOUT_L3 = {"l1": 0.24, "l2": 0.09}
PROTOCOL_ID = "code-quality-maintenance-v3.28"
ROUND = "runs-code-quality-maintenance-v3.28"
RESULTS = "docs/results/swe-v4-beam-2026-10"
COMPARATORS = ("docs/results/swe-v4-opus55-2026-09/opus55-astra-fable-efforts.csv",
               "docs/results/swe-v4-gpt61-sol-2026-09/gpt61-sol-v318-efforts.csv",
               "docs/results/swe-v4-astra-fable51-2026-09/astra-vs-fable51-v34-efforts.csv")
LOCK = "tasks/coding-intelligence-index-v4/suite.lock.json"
SWEEP = "runs-effort-beam-mirror"
LAUNCHER = "logs/beam-mirror.launch.sh"
RESUME = "logs/beam-mirror-resume.sh"
OVERLAP_LOG = "logs/beam-mirror-overlap.log"  # the launcher's per-minute logger writes it only when another job runs
TAG, COMMIT = "bench/2026-10-23-beam-mirror-frontier-v4", "bb74b25ce8e6afbc2b3e776d2e237bccdb30b3cd"
MIRROR_VERSION = "0.1.1"
CLI_LABEL = "Mirror CLI 0.1.1"
INSTALL_TREE_SHA256 = "cfe894ee157a3a51dade77fd57b7bd805f35cd2e9a41c0073a2b3d521a6d0bf5"
MIRROR_SETTINGS = {"usage_warning_acknowledged": True, "trusted_directories": ["<run workspace>"], "analytics": False}
# Reflection's daily API token limit stopped Max after 13 tasks on 2026-10-24; the sweep resumed after the 00:00 UTC reset.
LIMIT_STOP, LIMIT_RESUME = "2026-10-24T13:38:00+00:00", "2026-10-25T00:00:00+00:00"
INFRA_ABORTED = 1200
# Unjudged runs. The population builder excludes an empty patch; the operator rule no_source_change (owner, 2026-10-26)
# excludes a patch that changes no source file; hedgecore Max has no valid review from either judge.
EMPTY_PATCH = {("low", "legacy-blendcore-binary-parity"), ("low", "legacy-metercore-binary-parity"),
               ("medium", "legacy-granarycore-binary-parity")}
NO_SOURCE = {"submission-006", "submission-017", "submission-022", "submission-037", "submission-068", "submission-074",
             "submission-076", "submission-084", "submission-088", "submission-090", "submission-101", "submission-111"}
UNREVIEWABLE = "submission-027"  # max hedgecore
SOL_OVER_LIMIT = {"submission-005", "submission-027"}  # max payrollcore and hedgecore
JUDGED_NOTE = {
    "published": "published",
    "empty_patch": "not judged: the run ended with an empty patch, so there is no code to review; counts as a failed task",
    "no_source_change": "not judged: the run changed no source file (only file modes from chmod and scratch files), so the review "
                        "evidence is the untouched starting code; excluded like an empty patch (owner decision 2026-10-26); counts "
                        "as a failed task",
    "unreviewable": "not judged: Beam left 6.5M characters of scratch files in the workspace, so the evidence exceeds GPT-6.1 Sol's "
                    "input limit and Muse Spark 1.3's two attempts cited no code; no panel has a valid review",
}
FORBIDDEN = (chr(0x2014), chr(0x2013), "/Users/", "/home/", "/private/", "/var/folders/")
PUBLIC_V327 = SITE / "assets/data/swe-v4-deepseek-flash-v327/judge-protocols.json"


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
    """The pre-registered 24 plus 9 split; with no intent denominator the 9 points move to the reviewed layer."""
    return reviewed if intent is None else (SPLIT_WITHOUT_L3["l1"] * reviewed + SPLIT_WITHOUT_L3["l2"] * intent) / WEIGHTS["code_quality"]


def trace_records(run_dir):
    """The run's one mirror_usage receipt and its one cli_agent_start record."""
    found = {}
    for line in (run_dir / "trace.jsonl").read_text().splitlines():
        if '"mirror_usage"' in line or '"cli_agent_start"' in line:
            event = json.loads(line)
            if event.get("type") in ("mirror_usage", "cli_agent_start"):
                assert event["type"] not in found, run_dir.name
                found[event["type"]] = event["data"]
    assert set(found) == {"mirror_usage", "cli_agent_start"}, run_dir.name
    return found["mirror_usage"], found["cli_agent_start"]


def failed_requests(run_dir):
    """Model requests Mirror logged as failed (and carried on from): their texts, from the decoded conversation stream."""
    texts = []
    for line in (run_dir / "cli-agent-stream.jsonl").read_text().splitlines():
        record = json.loads(line)
        if record.get("log", {}).get("level") == "error":
            texts.append(record["log"]["text"])
    return texts


def solver_facts(run_dir, effort, lock):
    """Checks every run must pass, and the facts each row carries from the solver side."""
    solver = read(run_dir / "summary.json")
    provider = PROVIDER_EFFORT[effort]
    assert solver["model"] == SOLVER and solver["effort"]["requested"] == effort and solver["effort"]["provider_value"] == provider
    agent = solver["cli_agent"]
    assert agent["harness"] == "mirror" and agent["harness_version"] == MIRROR_VERSION and agent["billing"] == "api", run_dir.name
    assert agent["requested_model"] == agent["reported_model"] == API_MODEL and agent["model_identity_confidence"] == "harness-recorded"
    assert agent["subtype"] == "completed" and agent["cli_reported_cost_usd"] is None, run_dir.name
    for clause in ("web tools absent", "analytics off", "private Mirror home per run", "Mirror approvals automatic"):
        assert clause in agent["execution_boundary"], (run_dir.name, clause)
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
    assert start["harness_version"] == MIRROR_VERSION and start["install_tree_sha256"] == INSTALL_TREE_SHA256, run_dir.name
    assert start["requested_model"] == API_MODEL and start["requested_effort"] == provider and start["billing"] == "api"
    assert start["mirror_settings"] == MIRROR_SETTINGS, run_dir.name
    assert start["argv"][start["argv"].index("--reasoning-effort") + 1] == provider and "--no-update" in start["argv"]
    assert start["argv"][start["argv"].index("--approval-mode") + 1] == "auto" and start["argv"][-2:] == ["exec", "-"]
    tokens = solver["tokens"]
    assert (tokens["prompt"], tokens["completion"], tokens["cached_input"]) == (usage["prompt"], usage["completion"], usage["cached"])
    assert usage["cache_write"] == 0 and tokens["reasoning_output"] == 0, run_dir.name
    assert solver["total_tokens"] == tokens["prompt"] + tokens["completion"] == tokens["total"]
    assert usage["calls"] > 0 and usage["calls"] == agent["num_turns"], run_dir.name
    failures = failed_requests(run_dir)
    assert len(failures) == usage["errors"], run_dir.name
    assert all(t.startswith("model request failed: ") and t.endswith(f"[model={API_MODEL}]") for t in failures), run_dir.name
    # Reflection publishes no Beam price: the summary records no cost anywhere.
    economics = solver["economics"]
    assert solver["cost_usd"] is None and economics["marginal_cash_usd"] is None and economics["api_equivalent_cost_usd"] is None
    assert economics["measurement_quality"] == {"marginal_cash_usd": "unavailable", "api_equivalent_cost_usd": "unavailable"}
    assert solver["cost_detail"]["model_priced"] is False, run_dir.name
    hidden = solver["verifier"]["fail_to_pass"]
    return solver, {
        "solver_cli_version": CLI_LABEL, "install_tree_sha256": INSTALL_TREE_SHA256, "source_tag": TAG, "task_hash": solver["task_hash"],
        "requested_model": API_MODEL, "requested_effort": provider, "model_identity": "harness-recorded",
        "integrity_audit": {"web": "no_web", "benchmark_data_paths": 0, "answer_key_paths": 0, "contaminated": False},
        "hidden_behaviours_fixed": sum(1 for v in hidden.values() if v), "hidden_behaviours": len(hidden),
        "model_calls": usage["calls"], "failed_model_requests": usage["errors"], "raw_tokens": solver["total_tokens"],
        "token_usage": {"input_tokens": tokens["prompt"], "cached_input_tokens": tokens["cached_input"],
                        "uncached_input_tokens": tokens["prompt"] - tokens["cached_input"], "output_tokens": tokens["completion"]},
        "cost_usd": None,
    }, failures


def call_records(out):
    """Counted calls per stage, calls with a second attempt, operator markers, reviews and recoveries under calls/."""
    counts = {p.name: {s.name: sum(1 for d in s.iterdir() if d.is_dir()) for s in sorted(p.iterdir()) if s.is_dir()}
              for p in sorted((out / "calls").iterdir()) if p.is_dir()}
    retries = {p: sum(1 for d in (out / "calls" / p).glob("*/*") if len(list(d.glob("attempt-*.json"))) > 1) for p in counts}
    markers = {}
    for p in sorted((out / "calls").glob("*/*/*/operator-invalid.json")):
        markers[(p.parents[2].name, p.parents[1].name, p.parent.name)] = read(p)
    reviews = sorted((p.parents[2].name, p.parents[1].name, p.parent.name, read(p)["operator_review"]["finding"])
                     for p in (out / "calls").glob("*/*/*/attempt-*.json") if "operator_review" in read(p))
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

    # The round: one protocol, both judges passing, 99 of 112 submissions published, every binding hash intact.
    assert summary["protocol"] == protocol["id"] == PROTOCOL_ID
    assert summary["passing_panels"] == list(PANELS) and summary["failed_panels"] == []
    # ready_for_publication is False because 13 submissions are unpublished by rule (the Haiku 5.5 v3.24 precedent).
    assert not summary["ready_for_publication"]
    assert summary["fallback_reviews"] == {p: 0 for p in PANELS} and summary["self_preference"] == {}
    assert summary["expected_submissions"] == len(manifest) == len(summary["rows"]) == 112 and summary["published_submissions"] == 99
    assert not summary["human_calibrated"] and not summary["humans_involved"]
    assert protocol["source_comparison_sha256"] == digest(comparison_path)
    assert protocol["manifest_sha256"] == digest(out / "private-manifest.json")
    assert protocol["scored_siblings"] == {} and protocol["sensitivity_panels"] == {}
    assert set(protocol["reviewers"]) == set(PANELS)
    muse, sol = protocol["reviewers"]["muse"], protocol["reviewers"]["sol"]
    assert (muse["model"], muse["effort"], muse["lab"]) == ("muse-spark-1.3", "medium", "Meta")
    assert (sol["model"], sol["effort"], sol["codex_version"], sol["lab"]) == ("gpt-6.1-sol", "medium", "0.159.0", "OpenAI")
    assert muse["neutrality"] == sol["neutrality"] == "neutral for Reflection submissions"
    assert "byte-identical backup of the v3.4 binary" in muse["binary_location"]
    pins = protocol["judge_pins"]
    assert pins["codex"]["launcher"]["sha256"] == sol["binary_sha256"] and pins["codex"]["native"]["sha256"] == sol["native_binary_sha256"]
    assert protocol["binaries"][muse["muse"]]["sha256"] == muse["binary_sha256"]
    # The rubric, prompts, schemas, seed, repeats, allowance, weights, retry rule and controls equal v3.27's as published, and so
    # do both judges' model, effort and binary pins: the same panel DeepSeek V4.1 Flash was judged by.
    v327 = json.loads(PUBLIC_V327.read_text())
    for key in ("rubric", "system", "pair_instruction", "probe_instruction", "match_instruction", "schemas", "seed", "repeats",
                "gate_allowance", "weights", "invalid_response_retries", "control_source_hashes"):
        assert protocol[key] == v327[key], key
    for key in ("model", "effort", "binary_sha256", "timeout", "tier", "prompt_delivery", "system_prompt", "sandbox", "identity"):
        assert muse[key] == v327["scored_panel"]["muse"][key], key
    for key in ("model", "effort", "codex_version", "binary_sha256", "timeout", "prompt_delivery", "system_prompt", "identity"):
        assert sol[key] == v327["scored_panel"]["sol"][key], key
    cells = {"beam/low": 21, "beam/medium": 22, "beam/high": 23, "beam/extra-high": 23, "beam/max": 23}
    assert comparison["cells"] == protocol["population"]["cells"] == cells
    assert comparison["missing"] == protocol["population"]["missing"] == []
    assert comparison["excluded"] == protocol["population"]["excluded"]
    assert {(x["effort"], x["task"]) for x in comparison["excluded"]} == EMPTY_PATCH
    assert all(x["reason"].startswith("Incomplete source run: ") and x["finished"] and x["functional"] == 0.0 for x in comparison["excluded"])
    assert comparison["levels"] == {MODEL: list(EFFORTS)} and len(comparison["rows"]) == 112
    record_by_run = {r["run_id"]: r for r in comparison["rows"]}

    # Every finished solver summary in the sweep: 115 runs, 23 per level, no task twice; the attempts Reflection's daily token
    # limit cut short hold no summary.
    sweep = root / SWEEP
    found = {}
    for p in sorted(sweep.glob("*/legacy-*/summary.json")):
        effort = p.parent.parent.name
        assert effort in EFFORTS, p
        key = (effort, read(p)["task_id"])
        assert key not in found, key
        found[key] = p.parent
    assert all((d / "summary.json").exists() for d in sweep.glob("*/legacy-*"))
    assert len(found) == 115 and Counter(e for e, _ in found) == {e: 23 for e in EFFORTS}
    aborted = list((sweep / "infra-aborted").iterdir())
    assert len(aborted) == INFRA_ABORTED and all(p.name.startswith("max-legacy-") for p in aborted)
    assert not list((sweep / "infra-aborted").glob("*/summary.json"))  # a cut-short attempt is never scored
    launcher = (root / LAUNCHER).read_text()
    assert "overlap_procs=" in launcher and "logs/beam-mirror-overlap.log" in launcher and INSTALL_TREE_SHA256 in launcher
    assert f'grep -q "{API_ALIAS}"' in launcher  # the pre-level check that Reflection's API still lists Beam
    assert not (root / OVERLAP_LOG).exists()  # the per-minute logger never saw another benchmark job beside the sweep
    resume = (root / RESUME).read_text()
    assert "daily token limit" in resume and "2026-10-25T00:05:00Z" in resume
    DEST.mkdir(parents=True, exist_ok=True)

    facts_by_key = {}
    behaviours = {}
    failure_texts = Counter()
    for key, run_dir in found.items():
        solver, facts, failures = solver_facts(run_dir, key[0], lock)
        facts_by_key[key] = (solver, facts, run_dir)
        failure_texts.update(t.removeprefix("model request failed: ").split(" [model=")[0].split(":")[0] for t in failures)
        assert behaviours.setdefault(key[1], facts["hidden_behaviours"]) == facts["hidden_behaviours"], key

    counts, retries, markers, reviews, recoveries, window = call_records(out)
    rows = []
    for entry in summary["rows"]:
        run = manifest[entry["id"]]
        key = (run["effort"], run["task"])
        assert run["model"] == entry["model"] == MODEL and run["effort"] == entry["effort"] and run["task"] == entry["task"]
        assert not run.get("fallback") and not entry["fallback"]
        solver, facts, run_dir = facts_by_key[key]
        assert run_dir.name == run["run_id"] and digest(run_dir / "summary.json") == run["source_hashes"]["summary"], run["run_id"]
        assert run["solver_cli_version"] == MIRROR_VERSION and run["duration_s"] == solver["duration_s"]
        assert (run["functional"], run["quality"], run["security"]) == (solver["scores"]["functional"], solver["scores"]["quality"], solver["scores"]["security"])
        assert run["api_equivalent_cost_usd"] is None and run["solver_receipt"]["raw_tokens"] == facts["raw_tokens"]
        record = record_by_run[run["run_id"]]
        assert {k: v for k, v in record.items() if k != "source_directory"} == {k: v for k, v in run.items() if k in record and k != "source_directory"}
        panels = entry["panels"]
        assert not any(panels[p]["reviewer_fallback"] for p in PANELS)
        scored = [p for p in PANELS if panels[p]["l1"] is not None]
        published = entry.get("published")
        base = {"model": MODEL, "effort": run["effort"], "task": run["task"], "run_id": run["run_id"], "finished": True,
                "functional": run["functional"], "duration_s": run["duration_s"], "started_at": run["started_at"],
                "finished_at": run["finished_at"], "evidence_sha256": run["evidence_sha256"]}
        if not published:
            assert scored == [] and (entry["id"] in NO_SOURCE or entry["id"] == UNREVIEWABLE), entry["id"]
            if entry["id"] in NO_SOURCE:
                # Both panels' primary reviews are set aside under the operator rule, kept as selected.excluded.json.
                for p in PANELS:
                    marker = markers[(p, "primary", entry["id"])]
                    assert marker["rule"] == "no_source_change" and marker["owner_decision"].startswith("2026-10-26")
                    assert (out / "calls" / p / "primary" / entry["id"] / "selected.excluded.json").is_file()
                    assert not (out / "calls" / p / "primary" / entry["id"] / "selected.json").exists()
                assert run["functional"] < 1, entry["id"]
                status = "no_source_change"
            else:
                assert markers[("muse", "primary", entry["id"])]["rule"] == "invalidate_unrecoverable_primary"
                assert markers[("sol", "primary", entry["id"])]["rule"] == markers[("sol", "probe", entry["id"])]["rule"] == "input_over_judge_limit"
                status = "unreviewable"
            rows.append({**base, "judged_under": None, "judged": JUDGED_NOTE[status], "status": status, "scored_panels": [],
                         "automated_quality": run["quality"], "security": run["security"], "reviewed_score": None, "intent_recovery": None,
                         "intent_recovery_redistributed": None, "code_quality": None, "combined_33": None,
                         "combined_no_code_zero": 0.0 if status == "no_source_change" else None, "combined_20_profile": None,
                         "combined_single_judge": None, "panels": None, "passed_quirk_families": len(run["passed_families"]), **facts})
            continue
        if entry["id"] in SOL_OVER_LIMIT:
            assert scored == ["muse"] and markers[("sol", "primary", entry["id"])]["rule"] == "input_over_judge_limit", entry["id"]
        else:
            assert scored == list(PANELS), entry["id"]
        l1 = statistics.mean(panels[p]["l1"]["score"] for p in scored)
        intents = [panels[p]["l2"] for p in scored if panels[p]["l2"] is not None]
        assert all(panels[p]["l2"] is not None or panels[p]["l2_denominator"] == 0 for p in scored), entry["id"]
        l2 = statistics.mean(intents) if intents else None
        assert published["l2_redistributed"] == (l2 is None) and (len(run["passed_families"]) == 0) == (l2 is None), entry["id"]
        assert abs(l1 - published["l1"]) < 1e-9 and (l2 is None and published["l2"] is None or abs(l2 - published["l2"]) < 1e-9)
        code_quality = code_quality_of(l1, l2)
        assert abs(code_quality - published["code_quality"]) < 1e-9, run["run_id"]
        combined_33 = composite(run, code_quality, WEIGHTS["code_quality"])
        combined_20 = composite(run, code_quality, 0.20)
        assert abs(combined_33 - published["composite_v3"]) < 1e-9 and abs(combined_20 - published["composite_v2_profile"]) < 1e-9
        single = {p: (composite(run, code_quality_of(panels[p]["l1"]["score"], panels[p]["l2"]), WEIGHTS["code_quality"]) if p in scored else None)
                  for p in PANELS}
        rows.append({
            **base, "judged_under": PROTOCOL_ID, "judged": "published", "status": "published", "scored_panels": scored,
            "automated_quality": run["quality"], "security": run["security"],
            "reviewed_score": l1, "intent_recovery": l2, "intent_recovery_redistributed": l2 is None, "code_quality": code_quality,
            "combined_33": combined_33, "combined_no_code_zero": combined_33, "combined_20_profile": combined_20, "combined_single_judge": single,
            "panels": {p: ({"scored": True, "readability": panels[p]["l1"]["readability"], "maintainability": panels[p]["l1"]["maintainability"],
                            "reviewed_score": panels[p]["l1"]["score"], "intent_recovery": panels[p]["l2"],
                            "scored_quirks": panels[p]["l2_denominator"], "reviewer_fallback": False}
                           if p in scored else {"scored": False, "reason": "evidence over GPT-6.1 Sol's input limit"}) for p in PANELS},
            "passed_quirk_families": len(run["passed_families"]), **facts,
        })
    judged_keys = {(r["effort"], r["task"]) for r in rows}
    for effort, task in sorted(EMPTY_PATCH):
        solver, facts, run_dir = facts_by_key[effort, task]
        assert (run_dir / "final.patch").read_text().strip() == "" and (effort, task) not in judged_keys
        rows.append({"model": MODEL, "effort": effort, "task": task, "run_id": run_dir.name, "finished": True,
                     "functional": solver["scores"]["functional"], "duration_s": solver["duration_s"], "started_at": solver["started_at"],
                     "finished_at": solver["finished_at"], "evidence_sha256": None, "judged_under": None, "judged": JUDGED_NOTE["empty_patch"],
                     "status": "empty_patch", "scored_panels": [], "automated_quality": solver["scores"]["quality"],
                     "security": solver["scores"]["security"], "reviewed_score": None, "intent_recovery": None,
                     "intent_recovery_redistributed": None, "code_quality": None, "combined_33": None, "combined_no_code_zero": 0.0,
                     "combined_20_profile": None, "combined_single_judge": None, "panels": None, "passed_quirk_families": None, **facts})
    assert len(rows) == 115 and {(r["effort"], r["task"]) for r in rows} == set(found)
    rows.sort(key=lambda r: (EFFORTS.index(r["effort"]), r["task"]))
    assert Counter(r["status"] for r in rows) == {"published": 99, "no_source_change": 12, "empty_patch": 3, "unreviewable": 1}
    assert all(r["functional"] < 1 for r in rows if r["status"] in ("no_source_change", "empty_patch"))
    assert [r["functional"] for r in rows if r["status"] == "unreviewable"] == [1.0]  # hedgecore Max passed its tests; it counts as passed
    # Reflection's daily token limit: 13 Max runs finished before it stopped the sweep, the other 10 started after the reset.
    stop, restart = datetime.fromisoformat(LIMIT_STOP), datetime.fromisoformat(LIMIT_RESUME)
    maxes = [r for r in rows if r["effort"] == "max"]
    before = [r for r in maxes if datetime.fromisoformat(r["finished_at"]) < stop]
    assert len(before) == 13 and all(datetime.fromisoformat(r["started_at"]) >= restart for r in maxes if r not in before)
    assert all(datetime.fromisoformat(r["finished_at"]) < stop for r in rows if r["effort"] != "max")
    assert sum(behaviours.values()) == 231 and len(behaviours) == 23
    assert sum(r["failed_model_requests"] for r in rows) == 6 and sum(1 for r in rows if r["failed_model_requests"]) == 5
    assert failure_texts == {"The inference service is temporarily unavailable": 3, "520 <unknown status code>": 3}, failure_texts

    save("runs.json", {
        "runs": len(rows), "published": 99, "not_judged": {"no_source_change": 12, "empty_patch": 3, "unreviewable": 1}, "timeouts": 0,
        "weights": WEIGHTS, "code_quality_split": SPLIT_WITHOUT_L3, "judges": JUDGES,
        "judged_rule": "judged is \"published\" where the v3.28 summary publishes a Code quality score, the equal mean of the judges with a "
                       "valid review (scored_panels); every other row carries the reason it has none. status names the case",
        "no_code_rule": "combined_no_code_zero is the combined score with each run that left no code to judge (an empty patch or no "
                        "source change) counted as 0, as the board counts timeouts; for a judged run it equals combined_33, and the one "
                        "unreviewable run (max hedgecore) has none",
        "single_judge_rule": "combined_single_judge recomputes the combined score with Code quality from one judge's reviewed score and "
                             "intent recovery alone; it is a sensitivity figure, not the published score; null for a judge with no valid review",
        "intent_recovery_rule": "When a submission passed no quirk family, intent recovery has no denominator and its 9 points move to the "
                                "reviewed score for that submission (intent_recovery_redistributed); 16 published Beam runs needed it",
        "hidden_behaviour_fields": "hidden_behaviours counts the task's fail-to-pass hidden tests; hidden_behaviours_fixed counts those the run passed",
        "cost_fields": {"cost_usd": "null on every run: Reflection publishes no price for Beam"},
        "token_fields": {"raw_tokens": "input (cached included) plus output, summed over Mirror's per-call usage records",
                         "token_usage.output_tokens": "output tokens; Mirror reports no separate reasoning count",
                         "model_calls": "assistant records with usage in Mirror's conversation database",
                         "failed_model_requests": "model requests Mirror logged as failed and carried on from"},
        "model_identity": "harness-recorded: every inference in Mirror's conversation database names the requested model "
                          "(Beam-1.0-501B-A23B); Reflection's API also lists it under the alias Beam-501B-A23B",
        "rows": rows})

    def fmt(value, digits=4):
        return "" if value is None else f"{value:.{digits}f}"

    def pct(value):
        return None if value is None else 100 * value

    with (DEST / "runs.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "task", "run_id", "judged_under", "status", "combined_33", "combined_no_code_zero",
                         "combined_20_profile", "combined_muse_only", "combined_sol_only", "functional_pct", "automated_quality_pct",
                         "security_pct", "hidden_behaviours_fixed", "hidden_behaviours", "code_quality", "reviewed_score", "intent_recovery",
                         "muse_reviewed", "muse_readability", "muse_maintainability", "muse_intent_recovery",
                         "sol_reviewed", "sol_readability", "sol_maintainability", "sol_intent_recovery", "passed_quirk_families",
                         "model_calls", "failed_model_requests", "duration_s", "raw_tokens", "cached_input_tokens", "output_tokens",
                         "started_at", "finished_at", "solver_cli_version", "task_hash", "evidence_sha256"])
        for r in rows:
            p = r["panels"] or {q: {} for q in PANELS}
            single = r["combined_single_judge"] or {}
            writer.writerow([r["model"], r["effort"], r["task"], r["run_id"], r["judged_under"] or "", r["status"], fmt(r["combined_33"]),
                             fmt(r["combined_no_code_zero"]), fmt(r["combined_20_profile"]), fmt(single.get("muse")), fmt(single.get("sol")),
                             f'{100 * r["functional"]:.2f}', fmt(pct(r["automated_quality"]), 2), fmt(pct(r["security"]), 2),
                             r["hidden_behaviours_fixed"], r["hidden_behaviours"], fmt(r["code_quality"]), fmt(r["reviewed_score"]),
                             fmt(r["intent_recovery"]),
                             *[fmt(p[q].get(k)) for q in PANELS for k in ("reviewed_score", "readability", "maintainability", "intent_recovery")],
                             "" if r["passed_quirk_families"] is None else r["passed_quirk_families"], r["model_calls"],
                             r["failed_model_requests"], r["duration_s"], r["raw_tokens"], r["token_usage"]["cached_input_tokens"],
                             r["token_usage"]["output_tokens"], r["started_at"], r["finished_at"], r["solver_cli_version"], r["task_hash"],
                             r["evidence_sha256"] or ""])

    with (results / "beam-vs-frontier-card-efforts.csv").open(newline="") as source:
        table = {r["effort"]: r for r in csv.DictReader(source) if r["model"] == MODEL}
    groups = []
    for effort in EFFORTS:
        rs = [r for r in rows if r["effort"] == effort]
        judged = [r for r in rs if r["status"] == "published"]
        no_code = [r for r in rs if r["status"] in ("no_source_change", "empty_patch")]
        assert len(rs) == 23
        g = {
            "model": MODEL, "effort": effort, "n": len(judged), "runs": len(rs), "timeouts": 0,
            "not_judged": dict(sorted(Counter(r["status"] for r in rs if r["status"] != "published").items())),
            "not_judged_tasks": sorted(r["task"] for r in rs if r["status"] != "published"),
            "combined_33": mean_se(r["combined_33"] for r in judged),
            "combined_no_code_zero": mean_se(r["combined_no_code_zero"] for r in rs if r["combined_no_code_zero"] is not None) if no_code else None,
            "combined_20_profile": mean_se(r["combined_20_profile"] for r in judged),
            "combined_single_judge": {p: mean_se(r["combined_single_judge"][p] for r in judged if r["combined_single_judge"][p] is not None)
                                      for p in PANELS},
            "code_quality": mean_se(r["code_quality"] for r in judged), "reviewed_score": mean_se(r["reviewed_score"] for r in judged),
            "intent_recovery": mean_se(r["intent_recovery"] for r in judged if r["intent_recovery"] is not None),
            "intent_recovery_redistributed_runs": sum(r["intent_recovery_redistributed"] for r in judged),
            "single_judge_runs": sum(1 for r in judged if len(r["scored_panels"]) == 1),
            "readability": mean_se(statistics.mean(r["panels"][p]["readability"] for p in r["scored_panels"]) for r in judged),
            "maintainability": mean_se(statistics.mean(r["panels"][p]["maintainability"] for p in r["scored_panels"]) for r in judged),
            "by_panel": {p: mean_se(r["panels"][p]["reviewed_score"] for r in judged if p in r["scored_panels"]) for p in PANELS},
            "functional": mean_se(100 * r["functional"] for r in judged), "functional_all_runs": mean_se(100 * r["functional"] for r in rs),
            "automated_quality": mean_se(100 * r["automated_quality"] for r in judged), "security": mean_se(100 * r["security"] for r in judged),
            # passed counts judged runs; passed_all_runs counts all 23 and is the one to read.
            "passed": sum(r["functional"] == 1 for r in judged), "passed_all_runs": sum(r["functional"] == 1 for r in rs),
            "hidden_behaviours_fixed": sum(r["hidden_behaviours_fixed"] for r in rs), "hidden_behaviours": sum(r["hidden_behaviours"] for r in rs),
            # Runtime and tokens are facts of the sweep and cover every run, as on the harness card.
            "minutes": mean_se(r["duration_s"] / 60 for r in rs), "minutes_median": statistics.median(r["duration_s"] / 60 for r in rs),
            "priced_runs": 0, "cli_versions": {CLI_LABEL: len(rs)},
            "raw_tokens": mean_se(r["raw_tokens"] for r in rs), "raw_tokens_total": sum(r["raw_tokens"] for r in rs),
            "output_tokens": mean_se(r["token_usage"]["output_tokens"] for r in rs),
            "cached_input_share": mean_se(r["token_usage"]["cached_input_tokens"] / r["token_usage"]["input_tokens"] for r in rs),
            "model_calls": mean_se(r["model_calls"] for r in rs), "failed_model_requests": sum(r["failed_model_requests"] for r in rs),
            "usd": None,
        }
        # The round's own summary aggregates this level; it must match exactly.
        entry = summary["groups"][f"{MODEL}/{effort}"]
        assert g["n"] == entry["n"] == entry["composite_v3"]["n"] and g["intent_recovery_redistributed_runs"] == entry["l2_redistributed"]
        for field, key in (("combined_33", "composite_v3"), ("code_quality", "code_quality"), ("reviewed_score", "l1"), ("intent_recovery", "l2")):
            assert g[field]["n"] == entry[key]["n"], (effort, field)
            assert abs(g[field]["mean"] - entry[key]["mean"]) < 1e-9 and abs(g[field]["se"] - entry[key]["se"]) < 1e-9, (effort, field)
        for p in PANELS:
            assert g["by_panel"][p]["n"] == entry["by_panel"][p]["n"]
            assert abs(g["by_panel"][p]["mean"] - entry["by_panel"][p]["mean"]) < 1e-9 and abs(g["by_panel"][p]["se"] - entry["by_panel"][p]["se"]) < 1e-9
        # The harness card's per-level table carries the same figures.
        t = table[effort]
        assert (int(t["n"]), int(t["judged"]), int(t["passed"])) == (g["runs"], g["n"], g["passed_all_runs"]), effort
        for column, value in (("combined", g["combined_33"]["mean"]), ("combined_se", g["combined_33"]["se"]),
                              ("code_quality", g["code_quality"]["mean"]), ("minutes", g["minutes"]["mean"])):
            assert abs(float(t[column]) - value) <= 5e-5, (effort, column)
        assert t["usd_per_task"] == "", effort
        groups.append(g)
    assert [g["n"] for g in groups] == [11, 20, 23, 23, 22]
    assert [g["not_judged"] for g in groups] == [{"empty_patch": 2, "no_source_change": 10}, {"empty_patch": 1, "no_source_change": 2}, {}, {},
                                                 {"unreviewable": 1}]
    assert [g["passed_all_runs"] for g in groups] == [0, 0, 0, 4, 6]
    assert [round(g["combined_33"]["mean"], 2) for g in groups] == [39.51, 44.79, 55.01, 64.72, 63.92]
    assert [None if g["combined_no_code_zero"] is None else round(g["combined_no_code_zero"]["mean"], 2) for g in groups] == [18.90, 38.95, None, None, None]
    assert [g["combined_no_code_zero"]["n"] for g in groups[:2]] == [23, 23]
    assert [round(g["functional_all_runs"]["mean"], 1) for g in groups] == [0.9, 10.8, 35.6, 56.5, 58.3]
    assert [f'{g["minutes"]["mean"]:.1f}' for g in groups] == ["0.4", "1.9", "9.2", "18.8", "22.4"]
    assert [f'{g["raw_tokens"]["mean"] / 1e6:.2f}' for g in groups] == ["0.09", "0.44", "3.39", "12.42", "17.29"]
    assert [g["hidden_behaviours"] for g in groups] == [231] * 5
    assert [g["single_judge_runs"] for g in groups] == [0, 0, 0, 0, 1]
    save("groups.json", groups)

    with SCORES.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "effort", "n", "runs", "not_judged", "combined_33", "combined_33_se", "combined_no_code_zero", "combined_20_profile",
                         "combined_muse_only", "combined_sol_only", "code_quality", "code_quality_se", "reviewed_score", "intent_recovery",
                         "readability", "maintainability", "muse_reviewed", "sol_reviewed", "functional", "functional_all_runs",
                         "automated_quality", "security", "passed_of_23", "hidden_behaviours_fixed", "hidden_behaviours", "mean_minutes",
                         "mean_minutes_se", "median_minutes", "mean_raw_tokens", "mean_output_tokens", "mean_usd", "cli_version"])
        for g in groups:
            writer.writerow([NAMES[g["model"]], g["effort"], g["n"], g["runs"], g["runs"] - g["n"], f'{g["combined_33"]["mean"]:.4f}',
                             f'{g["combined_33"]["se"]:.4f}', fmt(g["combined_no_code_zero"] and g["combined_no_code_zero"]["mean"]),
                             f'{g["combined_20_profile"]["mean"]:.4f}', f'{g["combined_single_judge"]["muse"]["mean"]:.4f}',
                             f'{g["combined_single_judge"]["sol"]["mean"]:.4f}', f'{g["code_quality"]["mean"]:.4f}', f'{g["code_quality"]["se"]:.4f}',
                             f'{g["reviewed_score"]["mean"]:.4f}', f'{g["intent_recovery"]["mean"]:.4f}', f'{g["readability"]["mean"]:.4f}',
                             f'{g["maintainability"]["mean"]:.4f}', f'{g["by_panel"]["muse"]["mean"]:.4f}', f'{g["by_panel"]["sol"]["mean"]:.4f}',
                             f'{g["functional"]["mean"]:.4f}', f'{g["functional_all_runs"]["mean"]:.4f}', f'{g["automated_quality"]["mean"]:.4f}',
                             f'{g["security"]["mean"]:.4f}', g["passed_all_runs"], g["hidden_behaviours_fixed"], g["hidden_behaviours"],
                             f'{g["minutes"]["mean"]:.4f}', f'{g["minutes"]["se"]:.4f}', f'{g["minutes_median"]:.4f}', f'{g["raw_tokens"]["mean"]:.1f}',
                             f'{g["output_tokens"]["mean"]:.1f}', "", CLI_LABEL])

    totals = {MODEL: {"runs": len(rows), "raw_tokens": sum(r["raw_tokens"] for r in rows), "model_calls": sum(r["model_calls"] for r in rows),
                      "failed_model_requests": sum(r["failed_model_requests"] for r in rows),
                      "solver_hours": sum(r["duration_s"] for r in rows) / 3600, "usd": None}}
    save("economics.json", {
        "scope": "Solver inference only. Reflection publishes no price for Beam (its public API beta is free to start), so no run is "
                 "priced: cost is unavailable, not zero. Tokens and minutes are reported instead. Judging is excluded.",
        "pricing": None,
        "groups": [{"model": g["model"], "effort": g["effort"], "n": g["runs"], "usd": None, "raw_tokens": g["raw_tokens"],
                    "raw_tokens_total": g["raw_tokens_total"], "output_tokens": g["output_tokens"], "cached_input_share": g["cached_input_share"],
                    "model_calls": g["model_calls"], "failed_model_requests": g["failed_model_requests"], "minutes": g["minutes"]}
                   for g in groups],
        "totals": totals,
        "limitations": [
            "No list price exists for Beam, so the board shows Beam on its tokens and minutes views only.",
            "Tokens are summed from Mirror's per-call usage records; cached input is a subset of input, and Mirror reports no separate "
            "reasoning count.",
            "Six model requests in five runs failed (three \"temporarily unavailable\", three HTTP 520) and Mirror carried on; they "
            "report no usage.",
            "Tokens and minutes cover all 23 runs at every level, judged or not.",
        ],
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

    expected_markers = {(p, "primary", s): "no_source_change" for p in PANELS for s in NO_SOURCE}
    expected_markers.update({("muse", "primary", UNREVIEWABLE): "invalidate_unrecoverable_primary",
                             ("sol", "primary", UNREVIEWABLE): "input_over_judge_limit", ("sol", "probe", UNREVIEWABLE): "input_over_judge_limit",
                             ("sol", "primary", "submission-005"): "input_over_judge_limit"})
    assert {k: v["rule"] for k, v in markers.items()} == expected_markers
    assert counts == {"muse": {"calibration": 80, "match": 112, "pairwise": 10, "primary": 112, "probe": 112, "repeat": 5},
                      "sol": {"calibration": 80, "match": 111, "pairwise": 10, "primary": 112, "probe": 112, "repeat": 5}}, counts
    assert retries == {"muse": 2, "sol": 39}, retries
    assert [(p, s) for p, s, _, _ in reviews] == [("sol", "primary")] * 3 and all("429" in f for *_, f in reviews)
    assert len(recoveries) == 24 and all((p, s) == ("sol", "match") for p, s, _, _ in recoveries), recoveries
    assert all(rec["method"] == "one-based departure indexes moved to zero-based; statuses untouched" and rec["source_attempt"] == 1
               for *_, rec in recoveries)
    assert window[0].startswith("2026-10-25T04:31") and window[1].startswith("2026-10-25T20:21")
    save("judge-protocols.json", {
        "scored_panel": {p: public_settings(protocol["reviewers"][p]) for p in PANELS},
        "judge_names": JUDGES,
        "protocol_id": PROTOCOL_ID, "protocol_sha256": digest(out / "protocol.json"),
        "seat": "Grok 4.6 holds the usual second seat but judges through Cursor, whose account was still out of usage on 2026-10-24; the "
                "owner kept GPT-6.1 Sol in the seat, the pair v3.27 used for DeepSeek V4.1 Flash. Both judges retook the exam under v3.28 "
                "before any counted call.",
        "same_as_v327": "rubric, system text, pair, probe and match instructions, schemas, seed, repeats, gate allowance, weights, retry rule, "
                        "control hashes, and both judges' model, effort and binary pins equal the published v3.27 record",
        "amends": protocol["amends"], "system": protocol["system"], "rubric": protocol["rubric"],
        "pair_instruction": protocol["pair_instruction"], "probe_instruction": protocol["probe_instruction"],
        "match_instruction": protocol["match_instruction"], "schemas": protocol["schemas"], "weights": protocol["weights"],
        "gate_allowance": protocol["gate_allowance"], "repeats": protocol["repeats"], "seed": protocol["seed"],
        "single_panel_rule": protocol["single_panel_rule"], "invalid_response_retries": protocol["invalid_response_retries"],
        "comparability": protocol["comparability"], "control_source_hashes": protocol["control_source_hashes"],
        "population": {"description": protocol["population"]["description"], "cells": protocol["population"]["cells"],
                       "excluded": [{k: v for k, v in x.items() if k != "reason"} | {"reason": "empty patch"}
                                    for x in protocol["population"]["excluded"]],
                       "missing": protocol["population"]["missing"]},
        "planned_calls": protocol["planned_calls"],
        "judge_pins": {
            "muse": {"cli": "Muse CLI", "sha256": muse["binary_sha256"], "settings_source": pins["muse_settings_source"],
                     "note": "a byte-identical backup of the v3.4 binary, because Muse Code's updater removed the original copy; re-hashed before every stage"},
            "sol": {"cli": "Codex", "version": pins["codex"]["version"], "launcher_sha256": pins["codex"]["launcher"]["sha256"],
                    "native_sha256": pins["codex"]["native"]["sha256"], "rule": pins["codex"]["rule"]},
        },
        "counted_calls": counts, "second_attempts": retries,
        "operator_markers": [{"panel": p, "stage": s, "submission": i, "rule": m["rule"],
                              **{k: m[k] for k in ("reason", "effect", "owner_decision") if k in m}}
                             for (p, s, i), m in sorted(markers.items())],
        "transport_reviews": [{"panel": p, "stage": s, "submission": i, "finding": f,
                               "action": "one fresh attempt under the protocol's single-retry rule; the failed receipt is kept"}
                              for p, s, i, f in reviews],
        "operator_recoveries": [{"panel": p, "stage": s, "submission": i, "rule": "recover_one_based_indexes", "method": rec["method"],
                                 "source_attempt": rec["source_attempt"],
                                 "condition": "both attempts failed the index range check, every cited index lay in 1..count and the "
                                              "highest equalled count; the shifted result must then validate",
                                 "score_effect": "none: intent scoring reads match statuses only"} for p, s, i, rec in recoveries],
        "judging_window_utc": {"first_call_completed": window[0], "last_call_completed": window[1],
                               "summary_generated": summary["generated_at"]},
    })

    # The card is copied byte for byte from the harness.
    for name, target in CARDS.items():
        assert target.read_bytes() == (results / name).read_bytes(), name
    card = read(results / "beam-vs-frontier-card.json")
    assert card["final"] and card["sources"]["v3.28_summary_sha256"] == digest(out / "summary.json")
    assert card["png_sha256"] == digest(results / "beam-vs-frontier-card.png") and card["best"][MODEL] == "extra-high"

    save("provenance.json", {
        "source_artifacts_sha256": {
            **{f"v3.28/{f}": digest(out / f) for f in ("summary.json", "protocol.json", "private-manifest.json", "calibration-muse.json",
                                                       "calibration-sol.json")},
            **{f"v3.28/calls/{p}/{s}/{i}/operator-invalid.json": digest(out / "calls" / p / s / i / "operator-invalid.json")
               for (p, s, i) in sorted(markers)},
            **{name: digest(results / name) for name in ("comparison.json", "beam-vs-frontier-card-efforts.csv", "beam-vs-frontier-card.json",
                                                         "beam-vs-frontier-card.png")},
            **{Path(c).name: digest(root / c) for c in COMPARATORS},
            "suite.lock.json": digest(root / LOCK),
            "beam-mirror.launch.sh": digest(root / LAUNCHER),
            "beam-mirror-resume.sh": digest(root / RESUME),
        },
        "export_checks": ["115 solver summaries in the sweep folder, 23 per level, no task twice; the 1,200 attempts cut short by "
                          "Reflection's daily token limit hold no summary and are not part of the population",
                          "every run is mirror:Beam-1.0-501B-A23B at its requested level (Extra high as xhigh) on Mirror CLI 0.1.1, the "
                          "install tree hash equal to the pin, a private Mirror home with only the run workspace trusted and analytics off, "
                          "from bench/2026-10-23-beam-mirror-frontier-v4 with a clean source block and every task hash equal to the frozen "
                          "suite lock",
                          "every integrity audit: no web, no benchmark data or answer-key paths, not contaminated",
                          "each run's token totals equal its mirror_usage receipt; no run records a cost",
                          "the population record's hash and the manifest's hash equal the ones frozen in the protocol, and every judged "
                          "run's summary hash equals its manifest entry",
                          "rubric, prompts, schemas, seed, repeats, gate allowance, weights, retry rule, control hashes and both judges' "
                          "pins equal the published v3.27 record",
                          "both judges passed calibration under v3.28 with no failing gate and no allowance used; no reviewer fallback; "
                          "every operator marker accounted for: twelve no_source_change pairs, the two input_over_judge_limit runs and "
                          "Muse's unrecoverable hedgecore review; three transport retries; 24 GPT-6.1 Sol answer-key matches recovered "
                          "under recover_one_based_indexes",
                          "per-row Code quality and both combined scores recomputed and matched to the frozen summary, with intent "
                          "recovery redistributed where no quirk family passed; each level's means and standard errors, per-judge means "
                          "included, matched to the summary's groups",
                          "combined score, its standard error, Code quality, tasks passed and minutes per level matched to the harness "
                          "card table; the card is byte-identical to the harness copy and its record names this summary",
                          "the sweep's overlap logger recorded no other benchmark job; no dashes or host paths in exported text"],
        "limits": ["Reflection Beam is judged by Muse Spark 1.3 and GPT-6.1 Sol, the pair v3.27 used for DeepSeek V4.1 Flash, not by Muse "
                   "Spark 1.3 and Grok 4.6 like most Frontier v4 columns (Claude Opus 5.5, GPT-6.1 Sol and GPT-6 Astra included): Grok "
                   "4.6's Cursor account was out of usage. Scores from different panels are not calibrated against each other.",
                   "GPT-6.1 Sol rates Beam's reviewed Code quality 10.1 to 17.6 points above Muse Spark 1.3. The published score is their "
                   "mean; combined_single_judge gives each judge alone.",
                   "GPT-6.1 Sol judged these runs and is also a compared model on the card and the board; its own column comes from its "
                   "own round, judged by Muse Spark 1.3 and Grok 4.6.",
                   "16 runs are not judged: 15 left no code to review (three empty patches, twelve that changed no source file) and "
                   "count as failed tasks; Max hedgecore passed every hidden test but its evidence could not be reviewed by either judge. The combined score is over "
                   "the judged runs (11, 20, 23, 23 and 22 from Low to Max); combined_no_code_zero counts the 15 as 0 (18.90 at Low, "
                   "38.95 at Medium). Max payrollcore is published from Muse Spark 1.3 alone.",
                   "Reflection publishes no Beam price, so no cost is reported.",
                   "Model identity is harness-recorded: Mirror's conversation database names the requested model on every inference.",
                   "Mirror CLI 0.1.1 is an early beta, pinned by exact version and install tree hash; it cannot pin what Reflection's "
                   "API serves under the model id.",
                   "Task files are staged without execute bits, as for every column; where Beam met Permission denied on the legacy "
                   "binary, Mirror appended a note calling it a sandbox denial, and two Low runs ended believing the sandbox blocked "
                   "the binary. The adapter archived model messages and usage but not tool calls, so how often Beam saw the note "
                   "cannot be counted.",
                   "Reflection's daily API token limit stopped the sweep after 13 Max tasks on 2026-10-24; the 1,200 attempts it cut "
                   "short were set aside unscored and the sweep resumed after the 00:00 UTC reset. No finished run was affected.",
                   "Frontier Code quality is the reviewed layer plus intent recovery and is never compared with Routine v1 Code quality.",
                   "One attempt per task and level, on the owner's Mac, local sandbox, flat 3-hour task bound, one task at a time."],
        "publication_scope": "Per-run scores, per-panel sub-scores, aggregates, judge protocol text, calibration verdicts and control means, "
                             "integrity-audit verdicts, raw tokens, model calls and failed requests.",
        "withheld": ["raw prompts and responses", "submitted patches and reconstructed sources", "quirk answer keys (they describe hidden-test behaviour)",
                     "reviewer session identifiers and usage receipts", "Mirror conversation databases and solver traces",
                     "the 1,200 attempts cut short by the daily token limit", "host binary paths"],
        "integrity_limit": "Hash checks bind the export to frozen files; they do not prove that judges were unbiased or that no training overlap exists.",
    })
    print(DEST, len(rows), "runs;", len(groups), "groups")


if __name__ == "__main__":
    main()
